#!/usr/bin/env python3
"""
PointCloud2 range filter: drops points beyond max_range from origin.
Used to exclude distant environmental changes (e.g. new billboards)
from interfering with relocalization.

Subscribes: input_pointcloud (PointCloud2)
Publishes:  output_pointcloud (PointCloud2, filtered)
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2, PointField
import sensor_msgs_py.point_cloud2 as pc2
import numpy as np


class PointCloudRangeFilter(Node):
    def __init__(self):
        super().__init__('pointcloud_range_filter')

        self.declare_parameter('max_range', 4.0)  # max distance from origin (m)
        self.declare_parameter('input_topic', '/livox/lidar/pointcloud')
        self.declare_parameter('output_topic', '/livox/lidar/pointcloud_filtered')

        self.max_range = self.get_parameter('max_range').value
        input_topic = self.get_parameter('input_topic').value
        output_topic = self.get_parameter('output_topic').value

        self.sub = self.create_subscription(
            PointCloud2, input_topic, self.callback, 10)
        self.pub = self.create_publisher(PointCloud2, output_topic, 10)

        self.get_logger().info(
            f'Range filter active: max_range={self.max_range}m | '
            f'{input_topic} → {output_topic}')

    def callback(self, msg: PointCloud2):
        # Parse PointCloud2 → numpy
        points = pc2.read_points_numpy(msg, field_names=('x', 'y', 'z'))
        # Compute distances from origin
        dist = np.sqrt(points['x']**2 + points['y']**2 + points['z']**2)
        mask = dist <= self.max_range
        filtered = points[mask]

        if len(filtered) == 0:
            return

        # Re-pack into PointCloud2
        filtered_msg = pc2.create_cloud_numpy(msg.header, filtered)
        self.pub.publish(filtered_msg)


def main(args=None):
    rclpy.init(args=args)
    node = PointCloudRangeFilter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
