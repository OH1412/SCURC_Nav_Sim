#!/usr/bin/env python3
"""
发布 base_link 在 map 系下的位姿，类型为 nav_msgs/Odometry。

与 /aft_mapped_to_init 同消息类型，可替代 Fast-LIVO 的里程计输出，
通过 TF (map → base_link) 获取当前位姿并以 Odometry 话题发布。

默认发布话题: /base_link_in_map
配置参数:
  - target_topic:     发布话题名 (默认 /base_link_in_map)
  - publish_rate:      发布频率 Hz (默认 50.0)
  - base_frame:        机器人本体坐标系 (默认 base_link)
  - map_frame:         全局坐标系 (默认 map)
  - publish_tf:        是否同步发布 map→base_link 的 TF (默认 false)
"""

import sys
from pathlib import Path

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped
from tf2_ros import Buffer, TransformListener, TransformException

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mission_log_client import log_event


class BaseLinkOdomPublisher(Node):
    def __init__(self):
        super().__init__('base_link_odom_publisher')

        # ── 参数 ──────────────────────────────────────────────────
        self.declare_parameter('target_topic', '/base_link_in_map')
        self.declare_parameter('publish_rate', 50.0)
        self.declare_parameter('base_frame', 'base_link')
        self.declare_parameter('map_frame', 'map')
        self.declare_parameter('publish_tf', False)

        target_topic = self.get_parameter('target_topic').value
        self.publish_rate = self.get_parameter('publish_rate').value
        self.base_frame = self.get_parameter('base_frame').value
        self.map_frame = self.get_parameter('map_frame').value
        self.publish_tf_flag = self.get_parameter('publish_tf').value

        # ── TF 监听 ──────────────────────────────────────────────────
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # ── 发布者 ──────────────────────────────────────────────────
        self.odom_pub = self.create_publisher(Odometry, target_topic, 10)
        self._first_published = False

        # ── 定时器 ──────────────────────────────────────────────────
        self.timer = self.create_timer(1.0 / self.publish_rate, self._timer_callback)

        self.get_logger().info(
            f'base_link_odom_publisher 已启动: '
            f'{self.map_frame}→{self.base_frame} → '
            f'Odom 发布到 {target_topic} @ {self.publish_rate} Hz'
        )

    def _timer_callback(self):
        """定时查 TF 并发布 Odometry。"""
        try:
            transform: TransformStamped = self.tf_buffer.lookup_transform(
                self.map_frame,
                self.base_frame,
                rclpy.time.Time(),
            )
        except TransformException as e:
            self.get_logger().warning(
                f'无法获取 {self.map_frame}→{self.base_frame} 变换: {e}',
                throttle_duration_sec=5.0,
            )
            return

        # ── 构造 Odometry 消息 ─────────────────────────────────
        msg = Odometry()
        msg.header.stamp = transform.header.stamp
        msg.header.frame_id = self.map_frame
        msg.child_frame_id = self.base_frame

        msg.pose.pose.position.x = transform.transform.translation.x
        msg.pose.pose.position.y = transform.transform.translation.y
        msg.pose.pose.position.z = transform.transform.translation.z
        msg.pose.pose.orientation = transform.transform.rotation

        # 协方差设为 -1 表示该数据不可用
        msg.pose.covariance[0] = -1.0

        self.odom_pub.publish(msg)

        if not self._first_published:
            self._first_published = True
            log_event(
                self, 'base_link_odom_publisher', 'FIRST_ODOM',
                f'首帧 Odometry 已发布至 {self.get_parameter("target_topic").value}',
            )
            self.get_logger().info(
                f'首帧发布: x={transform.transform.translation.x:.3f}, '
                f'y={transform.transform.translation.y:.3f}'
            )


def main(args=None):
    rclpy.init(args=args)
    node = BaseLinkOdomPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
