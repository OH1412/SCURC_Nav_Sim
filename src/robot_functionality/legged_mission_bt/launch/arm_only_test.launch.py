#!/usr/bin/env python3
# 纯机械臂 BT 测试：仅启动串口 + mission_bt_node（不需要 Nav2）
#
# Usage:
#   ros2 launch legged_mission_bt arm_only_test.launch.py
#   ros2 launch legged_mission_bt arm_only_test.launch.py port:=/dev/ttyUSB0
#   ros2 launch legged_mission_bt arm_only_test.launch.py \
#     bt_xml_file:=/path/to/your_arm_mission.xml

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, TimerAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('legged_mission_bt')
    default_bt = os.path.join(pkg_share, 'behavior_trees', 'arm_only_demo.xml')
    arm_only_params = os.path.join(pkg_share, 'config', 'arm_only_params.yaml')

    port = LaunchConfiguration('port')
    bt_xml_file = LaunchConfiguration('bt_xml_file')
    mission_start_delay = LaunchConfiguration('mission_start_delay')

    serial_config = os.path.join(
        get_package_share_directory('serial_driver'),
        'config',
        'serial_config.yaml',
    )

    serial_node = Node(
        package='serial_driver',
        executable='serial_cmd_sender',
        name='serial_cmd_sender',
        output='screen',
        parameters=[serial_config, {'port': port}],
    )

    mission_bt_node = Node(
        package='legged_mission_bt',
        executable='mission_bt_node',
        name='mission_bt_node',
        output='screen',
        parameters=[
            arm_only_params,
            {'bt_xml_file': bt_xml_file},
        ],
    )

    delayed_mission_bt = TimerAction(
        period=mission_start_delay,
        actions=[mission_bt_node],
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'port', default_value='/dev/arm_port',
            description='Serial port for arm (e.g. /dev/arm_port, /dev/ttyUSB0)'),
        DeclareLaunchArgument(
            'bt_xml_file', default_value=default_bt,
            description='Arm-only behavior tree XML (no Nav2PoseNode required)'),
        DeclareLaunchArgument(
            'mission_start_delay', default_value='3.0',
            description='Seconds to wait after serial starts before running BT'),
        serial_node,
        delayed_mission_bt,
    ])
