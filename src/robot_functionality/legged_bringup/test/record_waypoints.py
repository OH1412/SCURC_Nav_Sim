#!/usr/bin/env python3
# ============================================================================
# 航点坐标采集助手
# ============================================================================
# 手动在 RViz 中用 NavigateToPose 导航机器人，到达目标后按 Enter 记录坐标。
# 按顺序采集: 航点1 → 2 → 3 → 4 → 5
#
# 用法:
#   终端1:  ros2 launch legged_bringup navigation.launch.py  (或 bringup)
#   终端2:  ros2 run legged_bringup record_waypoints.py
#
# 操作:
#   Enter  - 记录当前坐标（自动推进到下一航点）
#   r      - 重新记录上一个航点（覆盖）
#   s      - 跳过当前航点（坐标留空）
#   q      - 退出并保存已记录的坐标
#   Ctrl+C - 退出并保存
# ============================================================================

import math
import os
import signal
import sys
import threading
import time
from datetime import datetime

import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from nav_msgs.msg import Odometry


# ============================================================================
# 区域判定 — 与 position_based_param_switcher 一致
# ============================================================================
ZONE_LOWER = 1.35
ZONE_UPPER = 4.0
ZONE_HYSTERESIS = 0.1


def determine_zone(x: float, current_zone: str | None) -> str:
    """迟滞区域判定"""
    if current_zone is None:
        if ZONE_LOWER <= x <= ZONE_UPPER:
            return 'MIDDLE'
        return 'EDGE'
    elif current_zone == 'EDGE':
        lo = ZONE_LOWER + ZONE_HYSTERESIS  # 1.45
        hi = ZONE_UPPER - ZONE_HYSTERESIS  # 3.4
        if lo <= x <= hi:
            return 'MIDDLE'
        return 'EDGE'
    else:  # 'MIDDLE'
        lo = ZONE_LOWER - ZONE_HYSTERESIS  # 1.25
        hi = ZONE_UPPER + ZONE_HYSTERESIS  # 3.6
        if x < lo or x > hi:
            return 'EDGE'
        return 'MIDDLE'


def quat_to_yaw(q) -> float:
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


# ============================================================================
# 采集顺序
# ============================================================================
WAYPOINT_ORDER = [
    {"id": "航点1", "role": "过渡对齐点", "expected_zone": "EDGE"},
    {"id": "航点2", "role": "吸取第二行(左#5右#4)", "expected_zone": "MIDDLE"},
    {"id": "航点3", "role": "吸取第一行(左#1右#0)", "expected_zone": "MIDDLE"},
    {"id": "航点4", "role": "中间→边缘过渡", "expected_zone": "EDGE"},
    {"id": "航点5", "role": "放置区", "expected_zone": "EDGE"},
]


