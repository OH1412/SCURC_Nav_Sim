#!/usr/bin/env python3
"""手柄 X 键交替抓取/放置：每次按下选距离最近的抓取点或放置点。

第 1 次 X → 最近抓取点 (0~7)
第 2 次 X → 最近放置点 (8~15)
之后交替循环。

坐标详情发布到 /interactive_arm/coord_report，由 arm_coord_monitor 在独立终端显示。
"""

from __future__ import annotations

import math
import sys
import threading
import time
from pathlib import Path
from typing import Any

import rclpy
import yaml
from geometry_msgs.msg import Quaternion
from legged_mission_bt.msg import ArmPoseRequest, ArmWaypoint
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Joy
from std_msgs.msg import Float64MultiArray, String, UInt8MultiArray

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mission_log_client import log_event

PICK_MIN, PICK_MAX = 0, 7
PLACE_MIN, PLACE_MAX = 8, 15

ARM_ACTION_PICK = 1
ARM_ACTION_PLACE = 2
ARM_ACK_PICK_STATE = 0x01
ARM_ACK_PLACE_STATE = 0x02
ARM_ACK_OK = 0x00


def yaw_from_quaternion(q: Quaternion) -> float:
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


def normalize_angle(angle: float) -> float:
    while angle > math.pi:
        angle -= 2.0 * math.pi
    while angle < -math.pi:
        angle += 2.0 * math.pi
    return angle


def compose_aft_to_base_in_init(
    aft: dict[str, float],
    static: dict[str, float],
) -> dict[str, float]:
    ax = float(aft['x'])
    ay = float(aft['y'])
    az = float(aft.get('z', 0.0))
    ayaw = float(aft['yaw'])

    tx = float(static['x'])
    ty = float(static['y'])
    tz = float(static.get('z', 0.0))
    syaw = float(static.get('yaw', 0.0))

    c, s = math.cos(ayaw), math.sin(ayaw)
    bx = ax + c * tx - s * ty
    by = ay + s * tx + c * ty
    bz = az + tz
    byaw = normalize_angle(ayaw + syaw)
    return {'x': bx, 'y': by, 'z': bz, 'yaw': byaw}


def _action_for_point(point_id: int) -> tuple[int, int, str]:
    if PICK_MIN <= point_id <= PICK_MAX:
        return ARM_ACTION_PICK, ARM_ACK_PICK_STATE, '抓取'
    return ARM_ACTION_PLACE, ARM_ACK_PLACE_STATE, '放置'


def _serial_xy(x_mm: float, y_mm: float) -> tuple[float, float]:
    return -x_mm, -y_mm


def _format_arm_coords(
    *,
    action_name: str,
    point_id: int,
    label: str,
    wp: ArmWaypoint,
    action_code: int,
    dist_m: float | None = None,
) -> str:
    sx, sy = _serial_xy(wp.x, wp.y)
    lines = [
        '-' * 68,
        f'  机械臂坐标 — {action_name} 点位 {point_id} ({label})',
    ]
    if dist_m is not None:
        lines.append(f'  距机器人 map 平面距离: {dist_m:.3f} m')
    lines.extend([
        (
            f'  arm_waypoint (arm_root, mm/rad): '
            f'x={wp.x:.2f}  y={wp.y:.2f}  z={wp.z:.2f}  yaw={wp.yaw:.4f}'
        ),
        (
            f'  /arm_command  payload: '
            f'[x={wp.x:.2f}, y={wp.y:.2f}, z={wp.z:.2f}, yaw={wp.yaw:.4f}, action={action_code}]'
        ),
        (
            f'  串口实际 XY (driver 取反): '
            f'x={sx:.2f}  y={sy:.2f}  z={wp.z:.2f}  yaw={wp.yaw:.4f}'
        ),
        '-' * 68,
    ])
    return '\n'.join(lines)


