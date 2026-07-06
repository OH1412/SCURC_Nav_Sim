import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('legged_mission_bt')
    params_file = os.path.join(pkg_share, 'config', 'mission_quintuple_loader_params.yaml')

    return LaunchDescription([
        Node(
            package='legged_mission_bt',
            executable='mission_quintuple_loader.py',
            name='mission_quintuple_loader',
            output='screen',
            parameters=[params_file],
        ),
    ])
