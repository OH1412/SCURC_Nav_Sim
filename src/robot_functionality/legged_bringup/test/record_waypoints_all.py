#!/usr/bin/env python3
# ============================================================================
# 任意数量航点坐标采集助手
# ============================================================================
# 启动时询问航点数量，手动导航到目标位置后按 Enter 逐点记录，全部完成后自动保存。
#
# 用法:
#   终端1:  ros2 launch legged_bringup bringup_in_real.launch.py  (或 navigation)
#   终端2:  ros2 run legged_bringup record_waypoints_all.py
#
# 操作:
#   Enter  - 记录当前坐标（推进到下一航点）
#   r      - 重新记录上一个航点（覆盖）
#   s      - 跳过当前航点（坐标留空）
#   q      - 提前退出并保存已记录的坐标
#   Ctrl+C - 退出并保存
# ============================================================================

import math
import os
import sys
import threading
import time
from datetime import datetime

import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from nav_msgs.msg import Odometry


ZONE_LOWER = 1.35
ZONE_UPPER = 4.0
ZONE_HYSTERESIS = 0.1


def determine_zone(x: float, current_zone: str | None) -> str:
    if current_zone is None:
        if ZONE_LOWER <= x <= ZONE_UPPER:
            return 'MIDDLE'
        return 'EDGE'
    elif current_zone == 'EDGE':
        lo = ZONE_LOWER + ZONE_HYSTERESIS
        hi = ZONE_UPPER - ZONE_HYSTERESIS
        if lo <= x <= hi:
            return 'MIDDLE'
        return 'EDGE'
    else:
        lo = ZONE_LOWER - ZONE_HYSTERESIS
        hi = ZONE_UPPER + ZONE_HYSTERESIS
        if x < lo or x > hi:
            return 'EDGE'
        return 'MIDDLE'


def zone_at_x(x: float) -> str:
    return 'MIDDLE' if ZONE_LOWER <= x <= ZONE_UPPER else 'EDGE'


def quat_to_yaw(q) -> float:
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


def build_waypoint_order(count: int) -> list[dict]:
    return [
        {
            'id': f'航点{i + 1}',
            'role': f'自定义航点 {i + 1}',
            'expected_zone': None,
        }
        for i in range(count)
    ]


def ask_waypoint_count() -> int:
    print('=' * 70)
    print('📌 任意数量航点坐标采集')
    print('=' * 70)
    while True:
        try:
            raw = input('请输入要记录的航点数量: ').strip()
            count = int(raw)
            if count <= 0:
                print('❌ 数量必须大于 0，请重新输入。')
                continue
            if count > 999:
                print('❌ 数量过大（最大 999），请重新输入。')
                continue
            return count
        except ValueError:
            print('❌ 请输入有效整数。')
        except EOFError:
            print('\n未输入数量，退出。')
            sys.exit(0)


