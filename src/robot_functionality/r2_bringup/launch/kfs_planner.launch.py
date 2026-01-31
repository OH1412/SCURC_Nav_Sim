"""
Launch file to start the KFS planner node.

This launches the installed python script `kfs_planner_node.py` from the
`r2_bringup` package as a ROS2 node so it is managed by the launch system.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    bringup_dir = get_package_share_directory('r2_bringup')
    return LaunchDescription([
        Node(
            package='r2_bringup',
            executable='kfs_planner_node.py',
            name='kfs_planner',
            output='screen',
            emulate_tty=True,
        )
    ])
