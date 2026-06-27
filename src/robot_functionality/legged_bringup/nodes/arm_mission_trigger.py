#!/usr/bin/env python3
# ============================================================================
# 机械臂抓取使命自动触发器
# ============================================================================
# 发送一个 NavigateToPose goal 到 bt_navigator，触发自包含 BT。
# BT 内部已硬编码 3 个 waypoint + 机械臂抓取 + 10s 等待，外部 goal 仅作触发。
# ============================================================================

import sys
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import PoseStamped


class ArmMissionTrigger(Node):
    def __init__(self):
        super().__init__('arm_mission_trigger')

        self.declare_parameter('startup_delay', 0.0)
        self.declare_parameter('action_timeout', 30.0)

        startup_delay = self.get_parameter('startup_delay').value
        action_timeout = self.get_parameter('action_timeout').value

        self.get_logger().info(
            f'Arm mission trigger starting in {startup_delay:.1f}s...')

        self._ac = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self._action_timeout = action_timeout
        self._goal_sent = False
        self._timer = self.create_timer(startup_delay + 0.1, self._send_goal)

    def _send_goal(self):
        if self._goal_sent:
            return
        self._goal_sent = True
        self._timer.cancel()

        if not self._ac.wait_for_server(timeout_sec=10.0):
            self.get_logger().error(
                'NavigateToPose action server not available after 10s. Aborting.')
            rclpy.shutdown()
            sys.exit(1)

        goal = NavigateToPose.Goal()
        goal.pose = PoseStamped()
        goal.pose.header.frame_id = 'map'
        goal.pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose.pose.position.x = 0.0
        goal.pose.pose.position.y = 0.0
        goal.pose.pose.position.z = 0.0
        goal.pose.pose.orientation.w = 1.0
        # behavior_tree 留空，使用 bt_navigator 配置的默认 BT

        self.get_logger().info('Sending NavigateToPose goal to trigger BT...')
        future = self._ac.send_goal_async(goal)
        future.add_done_callback(self._goal_response_cb)

    def _goal_response_cb(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error('NavigateToPose goal REJECTED!')
            rclpy.shutdown()
            sys.exit(1)

        self.get_logger().info('Goal accepted. BT mission started!')
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self._result_cb)

    def _result_cb(self, future):
        result = future.result()
        self.get_logger().info(
            f'BT mission completed. Result: {result.status}')
        rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)
    node = ArmMissionTrigger()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
