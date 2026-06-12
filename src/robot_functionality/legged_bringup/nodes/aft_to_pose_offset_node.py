#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import PoseStamped


class AftMappedToPoseOffsetNode(Node):
    def __init__(self):
        super().__init__('aft_mapped_to_pose_offset')
        self.publisher_ = self.create_publisher(PoseStamped, '/LIVO2/pose_offset', 10)
        self.subscription_ = self.create_subscription(
            Odometry,
            '/aft_mapped_in_map',
            self.odometry_callback,
            10,
        )
        self.get_logger().info('Started /aft_mapped_in_map -> /LIVO2/pose_offset relay')

    def odometry_callback(self, msg: Odometry) -> None:
        pose_msg = PoseStamped()
        pose_msg.header = msg.header
        pose_msg.pose = msg.pose.pose
        self.publisher_.publish(pose_msg)


def main(args=None):
    rclpy.init(args=args)
    node = AftMappedToPoseOffsetNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
