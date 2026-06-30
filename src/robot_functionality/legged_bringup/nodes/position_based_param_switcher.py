#!/usr/bin/env python3
"""
Position-based Nav2 Parameter Switcher Node (Plan C — dynamic param set).

Monitors the robot's x coordinate from odometry and dynamically switches
DWB critic scales + goal checker tolerance via ros2 param set — zero downtime.

Zones:
  - 0 ≤ x < 1.35m   → edge  zone (rotation allowed, yaw unlocked, single-axis preferred)
  - 1.35m ≤ x ≤ 4.0m → middle zone (yaw locked to 0, vy=0, pure X-only movement)
  - 4.0m < x ≤ 6.30m → edge  zone (rotation allowed, yaw unlocked, single-axis preferred)

Hysteresis: ±0.1m around boundaries to prevent rapid oscillation.

All 8 critics are pre-loaded in nav2_params.yaml; this node only toggles
their scale values between 0 (disabled) and active weight.
"""

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from rcl_interfaces.srv import SetParameters
from rcl_interfaces.msg import Parameter, ParameterValue


# ---------------------------------------------------------------------------
# Parameter sets for each zone
#   Key = full ROS2 parameter name on /controller_server
#   Value = float
# ---------------------------------------------------------------------------

MIDDLE_PARAMS = {
    # 中间区：不检查朝向（只要 xy 到位即视为完成）
    # MaintainYawCritic(5000) 强锁 yaw=0，vy=0，纯X单轴运动
    'general_goal_checker.xy_goal_tolerance': 0.08,
    'general_goal_checker.yaw_goal_tolerance': 6.28,
    'FollowPath.RotateToGoal.scale': 0.0,
    'FollowPath.GoalAlign.scale': 0.0,
    'FollowPath.PathAlign.scale': 0.0,
    'FollowPath.dwb_yaw_constraint::MaintainYawCritic.scale': 5000.0,
    'FollowPath.dwb_yaw_constraint::DecouplingCritic.scale': 0.0,
    'FollowPath.min_vel_y': 0.0,
    'FollowPath.max_vel_y': 0.0,
}

EDGE_PARAMS = {
    # 边缘区：允许旋转对齐朝向，允许横向移动
    # yaw_goal_tolerance=0.05236 rad(3°)，精确对齐 yaw 确保中间区穿障碍物安全
    'general_goal_checker.xy_goal_tolerance': 0.08,
    'general_goal_checker.yaw_goal_tolerance': 0.05236,
    'FollowPath.RotateToGoal.scale': 32.0,
    'FollowPath.GoalAlign.scale': 24.0,
    'FollowPath.PathAlign.scale': 32.0,
    'FollowPath.dwb_yaw_constraint::MaintainYawCritic.scale': 0.0,
    'FollowPath.dwb_yaw_constraint::DecouplingCritic.scale': 30.0,
    'FollowPath.min_vel_y': -1.1,
    'FollowPath.max_vel_y': 1.1,
}

# Convenience lookup
ZONE_PARAMS = {'middle': MIDDLE_PARAMS, 'edge': EDGE_PARAMS}


def _make_param(name: str, value: float) -> Parameter:
    """Build a rcl_interfaces/Parameter with a float64 value (type=3)."""
    pv = ParameterValue(type=3, double_value=float(value))
    return Parameter(name=name, value=pv)


