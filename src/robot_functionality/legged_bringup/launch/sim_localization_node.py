#!/usr/bin/env python3
# ============================================================================
# 模拟定位节点 — 基于速度指令 + 死区抖动生成模拟定位
#
# 用途：在无 Fast-LIVO 的情况下，根据 Nav2 的 /cmd_vel 指令模拟机器人运动，
#       发布 /state_estimation（里程计）和 odom→base_link TF，
#       替代真实定位系统进行 MP/Zone 切换的仿真观察。
#
# 抖动模型（偏向 cmd_vel_udp_bridge_node.cpp 的死区映射规律）：
#   vx 死区: |vx| < 0.45 → 运动不可靠，50% 概率不动，否则跳变到 0.5
#   vy 死区: |vy| < 0.43 → 运动不可靠，50% 概率不动，否则跳变到 0.5
#   wz 死区: |wz| < 0.85 → 运动不可靠，50% 概率不动，否则跳变到 0.9
#   超过死区：正常积分 + 高斯噪声 + 随机游走漂移
#   大幅度抖动：位置观测噪声 σ=0.15m，周期性随机跳跃 0.2-0.5m
#
# 调试日志（大量）：
#   - 每次收到 /cmd_vel 时打印原始指令 vs 实际模拟速度
#   - 死区激活时打印详细信息
#   - 每次 Zone 切换时打印：时间、位置、目标、距离、zone 变化
#   - 周期性（5s）打印：当前位置、速度、与所有目标点的距离
#   - 随机跳跃事件打印
# ============================================================================

import math
import random
import time
from typing import Dict, List, Optional, Tuple

import rclpy
from rclpy.node import Node
from rclpy.qos import (
    QoSProfile,
    DurabilityPolicy,
    ReliabilityPolicy,
    HistoryPolicy,
)

from geometry_msgs.msg import Twist, TransformStamped, PoseWithCovarianceStamped
from nav_msgs.msg import Odometry
from std_msgs.msg import String, Float64
from tf2_ros import TransformBroadcaster


# ============================================================================
# 死区参数（与 cmd_vel_udp_bridge_node.cpp 保持一致）
# ============================================================================
DEADZONE_VX = 0.45       # vx 死区阈值
DEADZONE_VY = 0.43       # vy 死区阈值
DEADZONE_WZ = 0.85       # wz 死区阈值
MIN_EFFECTIVE_VX = 0.5   # vx 最小有效速度
MIN_EFFECTIVE_VY = 0.5   # vy 最小有效速度
MIN_EFFECTIVE_WZ = 0.9   # wz 最小有效速度

# ============================================================================
# 抖动参数 — 模拟定位不确定性
# 关键设计：真实轨迹 = 纯速度积分（无噪声累积），观测 = 真实 + 噪声
# ============================================================================
POSITION_NOISE_STD = 0.03       # 位置观测噪声标准差 (m) — 每步独立，不累积
YAW_NOISE_STD = 0.02            # 航向观测噪声标准差 (rad)
VELOCITY_NOISE_RATIO = 0.15     # 速度噪声比例（实际速度的 ±15%）
RANDOM_WALK_STD = 0.0005        # 随机游走每步标准差 (m) — 仅在运动时激活
JUMP_PROBABILITY = 0.0005       # 每步随机跳跃概率 (0.05% → 平均每40秒一次)
JUMP_MAGNITUDE_MIN = 0.05       # 随机跳跃最小幅度 (m)
JUMP_MAGNITUDE_MAX = 0.15       # 随机跳跃最大幅度 (m)
DEADZONE_MOVE_PROBABILITY = 0.5 # 死区内实际移动的概率
MIN_JUMP_INTERVAL = 2.0         # 两次跳跃最小间隔 (秒)


