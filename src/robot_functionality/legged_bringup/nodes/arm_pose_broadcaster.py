#!/usr/bin/env python3
# ============================================================================
# 机械臂目标坐标广播 — map 系固定点 → 当前 arm_root
# 16 标定点：0~7 抓取，8~15 放置
#
# arm_root 与 base_link 无旋转；arm_root 原点在 base_link 下 (-9.73, 0.04, 190.68) mm。
# 工作空间圆心、下发 arm_waypoint 均在 arm_root 系（mm, rad）。
#
# 数据流与坐标变换说明见同包 docs/arm_pose_broadcaster.md
# ============================================================================

from __future__ import annotations

import math
import os
import sys
from pathlib import Path
from typing import Any, Optional

import rclpy
import yaml
from geometry_msgs.msg import Quaternion
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy

from legged_mission_bt.msg import ArmPoseRequest, ArmWaypoint, NavReached

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mission_log_client import log_event

MM_PER_M = 1000.0
MIN_POINT_ID = 0
MAX_POINT_ID = 15
PICK_ID_MIN = 0
PICK_ID_MAX = 7
PLACE_ID_MIN = 8
PLACE_ID_MAX = 15


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


def se2_to_world(bx: float, by: float, byaw: float, lx: float, ly: float) -> tuple[float, float]:
    c, s = math.cos(byaw), math.sin(byaw)
    return bx + c * lx - s * ly, by + s * lx + c * ly


def se2_to_base(bx: float, by: float, byaw: float, wx: float, wy: float) -> tuple[float, float]:
    c, s = math.cos(byaw), math.sin(byaw)
    dx, dy = wx - bx, wy - by
    return c * dx + s * dy, -s * dx + c * dy


def compose_aft_to_base_in_init(
    aft: dict[str, float],
    static: dict[str, float],
) -> dict[str, float]:
    """init 系 aft 位姿 + 静态 aft→base_link → init 系 base_link 位姿。"""
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


def map_target_to_baselink(
    map_target: dict[str, float],
    base_in_init: dict[str, float],
) -> dict[str, float]:
    """map/init 系固定目标 → 当前 base_link（mm, rad）。中间步骤，再转 arm_root。"""
    map_x = float(map_target['x'])
    map_y = float(map_target['y'])
    map_z = float(map_target.get('z', 0.0))
    map_yaw = float(map_target.get('yaw', 0.0))

    cur_x = float(base_in_init['x'])
    cur_y = float(base_in_init['y'])
    cur_z = float(base_in_init.get('z', 0.0))
    cur_yaw = float(base_in_init['yaw'])

    out_x_m, out_y_m = se2_to_base(cur_x, cur_y, cur_yaw, map_x, map_y)
    out_z_mm = (map_z - cur_z) * MM_PER_M
    out_yaw = normalize_angle(map_yaw - cur_yaw)

    return {
        'x': out_x_m * MM_PER_M,
        'y': out_y_m * MM_PER_M,
        'z': out_z_mm,
        'yaw': out_yaw,
    }


def baselink_mm_to_arm_root_mm(
    pose_bl: dict[str, float],
    origin_in_bl_mm: dict[str, float],
) -> dict[str, float]:
    """base_link 下 mm → arm_root 下 mm（两系无旋转）。

    arm_root 原点在 base_link 下的位置为 origin_in_bl_mm；
    P_bl = origin + P_ar  →  P_ar = P_bl - origin。
    """
    ox = float(origin_in_bl_mm['x'])
    oy = float(origin_in_bl_mm['y'])
    oz = float(origin_in_bl_mm.get('z', 0.0))
    return {
        'x': float(pose_bl['x']) - ox,
        'y': float(pose_bl['y']) - oy,
        'z': float(pose_bl['z']) - oz,
        'yaw': float(pose_bl.get('yaw', 0.0)),
    }