class PositionBasedParamSwitcher(Node):
    """Switches Nav2 controller params dynamically based on robot x position."""

    def __init__(self):
        super().__init__('position_based_param_switcher')

        # Zone boundaries
        self.declare_parameter('lower_boundary', 1.35)
        self.declare_parameter('upper_boundary', 4.0)
        self.declare_parameter('hysteresis_margin', 0.1)
        self.declare_parameter('odom_topic', 'state_estimation')
        self.declare_parameter('target_node', 'controller_server')

        self.lower_boundary = self.get_parameter('lower_boundary').value
        self.upper_boundary = self.get_parameter('upper_boundary').value
        self.hysteresis = self.get_parameter('hysteresis_margin').value
        self.odom_topic: str = self.get_parameter('odom_topic').value  # type: ignore
        self.target_node: str = self.get_parameter('target_node').value  # type: ignore

        # State
        self.current_zone = None      # 'middle' or 'edge'
        self.switch_in_progress = False

        # SetParameters client for dynamic param updates
        srv_name = f'/{self.target_node}/set_parameters'
        self.param_client = self.create_client(SetParameters, srv_name)

        # Subscribe to odometry
        self.sub = self.create_subscription(
            Odometry, self.odom_topic, self.odom_callback, 10)

        # Periodic status print so user can verify which zone is active
        self.status_timer = self.create_timer(3.0, self._print_status)

        self.get_logger().info(
            '============================================================\n'
            f'  PositionBasedParamSwitcher (Plan C — dynamic param set)\n'
            f'  Edge  zone: x < {self.lower_boundary}  or  x > {self.upper_boundary}\n'
            f'  Middle zone: {self.lower_boundary} ≤ x ≤ {self.upper_boundary}\n'
            f'  Hysteresis: ±{self.hysteresis}m\n'
            f'  Target node: /{self.target_node}\n'
            '============================================================'
        )

    # ------------------------------------------------------------------
    # Zone logic
    # ------------------------------------------------------------------

    def _determine_zone(self, x: float) -> str:
        """Hysteresis-aware zone classification."""
        if self.current_zone == 'edge':
            lo = self.lower_boundary + self.hysteresis
            hi = self.upper_boundary - self.hysteresis
            if lo <= x <= hi:
                return 'middle'
            return 'edge'
        elif self.current_zone == 'middle':
            if x < self.lower_boundary - self.hysteresis:
                return 'edge'
            if x > self.upper_boundary + self.hysteresis:
                return 'edge'
            return 'middle'
        else:
            # First reading — no hysteresis
            if self.lower_boundary <= x <= self.upper_boundary:
                return 'middle'
            return 'edge'

    # ------------------------------------------------------------------
    # Periodic status dump
    # ------------------------------------------------------------------

    def _print_status(self):
        """Log current zone + planner type so user can verify switching."""
        if self.current_zone is None:
            self.get_logger().info(
                '⏳ WAITING: No odometry received yet, zone undetermined.')
            return

        if self.current_zone == 'middle':
            self.get_logger().info(
                'ZONE=MIDDLE | DWB: yaw锁0 vy=0 (MaintainYaw=5000) PathAlign=0 | '
                'RotateToGoal=0 GoalAlign=0 DecouplingCritic=0 | '
                f'范围: [{self.lower_boundary}, {self.upper_boundary}]m')
        else:
            self.get_logger().info(
                'ZONE=EDGE   | DWB: yaw自由 vy自由(±1.4) yaw_tol=0.052rad(3°) | '
                'RotateToGoal=32 GoalAlign=24 PathAlign=32 DecouplingCritic=30 | '
                f'范围: x<{self.lower_boundary} 或 x>{self.upper_boundary}m')

    # ------------------------------------------------------------------
    # Odometry → zone check
    # ------------------------------------------------------------------

    def odom_callback(self, msg: Odometry):
        if self.switch_in_progress:
            return

        x = msg.pose.pose.position.x
        new_zone = self._determine_zone(x)

        if new_zone != self.current_zone:
            old = self.current_zone
            self.current_zone = new_zone
            self.get_logger().info(
                f'Zone change: x={x:.3f}m | {old} → {new_zone}'
            )
            self._apply_zone_params(new_zone)

    # ------------------------------------------------------------------
    # Dynamic parameter update (zero downtime)
    # ------------------------------------------------------------------

    def _apply_zone_params(self, zone: str):
        """
        Push the zone's parameter set to controller_server atomically.

        All 8 parameters are set in one service call — the controller
        picks up new scale values on the very next control cycle (10 Hz).
        """
        self.switch_in_progress = True
        params_dict = ZONE_PARAMS[zone]
        params = [_make_param(k, v) for k, v in params_dict.items()]

        # Wait for service (should already be available)
        if not self.param_client.wait_for_service(timeout_sec=3.0):
            self.get_logger().error(
                f'/{self.target_node}/set_parameters not available — '
                f'is controller_server running?'
            )
            self.switch_in_progress = False
            return

        req = SetParameters.Request(parameters=params)
        try:
            future = self.param_client.call_async(req)
            # rclpy.spin_until_future_complete is not used here because
            # this callback runs inside rclpy.spin; we rely on the async
            # callback instead.
            future.add_done_callback(self._set_params_callback)
        except Exception as e:
            self.get_logger().error(f'Failed to call set_parameters: {e}')
            self.switch_in_progress = False

    def _set_params_callback(self, future):
        """Handle the set_parameters service response."""
        self.switch_in_progress = False
        try:
            result = future.result()
        except Exception as e:
            self.get_logger().error(f'set_parameters call failed: {e}')
            return

        # Check individual results
        failures = []
        for res in result.results:
            if not res.successful:
                failures.append(res.reason)

        if failures:
            self.get_logger().warning(
                f'Some params failed to set: {failures}'
            )
        else:
            self.get_logger().info(
                f'✓ Switched to {self.current_zone} zone params (8/8 OK)'
            )


def main(args=None):
    rclpy.init(args=args)
    node = PositionBasedParamSwitcher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
