#!/usr/bin/env python3
"""
发布 arm_root 在 map 系下的位姿，类型为 nav_msgs/Odometry。

arm_root 是机械臂工作空间原点，位于 base_link 的固定偏移处（无旋转）。
通过 TF (map → base_link) + 静态 offset 计算 arm_root 位姿并发布。

与 arm_pose_broadcaster 共用同样的 arm_root_in_base_link 参数。

默认发布话题: /arm_root_in_map
配置参数:
  - target_topic:               发布话题名 (默认 /arm_root_in_map)
  - publish_rate:               发布频率 Hz (默认 50.0)
  - base_frame:                 机器人本体坐标系 (默认 base_link)
  - map_frame:                  全局坐标系 (默认 map)
  - publish_tf:                 是否同步发布 map→arm_root 的 TF (默认 true)
  - arm_root_in_base_link.x:    arm_root 在 base_link 下 x (m) (默认 -0.00973)
  - arm_root_in_base_link.y:    arm_root 在 base_link 下 y (m) (默认 0.00004)
  - arm_root_in_base_link.z:    arm_root 在 base_link 下 z (m) (默认 0.19068)
"""

import math
import sys
from pathlib import Path

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped
from tf2_ros import Buffer, TransformListener, TransformBroadcaster, TransformException

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mission_log_client import log_event


class ArmRootOdomPublisher(Node):
    def __init__(self):
        super().__init__('arm_root_odom_publisher')

        self.declare_parameter('target_topic', '/arm_root_in_map')
        self.declare_parameter('publish_rate', 50.0)
        self.declare_parameter('base_frame', 'base_link')
        self.declare_parameter('map_frame', 'map')
        self.declare_parameter('publish_tf', True)
        self.declare_parameter('arm_root_in_base_link.x', -0.00973)
        self.declare_parameter('arm_root_in_base_link.y', 0.00004)
        self.declare_parameter('arm_root_in_base_link.z', 0.19068)

        self.target_topic = self.get_parameter('target_topic').value
        self.publish_rate = self.get_parameter('publish_rate').value
        self.base_frame = self.get_parameter('base_frame').value
        self.map_frame = self.get_parameter('map_frame').value
        self.publish_tf_flag = self.get_parameter('publish_tf').value
        self.offset_x = self.get_parameter('arm_root_in_base_link.x').value
        self.offset_y = self.get_parameter('arm_root_in_base_link.y').value
        self.offset_z = self.get_parameter('arm_root_in_base_link.z').value

        # ── TF ──
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.tf_broadcaster = TransformBroadcaster(self)

        # ── Publisher ──
        self.odom_pub = self.create_publisher(Odometry, self.target_topic, 10)
        self._first_published = False

        # ── Timer ──
        self.timer = self.create_timer(1.0 / self.publish_rate, self._timer_callback)

        self.get_logger().info(
            f'arm_root_odom_publisher: {self.map_frame}→arm_root → {self.target_topic} @ {self.publish_rate} Hz'
        )
        self.get_logger().info(
            f'arm_root offset in base_link: ({self.offset_x:.5f}, {self.offset_y:.5f}, {self.offset_z:.5f}) m'
        )

    def _timer_callback(self):
        try:
            transform: TransformStamped = self.tf_buffer.lookup_transform(
                self.map_frame, self.base_frame, rclpy.time.Time())
        except TransformException as e:
            self.get_logger().warning(
                f'TF lookup failed {self.map_frame}→{self.base_frame}: {e}',
                throttle_duration_sec=5.0)
            return

        bx = transform.transform.translation.x
        by = transform.transform.translation.y
        bz = transform.transform.translation.z
        bq = transform.transform.rotation

        # 提取 base_link yaw
        siny_cosp = 2.0 * (bq.w * bq.z + bq.x * bq.y)
        cosy_cosp = 1.0 - 2.0 * (bq.y * bq.y + bq.z * bq.z)
        byaw = math.atan2(siny_cosp, cosy_cosp)

        # arm_root = base_link + offset (base_link 系旋转后叠加)
        c, s = math.cos(byaw), math.sin(byaw)
        arm_x = bx + c * self.offset_x - s * self.offset_y
        arm_y = by + s * self.offset_x + c * self.offset_y
        arm_z = bz + self.offset_z

        # ── Odometry ──
        msg = Odometry()
        msg.header.stamp = transform.header.stamp
        msg.header.frame_id = self.map_frame
        msg.child_frame_id = 'arm_root'

        msg.pose.pose.position.x = arm_x
        msg.pose.pose.position.y = arm_y
        msg.pose.pose.position.z = arm_z
        msg.pose.pose.orientation = bq  # arm_root 与 base_link 无旋转
        msg.pose.covariance[0] = -1.0

        self.odom_pub.publish(msg)

        # ── TF ──
        if self.publish_tf_flag:
            tf_msg = TransformStamped()
            tf_msg.header.stamp = transform.header.stamp
            tf_msg.header.frame_id = self.map_frame
            tf_msg.child_frame_id = 'arm_root'
            tf_msg.transform.translation.x = arm_x
            tf_msg.transform.translation.y = arm_y
            tf_msg.transform.translation.z = arm_z
            tf_msg.transform.rotation = bq
            self.tf_broadcaster.sendTransform(tf_msg)

        if not self._first_published:
            self._first_published = True
            log_event(
                self, 'arm_root_odom_publisher', 'FIRST_ODOM',
                f'首帧 arm_root Odometry 已发布至 {self.target_topic}',
            )
            self.get_logger().info(
                f'arm_root 首帧: x={arm_x:.3f}, y={arm_y:.3f}, z={arm_z:.3f}'
            )


def main(args=None):
    rclpy.init(args=args)
    node = ArmRootOdomPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
