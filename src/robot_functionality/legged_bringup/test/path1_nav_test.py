#!/usr/bin/env python3
# ============================================================================
# 路径1 纯导航走点测试
# ============================================================================
# 逐段发送 NavigateToPose Action，走完路径1的 11 段航点序列。
# 订阅 /state_estimation 获取实时坐标，内嵌迟滞区域判定逻辑，
# 在到达每个航点时输出详细日志（终端 + 文件）。
#
# 航点坐标硬编码在 HARDCODED_WAYPOINTS 字典中。
# 也可通过 --ros-args -p waypoints_config:=/path/to/waypoints.yaml 覆盖。
#
# 用法:
#   ros2 run legged_bringup path1_nav_test.py
#   ros2 run legged_bringup path1_nav_test.py --ros-args -p waypoints_config:=/path/to/waypoints.yaml
#   ros2 run legged_bringup path1_nav_test.py --ros-args -p startup_delay:=10.0
# ============================================================================

import math
import os
import sys
import time
import threading
from datetime import datetime

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor

from geometry_msgs.msg import PoseStamped, Quaternion
from action_msgs.msg import GoalStatusArray
from nav2_msgs.action import ComputePathToPose, NavigateToPose
from nav_msgs.msg import Odometry, Path


# ============================================================================
# 区域判定常量 — 与 position_based_param_switcher 一致
# ============================================================================
ZONE_LOWER = 1.35         # 中间区下边界
ZONE_UPPER = 4.0          # 中间区上边界
ZONE_HYSTERESIS = 0.1     # 迟滞余量

# 首次判定阈值
ZONE_FIRST_LO = ZONE_LOWER           # 1.35 ≤ x ≤ 4.0 → MIDDLE
ZONE_FIRST_HI = ZONE_UPPER

# EDGE → MIDDLE: x 需在 [1.45, 3.9] 内
ZONE_EDGE_TO_MIDDLE_LO = ZONE_LOWER + ZONE_HYSTERESIS  # 1.45
ZONE_EDGE_TO_MIDDLE_HI = ZONE_UPPER - ZONE_HYSTERESIS  # 3.9

# MIDDLE → EDGE: x < 1.25 或 x > 4.1
ZONE_MIDDLE_TO_EDGE_LO = ZONE_LOWER - ZONE_HYSTERESIS  # 1.25
ZONE_MIDDLE_TO_EDGE_HI = ZONE_UPPER + ZONE_HYSTERESIS  # 4.1


# ============================================================================
# 路径1: 11 段航点 ID 顺序（定义哪些航点依次走）
# ============================================================================
# WP1→WP2→WP3(🧲吸箱1)→WP4→WP5(📦放箱1)→WP4→WP3→WP2(🧲吸箱2)→WP3→WP4→WP5(📦放箱2)
# 策略: 到达目标点必须经过之前所有中间点
PATH1_ID_SEQUENCE = [
    "航点1", "航点2", "航点3", "航点4", "航点5",   # 前半: 吸箱1+放置1
    "航点4", "航点3", "航点2",                     # 后半: 返回吸取箱2
    "航点3", "航点4", "航点5",                     # 终点: 放置箱2
]

# 航点坐标硬编码（2026-06-30 23:17 采集）
# 可通过 YAML 配置文件覆盖: --ros-args -p waypoints_config:=/path/to/waypoints.yaml
HARDCODED_WAYPOINTS: dict[str, dict] = {
    "航点1": {"role": "过渡对齐点",             "x": 0.9,     "y": -0.8571, "yaw": -0.0664},
    "航点2": {"role": "吸取第二行(左#5右#4)",   "x": 2.1299,  "y": -0.8171, "yaw": -0.0664},
    "航点3": {"role": "吸取第一行(左#1右#0)",   "x": 3.1121,  "y": -0.868,  "yaw": -0.0467},
    "航点4": {"role": "中间→边缘过渡",          "x": 4.3698,  "y": -0.8689, "yaw": -0.0106},
    "航点5": {"role": "放置区",                 "x": 5.3502,  "y": -0.657,  "yaw": -0.0193},
}
# key: (段号0-based), value: 手动说明；不在 dict 里的自动生成
_CUSTOM_DESCS: dict[int, str] = {
    0:  "启动区→航点1(过渡,边缘策略对齐yaw/y)",
    1:  "航点1→航点2(准备吸取区)",
    2:  "航点2→航点3(🧲 吸取第一个箱子 左#1右#0)",
    3:  "航点3→航点4(中间→边缘过渡)",
    4:  "航点4→航点5(📦 第一次放置箱子)",
    5:  "航点5→航点4(返回: 边缘过渡点)",
    6:  "航点4→航点3(返回: 经过吸取区)",
    7:  "航点3→航点2(🧲 吸取第二个箱子 左#5右#4)",
    8:  "航点2→航点3(经过中间点)",
    9:  "航点3→航点4(经过过渡点)",
    10: "航点4→航点5(📦 第二次放置箱子)",
}


