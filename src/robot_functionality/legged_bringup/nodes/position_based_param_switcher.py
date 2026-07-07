#!/usr/bin/env python3
"""
Nav2 Parameter Switcher Node — zone-driven by mission BT (limit_yaw).

Listens to /mission_bt/nav_zone for zone commands published by Nav2PoseNode.
Each Nav2PoseNode carries a limit_yaw attribute from the mission YAML:
  - limit_yaw: true  → zone = "middle" (yaw locked to 0, no rotation, lateral vy allowed)
  - limit_yaw: false → zone = "edge"   (rotation allowed, yaw unlocked, single-axis preferred)

Switches DWB critic scales + goal checker tolerance via ros2 param set — zero downtime.

All 8 critics are pre-loaded in nav2_params.yaml; this node only toggles
their scale values between 0 (disabled) and active weight.
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from rcl_interfaces.srv import SetParameters
from rcl_interfaces.msg import Parameter, ParameterValue


# ---------------------------------------------------------------------------
# Parameter sets for each zone
#   Key = full ROS2 parameter name on /controller_server
#   Value = float
# ---------------------------------------------------------------------------

MIDDLE_PARAMS = {
    # 中间区 (middle)：不检查朝向（只要 xy 到位即视为完成）
    # limit_yaw: true → yaw 锁定为 0，禁止旋转，允许横向 vy
    # x/y 容差与 nav2_params.yaml general_goal_checker / FollowPath 一致
    'general_goal_checker.x_goal_tolerance': 0.08,
    'general_goal_checker.y_goal_tolerance': 0.15,
    'general_goal_checker.yaw_goal_tolerance': 6.28,
    'FollowPath.x_goal_tolerance': 0.08,
    'FollowPath.y_goal_tolerance': 0.15,
    'FollowPath.dwb_yaw_constraint::RotateToGoalXY.scale': 0.0,
    'FollowPath.GoalAlign.scale': 0.0,
    'FollowPath.PathAlign.scale': 0.0,
    'FollowPath.dwb_yaw_constraint::MaintainYawCritic.scale': 5000.0,
    'FollowPath.dwb_yaw_constraint::DecouplingCritic.scale': 0.0,
    'FollowPath.min_vel_y': -1.4,
    'FollowPath.max_vel_y': 1.4,
}

EDGE_PARAMS = {
    # 边缘区 (edge)：允许旋转对齐朝向，允许横向移动
    # limit_yaw: false → 解除 yaw 限制，允许旋转对齐目标朝向
    # vy 保持原值（mapper 需要大 cmd 克服死区），通过降低 DecouplingCritic
    # 来抑制螃蟹走：DWB 更倾向转 yaw + 直走 X，需要 vy 时仍能全量输出
    'general_goal_checker.x_goal_tolerance': 0.08,
    'general_goal_checker.y_goal_tolerance': 0.15,
    'general_goal_checker.yaw_goal_tolerance': 0.17453,
    'FollowPath.x_goal_tolerance': 0.08,
    'FollowPath.y_goal_tolerance': 0.15,
    'FollowPath.dwb_yaw_constraint::RotateToGoalXY.scale': 32.0,
    'FollowPath.GoalAlign.scale': 24.0,
    'FollowPath.PathAlign.scale': 32.0,
    'FollowPath.dwb_yaw_constraint::MaintainYawCritic.scale': 0.0,
    'FollowPath.dwb_yaw_constraint::DecouplingCritic.scale': 5.0,
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
    """Switches Nav2 controller params dynamically based on mission BT zone commands."""

    def __init__(self):
        super().__init__('position_based_param_switcher')

        self.declare_parameter('nav_zone_topic', '/mission_bt/nav_zone')
        self.declare_parameter('target_node', 'controller_server')

        self.nav_zone_topic: str = self.get_parameter('nav_zone_topic').value  # type: ignore
        self.target_node: str = self.get_parameter('target_node').value  # type: ignore

        # State
        self.current_zone = None      # 'middle' or 'edge'
        self.switch_in_progress = False

        # SetParameters client for dynamic param updates
        srv_name = f'/{self.target_node}/set_parameters'
        self.param_client = self.create_client(SetParameters, srv_name)

        # Subscribe to nav_zone topic (published by Nav2PoseNode BT plugin)
        self.sub = self.create_subscription(
            String, self.nav_zone_topic, self.nav_zone_callback, 10)

        self.get_logger().info(
            '============================================================\n'
            '  PositionBasedParamSwitcher — zone-driven by limit_yaw\n'
            '  Zone "middle": limit_yaw=true  (yaw locked to 0, no rotation)\n'
            '  Zone "edge":   limit_yaw=false (rotation allowed, yaw unlocked)\n'
            f'  Listening on: {self.nav_zone_topic}\n'
            f'  Target node: /{self.target_node}\n'
            '============================================================'
        )

    # ------------------------------------------------------------------
    # Zone callback — zone is determined by mission BT, not x-coordinate
    # ------------------------------------------------------------------

    def nav_zone_callback(self, msg: String):
        if self.switch_in_progress:
            return

        new_zone = msg.data.strip()
        if new_zone not in ('middle', 'edge'):
            self.get_logger().warning(
                f'Unknown zone "{new_zone}" received (expected "middle" or "edge"), ignoring'
            )
            return

        if new_zone != self.current_zone:
            old = self.current_zone
            self.current_zone = new_zone
            self.get_logger().info(
                f'Zone change: {old} → {new_zone} (from {self.nav_zone_topic})'
            )
            self._apply_zone_params(new_zone)

    # ------------------------------------------------------------------
    # Dynamic parameter update (zero downtime)
    # ------------------------------------------------------------------

    def _apply_zone_params(self, zone: str):
        """
        Push the zone's parameter set to controller_server atomically.

        All parameters are set in one service call — the controller
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
                f'Switched to "{self.current_zone}" zone params — OK'
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