class WaypointRecorderAll(Node):
    """任意数量航点坐标采集节点"""

    def __init__(self, waypoint_order: list[dict]):
        super().__init__('record_waypoints_all')
        self._waypoint_order = waypoint_order
        self._total = len(waypoint_order)

        self._odom: Odometry | None = None
        self._odom_lock = threading.Lock()
        self._odom_sub = self.create_subscription(
            Odometry, '/aft_mapped_to_init', self._odom_cb, 10)

        self._aft_odom: Odometry | None = None
        self._aft_lock = threading.Lock()
        self._aft_sub = self.create_subscription(
            Odometry, '/aft_mapped_in_map', self._aft_cb, 10)

        self._current_zone: str | None = None
        self._zone_transitions: list[dict] = []

        self._wp_index = 0
        self._records: list[dict] = []
        self._running = True
        self._saved = False

        self._status_timer = self.create_timer(2.0, self._print_status)

        self.get_logger().info('=' * 70)
        self.get_logger().info('📌 任意数量航点坐标采集')
        self.get_logger().info(f'   目标数量: {self._total} 个航点')
        self.get_logger().info(
            f'   命名: 航点1 → 航点{self._total}'
        )
        self.get_logger().info(
            f'   区域边界: lower={ZONE_LOWER}, upper={ZONE_UPPER}, hyst={ZONE_HYSTERESIS}'
        )
        self.get_logger().info('')
        self.get_logger().info('操作: Enter=记录 | r=重录上一个 | s=跳过 | q=退出保存')
        self.get_logger().info('=' * 70)

    def _odom_cb(self, msg: Odometry):
        with self._odom_lock:
            self._odom = msg
        x = msg.pose.pose.position.x
        new_zone = determine_zone(x, self._current_zone)
        if new_zone != self._current_zone:
            old = self._current_zone
            self._current_zone = new_zone
            self._zone_transitions.append({
                'x': x, 'from': old, 'to': new_zone,
                'time': time.time(),
            })
            self.get_logger().info(
                f'🔀 区域切换: {old} → {new_zone} (x={x:.3f}m)')

    def _aft_cb(self, msg: Odometry):
        with self._aft_lock:
            self._aft_odom = msg

    def _print_status(self):
        if not self._running or self._wp_index >= self._total:
            return

        robot = self._get_robot_state()
        if not robot['available']:
            self.get_logger().info('⏳ 等待 /aft_mapped_to_init 数据...')
            return

        current_wp = self._waypoint_order[self._wp_index]
        zone_str = self._current_zone or '?'

        self.get_logger().info(
            f'📍 当前: ({robot["x"]:.3f}, {robot["y"]:.3f}, {robot["z"]:.3f}) '
            f'yaw={robot["yaw"]:.3f}rad({math.degrees(robot["yaw"]):.1f}°) | '
            f'区域: {zone_str} | '
            f'待采集: {current_wp["id"]} ({self._wp_index + 1}/{self._total})')

    def _get_robot_state(self) -> dict:
        with self._odom_lock:
            o = self._odom
        if o is None:
            return {'x': 0, 'y': 0, 'z': 0, 'yaw': 0, 'available': False}
        return {
            'x': o.pose.pose.position.x,
            'y': o.pose.pose.position.y,
            'z': o.pose.pose.position.z,
            'yaw': quat_to_yaw(o.pose.pose.orientation),
            'available': True,
        }

    def _get_aft_state(self) -> dict | None:
        with self._aft_lock:
            o = self._aft_odom
        if o is None:
            return None
        return {
            'x': o.pose.pose.position.x,
            'y': o.pose.pose.position.y,
            'z': o.pose.pose.position.z,
            'yaw': quat_to_yaw(o.pose.pose.orientation),
        }

    def record_current(self):
        if self._wp_index >= self._total:
            return

        robot = self._get_robot_state()
        aft = self._get_aft_state()
        wp = self._waypoint_order[self._wp_index]

        if not robot['available']:
            self.get_logger().error('❌ /aft_mapped_to_init 无数据，无法记录！')
            return

        expected_zone = zone_at_x(robot['x'])
        record = {
            'id': wp['id'],
            'role': wp['role'],
            'expected_zone': expected_zone,
            'actual_zone': self._current_zone or '?',
            'timestamp': datetime.now().isoformat(),
            'aft_mapped_to_init': {
                'x': round(robot['x'], 4),
                'y': round(robot['y'], 4),
                'z': round(robot['z'], 4),
                'yaw': round(robot['yaw'], 4),
            },
            'aft_mapped_in_map': {
                'x': round(aft['x'], 4),
                'y': round(aft['y'], 4),
                'z': round(aft['z'], 4),
                'yaw': round(aft['yaw'], 4),
            } if aft else None,
            'zone_transitions_during_nav': [
                {'x': round(t['x'], 3), 'from': t['from'], 'to': t['to']}
                for t in self._zone_transitions
            ],
        }

        self._records.append(record)

        self.get_logger().info('')
        self.get_logger().info('─' * 50)
        self.get_logger().info(
            f'📝 已记录 [{len(self._records)}/{self._total}] {wp["id"]}')
        self.get_logger().info(
            f'   aft_mapped_to_init: '
            f'({record["aft_mapped_to_init"]["x"]:.4f}, '
            f'{record["aft_mapped_to_init"]["y"]:.4f}, '
            f'{record["aft_mapped_to_init"]["z"]:.4f}) '
            f'yaw={record["aft_mapped_to_init"]["yaw"]:.4f}')
        if aft:
            self.get_logger().info(
                f'   aft_mapped_in_map: '
                f'({record["aft_mapped_in_map"]["x"]:.4f}, '
                f'{record["aft_mapped_in_map"]["y"]:.4f}, '
                f'{record["aft_mapped_in_map"]["z"]:.4f}) '
                f'yaw={record["aft_mapped_in_map"]["yaw"]:.4f}')
        self.get_logger().info(f'   区域: {record["actual_zone"]}')
        self.get_logger().info('─' * 50)

        self._wp_index += 1
        self._zone_transitions.clear()

        if self._wp_index >= self._total:
            self.get_logger().info('')
            self.get_logger().info(
                f'🎉 全部 {self._total} 个航点采集完成，正在保存...')
            self._save_and_exit()

    def rerecord_last(self):
        if not self._records:
            self.get_logger().warn('⚠️  没有已记录的上一个航点')
            return
        last = self._records.pop()
        self._wp_index -= 1
        self._zone_transitions.clear()
        self.get_logger().info(f'🔁 已撤销 {last["id"]}，请重新导航并确认')

    def skip_current(self):
        if self._wp_index >= self._total:
            return

        wp = self._waypoint_order[self._wp_index]
        record = {
            'id': wp['id'],
            'role': wp['role'],
            'expected_zone': None,
            'actual_zone': None,
            'timestamp': datetime.now().isoformat(),
            'aft_mapped_to_init': None,
            'aft_mapped_in_map': None,
            'zone_transitions_during_nav': [],
            'skipped': True,
        }
        self._records.append(record)
        self.get_logger().warn(f'⏭️  已跳过 {wp["id"]}')
        self._wp_index += 1
        self._zone_transitions.clear()

        if self._wp_index >= self._total:
            self.get_logger().info('🎉 全部航点处理完成（部分已跳过），正在保存...')
            self._save_and_exit()

    def _save_and_exit(self):
        self._save_records()
        self._running = False

    def _save_records(self):
        if self._saved or not self._records:
            return

        log_dir = os.path.dirname(os.path.realpath(__file__))
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        path = os.path.join(log_dir, f'recorded_waypoints_{ts}.yaml')

        with open(path, 'w', encoding='utf-8') as f:
            f.write('# 航点坐标采集记录 (record_waypoints_all.py)\n')
            f.write(f'# 采集时间: {datetime.now()}\n')
            f.write(f'# 航点数量: {len(self._records)}\n')
            f.write(
                f'# 区域边界: lower={ZONE_LOWER}, upper={ZONE_UPPER}, '
                f'hyst={ZONE_HYSTERESIS}\n'
            )
            ids = ' → '.join(r['id'] for r in self._records)
            f.write(f'# 采集顺序: {ids}\n')
            f.write('\n')
            f.write('waypoints:\n')
            for r in self._records:
                f.write(f'  - id: "{r["id"]}"\n')
                f.write(f'    role: "{r["role"]}"\n')
                if r.get('expected_zone'):
                    f.write(f'    expected_zone: "{r["expected_zone"]}"\n')
                if r.get('actual_zone'):
                    f.write(f'    actual_zone: "{r["actual_zone"]}"\n')
                if r.get('skipped'):
                    f.write('    skipped: true\n')
                if r.get('aft_mapped_to_init'):
                    se = r['aft_mapped_to_init']
                    f.write('    aft_mapped_to_init:\n')
                    f.write(f'      x: {se["x"]}\n')
                    f.write(f'      y: {se["y"]}\n')
                    f.write(f'      z: {se["z"]}\n')
                    f.write(f'      yaw: {se["yaw"]}\n')
                if r.get('aft_mapped_in_map'):
                    am = r['aft_mapped_in_map']
                    f.write('    aft_mapped_in_map:\n')
                    f.write(f'      x: {am["x"]}\n')
                    f.write(f'      y: {am["y"]}\n')
                    f.write(f'      z: {am["z"]}\n')
                    f.write(f'      yaw: {am["yaw"]}\n')
                zt = r.get('zone_transitions_during_nav') or []
                if zt:
                    f.write('    zone_transitions:\n')
                    for t in zt:
                        f.write(f'      - x: {t["x"]}\n')
                        f.write(f'        from: "{t["from"]}"\n')
                        f.write(f'        to: "{t["to"]}"\n')
                f.write('\n')

        self._saved = True
        self.get_logger().info(f'💾 已保存: {path}')

        self.get_logger().info('')
        self.get_logger().info('=' * 60)
        self.get_logger().info('📋 采集结果速查 (aft_mapped_to_init):')
        self.get_logger().info(
            f'   {"航点":<8} {"x":>8} {"y":>8} {"z":>8} {"yaw":>8} {"区域":<8}'
        )
        self.get_logger().info(
            f'   {"─"*8} {"─"*8} {"─"*8} {"─"*8} {"─"*8} {"─"*8}'
        )
        for r in self._records:
            if r.get('skipped'):
                self.get_logger().info(f'   {r["id"]:<8} {"(跳过)":>36}')
            else:
                se = r['aft_mapped_to_init']
                self.get_logger().info(
                    f'   {r["id"]:<8} '
                    f'{se["x"]:>8.4f} {se["y"]:>8.4f} {se["z"]:>8.4f} '
                    f'{se["yaw"]:>8.4f} {r["actual_zone"]:<8}'
                )
        self.get_logger().info('=' * 60)


