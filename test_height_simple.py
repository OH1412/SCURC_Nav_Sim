#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
import time

class SimpleHeightController(Node):
    def __init__(self):
        super().__init__('simple_height_controller')
        
        # Subscribe to state estimation
        self.height_sub = self.create_subscription(
            Odometry,
            '/state_estimation',
            self.height_callback,
            10
        )
        
        # Publisher for cmd_vel
        self.vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        
        # Parameters
        self.target_height = 0.3
        self.height_tolerance = 0.02
        self.lift_speed = 0.05
        self.height_offset = 0.0035
        self.current_height = 0.0
        self.first_height_received = False
        
        # Control timer
        self.control_timer = self.create_timer(0.1, self.control_loop)
        
        self.get_logger().info(f"简单高度控制器启动，目标高度: {self.target_height}m")
    
    def height_callback(self, msg):
        raw_height = msg.pose.pose.position.z
        self.current_height = raw_height + self.height_offset
        
        if not self.first_height_received:
            self.first_height_received = True
            self.get_logger().info(f"首次接收高度: {self.current_height:.4f}m")
    
    def control_loop(self):
        if not self.first_height_received:
            return
        
        diff = self.target_height - self.current_height
        
        # Check if we've reached the target
        if abs(diff) <= self.height_tolerance:
            # Stop movement
            cmd = Twist()
            cmd.linear.z = 0.0
            self.vel_pub.publish(cmd)
            
            self.get_logger().info(f"✅ 达到目标高度！当前: {self.current_height:.4f}m, 目标: {self.target_height:.4f}m")
            return
        
        # Calculate control effort
        control_effort = min(abs(diff) * 2.0, self.lift_speed)  # Proportional control
        
        # Create velocity command
        cmd = Twist()
        cmd.linear.x = 0.0
        cmd.linear.y = 0.0
        cmd.linear.z = control_effort if diff > 0 else -control_effort
        cmd.angular.x = 0.0
        cmd.angular.y = 0.0
        cmd.angular.z = 0.0
        
        self.vel_pub.publish(cmd)
        
        # Log progress every 2 seconds
        if int(time.time() * 5) % 10 == 0:  # Every 2 seconds
            self.get_logger().info(f"高度控制中: 当前={self.current_height:.4f}m, 目标={self.target_height:.4f}m, 差值={diff:.4f}m, 速度={cmd.linear.z:.4f}m/s")

def main():
    rclpy.init()
    controller = SimpleHeightController()
    
    try:
        rclpy.spin(controller)
    except KeyboardInterrupt:
        # Stop the robot
        cmd = Twist()
        controller.vel_pub.publish(cmd)
        controller.get_logger().info("高度控制停止")
    finally:
        controller.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()