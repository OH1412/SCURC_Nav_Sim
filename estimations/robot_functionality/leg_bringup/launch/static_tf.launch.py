import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch.actions import ExecuteProcess
from launch_ros.actions import Node


def generate_launch_description():
    bringup_dir = get_package_share_directory('leg_bringup')
    install_params = os.path.join(bringup_dir, 'params', 'static_tf_params.yaml')
    source_params = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'params', 'static_tf_params.yaml'))
    # Prefer the source params file if present (easier iteration during development)
    default_params = source_params if os.path.exists(source_params) else install_params

    tf_params = LaunchConfiguration('tf_params', default=default_params)

    return LaunchDescription([
        DeclareLaunchArgument('tf_params', default_value=default_params,
                       description='YAML params file'),

        # Launch the broadcaster as a ROS node so parameters are injected via the ROS2 parameter system
        Node(
            package='leg_bringup',
            executable='static_tf_broadcaster',
            output='screen',
            parameters=[tf_params],
        )
    ])