def legacy_to_map_target(
    entry: dict[str, Any],
    static: dict[str, float],
) -> Optional[dict[str, float]]:
    """兼容旧格式 reference_aft(aft 位姿) + arm_target(base_link mm) → map_target。"""
    ref_aft = entry.get('reference_aft')
    ref_arm = entry.get('arm_target')
    if ref_aft is None or ref_arm is None:
        return None

    base_at_calib = compose_aft_to_base_in_init(ref_aft, static)
    bl_x = float(ref_arm['x']) / MM_PER_M
    bl_y = float(ref_arm['y']) / MM_PER_M
    bl_z_mm = float(ref_arm.get('z', 0.0))
    bl_yaw = float(ref_arm.get('yaw', 0.0))

    map_x, map_y = se2_to_world(
        base_at_calib['x'], base_at_calib['y'], base_at_calib['yaw'], bl_x, bl_y)
    return {
        'x': map_x,
        'y': map_y,
        'z': base_at_calib['z'] + bl_z_mm / MM_PER_M,
        'yaw': normalize_angle(base_at_calib['yaw'] + bl_yaw),
    }


def point_role(arm_point_id: int) -> str:
    if PICK_ID_MIN <= arm_point_id <= PICK_ID_MAX:
        return 'pick'
    if PLACE_ID_MIN <= arm_point_id <= PLACE_ID_MAX:
        return 'place'
    return ''


def _project_onto_disk(
    px: float, py: float, cx: float, cy: float, radius: float,
) -> tuple[float, float]:
    """将点投影到以 (cx,cy) 为圆心、radius 为半径的闭圆盘内。"""
    dx = px - cx
    dy = py - cy
    dist = math.hypot(dx, dy)
    if dist <= radius or dist < 1e-12:
        return px, py
    scale = radius / dist
    return cx + dx * scale, cy + dy * scale


def disks_intersect(
    cx1: float, cy1: float, r1: float,
    cx2: float, cy2: float, r2: float,
) -> bool:
    """两圆盘是否有交集。"""
    return math.hypot(cx1 - cx2, cy1 - cy2) <= r1 + r2 + 1e-9


def optimize_suction_cup_xy(
    target_x_mm: float,
    target_y_mm: float,
    *,
    arm_workspace_radius_mm: float = 665.0,
    suction_cup_radius_mm: float = 35.0,
    goal_tolerance_radius_mm: float = 125.0,
) -> tuple[float, float, bool, float]:
    """在约束下求吸盘中心，使其尽量接近目标圆心。

    约束（吸盘整盘含在目标容差圆内；吸盘中心在工作空间圆内）：
      - 目标容差圆：圆心=标定点，半径 goal_tolerance_radius_mm，整盘在内 → 中心距目标 ≤ goal_R - cup_R
      - 机械臂 XY 工作空间：吸盘中心距 arm_root 原点 ≤ arm_workspace_radius_mm（665mm）

    坐标均在 arm_root 系（mm）；工作空间圆心为 arm_root 原点 (0, 0)。

    Returns:
        (cup_x, cup_y, feasible, offset_mm)
        offset_mm = 吸盘中心相对标定目标中心的距离
    """
    max_center_from_base = arm_workspace_radius_mm
    max_center_from_target = goal_tolerance_radius_mm - suction_cup_radius_mm

    if max_center_from_target <= 0.0:
        return target_x_mm, target_y_mm, False, 0.0

    tx, ty = target_x_mm, target_y_mm
    dist_target = math.hypot(tx, ty)

    # 快速路径：标定点本身即可行
    if dist_target <= max_center_from_base:
        return tx, ty, True, 0.0

    # 两圆盘无交集
    if not disks_intersect(0.0, 0.0, max_center_from_base, tx, ty, max_center_from_target):
        return tx, ty, False, dist_target

    # POCS：投影到 工作空间盘 ∩ 目标容差盘，迭代收敛到距 target 最近的可行点
    px, py = tx, ty
    for _ in range(32):
        nx, ny = _project_onto_disk(px, py, 0.0, 0.0, max_center_from_base)
        nx, ny = _project_onto_disk(nx, ny, tx, ty, max_center_from_target)
        if math.hypot(nx - px, ny - py) < 1e-6:
            px, py = nx, ny
            break
        px, py = nx, ny

    offset = math.hypot(px - tx, py - ty)
    dist_cup = math.hypot(px, py)
    feasible = (
        dist_cup <= max_center_from_base + 1e-6
        and offset <= max_center_from_target + 1e-6
    )
    return px, py, feasible, offset


