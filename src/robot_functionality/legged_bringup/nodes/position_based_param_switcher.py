#!/usr/bin/env python3
"""
Nav2 Parameter Switcher Node — zone-driven by mission BT (motion_planner).

Listens to /mission_bt/nav_zone for zone commands published by Nav2PoseNode.
Zone selection by motion_planner id:
  - motion_planner=0 → zone = "middle" (yaw lock segment dir front-facing, vy lateral, Y tracking)
  - motion_planner=1 → zone = "edge"   (front-tangent, rotation allowed, vy lateral)
  - motion_planner=2 → zone = "edge"   (rear-tangent, rotation allowed, vy lateral)
  - motion_planner=3 → zone = "straight" (x-only, vy=0, vtheta=0)
  - edge→middle transition: mp=1(1m), mp=2(2m) auto-switch when within threshold of goal

Switches DWB critic scales + goal checker tolerance via ros2 param set — zero downtime.

All critics are pre-loaded in nav2_params.yaml; this node toggles their scale values.
Custom dwb_yaw_constraint critics register dynamic scale callbacks so set_parameters
takes effect on the next control cycle.
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import (
    QoSProfile,
    DurabilityPolicy,
    ReliabilityPolicy,
    HistoryPolicy,
)
from std_msgs.msg import String
from rcl_interfaces.srv import SetParameters
from rcl_interfaces.msg import Parameter, ParameterValue


# Latched QoS: late subscribers (switcher starts 8s after nav) still receive last zone.
LATCHED_QOS = QoSProfile(
    depth=1,
    durability=DurabilityPolicy.TRANSIENT_LOCAL,
    reliability=ReliabilityPolicy.RELIABLE,
    history=HistoryPolicy.KEEP_LAST,
)

# ---------------------------------------------------------------------------
# Parameter sets for each zone
#   Key = full ROS2 parameter name on /controller_server
#   Value = float
# ---------------------------------------------------------------------------

MIDDLE_PARAMS = {
    # middle：MaintainYaw×5000 锁 map 0°
    # 仅第一次进入 |err|≤30° 之前可「纯旋」；进入后永久 phase-2（软打分，不再因偏航卡住 xy）
    # goal checker 容差仍 6.28，到位不卡 yaw
    'general_goal_checker.yaw_goal_tolerance': 6.28,
    'FollowPath.dwb_yaw_constraint::RotateToGoalXYCritic.scale': 0.0,
    'FollowPath.dwb_yaw_constraint::RotateToPathCritic.scale': 0.0,
    'FollowPath.GoalAlign.scale': 0.0,
    'FollowPath.PathAlign.scale': 0.0,
    'FollowPath.dwb_yaw_constraint::MaintainYawCritic.scale': 5000.0,
    'FollowPath.dwb_yaw_constraint::MaintainYawCritic.desired_yaw': 0.0,
    # 一次性 phase-1 带宽（仅首次对准用）；不是持续「超阈值就纯旋」
    'FollowPath.dwb_yaw_constraint::MaintainYawCritic.yaw_error_threshold': 0.5236,
    'FollowPath.dwb_yaw_constraint::DecouplingCritic.scale': 0.0,
    'FollowPath.PathDist.scale': 32.0,
    'FollowPath.min_vel_y': -1.0,
    'FollowPath.max_vel_y': 1.0,
    'FollowPath.trans_stopped_velocity': 0.25,
}

EDGE_PARAMS = {
    'general_goal_checker.yaw_goal_tolerance': 6.28,
    'FollowPath.dwb_yaw_constraint::RotateToGoalXYCritic.scale': 32.0,
    'FollowPath.dwb_yaw_constraint::RotateToPathCritic.scale': 96.0,
    'FollowPath.GoalAlign.scale': 24.0,
    'FollowPath.PathAlign.scale': 32.0,
    'FollowPath.dwb_yaw_constraint::MaintainYawCritic.scale': 0.0,
    'FollowPath.dwb_yaw_constraint::MaintainYawCritic.desired_yaw': 0.0,
    'FollowPath.dwb_yaw_constraint::DecouplingCritic.scale': 5.0,
    'FollowPath.PathDist.scale': 32.0,         # edge 默认路径距离权重
    'FollowPath.min_vel_y': -1.1,
    'FollowPath.max_vel_y': 1.1,
    'FollowPath.trans_stopped_velocity': 0.08,
}

STRAIGHT_PARAMS = {
    'general_goal_checker.yaw_goal_tolerance': 6.28,
    'FollowPath.dwb_yaw_constraint::RotateToGoalXYCritic.scale': 0.0,
    'FollowPath.dwb_yaw_constraint::RotateToPathCritic.scale': 0.0,
    'FollowPath.GoalAlign.scale': 0.0,
    'FollowPath.PathAlign.scale': 0.0,
    'FollowPath.dwb_yaw_constraint::MaintainYawCritic.scale': 0.0,
    'FollowPath.dwb_yaw_constraint::MaintainYawCritic.desired_yaw': 0.0,
    'FollowPath.dwb_yaw_constraint::MaintainYawCritic.yaw_error_threshold': 6.28,
    'FollowPath.dwb_yaw_constraint::DecouplingCritic.scale': 0.0,
    'FollowPath.PathDist.scale': 32.0,         # straight 默认路径距离权重
    'FollowPath.min_vel_y': 0.0,
    'FollowPath.max_vel_y': 0.0,
    'FollowPath.max_vel_theta': 0.0,
    'FollowPath.trans_stopped_velocity': 0.25,
}

ZONE_PARAMS = {'middle': MIDDLE_PARAMS, 'edge': EDGE_PARAMS, 'straight': STRAIGHT_PARAMS}


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
        self.declare_parameter('default_zone', 'edge')

        self.nav_zone_topic: str = self.get_parameter('nav_zone_topic').value  # type: ignore
        self.target_node: str = self.get_parameter('target_node').value  # type: ignore
        self.default_zone: str = self.get_parameter('default_zone').value  # type: ignore

        self.current_zone = None
        self.pending_zone = None
        self.switch_in_progress = False
        self._default_applied = False

        srv_name = f'/{self.target_node}/set_parameters'
        self.param_client = self.create_client(SetParameters, srv_name)

        self.sub = self.create_subscription(
            String, self.nav_zone_topic, self.nav_zone_callback, LATCHED_QOS)

        # Apply default zone once controller_server is ready (before first nav step).
        self.create_timer(1.0, self._maybe_apply_default_zone)

        self.get_logger().info(
            '============================================================\n'
            '  PositionBasedParamSwitcher — zone-driven by motion_planner\n'
            '  Zone "middle":   mp=0 / near-goal (MaintainYaw→map 0°, |err|>30° rotate-first)\n'
            '  Zone "edge":     mp=1/2 (rotation allowed, yaw unlocked; edge→middle at 2.0m)\n'
            '  Zone "straight": mp=3 (x-only, vy=vtheta=0)\n'
            f'  Listening on: {self.nav_zone_topic} (latched)\n'
            f'  Default zone: {self.default_zone}\n'
            f'  Target node: /{self.target_node}\n'
            '============================================================'
        )

    def nav_zone_callback(self, msg: String):
        new_zone = msg.data.strip()
        if new_zone not in ('middle', 'edge', 'straight'):
            self.get_logger().warning(
                f'Unknown zone "{new_zone}" received (expected "middle", "edge", or "straight"), ignoring'
            )
            return

        if self.switch_in_progress:
            self.pending_zone = new_zone
            return

        if new_zone == self.current_zone:
            return

        old = self.current_zone
        self.current_zone = new_zone
        self.get_logger().info(
            f'Zone change: {old} → {new_zone} (from {self.nav_zone_topic})'
        )
        self._apply_zone_params(new_zone)

    def _maybe_apply_default_zone(self):
        if self._default_applied or self.current_zone is not None:
            return
        if self.default_zone not in ZONE_PARAMS:
            return
        if not self.param_client.wait_for_service(timeout_sec=0.2):
            return

        self._default_applied = True
        self.current_zone = self.default_zone
        self.get_logger().info(
            f'Applying startup default zone "{self.default_zone}" '
            f'(waiting for /mission_bt/nav_zone override)'
        )
        self._apply_zone_params(self.default_zone)

    def _apply_zone_params(self, zone: str):
        self.switch_in_progress = True
        params_dict = ZONE_PARAMS[zone]
        params = [_make_param(k, v) for k, v in params_dict.items()]

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
        self.switch_in_progress = False
        try:
            result = future.result()
        except Exception as e:
            self.get_logger().error(f'set_parameters call failed: {e}')
            # Do NOT overwrite pending_zone here — an edge→middle command may
            # have arrived while this apply was in flight.
            return

        failures = [res.reason for res in result.results if not res.successful]
        if failures:
            self.get_logger().warning(f'Some params failed to set: {failures}')
        else:
            self.get_logger().info(
                f'Switched to "{self.current_zone}" zone params — OK'
            )
            # Debug probe (disabled — extra get_parameters round-trip):
            # try:
            #     from rcl_interfaces.srv import GetParameters
            #     ...
            #     self.get_logger().info(f'CRITIC_SCALE_STORE_CHECK zone=...')
            # except Exception as e:
            #     self.get_logger().warning(f'CRITIC_SCALE_STORE_CHECK setup failed: {e}')

        if self.pending_zone is not None and self.pending_zone != self.current_zone:
            zone = self.pending_zone
            self.pending_zone = None
            old = self.current_zone
            self.current_zone = zone
            self.get_logger().info(
                f'Applying queued zone: {old} → {zone}'
            )
            self._apply_zone_params(zone)


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
