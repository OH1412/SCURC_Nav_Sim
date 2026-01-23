#!/usr/bin/env python3

import os
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    """Launch the serial twist bridge node."""

    # Declare launch arguments
    serial_device_arg = DeclareLaunchArgument(
        'serial_device',
        default_value='/dev/ttyUSB0',
        description='Serial device path (e.g., /dev/ttyUSB0, /dev/ttyACM0)'
    )

    baud_rate_arg = DeclareLaunchArgument(
        'baud_rate',
        default_value='115200',
        description='Serial communication baud rate'
    )

    twist_topic_arg = DeclareLaunchArgument(
        'twist_topic',
        default_value='/cmd_vel',
        description='ROS topic to subscribe for Twist messages'
    )

    # Create the node
    serial_bridge_node = Node(
        package='serial_twist_bridge',
        executable='serial_bridge_node',
        name='serial_bridge',
        output='screen',
        parameters=[{
            'serial_device': LaunchConfiguration('serial_device'),
            'baud_rate': LaunchConfiguration('baud_rate'),
            'twist_topic': LaunchConfiguration('twist_topic'),
        }]
    )

    # Return the launch description
    return LaunchDescription([
        serial_device_arg,
        baud_rate_arg,
        twist_topic_arg,
        serial_bridge_node
    ])
