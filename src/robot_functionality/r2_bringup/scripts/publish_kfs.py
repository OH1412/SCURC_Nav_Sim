#!/usr/bin/env python3
"""
临时测试发布器：发布一条 KFSDecision（只发一次），使用 ROS 时钟打时间戳。
设计目标：在行为树启动后（延迟一段时间）自动运行，避免时间戳与 /clock 不一致导致的 MessageFilter 丢弃。
"""
import time
import argparse
import rclpy
from rclpy.node import Node
from yolov8_ros2_msgs.msg import KFSDecision


class ContinuousKfsPub(Node):
    def __init__(self):
        super().__init__('kfs_test_pub')
        self.pub = self.create_publisher(KFSDecision, '/kfs_decision', 10)

    def publish_loop(self, timeout_sec: float = 30.0, interval: float = 1.0):
        """持续发布，直到发现订阅者或超时。

        - timeout_sec: 最大持续时间（秒），0 表示无限期
        - interval: 每次发布间隔（秒）
        """
        self.get_logger().info('Waiting for at least 1 matching subscription(s)...')
        start = time.time()
        published_count = 0

        while rclpy.ok():
            now = time.time()
            elapsed = now - start
            if timeout_sec > 0 and elapsed >= timeout_sec:
                self.get_logger().warn(f'timeout ({timeout_sec}s) reached, stopping publisher')
                break

            # 构造消息并使用 ROS 时钟打点
            m = KFSDecision()
            m.total_stairs = 12
            m.stair_object_type = [1,4,2,0,3,0,1,0,2,0,0,0]
            m.stair_confidences = [0.9,0.0,0.85,0.0,0.6,0.0,0.95,0.0,0.8,0.0,0.0,0.0]
            m.stair_names = ['s1','s2','s3','s4','s5','s6','s7','s8','s9','s10','s11','s12']
            m.timestamp = self.get_clock().now().to_msg()
            m.frame_id = 'camera'

            try:
                self.pub.publish(m)
                published_count += 1
                self.get_logger().info(f'publishing #{published_count}: KFSDecision timestamp={m.timestamp.sec}')
            except Exception as e:
                self.get_logger().error('Publish failed: %s' % str(e))

            # 为了确保kfs_planner_node能接收到消息，持续发布一段时间
            if published_count >= 20:  # 发布20条消息后停止
                self.get_logger().info('Published 20 messages; stopping')
                break

            # 睡一段时间再试
            time.sleep(interval)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--timeout', type=float, default=30.0, help='最大发布超时（秒），0 表示无限期')
    parser.add_argument('--interval', type=float, default=1.0, help='发布间隔（秒）')
    args = parser.parse_args()

    rclpy.init()
    node = ContinuousKfsPub()
    try:
        # 等待 rclpy 初始化
        time.sleep(0.1)
        node.publish_loop(timeout_sec=args.timeout, interval=args.interval)
        # 再等待一下，确保消息发送
        time.sleep(0.2)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