class WaypointRecorder(Node):
    """航点坐标采集节点"""

    def __init__(self):
        super().__init__('record_waypoints')

        # ---- 实时坐标 ----
        self._odom: Odometry | None = None
        self._odom_lock = threading.Lock()
        self._odom_sub = self.create_subscription(
            Odometry, '/state_estimation', self._odom_cb, 10)

        # 可选: aft_mapped 作为参考
        self._aft_odom: Odometry | None = None
        self._aft_lock = threading.Lock()
        self._aft_sub = self.create_subscription(
            Odometry, '/aft_mapped_in_map', self._aft_cb, 10)

        # ---- 区域追踪 ----
        self._current_zone: str | None = None
        self._zone_transitions: list[dict] = []

        # ---- 采集状态 ----
        self._wp_index = 0           # 当前要采集的航点索引 (0=航点1)
        self._records: list[dict] = []   # 已采集的记录
        self._running = True

        # ---- 状态输出定时器 ----
        self._status_timer = self.create_timer(2.0, self._print_status)

        self.get_logger().info('=' * 70)
        self.get_logger().info('📌 航点坐标采集助手')
        self.get_logger().info(f'   采集顺序: {" → ".join(w["id"] for w in WAYPOINT_ORDER)}')
        self.get_logger().info(f'   区域边界: lower={ZONE_LOWER}, upper={ZONE_UPPER}, hyst={ZONE_HYSTERESIS}')
        self.get_logger().info('')
        self.get_logger().info('操作: Enter=记录 | r=重录上一个 | s=跳过 | q=退出保存')
        self.get_logger().info('=' * 70)

    # ------------------------------------------------------------------
    # 里程计回调
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # 实时状态
    # ------------------------------------------------------------------
    def _print_status(self):
        robot = self._get_robot_state()
        if not robot['available']:
            self.get_logger().info('⏳ 等待 /state_estimation 数据...')
            return

        current_wp = WAYPOINT_ORDER[self._wp_index]
        zone_str = f"{self._current_zone or '?'}"
        expected = current_wp['expected_zone']
        match = '✅' if zone_str == expected else '⚠️'

        self.get_logger().info(
            f'📍 当前: ({robot["x"]:.3f}, {robot["y"]:.3f}, {robot["z"]:.3f}) '
            f'yaw={robot["yaw"]:.3f}rad({math.degrees(robot["yaw"]):.1f}°) | '
            f'区域: {zone_str} {match}(预期{expected}) | '
            f'待采集: {current_wp["id"]}({self._wp_index+1}/{len(WAYPOINT_ORDER)})')

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

    # ------------------------------------------------------------------
    # 记录当前航点
    # ------------------------------------------------------------------
    def record_current(self):
        """记录当前坐标作为当前航点"""
        robot = self._get_robot_state()
        aft = self._get_aft_state()
        wp = WAYPOINT_ORDER[self._wp_index]

        if not robot['available']:
            self.get_logger().error('❌ /state_estimation 无数据，无法记录！')
            return

        record = {
            'id': wp['id'],
            'role': wp['role'],
            'expected_zone': wp['expected_zone'],
            'actual_zone': self._current_zone or '?',
            'timestamp': datetime.now().isoformat(),
            'state_estimation': {
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

        # 打印记录摘要
        zone_ok = record['actual_zone'] == wp['expected_zone']
        zone_icon = '✅' if zone_ok else '⚠️ 不匹配!'
        self.get_logger().info('')
        self.get_logger().info('─' * 50)
        self.get_logger().info(
            f'📝 已记录 [{len(self._records)}/{len(WAYPOINT_ORDER)}] {wp["id"]} '
            f'({wp["role"]})')
        self.get_logger().info(
            f'   state_estimation: '
            f'({record["state_estimation"]["x"]:.4f}, '
            f'{record["state_estimation"]["y"]:.4f}, '
            f'{record["state_estimation"]["z"]:.4f}) '
            f'yaw={record["state_estimation"]["yaw"]:.4f}')
        if aft:
            self.get_logger().info(
                f'   aft_mapped_in_map: '
                f'({record["aft_mapped_in_map"]["x"]:.4f}, '
                f'{record["aft_mapped_in_map"]["y"]:.4f}, '
                f'{record["aft_mapped_in_map"]["z"]:.4f}) '
                f'yaw={record["aft_mapped_in_map"]["yaw"]:.4f}')
        self.get_logger().info(
            f'   区域: {record["actual_zone"]} {zone_icon} '
            f'(预期 {wp["expected_zone"]})')
        if self._zone_transitions:
            self.get_logger().info(
                f'   本段区域切换: {len(self._zone_transitions)} 次')
            for t in self._zone_transitions:
                self.get_logger().info(
                    f'     {t["from"]} → {t["to"]} (x={t["x"]:.3f})')
        else:
            self.get_logger().info('   本段区域切换: 无')
        self.get_logger().info('─' * 50)

        # 推进索引 + 重置区域切换记录
        self._wp_index += 1
        self._zone_transitions.clear()

        # 检查是否全部完成
        if self._wp_index >= len(WAYPOINT_ORDER):
            self.get_logger().info('')
            self.get_logger().info('🎉 全部 5 个航点采集完成！')
            self._save_and_exit()

    def rerecord_last(self):
        """重新记录上一个航点"""
        if not self._records:
            self.get_logger().warn('⚠️  没有已记录的上一个航点')
            return

        last = self._records.pop()
        self._wp_index -= 1
        self._zone_transitions.clear()
        self.get_logger().info(f'🔁 已撤销 {last["id"]}，请重新导航并确认')

    def skip_current(self):
        """跳过当前航点"""
        wp = WAYPOINT_ORDER[self._wp_index]
        record = {
            'id': wp['id'],
            'role': wp['role'],
            'expected_zone': wp['expected_zone'],
            'actual_zone': None,
            'timestamp': datetime.now().isoformat(),
            'state_estimation': None,
            'aft_mapped_in_map': None,
            'zone_transitions_during_nav': [],
            'skipped': True,
        }
        self._records.append(record)
        self.get_logger().warn(f'⏭️  已跳过 {wp["id"]}')
        self._wp_index += 1
        self._zone_transitions.clear()

        if self._wp_index >= len(WAYPOINT_ORDER):
            self.get_logger().info('🎉 全部航点处理完成（部分已跳过）。')
            self._save_and_exit()

    # ------------------------------------------------------------------
    # 退出并保存
    # ------------------------------------------------------------------
    def _save_and_exit(self):
        """保存记录到文件并退出"""
        self._save_records()
        self._running = False

    def _save_records(self):
        """将记录写入 YAML 格式文件"""
        log_dir = os.path.dirname(os.path.realpath(__file__))
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        path = os.path.join(log_dir, f'recorded_waypoints_{ts}.yaml')

        with open(path, 'w', encoding='utf-8') as f:
            f.write(f'# 航点坐标采集记录\n')
            f.write(f'# 采集时间: {datetime.now()}\n')
            f.write(f'# 区域边界: lower={ZONE_LOWER}, upper={ZONE_UPPER}, hyst={ZONE_HYSTERESIS}\n')
            f.write(f'# 采集顺序: {" → ".join(w["id"] for w in WAYPOINT_ORDER)}\n')
            f.write('\n')
            f.write(f'waypoints:\n')
            for r in self._records:
                f.write(f'  - id: "{r["id"]}"\n')
                f.write(f'    role: "{r["role"]}"\n')
                f.write(f'    expected_zone: "{r["expected_zone"]}"\n')
                f.write(f'    actual_zone: "{r["actual_zone"]}"\n')
                if r.get('skipped'):
                    f.write(f'    skipped: true\n')
                if r.get('state_estimation'):
                    se = r['state_estimation']
                    f.write(f'    state_estimation:\n')
                    f.write(f'      x: {se["x"]}\n')
                    f.write(f'      y: {se["y"]}\n')
                    f.write(f'      z: {se["z"]}\n')
                    f.write(f'      yaw: {se["yaw"]}\n')
                if r.get('aft_mapped_in_map'):
                    am = r['aft_mapped_in_map']
                    f.write(f'    aft_mapped_in_map:\n')
                    f.write(f'      x: {am["x"]}\n')
                    f.write(f'      y: {am["y"]}\n')
                    f.write(f'      z: {am["z"]}\n')
                    f.write(f'      yaw: {am["yaw"]}\n')
                if r.get('zone_transitions_during_nav'):
                    zt = r['zone_transitions_during_nav']
                    if zt:
                        f.write(f'    zone_transitions:\n')
                        for t in zt:
                            f.write(f'      - x: {t["x"]}\n')
                            f.write(f'        from: "{t["from"]}"\n')
                            f.write(f'        to: "{t["to"]}"\n')
                f.write('\n')

        self.get_logger().info(f'💾 已保存: {path}')

        # 同时打印速查表
        self.get_logger().info('')
        self.get_logger().info('=' * 60)
        self.get_logger().info('📋 采集结果速查 (state_estimation):')
        self.get_logger().info(f'   {"航点":<8} {"x":>8} {"y":>8} {"z":>8} {"区域":<8} {"匹配"}')
        self.get_logger().info(f'   {"─"*8} {"─"*8} {"─"*8} {"─"*8} {"─"*8} {"─"*4}')
        for r in self._records:
            if r.get('skipped'):
                self.get_logger().info(f'   {r["id"]:<8} {"(跳过)":>27}')
            else:
                se = r['state_estimation']
                match = '✅' if r['actual_zone'] == r['expected_zone'] else '⚠️'
                self.get_logger().info(
                    f'   {r["id"]:<8} '
                    f'{se["x"]:>8.4f} {se["y"]:>8.4f} {se["z"]:>8.4f} '
                    f'{r["actual_zone"]:<8} {match}')
        self.get_logger().info('=' * 60)


# ============================================================================
# 交互式主循环 (在主线程运行)
# ============================================================================
def interactive_loop(node: WaypointRecorder):
    """终端交互循环 — 在后台 ROS 线程 spinning 的同时处理用户输入"""
    print()
    print('🕹️  在 RViz 中手动导航机器人到目标位置，到达后按 Enter 记录。')
    print(f'   下一个待采集: {WAYPOINT_ORDER[0]["id"]}')
    print('   Enter=记录 | r=重录 | s=跳过 | q=退出')
    print()

    while node._running:
        current_wp = WAYPOINT_ORDER[min(node._wp_index, len(WAYPOINT_ORDER) - 1)]
        prompt = f'[{current_wp["id"]}] 到达后按 Enter 记录 > '

        try:
            user_input = input(prompt).strip().lower()
        except EOFError:
            break

        if not node._running:
            break

        if user_input == '':
            # Enter → 记录
            node.record_current()
        elif user_input == 'r':
            node.rerecord_last()
        elif user_input == 's':
            node.skip_current()
        elif user_input == 'q':
            node.get_logger().info('👋 用户退出。')
            break
        else:
            print(f'   未知命令: "{user_input}" — Enter=记录 r=重录 s=跳过 q=退出')

    # 退出前保存
    if node._records:
        node._save_records()
    else:
        node.get_logger().info('没有记录任何航点。')


def main(args=None):
    rclpy.init(args=args)

    node = WaypointRecorder()

    # 后台线程运行 ROS spin
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(node)

    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()

    # 主线程处理交互输入
    try:
        interactive_loop(node)
    except KeyboardInterrupt:
        node.get_logger().info('⏹️  Ctrl+C 中断')
    finally:
        node._running = False
        if node._records:
            node._save_records()
        executor.shutdown()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
