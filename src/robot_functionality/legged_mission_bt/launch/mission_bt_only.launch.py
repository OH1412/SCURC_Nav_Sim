import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('legged_mission_bt')
    default_bt = os.path.join(pkg_share, 'behavior_trees', 'mission_plan_demo.xml')
    params_file = os.path.join(pkg_share, 'config', 'mission_bt_params.yaml')

    bt_xml_file = LaunchConfiguration('bt_xml_file')
    waypoints_file = LaunchConfiguration('waypoints_file')

    return LaunchDescription([
        DeclareLaunchArgument(
            'bt_xml_file', default_value=default_bt,
            description='Mission behavior tree XML path'),
        DeclareLaunchArgument(
            'waypoints_file', default_value='',
            description='Optional YAML seed; leave empty for topic injection'),
        Node(
            package='legged_mission_bt',
            executable='mission_bt_node',
            name='mission_bt_node',
            output='screen',
            parameters=[params_file, {
                'bt_xml_file': bt_xml_file,
                'waypoints_file': waypoints_file,
            }],
        ),
    ])
