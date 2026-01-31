# kfs_detection.launch.py
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='kfs_detection_nav',
            executable='kfs_detection_node',
            name='kfs_manager',
            output='screen'
        )
    ])