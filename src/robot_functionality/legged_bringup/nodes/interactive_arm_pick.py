#!/usr/bin/env python3
"""手柄 X 键机械臂操作：默认抓取/放置距离最近的点位，可手动指定。

- 无手动输入时：X 键 → 全点位 (0~15) 中距离最近的点，自动判断抓取或放置
- 有手动输入时：X 键 → 使用手动指定的点位
- 手动输入话题: /interactive_arm/manual_point (std_msgs/Int32)
  发布有效点位 ID (0~15) 设置手动目标；发布 -1 清除手动目标，恢复最近点模式

命令发送：100Hz 重发直到串口 ACK (state=0x03)，之后等待机械臂 ACK 完成。
坐标详情发布到 /interactive_arm/coord_report。
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
from std_msgs.msg import Float64MultiArray, Int32, String, UInt8MultiArray

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
ARM_SERIAL_DONE = 0x03


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
        self.declare_parameter('arm_serial_ack_topic', '/arm_serial_ack')
        self.declare_parameter('arm_pose_request_topic', '/mission_bt/arm_pose_request')
        self.declare_parameter('arm_waypoint_topic', '/mission_bt/arm_waypoint')
        self.declare_parameter('coord_report_topic', '/interactive_arm/coord_report')
        self.declare_parameter('manual_point_topic', '/interactive_arm/manual_point')
        self.declare_parameter('joy_topic', '/joy')
        self.declare_parameter('joy_button_index', 3)
        self.declare_parameter('odom_topic', '/aft_mapped_to_init')
        self.declare_parameter('aft_to_base_link.x', -0.21368)
        self.declare_parameter('aft_to_base_link.y', 0.0)
        self.declare_parameter('aft_to_base_link.z', -0.12978)
        self.declare_parameter('aft_to_base_link.yaw', 0.05)
        self.declare_parameter('arm_republish_interval', 0.01)

        self._arm_timeout = float(self.get_parameter('arm_timeout').value)
        self._waypoint_wait_timeout = float(self.get_parameter('waypoint_wait_timeout').value)
        self._republish_interval = float(self.get_parameter('arm_republish_interval').value)
        cmd_topic = str(self.get_parameter('arm_command_topic').value)
        status_topic = str(self.get_parameter('arm_status_topic').value)
        serial_ack_topic = str(self.get_parameter('arm_serial_ack_topic').value)
        request_topic = str(self.get_parameter('arm_pose_request_topic').value)
        waypoint_topic = str(self.get_parameter('arm_waypoint_topic').value)
        coord_topic = str(self.get_parameter('coord_report_topic').value)
        manual_topic = str(self.get_parameter('manual_point_topic').value)
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
        # 机械臂行为 ACK (state=0x01 Pick / 0x02 Place)
        self.create_subscription(UInt8MultiArray, status_topic, self._on_arm_status, qos)
        # 串口 ACK (state=0x03 Serial Done)
        self.create_subscription(UInt8MultiArray, serial_ack_topic, self._on_serial_ack, qos)
        self.create_subscription(Odometry, odom_topic, self._on_odom, 10)
        self.create_subscription(Joy, joy_topic, self._on_joy, 10)
        # 手动点位输入
        self.create_subscription(Int32, manual_topic, self._on_manual_point, qos)

        # ── 状态 ──
        self._busy = False
        self._last_joy_pressed = False
        self._robot_xy: tuple[float, float] | None = None
        self._manual_point_id: int | None = None  # 手动指定的点位

        # 动作进行中
        self._pending_point_id: int | None = None
        self._pending_ack_state: int | None = None
        self._pending_dist_m: float | None = None
        self._pending_action_code: int = 0
        self._waypoint: ArmWaypoint | None = None
        self._cmd_xyza: list[float] = []  # 重发用的命令

        self._waypoint_event = threading.Event()
        self._serial_ack_event = threading.Event()
        self._behavior_ack_event = threading.Event()
        self._serial_ack_ok = False
        self._behavior_ack_ok = False
        self._action_lock = threading.Lock()

        self.get_logger().info(
            'X 键机械臂操作就绪：默认最近点位 (0~15)，手动输入 '
            f'话题={manual_topic} (-1 清除)')
        self.get_logger().info(
            f'100Hz 重发 + 两阶段 ACK: 串口 ACK={serial_ack_topic} 行为 ACK={status_topic}')
        log_event(
            self, 'interactive_arm_pick', 'INTERACTIVE_ARM_READY',
            f'最近点模式 全点位={ALL_MIN}~{ALL_MAX} 手动输入话题={manual_topic}')

    # ─────────────────────────────────────────────────────────────────
    # 数据加载
    # ─────────────────────────────────────────────────────────────────

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
                'role': 'pick', 'label': f'抓取点 {slot + 1}', 'map_target': {},
            })
        for slot in range(PLACE_MIN, PLACE_MAX + 1):
            catalog.setdefault(slot, {
                'role': 'place', 'label': f'放置点 {slot - PLACE_MIN + 1}', 'map_target': {},
            })
        return catalog

    # ─────────────────────────────────────────────────────────────────
    # 订阅回调
    # ─────────────────────────────────────────────────────────────────

    def _on_odom(self, msg: Odometry) -> None:
        p = msg.pose.pose.position
        aft = {
            'x': p.x, 'y': p.y, 'z': p.z,
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

    def _on_manual_point(self, msg: Int32) -> None:
        pid = msg.data
        if pid < 0:
            self._manual_point_id = None
            self.get_logger().info('手动点位已清除，恢复最近点模式')
            self._publish_coord_report('→ 手动点位已清除，X 键 = 最近点\n')
        elif ALL_MIN <= pid <= ALL_MAX:
            self._manual_point_id = pid
            _, _, role_cn = _action_for_point(pid)
            label = self._catalog[pid].get('label', f'点位 {pid}')
            self.get_logger().info(f'手动点位已设置: {pid} ({role_cn}, {label})')
            self._publish_coord_report(f'→ 手动点位 {pid} ({role_cn}, {label})\n')
        else:
            self.get_logger().warn(f'无效点位 {pid}，范围 {ALL_MIN}~{ALL_MAX}，已忽略')

    def _on_waypoint(self, msg: ArmWaypoint) -> None:
        if self._pending_point_id is None:
            return
        if msg.id != str(self._pending_point_id):
            return
        self._waypoint = msg
        self._waypoint_event.set()

    def _on_serial_ack(self, msg: UInt8MultiArray) -> None:
        """串口 ACK (state=0x03): 串口接收完成 → 停止重发。"""
        if len(msg.data) < 2:
            return
        state = msg.data[0]
        if state != ARM_SERIAL_DONE:
            return
        if self._serial_ack_event.is_set():
            return
        self._serial_ack_ok = True
        self._serial_ack_event.set()

    def _on_arm_status(self, msg: UInt8MultiArray) -> None:
        """机械臂行为 ACK (state=0x01/0x02): 动作完成 → 行为树下一步。"""
        if len(msg.data) < 2 or self._pending_ack_state is None:
            return
        state, result = msg.data[0], msg.data[1]
        if state != self._pending_ack_state:
            return
        if self._behavior_ack_event.is_set():
            return
        self._behavior_ack_ok = result == ARM_ACK_OK
        self._behavior_ack_event.set()

    # ─────────────────────────────────────────────────────────────────
    # 最近点搜索 (全点位 0~15)
    # ─────────────────────────────────────────────────────────────────

    def _nearest_point(self) -> tuple[int | None, float | None]:
        if self._robot_xy is None:
            return None, None
        rx, ry = self._robot_xy
        best_id: int | None = None
        best_dist = float('inf')
        for slot in range(ALL_MIN, ALL_MAX + 1):
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

    # ─────────────────────────────────────────────────────────────────
    # X 键处理
    # ─────────────────────────────────────────────────────────────────

    def _handle_x_press(self) -> None:
        with self._action_lock:
            if self._busy:
                return

            # 手动点位优先
            if self._manual_point_id is not None:
                point_id = self._manual_point_id
                dist_m = self._compute_dist(point_id)
                action_code, ack_state, action_name = _action_for_point(point_id)
                label = self._catalog[point_id].get('label', f'点位 {point_id}')
                self.get_logger().info(
                    f'X 键 → 手动点位 {point_id} ({action_name}, {label}) '
                    f'dist={dist_m:.3f}m' if dist_m is not None else '')
            else:
                point_id, dist_m = self._nearest_point()
                if point_id is None:
                    self.get_logger().warn(
                        'X 键触发失败：定位未就绪或无有效 map_target 点位')
                    log_event(
                        self, 'interactive_arm_pick', 'NEAREST_POINT_FAILED',
                        'reason=no_pose_or_points', level='ERROR')
                    return
                action_code, ack_state, action_name = _action_for_point(point_id)
                label = self._catalog[point_id].get('label', f'点位 {point_id}')
                self.get_logger().info(
                    f'X 键 → 最近点位 {point_id} ({action_name}, {label}) '
                    f'dist={dist_m:.3f}m')

            self._do_arm_action(point_id, dist_m, action_code, ack_state, action_name, label)

    def _compute_dist(self, point_id: int) -> float | None:
        if self._robot_xy is None:
            return None
        mt = self._catalog[point_id].get('map_target') or {}
        if 'x' not in mt or 'y' not in mt:
            return None
        rx, ry = self._robot_xy
        return math.hypot(rx - float(mt['x']), ry - float(mt['y']))

    # ─────────────────────────────────────────────────────────────────
    # 动作执行 (100Hz 重发 + 两阶段 ACK)
    # ─────────────────────────────────────────────────────────────────

    def _do_arm_action(
        self, point_id: int, dist_m: float | None,
        action_code: int, ack_state: int, action_name: str, label: str,
    ) -> None:
        self._busy = True
        self._pending_point_id = point_id
        self._pending_ack_state = ack_state
        self._pending_dist_m = dist_m
        self._pending_action_code = action_code
        self._waypoint = None
        self._waypoint_event.clear()
        self._serial_ack_event.clear()
        self._behavior_ack_event.clear()
        self._serial_ack_ok = False
        self._behavior_ack_ok = False

        log_event(
            self, 'interactive_arm_pick', 'ARM_ACTION_REQUESTED',
            f'action={action_name} arm_point_id={point_id} label={label} '
            + (f'dist_m={dist_m:.3f}' if dist_m is not None else ''))

        # 1) 请求 arm_waypoint
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

        # 2) 坐标报告
        coord_text = _format_arm_coords(
            action_name=action_name, point_id=point_id, label=label,
            wp=wp, action_code=action_code, dist_m=self._pending_dist_m,
        )
        self._publish_coord_report(coord_text)

        # 3) 等待命令订阅者
        if not self._wait_for_cmd_subscriber():
            self.get_logger().error(
                f'{action_name} 点位 {point_id} 失败：/arm_command 无订阅者')
            log_event(
                self, 'interactive_arm_pick', 'ARM_COMMAND_NO_SUBSCRIBER',
                f'arm_point_id={point_id}', level='ERROR')
            self._reset_busy()
            return

        # 4) 缓存命令，启动 100Hz 重发循环
        self._cmd_xyza = [wp.x, wp.y, wp.z, wp.yaw, float(action_code)]
        sx, sy = _serial_xy(wp.x, wp.y)
        log_event(
            self, 'interactive_arm_pick', 'ARM_COMMAND_START',
            f'action={action_name} id={point_id} '
            f'x={wp.x:.2f} y={wp.y:.2f} z={wp.z:.2f} yaw={wp.yaw:.4f} '
            f'100Hz重发 串口XY=({sx:.2f},{sy:.2f})')

        last_log_time = 0.0
        deadline = time.monotonic() + self._arm_timeout
        cmd_sent_once = False

        while rclpy.ok() and time.monotonic() < deadline:
            # 重发命令 (100Hz)
            if not self._serial_ack_event.is_set():
                if self._cmd_pub.get_subscription_count() > 0:
                    cmd = Float64MultiArray()
                    cmd.data = self._cmd_xyza
                    self._cmd_pub.publish(cmd)
                    if not cmd_sent_once:
                        cmd_sent_once = True
                        self._publish_coord_report(
                            f'→ 已发送 /arm_command {action_name}: '
                            f'payload={self._cmd_xyza}  串口XY≈({sx:.2f}, {sy:.2f})')
                    now = time.monotonic()
                    if now - last_log_time > 1.0:
                        self.get_logger().debug(
                            f'重发 /arm_command 中... 等待串口 ACK')
                        last_log_time = now
                else:
                    if not cmd_sent_once:
                        pass  # wait for subscriber
                    time.sleep(self._republish_interval)
                    continue
            else:
                if self._serial_ack_event.is_set() and cmd_sent_once:
                    # 串口 ACK 已收到，检查行为 ACK
                    if self._behavior_ack_event.is_set():
                        break

            # 检查行为 ACK (可能在串口 ACK 之前到达)
            if self._behavior_ack_event.is_set() and self._serial_ack_event.is_set():
                break

            time.sleep(self._republish_interval)
        else:
            # 超时
            if not self._serial_ack_event.is_set():
                self.get_logger().error(
                    f'{action_name} 点位 {point_id} 超时：未收到串口 ACK')
                log_event(
                    self, 'interactive_arm_pick', 'ARM_SERIAL_ACK_TIMEOUT',
                    f'arm_point_id={point_id}', level='ERROR')
                self._publish_coord_report(
                    f'✗ {action_name} 点位 {point_id} 超时 (未收到串口 ACK)\n')
            elif not self._behavior_ack_event.is_set():
                self.get_logger().error(
                    f'{action_name} 点位 {point_id} 超时：收到串口 ACK 但未收到机械臂 ACK')
                log_event(
                    self, 'interactive_arm_pick', 'ARM_BEHAVIOR_ACK_TIMEOUT',
                    f'arm_point_id={point_id}', level='ERROR')
                self._publish_coord_report(
                    f'✗ {action_name} 点位 {point_id} 超时 (串口ACK已收，机械臂ACK未收)\n')
            self._reset_busy()
            return

        # 5) 完成
        if self._behavior_ack_ok:
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

    # ─────────────────────────────────────────────────────────────────
    # 工具方法
    # ─────────────────────────────────────────────────────────────────

    def _publish_coord_report(self, text: str) -> None:
        msg = String()
        msg.data = text
        self._coord_pub.publish(msg)

    def _wait_for_cmd_subscriber(self, timeout_sec: float = 5.0) -> bool:
        deadline = time.monotonic() + timeout_sec
        while rclpy.ok() and time.monotonic() < deadline:
            if self._cmd_pub.get_subscription_count() > 0:
                return True
            time.sleep(0.05)
        return self._cmd_pub.get_subscription_count() > 0

    def _reset_busy(self) -> None:
        self._busy = False
        self._pending_point_id = None
        self._pending_ack_state = None
        self._pending_dist_m = None
        self._pending_action_code = 0
        self._waypoint = None
        self._cmd_xyza = []


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
