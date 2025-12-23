#!/usr/bin/env python3
"""
LaserScan Filter Node
过滤有效数据比例不足的 LaserScan 消息

订阅: /raw_scan (sensor_msgs/LaserScan)
发布: /scan (sensor_msgs/LaserScan)

参数:
    - valid_ratio_threshold: 有效数据比例阈值 (默认 0.7, 即 70%)
    - input_topic: 输入话题名 (默认 /raw_scan)
    - output_topic: 输出话题名 (默认 /scan)
"""

import math
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import LaserScan


class ScanFilterNode(Node):
    def __init__(self):
        super().__init__('scan_filter_node')
        
        # 声明参数
        self.declare_parameter('valid_ratio_threshold', 0.3)  # 有效数据比例阈值
        self.declare_parameter('input_topic', '/raw_scan')     # 输入话题
        self.declare_parameter('output_topic', '/scan')        # 输出话题
        self.declare_parameter('log_filtered', False)          # 是否打印被过滤的帧信息
        
        # 获取参数
        self.valid_ratio_threshold = self.get_parameter('valid_ratio_threshold').value
        input_topic = self.get_parameter('input_topic').value
        output_topic = self.get_parameter('output_topic').value
        self.log_filtered = self.get_parameter('log_filtered').value
        
        # 设置 QoS
        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )
        
        # 创建订阅者和发布者
        self.subscription = self.create_subscription(
            LaserScan,
            input_topic,
            self.scan_callback,
            qos
        )
        
        self.publisher = self.create_publisher(
            LaserScan,
            output_topic,
            qos
        )
        
        # 统计信息
        self.total_frames = 0
        self.passed_frames = 0
        self.filtered_frames = 0
        
        # 标记是否已有有效帧通过过滤
        self.has_valid_output = False
        
        # 记录上次发布时间，用于检测是否需要发布空 scan
        self.last_publish_time = self.get_clock().now()
        
        # 创建定时器，检查是否需要发布空 scan（保持话题活跃）
        self.keepalive_timer = self.create_timer(0.1, self.keepalive_callback)
        
        self.get_logger().info(
            f'Scan Filter Node started:\n'
            f'  Input topic: {input_topic}\n'
            f'  Output topic: {output_topic}\n'
            f'  Valid ratio threshold: {self.valid_ratio_threshold * 100:.1f}%\n'
            f'  Will publish empty scans to keep topic alive when no valid data'
        )
    
    def keepalive_callback(self):
        """保持 /scan 话题活跃，如果长时间没有有效帧输出则发布空 scan"""
        now = self.get_clock().now()
        # 如果超过 0.2 秒没有发布，就发布空 scan
        if (now - self.last_publish_time).nanoseconds > 200_000_000:
            empty_scan = LaserScan()
            empty_scan.header.stamp = now.to_msg()
            empty_scan.header.frame_id = 'base_link'
            empty_scan.angle_min = -3.14159
            empty_scan.angle_max = 3.14159
            empty_scan.angle_increment = 0.0087  # ~0.5°
            empty_scan.time_increment = 0.0
            empty_scan.scan_time = 0.1
            empty_scan.range_min = 0.5
            empty_scan.range_max = 30.0
            empty_scan.ranges = [float('inf')] * 720
            empty_scan.intensities = []
            
            self.publisher.publish(empty_scan)
            self.last_publish_time = now
    
    def scan_callback(self, msg: LaserScan):
        """处理接收到的 LaserScan 消息"""
        self.total_frames += 1
        
        # 计算有效数据比例
        total_points = len(msg.ranges)
        if total_points == 0:
            return
        
        # 统计有效数据点数（非 inf 且在有效范围内）
        valid_count = 0
        for r in msg.ranges:
            if not math.isinf(r) and not math.isnan(r):
                if msg.range_min <= r <= msg.range_max:
                    valid_count += 1
        
        valid_ratio = valid_count / total_points
        
        # 检查是否达到阈值
        if valid_ratio >= self.valid_ratio_threshold:
            # 通过过滤，发布消息
            self.publisher.publish(msg)
            self.last_publish_time = self.get_clock().now()  # 更新发布时间
            self.passed_frames += 1
        else:
            # 被过滤掉
            self.filtered_frames += 1
            if self.log_filtered:
                self.get_logger().debug(
                    f'Frame filtered: valid_ratio={valid_ratio * 100:.1f}% '
                    f'(threshold={self.valid_ratio_threshold * 100:.1f}%), '
                    f'valid_points={valid_count}/{total_points}'
                )
    
    def destroy_node(self):
        """节点销毁时打印统计信息"""
        if self.total_frames > 0:
            pass_rate = self.passed_frames / self.total_frames * 100
            self.get_logger().info(
                f'Scan Filter Statistics:\n'
                f'  Total frames: {self.total_frames}\n'
                f'  Passed frames: {self.passed_frames}\n'
                f'  Filtered frames: {self.filtered_frames}\n'
                f'  Pass rate: {pass_rate:.1f}%'
            )
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = ScanFilterNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