def _make_desc(index: int, wp_id: str, role: str) -> str:
    """根据段号和角色自动生成航点说明"""
    if index in _CUSTOM_DESCS:
        return _CUSTOM_DESCS[index]

    # 根据 id 和位置生成描述
    short_roles = {
        "过渡对齐点": "过渡,边缘对齐",
        "吸取第二行(左#5右#4)": "第二行箱子区",
        "吸取第一行(左#1右#0)": "第一行箱子区",
        "中间→边缘过渡": "中间策略直走,过渡到边缘区",
        "放置区": "放置区",
        "边缘→中间过渡": "退回,边缘策略重新对齐",
    }
    role_desc = short_roles.get(role, role)

    # 查找上一个不同的航点作为起点描述
    return f"→{wp_id}({role_desc})"


def determine_zone(x: float, current_zone: str | None) -> str:
    """迟滞区域判定 — 和 position_based_param_switcher 完全一致"""
    if current_zone is None:
        if ZONE_FIRST_LO <= x <= ZONE_FIRST_HI:
            return 'MIDDLE'
        return 'EDGE'
    elif current_zone == 'EDGE':
        if ZONE_EDGE_TO_MIDDLE_LO <= x <= ZONE_EDGE_TO_MIDDLE_HI:
            return 'MIDDLE'
        return 'EDGE'
    else:  # 'MIDDLE'
        if x < ZONE_MIDDLE_TO_EDGE_LO or x > ZONE_MIDDLE_TO_EDGE_HI:
            return 'EDGE'
        return 'MIDDLE'


def zone_description(zone: str) -> str:
    """区域的中文策略描述"""
    if zone == 'MIDDLE':
        return 'MIDDLE (yaw锁0, vy=0, 纯X单轴)'
    return 'EDGE (yaw自由, vy=±1.1, 可旋转对齐)'


def quat_to_yaw(q: Quaternion) -> float:
    """四元数 → 偏航角 (rad)"""
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