def interactive_loop(node: WaypointRecorderAll):
    print()
    print('🕹️  在 RViz 中手动导航机器人到目标位置，到达后按 Enter 记录。')
    print(f'   共需采集 {node._total} 个航点，下一个: {node._waypoint_order[0]["id"]}')
    print('   Enter=记录 | r=重录 | s=跳过 | q=退出')
    print()

    while node._running and node._wp_index < node._total:
        current_wp = node._waypoint_order[node._wp_index]
        prompt = (
            f'[{current_wp["id"]} {node._wp_index + 1}/{node._total}] '
            f'到达后按 Enter 记录 > '
        )

        try:
            user_input = input(prompt).strip().lower()
        except EOFError:
            break

        if not node._running:
            break

        if user_input == '':
            node.record_current()
        elif user_input == 'r':
            node.rerecord_last()
        elif user_input == 's':
            node.skip_current()
        elif user_input == 'q':
            node.get_logger().info('👋 用户提前退出。')
            break
        else:
            print('   未知命令 — Enter=记录 r=重录 s=跳过 q=退出')

    if node._records and not node._saved:
        node._save_records()


def main(args=None):
    count = ask_waypoint_count()
    waypoint_order = build_waypoint_order(count)

    rclpy.init(args=args)
    node = WaypointRecorderAll(waypoint_order)

    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(node)

    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()

    try:
        interactive_loop(node)
    except KeyboardInterrupt:
        node.get_logger().info('⏹️  Ctrl+C 中断')
    finally:
        node._running = False
        if node._records and not node._saved:
            node._save_records()
        executor.shutdown()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
