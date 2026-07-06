#!/usr/bin/env python3
"""示例 mission_plan：抓取用 0~7，放置用 8~15。"""

import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy

from legged_mission_bt.msg import MissionPlan, MissionStep, NavWaypoint


class MissionPlanPublisher(Node):

    def __init__(self):
        super().__init__('mission_plan_publisher')
        self.declare_parameter('delay_sec', 2.0)
        delay = self.get_parameter('delay_sec').value

        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
        self._plan_pub = self.create_publisher(MissionPlan, '/mission_bt/mission_plan', qos)
        self._nav_pub = self.create_publisher(NavWaypoint, '/mission_bt/nav_waypoint', qos)

        self.create_timer(delay, self._publish_once)
        self._done = False

    def _publish_once(self):
        if self._done:
            return
        self._done = True

        nav_points = {
            'nav_pick': ('map', 1.925, -0.85, 0.0),
            'nav_place': ('map', 5.25, -0.85, 0.0),
        }
        for wp_id, (frame, x, y, yaw) in nav_points.items():
            msg = NavWaypoint()
            msg.id = wp_id
            msg.frame_id = frame
            msg.x, msg.y, msg.yaw = x, y, yaw
            self._nav_pub.publish(msg)
            time.sleep(0.05)

        plan = MissionPlan()
        steps = [
            ('nav_pick', 1, MissionStep.ARM_PICK),
            ('nav_place', 9, MissionStep.ARM_PLACE),
        ]
        for nav_id, arm_point_id, action in steps:
            step = MissionStep()
            step.nav_id = nav_id
            step.arm_point_id = arm_point_id
            step.arm_action = action
            plan.steps.append(step)

        self._plan_pub.publish(plan)
        self.get_logger().info('Published plan: pick→1, place→9')


def main():
    rclpy.init()
    node = MissionPlanPublisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