# ============================================================================
# YAML 配置加载
# ============================================================================
def load_waypoints_yaml(filepath: str) -> list[dict]:
    """
    从录制的航点 YAML 文件加载坐标，按 PATH1_ID_SEQUENCE 生成 16 段序列。

    YAML 格式 (与 record_waypoints.py 输出一致):
        waypoints:
          - id: "航点1"
            role: "过渡对齐点"
            state_estimation:
              x: 1.1887
              y: -0.8989
              z: 0.1024
              yaw: -0.0727
          ...
    返回:
        [{"id": "航点1", "x": 1.1887, "y": -0.8989, "yaw": -0.0727, "desc": "..."}, ...]
    """
    try:
        import yaml
    except ImportError:
        # Fallback: 手动解析简单 YAML
        return _parse_waypoints_manual(filepath)

    with open(filepath, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    return _build_sequence_from_data(data)


def _parse_waypoints_manual(filepath: str) -> list[dict]:
    """手动解析 recorded_waypoints YAML (无需 PyYAML)"""
    lookup: dict[str, dict] = {}
    current_id = None
    in_state_est = False

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            stripped = line.strip()

            # 航点 id
            if stripped.startswith('- id:') or stripped.startswith('id:'):
                current_id = stripped.split('"')[1] if '"' in stripped else stripped.split(':')[1].strip()
                in_state_est = False

            # role
            elif stripped.startswith('role:') and current_id:
                role = stripped.split('"')[1] if '"' in stripped else ''
                lookup[current_id] = {'role': role}

            # state_estimation 块
            elif stripped.startswith('state_estimation:'):
                in_state_est = True

            elif in_state_est and current_id:
                if stripped.startswith('x:'):
                    lookup[current_id]['x'] = float(stripped.split(':')[1].strip())
                elif stripped.startswith('y:'):
                    lookup[current_id]['y'] = float(stripped.split(':')[1].strip())
                elif stripped.startswith('yaw:'):
                    lookup[current_id]['yaw'] = float(stripped.split(':')[1].strip())
                    in_state_est = False  # yaw is last in state_estimation

    return _build_sequence_from_lookup(lookup)


def _build_sequence_from_data(data: dict) -> list[dict]:
    """从 yaml.safe_load 的结果构建序列"""
    lookup: dict[str, dict] = {}
    for wp in data.get('waypoints', []):
        se = wp.get('state_estimation', {})
        lookup[wp['id']] = {
            'role': wp.get('role', ''),
            'x': float(se.get('x', 0)),
            'y': float(se.get('y', 0)),
            'yaw': float(se.get('yaw', 0.0)),
        }
    return _build_sequence_from_lookup(lookup)


def _build_sequence_from_lookup(lookup: dict[str, dict]) -> list[dict]:
    """根据 ID 查找表和 PATH1_ID_SEQUENCE 构建 16 段序列"""
    if not lookup:
        raise RuntimeError('YAML 中没有 waypoints 数据！')

    sequence = []
    for i, wp_id in enumerate(PATH1_ID_SEQUENCE):
        if wp_id not in lookup:
            raise KeyError(
                f'航点 "{wp_id}" (段{i+1}) 在配置文件中未找到！'
                f'可用航点: {list(lookup.keys())}')

        coords = lookup[wp_id]
        desc = _make_desc(i, wp_id, coords.get('role', ''))
        sequence.append({
            'id': wp_id,
            'x': coords['x'],
            'y': coords['y'],
            'yaw': coords['yaw'],
            'desc': desc,
        })
    return sequence


# ============================================================================
# 主测试节点
# ============================================================================
class Path1NavTest(Node):
    """路径1 纯导航走点测试节点"""

    def __init__(self):
        super().__init__('path1_nav_test')

        # ---- 参数 ----
        self.declare_parameter('startup_delay', 7.0)
        self.declare_parameter('nav_timeout', 120.0)
        self.declare_parameter('stop_on_failure', True)

        # 航点配置文件路径 (默认: 空 → 使用硬编码数据)
        default_config = ''
        self.declare_parameter('waypoints_config', default_config)

        self._startup_delay = self.get_parameter('startup_delay').value
        self._nav_timeout = self.get_parameter('nav_timeout').value
        self._stop_on_failure = self.get_parameter('stop_on_failure').value
        config_path = self.get_parameter('waypoints_config').value

        # ---- 加载航点序列 ----
        if config_path:
            # 用户指定了 YAML 配置文件，从文件加载
            try:
                self._sequence = load_waypoints_yaml(config_path)
                self.get_logger().info(f'✅ 从配置文件加载了 {len(self._sequence)} 段航点序列')
                self.get_logger().info(f'   配置文件: {config_path}')
            except FileNotFoundError:
                self.get_logger().error(f'❌ 航点配置文件不存在: {config_path}')
                self.get_logger().error('   请先运行 record_waypoints.py 录制航点，或通过参数指定路径:')
                self.get_logger().error('   --ros-args -p waypoints_config:=/path/to/waypoints.yaml')
                raise
            except Exception as e:
                self.get_logger().error(f'❌ 加载航点配置失败: {e}')
                raise
        else:
            # 使用硬编码航点
            self._sequence = _build_sequence_from_lookup(HARDCODED_WAYPOINTS)
            self.get_logger().info(f'✅ 使用硬编码航点，共 {len(self._sequence)} 段')
            self.get_logger().info(f'   采集时间: 2026-06-30 23:17')

        # ---- 日志文件 ----
        log_dir = os.path.dirname(os.path.realpath(__file__))
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self._log_path = os.path.join(log_dir, f'path1_nav_log_{timestamp}.txt')
        self._log_file = open(self._log_path, 'w', encoding='utf-8')
        self._log_file.write(f'路径1 导航走点测试  |  开始: {datetime.now()}\n')
        self._log_file.write(f'配置文件: {config_path}\n')
        self._log_file.write(f'区域边界: lower={ZONE_LOWER}, upper={ZONE_UPPER}, hysteresis={ZONE_HYSTERESIS}\n')
        self._log_file.write(f'航点数: {len(self._sequence)}\n')
        self._log_file.write('=' * 70 + '\n\n')
        self._log_file.flush()

        # ---- 导航 Action 客户端 ----
        self._nav_ac = ActionClient(self, NavigateToPose, 'navigate_to_pose')

        # ---- 规划器 Action 客户端 — 诊断探针 ----
        self._cp_ac = ActionClient(self, ComputePathToPose, 'compute_path_to_pose')

        # ---- 实时坐标订阅 (/state_estimation) ----
        self._current_odom: Odometry | None = None
        self._odom_lock = threading.Lock()
        self._odom_sub = self.create_subscription(
            Odometry, '/state_estimation', self._odom_callback, 10)

        # ---- 全局规划订阅 (/plan) — 诊断用 ----
        self._last_plan: Path | None = None
        self._plan_received_time: float = 0.0
        self._plan_lock = threading.Lock()
        self._plan_sub = self.create_subscription(
            Path, '/plan', self._plan_callback, 10)

        # ---- 规划器 action 状态订阅 — 诊断 ComputePathToPose 是否被调用 ----
        self._plan_action_status_history: list[dict] = []  # [{time, status_list}, ...]
        self._plan_action_status_lock = threading.Lock()
        self._plan_action_status_sub = self.create_subscription(
            GoalStatusArray, '/compute_path_to_pose/_action/status',
            self._plan_action_status_cb, 10)

        # ---- 本段规划追踪 ----
        self._leg_plan_count = 0
        self._leg_plan_first_time: float = 0.0
        self._leg_plan_last_time: float = 0.0

        # ---- 区域追踪 ----
        self._current_zone: str | None = None
        self._zone_transitions: list[dict] = []
        self._leg_start_time: float = 0.0
        self._leg_start_zone: str | None = None

        # ---- 状态机 ----
        self._step_index = -1
        self._nav_goal_handle = None
        self._leg_nav_failed = False

        # ---- 启动 ----
        self.get_logger().info('=' * 70)
        self.get_logger().info('路径1 导航走点测试')
        self.get_logger().info(
            f'航点: {len(self._sequence)} 段 | '
            f'启动延迟: {self._startup_delay}s | '
            f'超时: {self._nav_timeout}s | '
            f'失败中止: {self._stop_on_failure}')
        self.get_logger().info(
            f'区域边界: lower={ZONE_LOWER}, upper={ZONE_UPPER}, hysteresis={ZONE_HYSTERESIS}')
        self.get_logger().info(f'日志文件: {self._log_path}')
        self.get_logger().info('=' * 70)

        # ---- 打印航点速览 ----
        self._log('')
        self._log('📋 航点序列速览:')
        self._log(f'   {"#":<4} {"航点":<8} {"x":>8} {"y":>8} {"yaw":>8} {"预期区域":<12} {"说明"}')
        self._log(f'   {"-"*4} {"-"*8} {"-"*8} {"-"*8} {"-"*8} {"-"*12} {"-"*30}')

        for i, wp in enumerate(self._sequence):
            exp_zone = 'MIDDLE' if ZONE_LOWER <= wp['x'] <= ZONE_UPPER else 'EDGE'
            short_desc = wp['desc'].split('(')[0] if '(' in wp['desc'] else wp['desc'][:28]
            self._log(f'   {i+1:<4} {wp["id"]:<8} {wp["x"]:>8.3f} {wp["y"]:>8.3f} '
                      f'{wp["yaw"]:>8.3f} {exp_zone:<12} {short_desc}')
        self._log('')

        # 延迟后启动第一段
        self._startup_timer = self.create_timer(
            self._startup_delay, self._start_mission)

    # ------------------------------------------------------------------
    # 日志输出（终端 + 文件）
    # ------------------------------------------------------------------
    def _log(self, msg: str):
        self.get_logger().info(msg)
        self._log_file.write(msg + '\n')
        self._log_file.flush()

    def _log_separator(self, char: str = '='):
        self._log(char * 70)

    # ------------------------------------------------------------------
    # 里程计回调
    # ------------------------------------------------------------------
    def _odom_callback(self, msg: Odometry):
        with self._odom_lock:
            self._current_odom = msg

        x = msg.pose.pose.position.x
        new_zone = determine_zone(x, self._current_zone)

        if new_zone != self._current_zone:
            old_zone = self._current_zone
            self._current_zone = new_zone
            transition = {
                'x': x, 'from': old_zone, 'to': new_zone, 'time': time.time(),
            }
            self._zone_transitions.append(transition)
            self.get_logger().info(
                f'🔀 区域切换: {old_zone} → {new_zone} (x={x:.3f}m)')

    # ------------------------------------------------------------------
    # 全局规划回调 — 诊断段4假成功
    # ------------------------------------------------------------------
    def _plan_callback(self, msg: Path):
        t_now = time.time()
        with self._plan_lock:
            self._last_plan = msg
            self._plan_received_time = t_now
        self._leg_plan_count += 1
        if self._leg_plan_first_time == 0.0:
            self._leg_plan_first_time = t_now
        self._leg_plan_last_time = t_now

    # ------------------------------------------------------------------
    # 规划器 action 状态回调 — 诊断 ComputePathToPose 生命周期
    # ------------------------------------------------------------------
    def _plan_action_status_cb(self, msg: GoalStatusArray):
        """记录 /compute_path_to_pose 的 action 状态变化"""
        t_now = time.time()
        entry = {
            'time': t_now,
            'status_list': [
                {'goal_id': str(s.goal_info.goal_id.uuid),
                 'status': s.status}
                for s in msg.status_list
            ]
        }
        with self._plan_action_status_lock:
            self._plan_action_status_history.append(entry)
        # 只打印非空状态
        if msg.status_list:
            status_names = {0: 'UNKNOWN', 1: 'ACCEPTED', 2: 'EXECUTING',
                           3: 'CANCELING', 4: 'SUCCEEDED', 5: 'CANCELED',
                           6: 'ABORTED'}
            for s in msg.status_list:
                sname = status_names.get(s.status, str(s.status))
                self.get_logger().info(
                    f'🔍 [ComputePathToPose] status={sname} '
                    f'goal={str(s.goal_info.goal_id.uuid)[:8]}...')

    # ------------------------------------------------------------------
    # 规划器诊断探针 — 直接调 ComputePathToPose 拿 Result
    # ------------------------------------------------------------------
    def _diagnose_planner(self, target_x: float, target_y: float, target_yaw: float) -> dict:
        """
        向 planner_server 发送一个 ComputePathToPose 目标，同步等待结果。
        返回 {'ok': bool, 'path_len': int, 'planning_time': float, 'error': str}
        """
        result = {'ok': False, 'path_len': 0, 'planning_time': 0.0, 'error': ''}

        if not self._cp_ac.wait_for_server(timeout_sec=3.0):
            result['error'] = 'planner_server action 不可用 (3s超时)'
            return result

        robot = self._get_robot_state()
        goal = ComputePathToPose.Goal()
        goal.goal = PoseStamped()
        goal.goal.header.frame_id = 'map'
        goal.goal.header.stamp = self.get_clock().now().to_msg()
        goal.goal.pose.position.x = target_x
        goal.goal.pose.position.y = target_y
        goal.goal.pose.position.z = 0.0
        half_yaw = target_yaw / 2.0
        goal.goal.pose.orientation.z = math.sin(half_yaw)
        goal.goal.pose.orientation.w = math.cos(half_yaw)
        goal.planner_id = 'GridBased'
        goal.use_start = False  # 使用当前机器人位姿作为起点

        t0 = time.time()
        send_future = self._cp_ac.send_goal_async(goal)
        # 同步等待结果（在 spin 线程回调之外用 rclpy.spin_until_future_complete）
        try:
            rclpy.spin_until_future_complete(self, send_future, timeout_sec=5.0)
        except Exception:
            result['error'] = f'send_goal_async 超时/异常 (t={time.time()-t0:.3f}s)'
            return result

        goal_handle = send_future.result()
        if goal_handle is None:
            result['error'] = f'goal_handle 为 None (planner_server 未响应)'
            return result

        if not goal_handle.accepted:
            result['error'] = 'Goal 被 planner_server 拒绝 (not accepted)'
            return result

        result_future = goal_handle.get_result_async()
        try:
            rclpy.spin_until_future_complete(self, result_future, timeout_sec=10.0)
        except Exception:
            result['error'] = f'get_result 超时/异常 (t={time.time()-t0:.3f}s)'
            return result

        cp_result = result_future.result()
        if cp_result is None:
            result['error'] = 'ComputePathToPose result 为 None'
            return result

        result['ok'] = True
        result['path_len'] = len(cp_result.result.path.poses)
        result['planning_time'] = (
            cp_result.result.planning_time.sec +
            cp_result.result.planning_time.nanosec * 1e-9
        )
        return result

    # ------------------------------------------------------------------
    # 获取当前机器人状态
    # ------------------------------------------------------------------
    def _get_robot_state(self) -> dict:
        with self._odom_lock:
            if self._current_odom is None:
                return {'x': 0.0, 'y': 0.0, 'z': 0.0, 'yaw': 0.0, 'available': False}
            odom = self._current_odom
        return {
            'x': odom.pose.pose.position.x,
            'y': odom.pose.pose.position.y,
            'z': odom.pose.pose.position.z,
            'yaw': quat_to_yaw(odom.pose.pose.orientation),
            'available': True,
        }

    # ------------------------------------------------------------------
    # 任务启动
    # ------------------------------------------------------------------
    def _start_mission(self):
        self._startup_timer.cancel()

        if not self._nav_ac.wait_for_server(timeout_sec=10.0):
            self._log('❌ NavigateToPose Action Server 不可用 (10s超时). '
                      'bt_navigator 是否运行?')
            self._log('请先启动导航栈: ros2 launch legged_bringup navigation.launch.py')
            self._shutdown()
            return

        self._log('✅ NavigateToPose Action Server 已就绪')
        self._advance_to_next_waypoint()

    # ------------------------------------------------------------------
    # 推进到下一航点
    # ------------------------------------------------------------------
    def _advance_to_next_waypoint(self):
        self._step_index += 1

        if self._step_index >= len(self._sequence):
            self._log_separator()
            self._log(f'🎉 全部 {len(self._sequence)} 段走完！测试完成。')
            self._log(f'完整日志: {self._log_path}')
            self._log_separator()
            self._shutdown()
            return

        wp = self._sequence[self._step_index]
        step_num = self._step_index + 1
        total = len(self._sequence)

        self._zone_transitions.clear()
        self._leg_nav_failed = False
        # 重置规划追踪
        self._leg_plan_count = 0
        self._leg_plan_first_time = 0.0
        self._leg_plan_last_time = 0.0
        robot = self._get_robot_state()
        self._leg_start_time = time.time()
        self._leg_start_zone = self._current_zone

        # 段间短暂延迟：让 BT 的 PipelineSequence 清理上一段的 {smoothed_path}，
        # 防止 FollowPath 用旧路径瞬间判定到达（假成功 bug）
        if self._step_index > 0:
            time.sleep(0.5)

        # 重置本段规划器 action 状态历史
        with self._plan_action_status_lock:
            self._plan_action_status_history.clear()
        self.get_logger().info(f'🔍 [诊断] 段{step_num}规划器 action 状态历史已重置')

        self._log_separator()
        self._log(f'▶ [{step_num:2d}/{total}] 开始导航 → {wp["id"]}')
        self._log(f'  目标: ({wp["x"]:.3f}, {wp["y"]:.3f}) yaw={wp["yaw"]:.3f}')
        self._log(f'  说明: {wp["desc"]}')
        self._log(f'  起点坐标: ({robot["x"]:.3f}, {robot["y"]:.3f}) '
                  f'yaw={robot["yaw"]:.3f}rad | 区域: {self._current_zone}')
        self._log(f'  起点策略: {zone_description(self._current_zone or "UNKNOWN")}')

        goal = NavigateToPose.Goal()
        goal.pose = PoseStamped()
        goal.pose.header.frame_id = 'map'
        goal.pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose.pose.position.x = wp['x']
        goal.pose.pose.position.y = wp['y']
        goal.pose.pose.position.z = 0.0
        half_yaw = wp['yaw'] / 2.0
        goal.pose.pose.orientation.z = math.sin(half_yaw)
        goal.pose.pose.orientation.w = math.cos(half_yaw)

        t_send = time.time()
        future = self._nav_ac.send_goal_async(goal)
        future.add_done_callback(self._nav_goal_response_cb)
        self._log(f'   ⏱️  Goal 已发送 (t={t_send - self._leg_start_time:.3f}s since leg start)')

    # ------------------------------------------------------------------
    # 导航 Goal 响应回调
    # ------------------------------------------------------------------
    def _nav_goal_response_cb(self, future):
        t_response = time.time()
        try:
            goal_handle = future.result()
        except Exception as e:
            self._log(f'❌ 导航 Goal 发送异常: {e}')
            self._handle_nav_failure()
            return

        if not goal_handle.accepted:
            self._log('❌ 导航 Goal 被拒绝')
            self._handle_nav_failure()
            return

        self._nav_goal_handle = goal_handle
        dt_response = t_response - self._leg_start_time
        self._log(f'   ✅ Goal 已接受 (响应延迟={dt_response:.2f}s)，导航中...')

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self._nav_result_cb)

    # ------------------------------------------------------------------
    # 导航结果回调
    # ------------------------------------------------------------------
    def _nav_result_cb(self, future):
        elapsed = time.time() - self._leg_start_time
        wp = self._sequence[self._step_index]
        step_num = self._step_index + 1
        total = len(self._sequence)

        try:
            result = future.result()
            nav_ok = True
        except Exception as e:
            self._log(f'❌ 导航异常: {e}')
            nav_ok = False

        robot = self._get_robot_state()

        # ---- 规划器 action 状态诊断 ----
        with self._plan_action_status_lock:
            action_events = list(self._plan_action_status_history)
        status_names = {0: 'UNKNOWN', 1: 'ACCEPTED', 2: 'EXECUTING',
                       3: 'CANCELING', 4: 'SUCCEEDED', 5: 'CANCELED', 6: 'ABORTED'}
        if action_events:
            self._log(f'  🔍 ComputePathToPose action 事件: {len(action_events)} 条')
            for e in action_events:
                for s in e['status_list']:
                    self._log(f'    [{e["time"] - self._leg_start_time:+.3f}s] goal={str(s["goal_id"])[:8]}... '
                            f'status={status_names.get(s["status"], s["status"])}')
        else:
            self._log(f'  🔍 ⚠️ ComputePathToPose action 事件: 0 条 — BT 可能未调用规划器！')

        # ---- 规划诊断：记录本段收到的 /plan 信息 ----
        self._log(f'  🔍 规划诊断: 本段收到 {self._leg_plan_count} 次 /plan')
        with self._plan_lock:
            last_plan = self._last_plan
            plan_time = self._plan_received_time
        if last_plan is not None and len(last_plan.poses) > 0:
            plan_start = last_plan.poses[0].pose.position
            plan_end = last_plan.poses[-1].pose.position
            dt_plan = plan_time - self._leg_start_time if plan_time > 0 else -1
            dist_to_end = math.sqrt(
                (robot['x'] - plan_end.x)**2 + (robot['y'] - plan_end.y)**2)
            self._log(f'  🔍 /plan 起点=({plan_start.x:.3f},{plan_start.y:.3f}) '
                      f'终点=({plan_end.x:.3f},{plan_end.y:.3f}) 点数={len(last_plan.poses)}')
            self._log(f'  🔍 /plan 最后接收于 goal 发送后 {dt_plan:.3f}s, '
                      f'机器人距 plan 终点 {dist_to_end:.3f}m')
            # 判断 plan 是否指向当前目标
            target_x, target_y = wp['x'], wp['y']
            plan_target_dist = math.sqrt(
                (plan_end.x - target_x)**2 + (plan_end.y - target_y)**2)
            if plan_target_dist > 0.5:
                self._log(f'  🔍 ⚠️ /plan 终点距当前目标 {plan_target_dist:.3f}m — 可能是旧路径！')
        else:
            self._log(f'  🔍 ⚠️ 未收到任何 /plan！规划器可能未生成路径')
        self._log_separator('-')

        # 即使 Nav2 返回成功，也检查实际是否真的到达
        if nav_ok:
            target_x, target_y = wp['x'], wp['y']
            dx = robot['x'] - target_x
            dy = robot['y'] - target_y
            dxy = math.sqrt(dx * dx + dy * dy)
            # 如果偏差超过 tolerance 的 3 倍（0.24m），视为假成功
            if dxy > 0.24:
                self._log(f'⚠️  Nav2 报告成功但机器人距离目标 {dxy:.3f}m，视为失败')
                nav_ok = False
            # 如果耗时 < 1s 且偏差 > 0.15m，明显是假成功
            if elapsed < 1.0 and dxy > 0.15:
                self._log(f'⚠️  瞬间返回成功（{elapsed:.2f}s）但偏差 {dxy:.3f}m，视为假成功')
                nav_ok = False

        if not nav_ok:
            # 放置区(段5)或 0 规划时追加探针诊断
            if step_num == 5 or self._leg_plan_count == 0:
                self._log(f'  🔍 [探针-失败后] 向 planner_server 发送 ComputePathToPose 诊断请求...')
                probe = self._diagnose_planner(wp['x'], wp['y'], wp['yaw'])
                if probe['ok']:
                    self._log(f'  🔍 [探针-失败后] ✅ 规划器返回成功: path={probe["path_len"]}点, '
                             f'planning_time={probe["planning_time"]:.4f}s')
                else:
                    self._log(f'  🔍 [探针-失败后] ❌ 规划器失败: {probe["error"]}')
            self._handle_nav_failure(robot, elapsed)
            return

        target_x, target_y, target_yaw = wp['x'], wp['y'], wp['yaw']
        dx = robot['x'] - target_x
        dy = robot['y'] - target_y
        dxy = math.sqrt(dx * dx + dy * dy)
        dyaw = robot['yaw'] - target_yaw
        dyaw = math.atan2(math.sin(dyaw), math.cos(dyaw))

        arrival_zone = self._current_zone or 'UNKNOWN'

        self._log_separator('-')
        self._log(f'✅ [{step_num:2d}/{total}] 到达 {wp["id"]} | 耗时: {elapsed:.2f}s')
        self._log(f'  目标坐标:  ({target_x:.3f}, {target_y:.3f}) yaw={target_yaw:.3f}')
        self._log(f'  实际坐标:  ({robot["x"]:.3f}, {robot["y"]:.3f}) yaw={robot["yaw"]:.3f}'
                  f'{" ← /state_estimation" if robot["available"] else " ← 无数据"}')
        self._log(f'  偏差:      Δxy={dxy:.3f}m  Δyaw={dyaw:.3f}rad ({math.degrees(dyaw):.1f}°)')
        self._log(f'  到达时区域: {arrival_zone} (x={robot["x"]:.3f}, 边界 [{ZONE_LOWER}, {ZONE_UPPER}])')

        start_zone = self._leg_start_zone
        end_zone = arrival_zone
        if start_zone == end_zone:
            self._log(f'  本段策略:   {zone_description(end_zone)}')
            self._log(f'  区域切换:   无切换 (全程 {end_zone})')
        else:
            self._log(f'  起点策略:   {zone_description(start_zone or "UNKNOWN")}')
            self._log(f'  终点策略:   {zone_description(end_zone)}')

            if self._zone_transitions:
                for i, t in enumerate(self._zone_transitions):
                    leg_elapsed = t['time'] - self._leg_start_time
                    remaining = elapsed - leg_elapsed
                    self._log(f'  区域切换 #{i+1}:  {t["from"]} → {t["to"]} '
                              f'(x={t["x"]:.3f}m, 距起点 {leg_elapsed:.2f}s, '
                              f'切换后继续 {remaining:.2f}s)')
            else:
                self._log(f'  区域切换:   {start_zone} → {end_zone} (切换时机未捕获)')

        self._log_separator('-')
        self._advance_to_next_waypoint()

    # ------------------------------------------------------------------
    # 导航失败处理
    # ------------------------------------------------------------------
    def _handle_nav_failure(self, robot: dict | None = None, elapsed: float = 0.0):
        self._leg_nav_failed = True
        wp = self._sequence[self._step_index]
        step_num = self._step_index + 1
        total = len(self._sequence)

        if robot is None:
            robot = self._get_robot_state()

        self._log_separator('-')
        self._log(f'❌ [{step_num:2d}/{total}] 失败 {wp["id"]} | 耗时: {elapsed:.2f}s (未到达)')
        self._log(f'  目标:      ({wp["x"]:.3f}, {wp["y"]:.3f}) yaw={wp["yaw"]:.3f}')
        self._log(f'  当前坐标:  ({robot["x"]:.3f}, {robot["y"]:.3f}) yaw={robot["yaw"]:.3f}')
        self._log(f'  当前区域:  {self._current_zone or "UNKNOWN"}')
        self._log(f'  本段区域切换: {len(self._zone_transitions)} 次')

        if self._zone_transitions:
            for t in self._zone_transitions:
                self._log(f'    {t["from"]} → {t["to"]} (x={t["x"]:.3f})')

        self._log_separator('-')

        if self._stop_on_failure:
            self._log('⛔ stop_on_failure=true，测试中止。')
            self._log(f'完整日志: {self._log_path}')
            self._shutdown()
        else:
            self._log('⚠️  stop_on_failure=false，继续下一段...')
            self._advance_to_next_waypoint()

    # ------------------------------------------------------------------
    # 关闭
    # ------------------------------------------------------------------
    def _shutdown(self):
        self._log_file.close()
        rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)

    node = Path1NavTest()

    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(node)

    try:
        executor.spin()
    except KeyboardInterrupt:
        node.get_logger().info('⏹️  用户中断 (Ctrl+C)')
    finally:
        if node._log_file and not node._log_file.closed:
            node._log_file.close()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
