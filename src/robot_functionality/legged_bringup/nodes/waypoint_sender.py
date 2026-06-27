#!/usr/bin/env python3
# ============================================================================
# 定点导航 - Waypoint Sender
# ============================================================================
# 从 waypoints.yaml 加载定点列表，发送给 waypoint_follower。
#
# 用法:
#   1) 直接运行:
#      ros2 run legged_bringup waypoint_sender.py \
#        --ros-args -p waypoint_file:=<path_to_waypoints.yaml>
#
#   2) 通过 launch 文件启动:
#      在 launch 中 add Node，指定 waypoint_file 参数
#
#   3) 不指定 waypoint_file 则使用默认路径:
#      <legged_bringup>/params/waypoints.yaml
# ============================================================================

import math
import os
import sys

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
import yaml

from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import FollowWaypoints


def yaw_to_quaternion(yaw: float):
    """欧拉角 yaw → 四元数 (只绕 z 轴旋转)"""
    return {
        'x': 0.0,
        'y': 0.0,
        'z': math.sin(yaw / 2.0),
        'w': math.cos(yaw / 2.0),
    }


class WaypointSender(Node):
    """加载 waypoints.yaml 并发送 FollowWaypoints 动作"""

    def __init__(self):
        super().__init__('waypoint_sender')

        # 默认路径
        bringup_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        default_waypoint_file = os.path.join(bringup_dir, 'params', 'waypoints.yaml')

        self.declare_parameter('waypoint_file', default_waypoint_file)
        self.declare_parameter('startup_delay', 10.0)

        waypoint_file = self.get_parameter('waypoint_file').value
        startup_delay = self.get_parameter('startup_delay').value

        self.get_logger().info(f'Waypoint file: {waypoint_file}')
        self.get_logger().info(f'Startup delay: {startup_delay:.1f}s')

        # 加载 waypoints
        poses = self.load_waypoints(waypoint_file)
        if not poses:
            self.get_logger().fatal('No waypoints loaded. Exiting.')
            sys.exit(1)

        self.get_logger().info(f'Loaded {len(poses)} waypoint(s):')
        for i, p in enumerate(poses):
            pos = p.pose.position
            self.get_logger().info(f'  [{i}] x={pos.x:.2f}, y={pos.y:.2f}')

        # 延迟后发送
        self.action_client = ActionClient(self, FollowWaypoints, 'follow_waypoints')
        self.goal = FollowWaypoints.Goal()
        self.goal.poses = poses
        self.timer = self.create_timer(startup_delay, self.send_waypoints)

    def load_waypoints(self, filepath: str):
        """从 YAML 加载定点列表"""
        if not os.path.exists(filepath):
            self.get_logger().fatal(f'Waypoint file not found: {filepath}')
            return []

        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)

        if not data or 'waypoints' not in data:
            self.get_logger().fatal('Invalid waypoint file: missing "waypoints" key')
            return []

        poses = []
        for wp in data['waypoints']:
            pose = PoseStamped()
            pose.header.frame_id = wp.get('frame_id', 'map')
            pose.header.stamp.sec = 0
            pose.header.stamp.nanosec = 0

            pose.pose.position.x = float(wp.get('x', 0.0))
            pose.pose.position.y = float(wp.get('y', 0.0))
            pose.pose.position.z = float(wp.get('z', 0.0))

            yaw = float(wp.get('yaw', 0.0))
            q = yaw_to_quaternion(yaw)
            pose.pose.orientation.x = q['x']
            pose.pose.orientation.y = q['y']
            pose.pose.orientation.z = q['z']
            pose.pose.orientation.w = q['w']

            poses.append(pose)

        return poses

    def send_waypoints(self):
        """发送 FollowWaypoints 动作"""
        self.timer.cancel()

        if not self.action_client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error(
                'FollowWaypoints action server (/follow_waypoints) not available. '
                'Is waypoint_follower running?'
            )
            return

        self.get_logger().info('Sending waypoints to waypoint_follower...')
        self._send_goal_future = self.action_client.send_goal_async(
            self.goal,
            feedback_callback=self.feedback_callback
        )
        self._send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error('Waypoint goal rejected by waypoint_follower')
            return

        self.get_logger().info('Waypoint goal accepted. Navigating...')
        self._get_result_future = goal_handle.get_result_async()
        self._get_result_future.add_done_callback(self.result_callback)

    def feedback_callback(self, feedback_msg):
        feedback = feedback_msg.feedback
        total = len(self.goal.poses)
        self.get_logger().info(
            f'Progress: waypoint {feedback.current_waypoint + 1}/{total}'
        )

    def result_callback(self, future):
        result = future.result().result
        if result.missed_waypoints:
            self.get_logger().warn(f'Missed waypoints (indices): {list(result.missed_waypoints)}')
        else:
            self.get_logger().info('All waypoints completed successfully!')
        rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)
    node = WaypointSender()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except SystemExit:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
