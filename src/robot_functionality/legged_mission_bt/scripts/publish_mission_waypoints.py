#!/usr/bin/env python3
"""示例：外部节点通过话题向 mission_bt_node 注入航点。

Usage:
  ros2 run legged_mission_bt publish_mission_waypoints.py
  ros2 run legged_mission_bt publish_mission_waypoints.py --ros-args -p delay_sec:=5.0
"""

import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy

from legged_mission_bt.msg import ArmWaypoint, NavWaypoint


class MissionWaypointPublisher(Node):

    def __init__(self):
        super().__init__('mission_waypoint_publisher')
        self.declare_parameter('delay_sec', 2.0)
        self.declare_parameter('nav_waypoint_topic', '/mission_bt/nav_waypoint')
        self.declare_parameter('arm_waypoint_topic', '/mission_bt/arm_waypoint')

        delay = self.get_parameter('delay_sec').value
        nav_topic = self.get_parameter('nav_waypoint_topic').value
        arm_topic = self.get_parameter('arm_waypoint_topic').value

        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
        self._nav_pub = self.create_publisher(NavWaypoint, nav_topic, qos)
        self._arm_pub = self.create_publisher(ArmWaypoint, arm_topic, qos)

        self.get_logger().info(
            f'Will publish demo waypoints in {delay:.1f}s to {nav_topic} / {arm_topic}')
        self.create_timer(delay, self._publish_once)
        self._published = False

    def _publish_once(self):
        if self._published:
            return
        self._published = True

        nav_points = [
            ('1', 'map', 1.35, -0.85, 0.0),
            ('2', 'map', 1.925, -0.85, 0.0),
            ('3', 'map', 5.25, -0.85, 0.0),
        ]
        arm_points = [
            ('10', 0.0, -550.0, -100.0, 0.0),
            ('11', 0.0, -500.0, -50.0, 0.0),
        ]

        for wp_id, frame, x, y, yaw in nav_points:
            msg = NavWaypoint()
            msg.id = wp_id
            msg.frame_id = frame
            msg.x = x
            msg.y = y
            msg.yaw = yaw
            self._nav_pub.publish(msg)
            self.get_logger().info(f'Published nav wp_id={wp_id} ({x:.3f}, {y:.3f})')
            time.sleep(0.05)

        for wp_id, x, y, z, yaw in arm_points:
            msg = ArmWaypoint()
            msg.id = wp_id
            msg.x = x
            msg.y = y
            msg.z = z
            msg.yaw = yaw
            self._arm_pub.publish(msg)
            self.get_logger().info(f'Published arm wp_id={wp_id} ({x:.1f}, {y:.1f}, {z:.1f})')
            time.sleep(0.05)

        self.get_logger().info('All demo waypoints published. BT nodes can now resolve wp_id.')


def main():
    rclpy.init()
    node = MissionWaypointPublisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
