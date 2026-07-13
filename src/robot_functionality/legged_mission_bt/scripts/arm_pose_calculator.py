#!/usr/bin/env python3
"""示例：外部机械臂坐标计算节点 — 收到 arm_pose_request 后发布 arm_waypoint。

实际项目中替换 _compute_arm_pose() 为视觉/运动学计算。

Usage:
  ros2 run legged_mission_bt arm_pose_calculator.py
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy

from legged_mission_bt.msg import ArmPoseRequest, ArmWaypoint, NavReached

PICK_IDS = frozenset({0, 1, 2, 3, 4, 5, 6, 7, 16})
PLACE_IDS = frozenset({8, 9, 10, 11, 12, 13, 14, 15, 17})


class ArmPoseCalculator(Node):

    def __init__(self):
        super().__init__('arm_pose_calculator')
        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)

        self._arm_pub = self.create_publisher(ArmWaypoint, '/mission_bt/arm_waypoint', qos)
        self.create_subscription(
            ArmPoseRequest, '/mission_bt/arm_pose_request', self._on_request, qos)
        self.create_subscription(
            NavReached, '/mission_bt/nav_reached', self._on_nav_reached, qos)

        self.get_logger().info('Arm pose calculator ready (listening arm_pose_request)')

    def _on_nav_reached(self, msg):
        self.get_logger().debug(f'nav_reached: {msg.nav_id}')

    def _on_request(self, msg: ArmPoseRequest):
        slot = str(msg.arm_point_id)
        x, y, z, yaw = self._compute_arm_pose(msg.arm_point_id)
        out = ArmWaypoint()
        out.id = slot
        out.x = x
        out.y = y
        out.z = z
        out.yaw = yaw
        self._arm_pub.publish(out)
        self.get_logger().info(
            f'Computed arm wp_id={slot} nav={msg.nav_id} → ({x:.1f}, {y:.1f}, {z:.1f})')

    def _compute_arm_pose(self, arm_point_id: int):
        """占位：按点位编号返回 arm_base 毫米坐标。"""
        if arm_point_id in PICK_IDS:
            return 0.0, -550.0, -100.0, 0.0
        if arm_point_id in PLACE_IDS:
            return 0.0, -500.0, -50.0, 0.0
        return 0.0, -500.0, -50.0, 0.0


def main():
    rclpy.init()
    node = ArmPoseCalculator()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
