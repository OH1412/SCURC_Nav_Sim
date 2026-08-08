from launch import LaunchDescription
from launch_ros.actions import Node
import os
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    config_path = os.path.join(
        get_package_share_directory('serial_driver'),
        'config',
        'serial_config.yaml'
    )

    return LaunchDescription([
        Node(
            package='serial_driver',
            executable='serial_cmd_sender',
            name='serial_cmd_sender',
            parameters=[config_path]
        )
    ])
