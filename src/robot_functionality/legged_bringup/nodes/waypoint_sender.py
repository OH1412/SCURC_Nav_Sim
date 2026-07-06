#!/usr/bin/env python3
# ============================================================================
# 定点导航 - Waypoint Sender
# ============================================================================
# 从 waypoints.yaml 加载航点，逐点发送 NavigateToPose。
# 使用 nav2_params 中的 default_nav_to_pose_bt_xml（navigate_waypoints_with_task.xml：
#   规划 → 跟随 → ArmControl）。
#
# 用法:
#   ros2 run legged_bringup waypoint_sender.py
#   ros2 run legged_bringup waypoint_sender.py --ros-args \
#     -p waypoint_file:=<path_to_waypoints.yaml>
# ============================================================================

import math
import os
import sys

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
import yaml

from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose


def yaw_to_quaternion(yaw: float):
    return {
        'x': 0.0,
        'y': 0.0,
        'z': math.sin(yaw / 2.0),
        'w': math.cos(yaw / 2.0),
    }


class WaypointSender(Node):
    """逐点 NavigateToPose，BT 内执行 ArmControl"""

    def __init__(self):
        super().__init__('waypoint_sender')

        bringup_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        default_waypoint_file = os.path.join(bringup_dir, 'params', 'waypoints.yaml')

        self.declare_parameter('waypoint_file', default_waypoint_file)
        self.declare_parameter('startup_delay', 10.0)
        self.declare_parameter('leg_delay', 0.5)

        waypoint_file = self.get_parameter('waypoint_file').value
        startup_delay = self.get_parameter('startup_delay').value
        self._leg_delay = self.get_parameter('leg_delay').value

        self.get_logger().info(f'Waypoint file: {waypoint_file}')
        self.get_logger().info(f'Startup delay: {startup_delay:.1f}s')
        self.get_logger().info(
            'BT: navigate_to_pose_w_replanning_and_recovery (pure navigation)')

        self._poses = self.load_waypoints(waypoint_file)
        if not self._poses:
            self.get_logger().fatal('No waypoints loaded. Exiting.')
            sys.exit(1)

        for i, p in enumerate(self._poses):
            pos = p.pose.position
            self.get_logger().info(
                f'  [{i + 1}/{len(self._poses)}] x={pos.x:.3f}, y={pos.y:.3f}')

        self._index = -1
        self._nav_ac = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self._startup_timer = self.create_timer(startup_delay, self._start_mission)

    def load_waypoints(self, filepath: str):
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

    def _start_mission(self):
        self._startup_timer.cancel()
        if not self._nav_ac.wait_for_server(timeout_sec=15.0):
            self.get_logger().error(
                'NavigateToPose action server unavailable. Is bt_navigator running?')
            rclpy.shutdown()
            return
        self.get_logger().info('NavigateToPose ready. Starting waypoint sequence...')
        self._advance()

    def _advance(self):
        self._index += 1
        if self._index >= len(self._poses):
            self.get_logger().info('All waypoints completed.')
            rclpy.shutdown()
            return

        if self._index > 0 and self._leg_delay > 0.0:
            import time
            time.sleep(self._leg_delay)

        pose = self._poses[self._index]
        goal = NavigateToPose.Goal()
        goal.pose = pose
        goal.pose.header.stamp = self.get_clock().now().to_msg()

        n = self._index + 1
        total = len(self._poses)
        pos = pose.pose.position
        self.get_logger().info(
            f'▶ [{n}/{total}] NavigateToPose → ({pos.x:.3f}, {pos.y:.3f})')
        future = self._nav_ac.send_goal_async(goal)
        future.add_done_callback(self._goal_response_cb)

    def _goal_response_cb(self, future):
        try:
            goal_handle = future.result()
        except Exception as e:
            self.get_logger().error(f'Goal send failed: {e}')
            rclpy.shutdown()
            return

        if not goal_handle.accepted:
            self.get_logger().error(f'Goal [{self._index + 1}] rejected')
            rclpy.shutdown()
            return

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self._result_cb)

    def _result_cb(self, future):
        try:
            result = future.result()
            status = result.status
        except Exception as e:
            self.get_logger().error(f'Goal [{self._index + 1}] result error: {e}')
            rclpy.shutdown()
            return

        # action_msgs/GoalStatus STATUS_SUCCEEDED = 4
        if status != 4:
            self.get_logger().error(
                f'Goal [{self._index + 1}] failed (status={status}). Stopping.')
            rclpy.shutdown()
            return

        self.get_logger().info(f'✅ [{self._index + 1}/{len(self._poses)}] done')
        self._advance()


def main(args=None):
    rclpy.init(args=args)
    node = WaypointSender()
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
