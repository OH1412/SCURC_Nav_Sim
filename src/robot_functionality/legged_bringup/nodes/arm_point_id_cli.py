#!/usr/bin/env python3
"""终端输入点位编号 (0~15)，自动判断抓取/放置并执行，打印 arm_root 目标与 ACK。"""

from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path
from typing import Any

import rclpy
import yaml
from ament_index_python.packages import get_package_share_directory
from legged_mission_bt.msg import ArmPoseRequest, ArmWaypoint
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from std_msgs.msg import Float64MultiArray, UInt8MultiArray

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mission_log_client import log_event

PICK_MIN, PICK_MAX = 0, 7
PLACE_MIN, PLACE_MAX = 8, 15
ALL_MIN, ALL_MAX = 0, 15

ARM_ACTION_PICK = 1
ARM_ACTION_PLACE = 2
ARM_ACK_PICK_STATE = 0x01
ARM_ACK_PLACE_STATE = 0x02
ARM_ACK_OK = 0x00

STATE_CN = {
    ARM_ACK_PICK_STATE: 'PICK完成',
    ARM_ACK_PLACE_STATE: 'PLACE完成',
}
RESULT_CN = {ARM_ACK_OK: '成功', 0x01: '失败'}


def _action_for_point(point_id: int) -> tuple[int, int, str]:
    if PICK_MIN <= point_id <= PICK_MAX:
        return ARM_ACTION_PICK, ARM_ACK_PICK_STATE, '抓取'
    return ARM_ACTION_PLACE, ARM_ACK_PLACE_STATE, '放置'


def _serial_xy(x_mm: float, y_mm: float) -> tuple[float, float]:
    return -x_mm, -y_mm


def _format_report(
    *,
    action_name: str,
    point_id: int,
    label: str,
    wp: ArmWaypoint,
    action_code: int,
) -> str:
    sx, sy = _serial_xy(wp.x, wp.y)
    payload = [wp.x, wp.y, wp.z, wp.yaw, float(action_code)]
    lines = [
        '-' * 68,
        f'  {action_name} — 点位 {point_id} ({label})',
        (
            f'  arm_root 目标 (mm/rad): '
            f'x={wp.x:.2f}  y={wp.y:.2f}  z={wp.z:.2f}  yaw={wp.yaw:.4f}'
        ),
        (
            f'  /arm_command 发送数据: '
            f'[x={payload[0]:.2f}, y={payload[1]:.2f}, z={payload[2]:.2f}, '
            f'yaw={payload[3]:.4f}, action={int(payload[4])}]'
        ),
        (
            f'  串口实际 XY (driver 取反): '
            f'x={sx:.2f}  y={sy:.2f}  z={wp.z:.2f}  yaw={wp.yaw:.4f}'
        ),
        '-' * 68,
    ]
    return '\n'.join(lines)