def saturate_arm_root_workspace_xy(
    x_mm: float,
    y_mm: float,
    radius_mm: float,
) -> tuple[float, float, bool, float]:
    """将 arm_root XY 饱和到工作空间圆盘内：超出则沿原方向缩放到 radius_mm。"""
    dist = math.hypot(x_mm, y_mm)
    if dist <= radius_mm + 1e-6:
        return x_mm, y_mm, False, dist
    if dist < 1e-12:
        return x_mm, y_mm, False, 0.0
    scale = radius_mm / dist
    return x_mm * scale, y_mm * scale, True, dist


class ArmPoseBroadcaster(Node):

    def __init__(self) -> None:
        super().__init__('arm_pose_broadcaster')

        bringup_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        default_points = os.path.join(bringup_dir, 'params', 'arm_points.yaml')

        self.declare_parameter('arm_points_file', default_points)
        self.declare_parameter('odom_topic', '/aft_mapped_in_map')
        self.declare_parameter('arm_pose_request_topic', '/mission_bt/arm_pose_request')
        self.declare_parameter('nav_reached_topic', '/mission_bt/nav_reached')
        self.declare_parameter('arm_waypoint_topic', '/mission_bt/arm_waypoint')
        # 静态 TF aft_mapped → base_link（与 static_tf_params.yaml t1 一致）
        self.declare_parameter('aft_to_base_link.x', -0.21368)
        self.declare_parameter('aft_to_base_link.y', 0.0)
        self.declare_parameter('aft_to_base_link.z', -0.12978)
        self.declare_parameter('aft_to_base_link.yaw', 0.05)
        # 吸盘几何（XY）：工作空间圆 + 目标容差圆，下发吸盘中心
        self.declare_parameter('enable_suction_cup_xy_adjust', True)
        self.declare_parameter('arm_workspace_radius_mm', 665.0)
        self.declare_parameter('suction_cup_radius_mm', 35.0)
        self.declare_parameter('goal_tolerance_radius_mm', 125.0)
        # arm_root 原点在 base_link 下的位置（mm，无旋转）
        self.declare_parameter('arm_root_in_base_link.x_mm', -9.73)
        self.declare_parameter('arm_root_in_base_link.y_mm', 0.04)
        self.declare_parameter('arm_root_in_base_link.z_mm', 190.68)

        points_path = self.get_parameter('arm_points_file').value
        odom_topic = self.get_parameter('odom_topic').value
        req_topic = self.get_parameter('arm_pose_request_topic').value
        nav_reached_topic = self.get_parameter('nav_reached_topic').value
        arm_wp_topic = self.get_parameter('arm_waypoint_topic').value

        self._aft_to_base = {
            'x': self.get_parameter('aft_to_base_link.x').value,
            'y': self.get_parameter('aft_to_base_link.y').value,
            'z': self.get_parameter('aft_to_base_link.z').value,
            'yaw': self.get_parameter('aft_to_base_link.yaw').value,
        }
        self._suction_geom = {
            'enabled': self.get_parameter('enable_suction_cup_xy_adjust').value,
            'arm_r': float(self.get_parameter('arm_workspace_radius_mm').value),
            'cup_r': float(self.get_parameter('suction_cup_radius_mm').value),
            'goal_r': float(self.get_parameter('goal_tolerance_radius_mm').value),
        }
        self._arm_root_origin_bl_mm = {
            'x': float(self.get_parameter('arm_root_in_base_link.x_mm').value),
            'y': float(self.get_parameter('arm_root_in_base_link.y_mm').value),
            'z': float(self.get_parameter('arm_root_in_base_link.z_mm').value),
        }

        self._arm_points = self._load_arm_points(points_path)
        self._latest_aft: Optional[dict[str, float]] = None
        self._pending: Optional[ArmPoseRequest] = None
        self._request_seq = 0

        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
        self._arm_pub = self.create_publisher(ArmWaypoint, arm_wp_topic, qos)

        self.create_subscription(Odometry, odom_topic, self._on_odom, 10)
        self.create_subscription(ArmPoseRequest, req_topic, self._on_arm_request, qos)
        self.create_subscription(NavReached, nav_reached_topic, self._on_nav_reached, qos)

        self.get_logger().info(
            f'Loaded {len(self._arm_points)} arm points (map frame): pick 0~7, place 8~15')
        self.get_logger().info(
            f'aft→base_link static offset: '
            f'({self._aft_to_base["x"]:.5f}, {self._aft_to_base["y"]:.5f}, '
            f'{self._aft_to_base["z"]:.5f}, yaw={self._aft_to_base["yaw"]:.4f})')
        o = self._arm_root_origin_bl_mm
        self.get_logger().info(
            f'arm_root origin in base_link (mm): ({o["x"]:.2f}, {o["y"]:.2f}, {o["z"]:.2f})')
        if self._suction_geom['enabled']:
            g = self._suction_geom
            self.get_logger().info(
                f'suction cup XY adjust: arm_center≤{g["arm_r"]:.0f}mm from arm_root, '
                f'goal_R={g["goal_r"]:.0f}mm cup_r={g["cup_r"]:.0f}mm '
                f'→ center≤{g["goal_r"]-g["cup_r"]:.0f}mm from target')

    def _to_arm_root(self, pose_bl: dict[str, float]) -> dict[str, float]:
        return baselink_mm_to_arm_root_mm(pose_bl, self._arm_root_origin_bl_mm)

    def _apply_suction_cup_xy(self, arm: dict[str, float], slot: str) -> Optional[dict[str, float]]:
        """将标定目标 XY 调整为吸盘中心（整盘在容差圆与工作空间内，且最靠近目标圆心）。"""
        if not self._suction_geom['enabled']:
            return arm

        g = self._suction_geom
        tx, ty = arm['x'], arm['y']
        cx, cy, feasible, offset = optimize_suction_cup_xy(
            tx, ty,
            arm_workspace_radius_mm=g['arm_r'],
            suction_cup_radius_mm=g['cup_r'],
            goal_tolerance_radius_mm=g['goal_r'],
        )
        if not feasible:
            self.get_logger().warn(
                f'Point {slot}: suction cup adjust infeasible for target ({tx:.1f}, {ty:.1f}) mm — '
                f'using raw target; workspace saturation may apply')
            return arm

        if offset > 1e-3:
            self.get_logger().info(
                f'Point {slot}: suction cup center adjusted '
                f'({tx:.1f},{ty:.1f})→({cx:.1f},{cy:.1f}) mm, offset={offset:.1f}mm')
        arm = dict(arm)
        arm['x'] = cx
        arm['y'] = cy
        return arm

    def _saturate_arm_workspace(self, arm: dict[str, float], slot: str) -> tuple[dict[str, float], bool]:
        """最终下发前将 XY 饱和到 arm_root 工作空间圆（默认 665mm）。"""
        radius = self._suction_geom['arm_r']
        sx, sy, saturated, dist = saturate_arm_root_workspace_xy(arm['x'], arm['y'], radius)
        if not saturated:
            return arm, False
        self.get_logger().warn(
            f'Point {slot}: arm_root XY ({arm["x"]:.1f}, {arm["y"]:.1f}) mm exceeds '
            f'workspace {radius:.0f}mm (dist={dist:.1f}); '
            f'saturated to ({sx:.1f}, {sy:.1f}) mm along same direction')
        out = dict(arm)
        out['x'] = sx
        out['y'] = sy
        return out, True

    def _current_base_in_init(self) -> Optional[dict[str, float]]:
        if self._latest_aft is None:
            return None
        return compose_aft_to_base_in_init(self._latest_aft, self._aft_to_base)

    def _resolve_map_target(self, slot: str, entry: dict[str, Any]) -> Optional[dict[str, float]]:
        map_target = entry.get('map_target')
        if map_target is not None:
            return map_target

        converted = legacy_to_map_target(entry, self._aft_to_base)
        if converted is not None:
            self.get_logger().warn(
                f'Point {slot}: using legacy reference_aft+arm_target (please migrate to map_target)')
            return converted

        return None

    def _load_arm_points(self, path: str) -> dict[str, dict[str, Any]]:
        if not os.path.isfile(path):
            self.get_logger().warn(f'Arm points file not found: {path}')
            return {}

        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}

        points = data.get('arm_points', {})
        if not isinstance(points, dict):
            raise ValueError('arm_points must be a map keyed by "0".."15"')

        for i in range(MIN_POINT_ID, MAX_POINT_ID + 1):
            key = str(i)
            if key not in points:
                self.get_logger().warn(f'arm_points missing slot "{key}"')
                continue
            role = points[key].get('role', '')
            if PICK_ID_MIN <= i <= PICK_ID_MAX and role != 'pick':
                self.get_logger().warn(f'Point {key}: expected role pick, got {role}')
            if PLACE_ID_MIN <= i <= PLACE_ID_MAX and role != 'place':
                self.get_logger().warn(f'Point {key}: expected role place, got {role}')
            if self._resolve_map_target(key, points[key]) is None:
                if points[key].get('arm_root_target') is None and points[key].get('base_link_target') is None:
                    self.get_logger().error(
                        f'Point {key}: missing map_target (and no arm_root/base_link fallback)')
        return points

    def _resolve_arm_root_target(
        self, slot: str, entry: dict[str, Any]
    ) -> Optional[dict[str, float]]:
        art = entry.get('arm_root_target')
        if art is not None:
            return {
                'x': float(art['x']),
                'y': float(art['y']),
                'z': float(art.get('z', 0.0)),
                'yaw': float(art.get('yaw', 0.0)),
            }

        blt = entry.get('base_link_target')
        if blt is None:
            return None
        bl_pose = {
            'x': float(blt['x']),
            'y': float(blt['y']),
            'z': float(blt.get('z', 0.0)),
            'yaw': float(blt.get('yaw', 0.0)),
        }
        self.get_logger().warn(
            f'Point {slot}: base_link_target is deprecated; converted to arm_root')
        return self._to_arm_root(bl_pose)

    def _on_odom(self, msg: Odometry) -> None:
        p = msg.pose.pose.position
        self._latest_aft = {
            'x': p.x,
            'y': p.y,
            'z': p.z,
            'yaw': yaw_from_quaternion(msg.pose.pose.orientation),
        }
        if self._pending is not None:
            self._try_publish_for_request(self._pending)

    def _on_nav_reached(self, msg: NavReached) -> None:
        log_event(
            self, 'arm_pose_broadcaster', 'NAV_REACHED_RECEIVED',
            f'导航点={msg.nav_id}',
        )
        self.get_logger().info(f'nav_reached nav_id={msg.nav_id}')

    def _on_arm_request(self, msg: ArmPoseRequest) -> None:
        self._request_seq += 1
        log_event(
            self, 'arm_pose_broadcaster', 'ARM_POSE_REQUEST_RECEIVED',
            f'序号={self._request_seq} 机械臂点位={msg.arm_point_id} 关联导航点={msg.nav_id}',
        )
        self._pending = msg
        self._try_publish_for_request(msg)

    def _try_publish_for_request(self, msg: ArmPoseRequest) -> None:
        pid = msg.arm_point_id
        if not (MIN_POINT_ID <= pid <= MAX_POINT_ID):
            log_event(
                self, 'arm_pose_broadcaster', 'ARM_WAYPOINT_INVALID_POINT',
                f'机械臂点位={pid}（有效范围0~15）', level='ERROR',
            )
            self.get_logger().error(
                f'Invalid arm_point_id (need 0~15), got {pid}')
            return

        slot = str(pid)
        expected = point_role(pid)
        entry = self._arm_points.get(slot)
        if entry is None:
            log_event(
                self, 'arm_pose_broadcaster', 'ARM_WAYPOINT_MISSING_ENTRY',
                f'点位编号={slot} 在arm_points.yaml中不存在', level='ERROR',
            )
            self.get_logger().error(f'arm_points.yaml has no entry for slot "{slot}"')
            return

        point_role_yaml = entry.get('role', '')
        if point_role_yaml != expected:
            role_cn = '抓取' if expected == 'pick' else '放置'
            yaml_role_cn = '抓取' if point_role_yaml == 'pick' else (
                '放置' if point_role_yaml == 'place' else point_role_yaml)
            log_event(
                self, 'arm_pose_broadcaster', 'ARM_WAYPOINT_ROLE_MISMATCH',
                f'点位={slot} 配置角色={yaml_role_cn} 期望角色={role_cn}',
                level='ERROR',
            )
            return

        map_target = self._resolve_map_target(slot, entry)
        arm_root_fallback = self._resolve_arm_root_target(slot, entry)

        if map_target is None and arm_root_fallback is None:
            log_event(
                self, 'arm_pose_broadcaster', 'ARM_WAYPOINT_NO_TARGET',
                f'点位={slot} 缺少map_target与arm_root备用坐标', level='ERROR',
            )
            self.get_logger().error(
                f'Slot "{slot}" missing map_target and arm_root/base_link fallback')
            return

        if self._latest_aft is None:
            if arm_root_fallback is not None:
                arm = arm_root_fallback
                mode = 'arm_root_target (no /aft_mapped_to_init)'
            else:
                self.get_logger().warn('Waiting for /aft_mapped_to_init...')
                return
        else:
            if map_target is None:
                log_event(
                    self, 'arm_pose_broadcaster', 'ARM_WAYPOINT_NO_MAP_TARGET',
                    f'点位={slot} 有里程计但缺少map_target', level='ERROR',
                )
                self.get_logger().error(
                    f'Slot "{slot}" has /aft_mapped_to_init but no map_target')
                return
            base_in_init = self._current_base_in_init()
            if base_in_init is None:
                return
            arm = self._to_arm_root(map_target_to_baselink(map_target, base_in_init))
            mode = 'map_target → arm_root'

        adjusted = self._apply_suction_cup_xy(arm, slot)
        if adjusted is None:
            return
        arm = adjusted
        if self._suction_geom['enabled']:
            mode = f'{mode} + suction_cup_xy'

        arm, saturated = self._saturate_arm_workspace(arm, slot)
        if saturated:
            mode = f'{mode} + workspace_saturate'

        out = ArmWaypoint()
        out.id = slot
        out.x = arm['x']
        out.y = arm['y']
        out.z = arm['z']
        out.yaw = arm['yaw']
        self._arm_pub.publish(out)

        label = entry.get('label', slot)
        role_cn = '抓取' if expected == 'pick' else '放置'
        log_event(
            self, 'arm_pose_broadcaster', 'ARM_WAYPOINT_PUBLISHED',
            f'点位={slot} 角色={role_cn} 标签={label} 计算方式={mode} '
            f'机械臂坐标(mm)=({out.x:.1f},{out.y:.1f},{out.z:.1f}) 航向={out.yaw:.3f}弧度',
        )
        self.get_logger().info(
            f'Published arm_waypoint id={slot} ({label}, {expected}) [{mode}] '
            f'arm_root(mm)=({out.x:.1f}, {out.y:.1f}, {out.z:.1f}, yaw={out.yaw:.3f})')
        self._pending = None


def main() -> None:
    rclpy.init()
    node = ArmPoseBroadcaster()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
