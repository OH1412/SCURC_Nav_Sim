#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

class CmdVelPublisher(Node):
    def __init__(self):
        super().__init__('cmd_vel_publisher')
        self.publisher_ = self.create_publisher(Twist, '/cmd_vel', 10)
        timer_period = 0.5  # 0.5秒发一次
        self.timer = self.create_timer(timer_period, self.timer_callback)
        self.get_logger().info('CmdVelPublisher started, publishing every 0.5 seconds.')

    def timer_callback(self):
        msg = Twist()
        # 模拟发送线速度和角速度
        msg.linear.x = 0.5   # 0.5 m/s
        msg.angular.z = 0.1  # 0.1 rad/s
        self.publisher_.publish(msg)
        self.get_logger().info(f'Publishing: linear.x={msg.linear.x}, angular.z={msg.angular.z}')

def main(args=None):
    rclpy.init(args=args)
    node = CmdVelPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()
                 
if __name__ == '__main__':
    main()              