class ArmPointIdCli(Node):
    def __init__(self) -> None:
        super().__init__('arm_point_id_cli')

        default_arm_points = os.path.join(
            get_package_share_directory('legged_bringup'),
            'params',
            'arm_points.yaml',
        )
        self.declare_parameter('arm_points_file', default_arm_points)
        self.declare_parameter('arm_timeout', 30.0)
        self.declare_parameter('waypoint_wait_timeout', 120.0)
        self.declare_parameter('arm_command_topic', '/arm_command')
        self.declare_parameter('arm_status_topic', '/arm_status')
        self.declare_parameter('arm_pose_request_topic', '/mission_bt/arm_pose_request')
        self.declare_parameter('arm_waypoint_topic', '/mission_bt/arm_waypoint')
        self.declare_parameter('arm_republish_interval', 0.01)

        self._arm_timeout = float(self.get_parameter('arm_timeout').value)
        self._waypoint_wait_timeout = float(
            self.get_parameter('waypoint_wait_timeout').value
        )
        self._republish_interval = float(
            self.get_parameter('arm_republish_interval').value
        )
        cmd_topic = str(self.get_parameter('arm_command_topic').value)
        status_topic = str(self.get_parameter('arm_status_topic').value)
        request_topic = str(self.get_parameter('arm_pose_request_topic').value)
        waypoint_topic = str(self.get_parameter('arm_waypoint_topic').value)

        self._catalog = self._load_catalog(
            str(self.get_parameter('arm_points_file').value)
        )

        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
        self._cmd_pub = self.create_publisher(Float64MultiArray, cmd_topic, qos)
        self._request_pub = self.create_publisher(ArmPoseRequest, request_topic, qos)
        self.create_subscription(ArmWaypoint, waypoint_topic, self._on_waypoint, qos)
        self.create_subscription(UInt8MultiArray, status_topic, self._on_arm_status, qos)

        self._busy = False
        self._pending_point_id: int | None = None
        self._pending_ack_state: int | None = None
        self._waypoint: ArmWaypoint | None = None
        self._waypoint_event = threading.Event()
        self._ack_event = threading.Event()
        self._ack_ok = False
        self._action_lock = threading.Lock()

    def _load_catalog(self, path: str) -> dict[int, dict[str, Any]]:
        catalog: dict[int, dict[str, Any]] = {}
        if path and os.path.isfile(path):
            with open(path, encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            for key, entry in (data.get('arm_points') or {}).items():
                slot = int(key)
                if not (ALL_MIN <= slot <= ALL_MAX):
                    continue
                role = entry.get('role', 'pick' if slot <= PICK_MAX else 'place')
                catalog[slot] = {
                    'role': role,
                    'label': entry.get(
                        'label',
                        f'{"抓取" if role == "pick" else "放置"}点 {slot}',
                    ),
                }
        for slot in range(ALL_MIN, ALL_MAX + 1):
            catalog.setdefault(
                slot,
                {
                    'role': 'pick' if slot <= PICK_MAX else 'place',
                    'label': (
                        f'抓取点 {slot + 1}'
                        if slot <= PICK_MAX
                        else f'放置点 {slot - PLACE_MIN + 1}'
                    ),
                },
            )
        return catalog

    def _on_waypoint(self, msg: ArmWaypoint) -> None:
        if self._pending_point_id is None:
            return
        if msg.id != str(self._pending_point_id):
            return
        self._waypoint = msg
        self._waypoint_event.set()

    def _on_arm_status(self, msg: UInt8MultiArray) -> None:
        if len(msg.data) < 2 or self._pending_ack_state is None:
            return
        state, result = int(msg.data[0]), int(msg.data[1])
        if state != self._pending_ack_state:
            return
        if self._ack_event.is_set():
            return
        self._ack_ok = result == ARM_ACK_OK
        self._ack_event.set()

    def _wait_for_cmd_subscriber(self, timeout_sec: float = 5.0) -> bool:
        deadline = time.monotonic() + timeout_sec
        while rclpy.ok() and time.monotonic() < deadline:
            if self._cmd_pub.get_subscription_count() > 0:
                return True
            time.sleep(0.05)
        return self._cmd_pub.get_subscription_count() > 0

    def execute_point(self, point_id: int) -> bool:
        with self._action_lock:
            if self._busy:
                print('  忙碌中，请等待当前动作完成', flush=True)
                return False
            self._busy = True

        action_code, ack_state, action_name = _action_for_point(point_id)
        label = self._catalog[point_id].get('label', f'点位 {point_id}')

        self._pending_point_id = point_id
        self._pending_ack_state = ack_state
        self._waypoint = None
        self._waypoint_event.clear()
        self._ack_event.clear()
        self._ack_ok = False

        log_event(
            self,
            'arm_point_id_cli',
            'ARM_POINT_REQUESTED',
            f'action={action_name} arm_point_id={point_id} label={label}',
        )

        req = ArmPoseRequest()
        req.arm_point_id = point_id
        req.nav_id = ''
        self._request_pub.publish(req)

        if not self._waypoint_event.wait(timeout=self._waypoint_wait_timeout):
            print(f'  ✗ 等待 arm_waypoint 超时 (点位 {point_id})', flush=True)
            self._busy = False
            self._pending_point_id = None
            self._pending_ack_state = None
            return False

        wp = self._waypoint
        assert wp is not None
        print(_format_report(
            action_name=action_name,
            point_id=point_id,
            label=label,
            wp=wp,
            action_code=action_code,
        ), flush=True)

        if not self._wait_for_cmd_subscriber():
            print(f'  ✗ /arm_command 无订阅者 (串口节点未就绪?)', flush=True)
            self._busy = False
            self._pending_point_id = None
            self._pending_ack_state = None
            return False

        cmd_xyza = [wp.x, wp.y, wp.z, wp.yaw, float(action_code)]
        deadline = time.monotonic() + self._arm_timeout
        sent_once = False

        while rclpy.ok() and time.monotonic() < deadline:
            if not self._ack_event.is_set():
                if self._cmd_pub.get_subscription_count() > 0:
                    msg = Float64MultiArray()
                    msg.data = cmd_xyza
                    self._cmd_pub.publish(msg)
                    if not sent_once:
                        sent_once = True
                        print(
                            f'  >> 已发送 /arm_command ({action_name})',
                            flush=True,
                        )
            else:
                break
            time.sleep(self._republish_interval)

        if not self._ack_event.is_set():
            print(f'  ✗ {action_name} 点位 {point_id} 超时：未收到 ACK', flush=True)
            self._busy = False
            self._pending_point_id = None
            self._pending_ack_state = None
            return False

        state = self._pending_ack_state
        result = ARM_ACK_OK if self._ack_ok else 0x01
        print(
            f'  << ACK: state=0x{state:02X} ({STATE_CN.get(state, "未知")}) '
            f'result=0x{result:02X} ({RESULT_CN.get(result, "未知")})',
            flush=True,
        )
        if self._ack_ok:
            print(f'  ✓ {action_name} 点位 {point_id} 完成\n', flush=True)
            log_event(
                self,
                'arm_point_id_cli',
                'ARM_ACK_SUCCESS',
                f'action={action_name} arm_point_id={point_id}',
            )
            ok = True
        else:
            print(f'  ✗ {action_name} 点位 {point_id} 失败\n', flush=True)
            log_event(
                self,
                'arm_point_id_cli',
                'ARM_ACK_FAILURE',
                f'action={action_name} arm_point_id={point_id}',
                level='ERROR',
            )
            ok = False

        self._busy = False
        self._pending_point_id = None
        self._pending_ack_state = None
        return ok


def _stdin_loop(node: ArmPointIdCli) -> None:
    print('=' * 68, flush=True)
    print('  机械臂点位联调 — 输入点位编号', flush=True)
    print('  0~7  = 抓取    8~15 = 放置', flush=True)
    print('  示例: 3        示例: 9', flush=True)
    print('  退出: q', flush=True)
    print('=' * 68 + '\n', flush=True)

    try:
        while rclpy.ok():
            line = input('点位> ').strip()
            if not line:
                continue
            if line.lower() in ('q', 'quit', 'exit'):
                break
            try:
                point_id = int(line)
            except ValueError:
                print('  请输入整数编号', flush=True)
                continue
            if not (ALL_MIN <= point_id <= ALL_MAX):
                print(f'  无效编号，范围 {ALL_MIN}~{ALL_MAX}', flush=True)
                continue
            _, _, action_name = _action_for_point(point_id)
            print(f'  → 执行 {action_name} 点位 {point_id}', flush=True)
            node.execute_point(point_id)
    except (KeyboardInterrupt, EOFError):
        pass


def main() -> None:
    rclpy.init()
    node = ArmPointIdCli()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)

    stdin_thread = threading.Thread(target=_stdin_loop, args=(node,), daemon=True)
    stdin_thread.start()

    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