class InteractiveArmPick(Node):
    def __init__(self) -> None:
        super().__init__('interactive_arm_pick')

        self.declare_parameter('arm_points_file', '')
        self.declare_parameter('arm_timeout', 30.0)
        self.declare_parameter('waypoint_wait_timeout', 120.0)
        self.declare_parameter('arm_command_topic', '/arm_command')
        self.declare_parameter('arm_status_topic', '/arm_status')
        self.declare_parameter('arm_pose_request_topic', '/mission_bt/arm_pose_request')
        self.declare_parameter('arm_waypoint_topic', '/mission_bt/arm_waypoint')
        self.declare_parameter('coord_report_topic', '/interactive_arm/coord_report')
        self.declare_parameter('joy_topic', '/joy')
        self.declare_parameter('joy_button_index', 3)
        self.declare_parameter('odom_topic', '/aft_mapped_to_init')
        self.declare_parameter('aft_to_base_link.x', -0.21368)
        self.declare_parameter('aft_to_base_link.y', 0.0)
        self.declare_parameter('aft_to_base_link.z', -0.12978)
        self.declare_parameter('aft_to_base_link.yaw', 0.05)

        self._arm_timeout = float(self.get_parameter('arm_timeout').value)
        self._waypoint_wait_timeout = float(self.get_parameter('waypoint_wait_timeout').value)
        cmd_topic = str(self.get_parameter('arm_command_topic').value)
        status_topic = str(self.get_parameter('arm_status_topic').value)
        request_topic = str(self.get_parameter('arm_pose_request_topic').value)
        waypoint_topic = str(self.get_parameter('arm_waypoint_topic').value)
        coord_topic = str(self.get_parameter('coord_report_topic').value)
        joy_topic = str(self.get_parameter('joy_topic').value)
        self._joy_button = int(self.get_parameter('joy_button_index').value)
        odom_topic = str(self.get_parameter('odom_topic').value)

        self._aft_to_base = {
            'x': float(self.get_parameter('aft_to_base_link.x').value),
            'y': float(self.get_parameter('aft_to_base_link.y').value),
            'z': float(self.get_parameter('aft_to_base_link.z').value),
            'yaw': float(self.get_parameter('aft_to_base_link.yaw').value),
        }

        self._catalog = self._load_catalog(str(self.get_parameter('arm_points_file').value))

        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
        self._cmd_pub = self.create_publisher(Float64MultiArray, cmd_topic, qos)
        self._request_pub = self.create_publisher(ArmPoseRequest, request_topic, qos)
        self._coord_pub = self.create_publisher(String, coord_topic, qos)
        self.create_subscription(ArmWaypoint, waypoint_topic, self._on_waypoint, qos)
        self.create_subscription(UInt8MultiArray, status_topic, self._on_status, qos)
        self.create_subscription(Odometry, odom_topic, self._on_odom, 10)
        self.create_subscription(Joy, joy_topic, self._on_joy, 10)

        self._busy = False
        self._next_is_pick = True
        self._last_joy_pressed = False
        self._robot_xy: tuple[float, float] | None = None
        self._pending_point_id: int | None = None
        self._pending_ack_state: int | None = None
        self._pending_dist_m: float | None = None
        self._waypoint: ArmWaypoint | None = None
        self._waypoint_event = threading.Event()
        self._ack_event = threading.Event()
        self._ack_ok = False
        self._action_lock = threading.Lock()

        self.get_logger().info(
            'X 键交替抓取/放置已就绪：第1次=最近抓取点，第2次=最近放置点，之后循环')
        self.get_logger().info(
            f'joy 话题={joy_topic} 按钮索引={self._joy_button}  '
            f'坐标输出话题={coord_topic}')
        log_event(
            self, 'interactive_arm_pick', 'INTERACTIVE_ARM_READY',
            f'X键交替 抓取={PICK_MIN}~{PICK_MAX} 放置={PLACE_MIN}~{PLACE_MAX}')

    def _load_catalog(self, path: str) -> dict[int, dict[str, Any]]:
        catalog: dict[int, dict[str, Any]] = {}
        if path:
            with open(path, encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            for key, entry in (data.get('arm_points') or {}).items():
                slot = int(key)
                if not (PICK_MIN <= slot <= PLACE_MAX):
                    continue
                role = entry.get('role', 'pick' if slot <= PICK_MAX else 'place')
                catalog[slot] = {
                    'role': role,
                    'label': entry.get('label', f'{"抓取" if role == "pick" else "放置"}点 {slot}'),
                    'map_target': entry.get('map_target', {}),
                }

        for slot in range(PICK_MIN, PICK_MAX + 1):
            catalog.setdefault(slot, {
                'role': 'pick',
                'label': f'抓取点 {slot + 1}',
                'map_target': {},
            })
        for slot in range(PLACE_MIN, PLACE_MAX + 1):
            catalog.setdefault(slot, {
                'role': 'place',
                'label': f'放置点 {slot - PLACE_MIN + 1}',
                'map_target': {},
            })
        return catalog

    def _on_odom(self, msg: Odometry) -> None:
        p = msg.pose.pose.position
        aft = {
            'x': p.x,
            'y': p.y,
            'z': p.z,
            'yaw': yaw_from_quaternion(msg.pose.pose.orientation),
        }
        base = compose_aft_to_base_in_init(aft, self._aft_to_base)
        self._robot_xy = (base['x'], base['y'])

    def _on_joy(self, msg: Joy) -> None:
        if len(msg.buttons) <= self._joy_button:
            return
        pressed = msg.buttons[self._joy_button] == 1
        rising = pressed and not self._last_joy_pressed
        self._last_joy_pressed = pressed
        if not rising or self._busy:
            return
        threading.Thread(target=self._handle_x_press, daemon=True).start()

    def _nearest_point(self, slot_min: int, slot_max: int) -> tuple[int | None, float | None]:
        if self._robot_xy is None:
            return None, None
        rx, ry = self._robot_xy
        best_id: int | None = None
        best_dist = float('inf')
        for slot in range(slot_min, slot_max + 1):
            mt = self._catalog[slot].get('map_target') or {}
            if 'x' not in mt or 'y' not in mt:
                continue
            px, py = float(mt['x']), float(mt['y'])
            dist = math.hypot(rx - px, ry - py)
            if dist < best_dist:
                best_dist = dist
                best_id = slot
        if best_id is None:
            return None, None
        return best_id, best_dist

    def _handle_x_press(self) -> None:
        with self._action_lock:
            if self._busy:
                return
            is_pick = self._next_is_pick
            if is_pick:
                point_id, dist_m = self._nearest_point(PICK_MIN, PICK_MAX)
                action_kind = '抓取'
            else:
                point_id, dist_m = self._nearest_point(PLACE_MIN, PLACE_MAX)
                action_kind = '放置'

            if point_id is None:
                self.get_logger().warn(
                    f'X 键触发{action_kind}失败：定位未就绪或无有效 map_target 点位')
                log_event(
                    self, 'interactive_arm_pick', 'NEAREST_POINT_FAILED',
                    f'action={action_kind} reason=no_pose_or_points',
                    level='ERROR')
                return

            next_hint = '放置' if is_pick else '抓取'
            self.get_logger().info(
                f'X 键 → {action_kind} 最近点位 {point_id} '
                f'(dist={dist_m:.3f}m)，成功后下次 X 键将{next_hint}')
            self._do_arm_action(point_id, dist_m, expect_pick=is_pick)

    def _publish_coord_report(self, text: str) -> None:
        msg = String()
        msg.data = text
        self._coord_pub.publish(msg)

    def _on_waypoint(self, msg: ArmWaypoint) -> None:
        if self._pending_point_id is None:
            return
        if msg.id != str(self._pending_point_id):
            return
        self._waypoint = msg
        self._waypoint_event.set()

    def _on_status(self, msg: UInt8MultiArray) -> None:
        if len(msg.data) < 2 or self._pending_ack_state is None:
            return
        state, result = msg.data[0], msg.data[1]
        if state != self._pending_ack_state:
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

    def _do_arm_action(self, point_id: int, dist_m: float | None, *, expect_pick: bool) -> None:
        action_code, ack_state, action_name = _action_for_point(point_id)
        label = self._catalog[point_id].get('label', f'点位 {point_id}')

        self._busy = True
        self._pending_point_id = point_id
        self._pending_ack_state = ack_state
        self._pending_dist_m = dist_m
        self._waypoint = None
        self._waypoint_event.clear()
        self._ack_event.clear()
        self._ack_ok = False

        log_event(
            self, 'interactive_arm_pick', 'ARM_ACTION_REQUESTED',
            (
                f'action={action_name} arm_point_id={point_id} label={label} '
                f'dist_m={dist_m:.3f}'
                if dist_m is not None
                else f'action={action_name} arm_point_id={point_id} label={label}'
            ))

        req = ArmPoseRequest()
        req.arm_point_id = point_id
        req.nav_id = ''
        self._request_pub.publish(req)

        if not self._waypoint_event.wait(timeout=self._waypoint_wait_timeout):
            self.get_logger().error(
                f'{action_name} 点位 {point_id} 失败：等待 arm_waypoint 超时')
            log_event(
                self, 'interactive_arm_pick', 'ARM_WAYPOINT_TIMEOUT',
                f'arm_point_id={point_id}', level='ERROR')
            self._reset_busy()
            return

        wp = self._waypoint
        assert wp is not None
        coord_text = _format_arm_coords(
            action_name=action_name,
            point_id=point_id,
            label=label,
            wp=wp,
            action_code=action_code,
            dist_m=self._pending_dist_m,
        )
        self._publish_coord_report(coord_text)

        if not self._wait_for_cmd_subscriber():
            self.get_logger().error(
                f'{action_name} 点位 {point_id} 失败：/arm_command 无订阅者')
            log_event(
                self, 'interactive_arm_pick', 'ARM_COMMAND_NO_SUBSCRIBER',
                f'arm_point_id={point_id}', level='ERROR')
            self._reset_busy()
            return

        cmd = Float64MultiArray()
        cmd.data = [wp.x, wp.y, wp.z, wp.yaw, float(action_code)]
        self._cmd_pub.publish(cmd)
        sx, sy = _serial_xy(wp.x, wp.y)
        sent_line = (
            f'→ 已发送 /arm_command {action_name}: '
            f'payload=[{wp.x:.2f}, {wp.y:.2f}, {wp.z:.2f}, {wp.yaw:.4f}, {action_code}]  '
            f'串口XY≈({sx:.2f}, {sy:.2f})'
        )
        self._publish_coord_report(sent_line)
        log_event(
            self, 'interactive_arm_pick', 'ARM_COMMAND_SENT',
            f'action={action_name} id={point_id} '
            f'x={wp.x:.2f} y={wp.y:.2f} z={wp.z:.2f} yaw={wp.yaw:.4f} '
            f'serial_x={sx:.2f} serial_y={sy:.2f}')

        if not self._ack_event.wait(timeout=self._arm_timeout):
            self.get_logger().error(
                f'{action_name} 点位 {point_id} 失败：等待 ACK 超时')
            log_event(
                self, 'interactive_arm_pick', 'ARM_ACK_TIMEOUT',
                f'action={action_name} arm_point_id={point_id}', level='ERROR')
            self._reset_busy()
            return

        if self._ack_ok:
            self._next_is_pick = not expect_pick
            self.get_logger().info(f'✓ {action_name} 点位 {point_id} 完成 (ACK OK)')
            self._publish_coord_report(f'✓ {action_name} 点位 {point_id} 完成 (ACK OK)\n')
            log_event(
                self, 'interactive_arm_pick', 'ARM_ACK_SUCCESS',
                f'action={action_name} arm_point_id={point_id}')
        else:
            self.get_logger().error(f'✗ {action_name} 点位 {point_id} 失败 (ACK FAIL)')
            self._publish_coord_report(f'✗ {action_name} 点位 {point_id} 失败 (ACK FAIL)\n')
            log_event(
                self, 'interactive_arm_pick', 'ARM_ACK_FAILURE',
                f'action={action_name} arm_point_id={point_id}', level='ERROR')

        self._reset_busy()

    def _reset_busy(self) -> None:
        self._busy = False
        self._pending_point_id = None
        self._pending_ack_state = None
        self._pending_dist_m = None
        self._waypoint = None


def main() -> None:
    rclpy.init()
    node = InteractiveArmPick()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()


if __name__ == '__main__':
    main()