class SimulatedLocalizationNode(Node):
    """模拟定位：速度积分 + 死区抖动 + 大量调试日志"""

    def __init__(self):
        super().__init__('simulated_localization')

        # ---- 参数声明 ----
        self.declare_parameter('odom_topic', '/state_estimation')
        self.declare_parameter('cmd_vel_topic', '/cmd_vel')
        self.declare_parameter('nav_zone_topic', '/mission_bt/nav_zone')
        self.declare_parameter('nav_segment_yaw_topic', '/mission_bt/nav_segment_yaw')
        self.declare_parameter('base_frame', 'base_link')
        self.declare_parameter('odom_frame', 'odom')
        self.declare_parameter('map_frame', 'map')
        self.declare_parameter('publish_rate', 50.0)
        self.declare_parameter('initial_x', 0.0)
        self.declare_parameter('initial_y', 0.0)
        self.declare_parameter('initial_yaw', 0.0)
        self.declare_parameter('enable_noise', True)
        self.declare_parameter('noise_level', 1.0)  # 噪声倍率，>1 更大抖动
        self.declare_parameter('log_velocity_detail', True)  # 是否打印每次速度细节
        self.declare_parameter('progress_log_interval', 5.0)  # 进度日志间隔

        # 读取参数
        self.odom_topic = self.get_parameter('odom_topic').value
        self.cmd_vel_topic = self.get_parameter('cmd_vel_topic').value
        self.nav_zone_topic = self.get_parameter('nav_zone_topic').value
        self.nav_segment_yaw_topic = self.get_parameter('nav_segment_yaw_topic').value
        self.base_frame = self.get_parameter('base_frame').value
        self.odom_frame = self.get_parameter('odom_frame').value
        self.map_frame = self.get_parameter('map_frame').value
        self.publish_rate = self.get_parameter('publish_rate').value
        self.enable_noise = self.get_parameter('enable_noise').value
        self.noise_level = self.get_parameter('noise_level').value
        self.log_velocity_detail = self.get_parameter('log_velocity_detail').value
        self.progress_log_interval = self.get_parameter('progress_log_interval').value

        # ---- 状态变量 ----
        self.pose_x = self.get_parameter('initial_x').value
        self.pose_y = self.get_parameter('initial_y').value
        self.pose_yaw = self.get_parameter('initial_yaw').value
        self.current_vx = 0.0
        self.current_vy = 0.0
        self.current_wz = 0.0
        self.current_zone = 'unknown'
        self.current_segment_yaw = 0.0
        self.last_cmd_vel_time = self.get_clock().now()
        self.start_time = self.get_clock().now()
        self.last_progress_log_time = self.start_time
        self.deadzone_active = {'vx': False, 'vy': False, 'wz': False}
        self.zone_change_count = 0
        self._last_jump_time = self.get_clock().now()

        # ---- 目标点列表（从 mission_hardcoded.yaml 提取，用于距离计算） ----
        self.waypoints: Dict[str, Tuple[float, float, float]] = {
            'nav_p0_wp0': (0.3500, 0.0000, 0.0000),
            'nav_p1_wp1': (1.0515, 0.4250, 0.0000),
            'nav_p1_wp2': (1.9015, 0.4250, 0.0000),
            'nav_p1_wp3': (3.8915, 0.4250, 0.0000),
            'nav_p1_wp4': (1.7015, -0.1750, 0.0000),
            'nav_p2_wp1': (2.2515, -1.2750, 0.0000),
            'nav_p2_wp2': (3.1015, -1.2750, 0.0000),
            'nav_p2_wp3': (4.6905, -1.2000, 0.0000),
            'nav_p3_wp1': (2.2515, -0.4250, 0.0000),
            'nav_p3_wp2': (3.1015, -0.4250, 0.0000),
            'nav_p3_wp3': (4.6905, -0.4000, 0.0000),
            'nav_p4_wp1': (2.2515, 0.4250, 0.0000),
            'nav_p4_wp2': (3.1015, 0.4250, 0.0000),
            'nav_p4_wp3': (4.6905, 0.4000, 0.0000),
            'nav_p5_wp1': (2.2515, 1.2750, 0.0000),
            'nav_p5_wp2': (3.1015, 1.2750, 0.0000),
            'nav_p5_wp3': (4.6905, 1.2000, 0.0000),
        }

        # ---- 订阅者 ----
        # Latched QoS for zone/segment_yaw topics
        latched_qos = QoSProfile(
            depth=1,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
        )

        self.cmd_vel_sub = self.create_subscription(
            Twist, self.cmd_vel_topic, self.cmd_vel_callback, 10)

        self.zone_sub = self.create_subscription(
            String, self.nav_zone_topic, self.zone_callback, latched_qos)

        self.segment_yaw_sub = self.create_subscription(
            Float64, self.nav_segment_yaw_topic, self.segment_yaw_callback, latched_qos)

        # ---- 发布者 ----
        self.odom_pub = self.create_publisher(Odometry, self.odom_topic, 10)
        self.true_pose_pub = self.create_publisher(
            PoseWithCovarianceStamped, '/sim_true_pose', 10)

        # ---- TF 广播 ----
        self.tf_broadcaster = TransformBroadcaster(self)

        # ---- 定时器 ----
        dt = 1.0 / self.publish_rate
        self.publish_timer = self.create_timer(dt, self.publish_timer_callback)

        # ---- 打印启动信息 ----
        self._log_startup_info()

    # ========================================================================
    # 日志辅助
    # ========================================================================
    def _ts_now(self) -> str:
        """返回当前时间戳字符串"""
        now = self.get_clock().now()
        elapsed = (now - self.start_time).nanoseconds / 1e9
        return f"T+{elapsed:.3f}s"

    def _ts_double(self) -> Tuple[str, float]:
        """返回时间戳字符串和相对秒数"""
        now = self.get_clock().now()
        elapsed = (now - self.start_time).nanoseconds / 1e9
        return f"T+{elapsed:.3f}s", elapsed

    def _log_startup_info(self):
        """打印启动配置信息"""
        self.get_logger().info(
            '╔══════════════════════════════════════════════════════════════╗\n'
            '║        SIMULATED LOCALIZATION NODE — 模拟定位节点            ║\n'
            '╠══════════════════════════════════════════════════════════════╣\n'
            '║  用途: 替代 Fast-LIVO，模拟定位观察 MP/Zone 切换             ║\n'
            '╠══════════════════════════════════════════════════════════════╣\n'
            '║  初始位姿:                                                  ║'
        )
        self.get_logger().info(
            f'║    x={self.pose_x:.3f}, y={self.pose_y:.3f}, yaw={self.pose_yaw:.3f} rad'
        )
        self.get_logger().info(
            '╠══════════════════════════════════════════════════════════════╣\n'
            '║  死区参数 (与 cmd_vel_udp_bridge 一致):                      ║'
        )
        self.get_logger().info(
            f'║    vx:  deadzone={DEADZONE_VX:.2f}, min_eff={MIN_EFFECTIVE_VX:.2f}'
        )
        self.get_logger().info(
            f'║    vy:  deadzone={DEADZONE_VY:.2f}, min_eff={MIN_EFFECTIVE_VY:.2f}'
        )
        self.get_logger().info(
            f'║    wz:  deadzone={DEADZONE_WZ:.2f}, min_eff={MIN_EFFECTIVE_WZ:.2f}'
        )
        self.get_logger().info(
            '╠══════════════════════════════════════════════════════════════╣\n'
            '║  抖动参数（静止=无漂移，运动时才加噪声）:                    ║'
        )
        self.get_logger().info(
            f'║    位置噪声 σ={POSITION_NOISE_STD * self.noise_level:.3f}m (速度比例缩放)'
        )
        self.get_logger().info(
            f'║    航向噪声 σ={YAW_NOISE_STD * self.noise_level:.3f}rad'
        )
        self.get_logger().info(
            f'║    速度噪声 ±{VELOCITY_NOISE_RATIO * 100:.0f}%'
        )
        self.get_logger().info(
            f'║    随机游走 σ={RANDOM_WALK_STD * self.noise_level:.4f}m/step (×速度)'
        )
        self.get_logger().info(
            f'║    跳跃概率 {JUMP_PROBABILITY * 100:.2f}%, 幅度 [{JUMP_MAGNITUDE_MIN}-{JUMP_MAGNITUDE_MAX}]m, 最小间隔 {MIN_JUMP_INTERVAL}s'
        )
        self.get_logger().info(
            f'║    死区内移动概率 {DEADZONE_MOVE_PROBABILITY * 100:.0f}%'
        )
        self.get_logger().info(
            '╠══════════════════════════════════════════════════════════════╣\n'
            '║  订阅:                                                      ║'
        )
        self.get_logger().info(f'║    cmd_vel:          {self.cmd_vel_topic}')
        self.get_logger().info(f'║    nav_zone:         {self.nav_zone_topic}')
        self.get_logger().info(f'║    nav_segment_yaw:  {self.nav_segment_yaw_topic}')
        self.get_logger().info(
            '╠══════════════════════════════════════════════════════════════╣\n'
            '║  发布:                                                      ║'
        )
        self.get_logger().info(f'║    odometry:         {self.odom_topic} @ {self.publish_rate}Hz')
        self.get_logger().info(f'║    true_pose:        /sim_true_pose (无噪声真实位姿)')
        self.get_logger().info(f'║    TF:               {self.odom_frame} → {self.base_frame}')
        self.get_logger().info(
            '╚══════════════════════════════════════════════════════════════╝'
        )

    # ========================================================================
    # 死区抖动模拟
    # ========================================================================
    def apply_deadzone_jitter(self, cmd_vx: float, cmd_vy: float, cmd_wz: float
                              ) -> Tuple[float, float, float]:
        """
        对速度指令施加死区抖动，模拟 cmd_vel_udp_bridge 映射规律。

        物理直觉：
        - 死区内：电机静摩擦力导致运动不可靠 → 大概率不动，小概率突然跳动
        - 死区外：电机以最小有效速度运行 + 随机波动
        """
        if not self.enable_noise:
            return cmd_vx, cmd_vy, cmd_wz

        level = self.noise_level

        def _process_axis(value: float, deadzone: float, min_eff: float, name: str
                          ) -> float:
            """处理单个轴的速度"""
            if value == 0.0:
                self.deadzone_active[name] = False
                return 0.0

            abs_v = abs(value)

            if abs_v < deadzone:
                # ── 死区内：运动不可靠 ──
                self.deadzone_active[name] = True
                if random.random() < DEADZONE_MOVE_PROBABILITY:
                    # 突然跳变到最小有效速度（模拟死区补偿）
                    effective = math.copysign(min_eff, value)
                    # 加上大幅度随机波动
                    noise = random.gauss(0, min_eff * VELOCITY_NOISE_RATIO * level)
                    result = effective + noise
                    # 确保符号不变
                    if math.copysign(1.0, result) != math.copysign(1.0, value):
                        result = math.copysign(abs(min_eff * 0.3), value)
                    self.get_logger().debug(
                        f'  [DEADZONE-MOVE] {name}: cmd={value:.4f} deadzone={deadzone:.2f} '
                        f'→ boosted={effective:.4f} + noise={noise:.4f} = {result:.4f}'
                    )
                    return result
                else:
                    # 不动（模拟静摩擦力）
                    self.get_logger().debug(
                        f'  [DEADZONE-STUCK] {name}: cmd={value:.4f} < deadzone={deadzone:.2f} '
                        f'→ 静摩擦力，不移动'
                    )
                    return 0.0
            else:
                # ── 死区外：正常运动 + 噪声 ──
                self.deadzone_active[name] = False
                # 确保至少以最小有效速度运动
                effective = value
                if abs_v < min_eff:
                    effective = math.copysign(min_eff, value)
                noise = random.gauss(0, abs(effective) * VELOCITY_NOISE_RATIO * level)
                result = effective + noise
                # 保持符号
                if math.copysign(1.0, result) != math.copysign(1.0, value):
                    result = math.copysign(max(abs(effective) * 0.5, abs(min_eff * 0.3)), value)
                return result

        actual_vx = _process_axis(cmd_vx, DEADZONE_VX, MIN_EFFECTIVE_VX, 'vx')
        actual_vy = _process_axis(cmd_vy, DEADZONE_VY, MIN_EFFECTIVE_VY, 'vy')
        actual_wz = _process_axis(cmd_wz, DEADZONE_WZ, MIN_EFFECTIVE_WZ, 'wz')

        return actual_vx, actual_vy, actual_wz

    # ========================================================================
    # 回调
    # ========================================================================
    def cmd_vel_callback(self, msg: Twist):
        """接收 Nav2 速度指令"""
        raw_vx = msg.linear.x
        raw_vy = msg.linear.y
        raw_wz = msg.angular.z

        ts, _ = self._ts_double()
        self.last_cmd_vel_time = self.get_clock().now()

        # 施加死区抖动
        actual_vx, actual_vy, actual_wz = self.apply_deadzone_jitter(
            raw_vx, raw_vy, raw_wz)

        self.current_vx = actual_vx
        self.current_vy = actual_vy
        self.current_wz = actual_wz

        if self.log_velocity_detail:
            any_deadzone = any(self.deadzone_active.values())
            dz_tag = ' [DEADZONE!]' if any_deadzone else ''
            self.get_logger().info(
                f'[{ts}]{dz_tag} CMD_VEL: '
                f'raw(vx={raw_vx:+.4f}, vy={raw_vy:+.4f}, wz={raw_wz:+.4f}) → '
                f'sim(vx={actual_vx:+.4f}, vy={actual_vy:+.4f}, wz={actual_wz:+.4f})'
                f' | dz_active: vx={self.deadzone_active["vx"]} '
                f'vy={self.deadzone_active["vy"]} wz={self.deadzone_active["wz"]}'
            )

    def zone_callback(self, msg: String):
        """监控 Zone 切换"""
        new_zone = msg.data.strip()
        if new_zone == self.current_zone:
            return

        ts, elapsed = self._ts_double()
        old_zone = self.current_zone
        self.current_zone = new_zone
        self.zone_change_count += 1

        # 计算到所有目标点的距离
        nearest_wp, nearest_dist = self._find_nearest_waypoint()

        self.get_logger().info(
            '╔══════════════════════════════════════════════════════════════╗'
        )
        self.get_logger().info(
            '║  🔄 ZONE SWITCH DETECTED                                    ║'
        )
        self.get_logger().info(
            '╠══════════════════════════════════════════════════════════════╣'
        )
        self.get_logger().info(
            f'║  时间:        {ts}'
        )
        self.get_logger().info(
            f'║  相对时间:    {elapsed:.3f}s 自启动'
        )
        self.get_logger().info(
            f'║  Zone 切换:   {old_zone}  →  {new_zone}'
        )
        self.get_logger().info(
            f'║  切换次数:    #{self.zone_change_count}'
        )
        self.get_logger().info(
            f'║  当前位置:    x={self.pose_x:.4f}, y={self.pose_y:.4f}, yaw={self.pose_yaw:.4f} rad ({math.degrees(self.pose_yaw):.1f}°)'
        )
        self.get_logger().info(
            f'║  当前速度:    vx={self.current_vx:.4f}, vy={self.current_vy:.4f}, wz={self.current_wz:.4f}'
        )
        self.get_logger().info(
            f'║  最近目标点:  {nearest_wp} (距离={nearest_dist:.4f}m)'
        )

        # 打印到所有目标点的距离
        self.get_logger().info(
            '╠══════════════════════════════════════════════════════════════╣'
        )
        self.get_logger().info(
            '║  到各目标点距离:                                            ║'
        )
        for wp_name, (wx, wy, wyaw) in sorted(self.waypoints.items()):
            dist = math.hypot(self.pose_x - wx, self.pose_y - wy)
            self.get_logger().info(
                f'║    {wp_name:20s}: ({wx:6.2f}, {wy:6.2f})  dist={dist:.4f}m'
            )

        # 推断 MP
        if new_zone == 'middle':
            mp_guess = 'mp=0 (yaw锁定航段方向, Y追踪)'
        elif new_zone == 'edge':
            mp_guess = 'mp=1/2 (允许旋转, yaw解锁)'
        elif new_zone == 'straight':
            mp_guess = 'mp=3 (x-only, vy=vtheta=0)'
        else:
            mp_guess = 'unknown'
        self.get_logger().info(
            f'║  推断 MP:     {mp_guess}'
        )
        self.get_logger().info(
            '╚══════════════════════════════════════════════════════════════╝'
        )

    def segment_yaw_callback(self, msg: Float64):
        """接收航段方位角"""
        self.current_segment_yaw = msg.data

    # ========================================================================
    # 位姿更新与发布
    # ========================================================================
    def publish_timer_callback(self):
        """定时积分速度、加噪声、发布里程计和 TF

        关键设计：真实位姿 = 纯速度积分（无噪声累积），观测 = 真实 + 噪声。
        即：发布的 odometry 有噪声（模拟定位误差），但内部积分用真实位姿，
        避免噪声累积导致发散漂移。
        """
        now = self.get_clock().now()
        dt_seconds = 1.0 / self.publish_rate

        # ---- 1) 速度积分（真实轨迹，无噪声） ----
        actual_vx = self.current_vx
        actual_vy = self.current_vy
        actual_wz = self.current_wz

        cos_yaw = math.cos(self.pose_yaw)
        sin_yaw = math.sin(self.pose_yaw)
        world_vx = actual_vx * cos_yaw - actual_vy * sin_yaw
        world_vy = actual_vx * sin_yaw + actual_vy * cos_yaw

        # 真实位姿：纯积分，不做任何噪声累积
        true_x = self.pose_x + world_vx * dt_seconds
        true_y = self.pose_y + world_vy * dt_seconds
        true_yaw = self.pose_yaw + actual_wz * dt_seconds
        true_yaw = math.atan2(math.sin(true_yaw), math.cos(true_yaw))

        # 计算当前速度标量（用于判断是否在运动）
        speed = math.hypot(actual_vx, actual_vy)

        # ---- 2) 生成观测位姿（真实 + 噪声） ----
        if self.enable_noise:
            level = self.noise_level

            # 位置观测噪声：仅在运动时显著
            obs_noise_std = POSITION_NOISE_STD * level * (1.0 + speed)
            noise_x = random.gauss(0, obs_noise_std)
            noise_y = random.gauss(0, obs_noise_std)
            noise_yaw = random.gauss(0, YAW_NOISE_STD * level * (1.0 + abs(actual_wz)))

            # 随机游走漂移：速度越大漂移越大，静止时几乎不漂
            walk_scale = speed * level
            random_walk_x = random.gauss(0, RANDOM_WALK_STD * walk_scale)
            random_walk_y = random.gauss(0, RANDOM_WALK_STD * walk_scale)
            random_walk_yaw = random.gauss(0, RANDOM_WALK_STD * 0.1 * walk_scale)

            # 随机跳跃：仅在运动时可能发生，且有最小间隔
            jump_x, jump_y = 0.0, 0.0
            if speed > 0.05:  # 仅运动时跳跃
                elapsed_since_jump = (now - self._last_jump_time).nanoseconds / 1e9
                if elapsed_since_jump > MIN_JUMP_INTERVAL:
                    if random.random() < JUMP_PROBABILITY:
                        angle = random.uniform(0, 2 * math.pi)
                        magnitude = random.uniform(JUMP_MAGNITUDE_MIN,
                                                   JUMP_MAGNITUDE_MAX) * level
                        jump_x = magnitude * math.cos(angle)
                        jump_y = magnitude * math.sin(angle)
                        self._last_jump_time = now
                        self.get_logger().warn(
                            f'[{self._ts_now()}] ⚡ POSITION JUMP: '
                            f'dx={jump_x:.4f}, dy={jump_y:.4f}, '
                            f'magnitude={magnitude:.4f}m, speed={speed:.3f}'
                        )

            obs_x = true_x + noise_x + random_walk_x + jump_x
            obs_y = true_y + noise_y + random_walk_y + jump_y
            obs_yaw = true_yaw + noise_yaw + random_walk_yaw
            obs_yaw = math.atan2(math.sin(obs_yaw), math.cos(obs_yaw))
        else:
            obs_x = true_x
            obs_y = true_y
            obs_yaw = true_yaw

        # ★关键修复：用真实位姿更新内部状态（噪声不累积）
        # 上一版本用 obs_* 更新导致噪声指数级发散
        self.pose_x = true_x
        self.pose_y = true_y
        self.pose_yaw = true_yaw

        # ---- 3) 发布里程计 (/state_estimation) — 使用含噪声的观测 ----
        self._publish_odometry(now, obs_x, obs_y, obs_yaw, actual_vx, actual_vy, actual_wz)

        # ---- 4) 发布无噪声真实位姿 (调试用) ----
        self._publish_true_pose(now, true_x, true_y, true_yaw)

        # ---- 5) 周期性进度日志 ----
        self._maybe_log_progress(now)

    def _publish_odometry(self, now, x: float, y: float, yaw: float,
                          vx: float, vy: float, wz: float):
        """发布 nav_msgs/Odometry 到 /state_estimation"""
        odom = Odometry()
        odom.header.stamp = now.to_msg()
        odom.header.frame_id = self.odom_frame
        odom.child_frame_id = self.base_frame

        # 位姿
        odom.pose.pose.position.x = x
        odom.pose.pose.position.y = y
        odom.pose.pose.position.z = 0.0

        cy = math.cos(yaw * 0.5)
        sy = math.sin(yaw * 0.5)
        odom.pose.pose.orientation.z = sy
        odom.pose.pose.orientation.w = cy

        # 协方差（模拟定位不确定性）
        cov = 0.02 * self.noise_level if self.enable_noise else 0.001
        odom.pose.covariance[0] = cov   # x
        odom.pose.covariance[7] = cov   # y
        odom.pose.covariance[35] = cov * 0.5  # yaw

        # 速度
        odom.twist.twist.linear.x = vx
        odom.twist.twist.linear.y = vy
        odom.twist.twist.angular.z = wz

        self.odom_pub.publish(odom)

        # ---- 发布 TF ----
        tf_msg = TransformStamped()
        tf_msg.header.stamp = now.to_msg()
        tf_msg.header.frame_id = self.odom_frame
        tf_msg.child_frame_id = self.base_frame
        tf_msg.transform.translation.x = x
        tf_msg.transform.translation.y = y
        tf_msg.transform.translation.z = 0.0
        tf_msg.transform.rotation.z = sy
        tf_msg.transform.rotation.w = cy

        self.tf_broadcaster.sendTransform(tf_msg)

    def _publish_true_pose(self, now, x: float, y: float, yaw: float):
        """发布无噪声真实位姿用于调试"""
        pose = PoseWithCovarianceStamped()
        pose.header.stamp = now.to_msg()
        pose.header.frame_id = self.map_frame
        pose.pose.pose.position.x = x
        pose.pose.pose.position.y = y
        pose.pose.pose.position.z = 0.0
        cy = math.cos(yaw * 0.5)
        sy = math.sin(yaw * 0.5)
        pose.pose.pose.orientation.z = sy
        pose.pose.pose.orientation.w = cy
        self.true_pose_pub.publish(pose)

    def _find_nearest_waypoint(self) -> Tuple[str, float]:
        """找到距离最近的目标点及其距离"""
        nearest = 'none'
        min_dist = float('inf')
        for wp_name, (wx, wy, _) in self.waypoints.items():
            dist = math.hypot(self.pose_x - wx, self.pose_y - wy)
            if dist < min_dist:
                min_dist = dist
                nearest = wp_name
        return nearest, min_dist

    def _maybe_log_progress(self, now):
        """周期性打印导航进度"""
        elapsed = (now - self.last_progress_log_time).nanoseconds / 1e9
        if elapsed < self.progress_log_interval:
            return

        self.last_progress_log_time = now
        ts, total_elapsed = self._ts_double()
        nearest_wp, nearest_dist = self._find_nearest_waypoint()

        dz_tags = []
        if self.deadzone_active['vx']:
            dz_tags.append('vx')
        if self.deadzone_active['vy']:
            dz_tags.append('vy')
        if self.deadzone_active['wz']:
            dz_tags.append('wz')
        dz_str = ','.join(dz_tags) if dz_tags else 'none'

        self.get_logger().info(
            f'[{ts}] 📍 PROGRESS: '
            f'pos=({self.pose_x:.4f}, {self.pose_y:.4f}, yaw={math.degrees(self.pose_yaw):.1f}°) | '
            f'vel=(vx={self.current_vx:+.4f}, vy={self.current_vy:+.4f}, wz={self.current_wz:+.4f}) | '
            f'zone={self.current_zone} | '
            f'nearest_wp={nearest_wp}({nearest_dist:.3f}m) | '
            f'deadzone_active=[{dz_str}] | '
            f'segment_yaw={math.degrees(self.current_segment_yaw):.1f}°'
        )

        # 打印到前5近的目标点
        dists = []
        for wp_name, (wx, wy, _) in self.waypoints.items():
            dist = math.hypot(self.pose_x - wx, self.pose_y - wy)
            dists.append((dist, wp_name, wx, wy))
        dists.sort()
        self.get_logger().info(f'[{ts}]   Top-5 nearest waypoints:')
        for dist, wp_name, wx, wy in dists[:5]:
            dx = wx - self.pose_x
            dy = wy - self.pose_y
            bearing = math.degrees(math.atan2(dy, dx))
            self.get_logger().info(
                f'[{ts}]     {wp_name}: ({wx:.2f}, {wy:.2f}) '
                f'dist={dist:.4f}m, bearing={bearing:.1f}°, '
                f'dx={dx:+.4f}, dy={dy:+.4f}'
            )

    # ========================================================================
    # 析构
    # ========================================================================
    def destroy_node(self):
        total_elapsed = (self.get_clock().now() - self.start_time).nanoseconds / 1e9
        self.get_logger().info(
            f'╔══════════════════════════════════════════════════════════════╗\n'
            f'║  SIMULATED LOCALIZATION SHUTDOWN                            ║\n'
            f'╠══════════════════════════════════════════════════════════════╣\n'
            f'║  总运行时间:   {total_elapsed:.1f}s\n'
            f'║  最终位置:     x={self.pose_x:.4f}, y={self.pose_y:.4f}, yaw={self.pose_yaw:.4f}\n'
            f'║  Zone 切换次数: {self.zone_change_count}\n'
            f'║  最终 Zone:    {self.current_zone}\n'
            f'╚══════════════════════════════════════════════════════════════╝'
        )
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = SimulatedLocalizationNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
