#!/usr/bin/env python3
# Copyright (c) 2026
# Real-robot bringup + standalone mission BT (fly_step architecture).
#
# Nav2PoseNode / ArmPickNode / ArmPlaceNode are ticked by mission_bt_node,
# NOT embedded in bt_navigator default BT.
#
# Usage:
#   ros2 launch legged_bringup bringup_arm_mission.launch.py
#   ros2 launch legged_bringup bringup_arm_mission.launch.py \
#     bt_xml_file:=$(ros2 pkg prefix legged_mission_bt)/share/legged_mission_bt/behavior_trees/mission_template.xml

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, IncludeLaunchDescription,
                            TimerAction, SetEnvironmentVariable)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    start_delay = LaunchConfiguration('start_delay')
    enable_udp_forwarding = LaunchConfiguration('enable_udp_forwarding')
    enable_serial_driver = LaunchConfiguration('enable_serial_driver')
    enable_terrain_analysis = LaunchConfiguration('enable_terrain_analysis')
    enable_stand_up = LaunchConfiguration('enable_stand_up')
    stand_up_delay = LaunchConfiguration('stand_up_delay')
    reloc_delay = LaunchConfiguration('reloc_delay')
    enable_mission_bt = LaunchConfiguration('enable_mission_bt')
    mission_bt_delay = LaunchConfiguration('mission_bt_delay')
    bt_xml_file = LaunchConfiguration('bt_xml_file')
    waypoints_file = LaunchConfiguration('waypoints_file')
    enable_arm_pose_broadcaster = LaunchConfiguration('enable_arm_pose_broadcaster')
    arm_points_file = LaunchConfiguration('arm_points_file')
    udp_ip = LaunchConfiguration('udp_ip')
    udp_port = LaunchConfiguration('udp_port')
    udp_mode = LaunchConfiguration('udp_mode')
    udp_cmd_vel_topic = LaunchConfiguration('udp_cmd_vel_topic')
    udp_use_twist_stamped = LaunchConfiguration('udp_use_twist_stamped')
    udp_estop_topic = LaunchConfiguration('udp_estop_topic')

    legged_share = get_package_share_directory('legged_bringup')
    mission_bt_share = get_package_share_directory('legged_mission_bt')
    default_bt_xml = os.path.join(mission_bt_share, 'behavior_trees', 'mission_plan_demo.xml')
    nav2_params_file = os.path.join(legged_share, 'params', 'nav2_params.yaml')
    mission_bt_params = os.path.join(mission_bt_share, 'config', 'mission_bt_params.yaml')
    default_arm_points = os.path.join(legged_share, 'params', 'arm_points.yaml')

    declare_use_sim_time = DeclareLaunchArgument(
        'use_sim_time', default_value='false')
    declare_start_delay = DeclareLaunchArgument(
        'start_delay', default_value='5.0',
        description='Seconds after Livox start before bringup_all_in_one')
    declare_enable_udp_forwarding = DeclareLaunchArgument(
        'enable_udp_forwarding', default_value='true')
    declare_enable_serial_driver = DeclareLaunchArgument(
        'enable_serial_driver', default_value='true',
        description='Serial driver for arm (/arm_command, /arm_status)')
    declare_enable_terrain_analysis = DeclareLaunchArgument(
        'enable_terrain_analysis', default_value='false')
    declare_enable_stand_up = DeclareLaunchArgument(
        'enable_stand_up', default_value='true')
    declare_stand_up_delay = DeclareLaunchArgument(
        'stand_up_delay', default_value='3.0')
    declare_reloc_delay = DeclareLaunchArgument(
        'reloc_delay', default_value='0.0')
    declare_enable_mission_bt = DeclareLaunchArgument(
        'enable_mission_bt', default_value='true',
        description='Start standalone mission_bt_node (fly_step architecture)')
    declare_mission_bt_delay = DeclareLaunchArgument(
        'mission_bt_delay', default_value='30.0',
        description='Seconds after Livox start before mission BT (after Nav2 ready)')
    declare_bt_xml_file = DeclareLaunchArgument(
        'bt_xml_file', default_value=default_bt_xml,
        description='Mission behavior tree XML (Sequence of Nav/Pick/Place nodes)')
    declare_waypoints_file = DeclareLaunchArgument(
        'waypoints_file', default_value='',
        description='Optional YAML seed for waypoints; leave empty to inject via topics')
    declare_enable_arm_pose_broadcaster = DeclareLaunchArgument(
        'enable_arm_pose_broadcaster', default_value='true',
        description='Start arm_pose_broadcaster (aft offset → arm_waypoint)')
    declare_arm_points_file = DeclareLaunchArgument(
        'arm_points_file', default_value=default_arm_points,
        description='Sixteen arm points: pick 0~7, place 8~15 (arm_points.yaml)')
    declare_udp_ip = DeclareLaunchArgument('udp_ip', default_value='127.0.0.1')
    declare_udp_port = DeclareLaunchArgument('udp_port', default_value='9870')
    declare_udp_mode = DeclareLaunchArgument('udp_mode', default_value='2')
    declare_udp_cmd_vel_topic = DeclareLaunchArgument(
        'udp_cmd_vel_topic', default_value='/cmd_vel')
    declare_udp_use_twist_stamped = DeclareLaunchArgument(
        'udp_use_twist_stamped', default_value='false')
    declare_udp_estop_topic = DeclareLaunchArgument(
        'udp_estop_topic', default_value='')

    stdout_linebuf_envvar = SetEnvironmentVariable(
        'RCUTILS_LOGGING_BUFFERED_STREAM', '1')

    # Livox driver
    livox_launch_path = None
    try:
        livox_share = get_package_share_directory('livox_ros_driver2')
    except Exception:
        livox_share = None

    candidates = []
    if livox_share:
        candidates.append(os.path.join(livox_share, 'launch_ROS2', 'msg_MID360_launch.py'))
        candidates.append(os.path.join(livox_share, 'launch', 'msg_MID360_launch.py'))

    for p in candidates:
        if os.path.exists(p):
            livox_launch_path = p
            break

    if livox_launch_path is None:
        raise FileNotFoundError('Cannot find Livox MID360 launch file.')

    start_livox = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(livox_launch_path),
        launch_arguments={}.items(),
    )

    # Serial driver (arm)
    start_serial_driver = None
    try:
        serial_driver_share = get_package_share_directory('serial_driver')
        start_serial_driver = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(serial_driver_share, 'launch', 'serial_driver.launch.py')
            ),
            condition=IfCondition(enable_serial_driver),
        )
    except Exception:
        start_serial_driver = None

    cmd_vel_udp_bridge = Node(
        package='cmd_vel_udp_bridge',
        executable='cmd_vel_udp_bridge_node',
        name='cmd_vel_udp_bridge',
        output='screen',
        condition=IfCondition(enable_udp_forwarding),
        parameters=[nav2_params_file, {
            'udp_ip': udp_ip,
            'udp_port': udp_port,
            'mode': udp_mode,
            'cmd_vel_topic': udp_cmd_vel_topic,
            'use_twist_stamped': udp_use_twist_stamped,
            'estop_topic': udp_estop_topic,
        }],
    )

    bringup_all_in_one_path = os.path.join(legged_share, 'launch', 'bringup_all_in_one.launch.py')
    start_bringup_all = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(bringup_all_in_one_path),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'use_pointcloud_to_scan': 'false',
            'enable_terrain_analysis': enable_terrain_analysis,
        }.items(),
    )

    delayed_bringup = TimerAction(period=start_delay, actions=[start_bringup_all])

    aft_to_pose_offset_node = Node(
        package='legged_bringup',
        executable='aft_to_pose_offset_node.py',
        name='aft_to_pose_offset_node',
        output='screen',
    )
    delayed_aft_pose_offset = TimerAction(period=start_delay, actions=[aft_to_pose_offset_node])

    stand_up_sender_node = Node(
        package='legged_bringup',
        executable='stand_up_sender.py',
        name='stand_up_sender',
        output='screen',
        condition=IfCondition(enable_stand_up),
        parameters=[nav2_params_file, {
            'udp_ip': udp_ip,
            'udp_port': udp_port,
            'reloc_delay': reloc_delay,
        }],
    )
    delayed_stand_up_sender = TimerAction(
        period=stand_up_delay,
        actions=[stand_up_sender_node],
        condition=IfCondition(enable_stand_up),
    )

    # Standalone mission BT (fly_step architecture)
    mission_bt_node = Node(
        package='legged_mission_bt',
        executable='mission_bt_node',
        name='mission_bt_node',
        output='screen',
        condition=IfCondition(enable_mission_bt),
        parameters=[
            mission_bt_params,
            {
                'bt_xml_file': bt_xml_file,
                'waypoints_file': waypoints_file,
                'use_sim_time': use_sim_time,
            },
        ],
    )
    delayed_mission_bt = TimerAction(
        period=mission_bt_delay,
        actions=[mission_bt_node],
        condition=IfCondition(enable_mission_bt),
    )

    arm_pose_broadcaster_node = Node(
        package='legged_bringup',
        executable='arm_pose_broadcaster.py',
        name='arm_pose_broadcaster',
        output='screen',
        condition=IfCondition(enable_arm_pose_broadcaster),
        parameters=[{
            'arm_points_file': arm_points_file,
        }],
    )

    ld = LaunchDescription()
    ld.add_action(stdout_linebuf_envvar)
    ld.add_action(declare_use_sim_time)
    ld.add_action(declare_start_delay)
    ld.add_action(declare_enable_udp_forwarding)
    ld.add_action(declare_enable_serial_driver)
    ld.add_action(declare_enable_terrain_analysis)
    ld.add_action(declare_enable_stand_up)
    ld.add_action(declare_stand_up_delay)
    ld.add_action(declare_reloc_delay)
    ld.add_action(declare_enable_mission_bt)
    ld.add_action(declare_mission_bt_delay)
    ld.add_action(declare_bt_xml_file)
    ld.add_action(declare_waypoints_file)
    ld.add_action(declare_enable_arm_pose_broadcaster)
    ld.add_action(declare_arm_points_file)
    ld.add_action(declare_udp_ip)
    ld.add_action(declare_udp_port)
    ld.add_action(declare_udp_mode)
    ld.add_action(declare_udp_cmd_vel_topic)
    ld.add_action(declare_udp_use_twist_stamped)
    ld.add_action(declare_udp_estop_topic)

    ld.add_action(start_livox)
    if start_serial_driver is not None:
        ld.add_action(start_serial_driver)
    ld.add_action(cmd_vel_udp_bridge)
    ld.add_action(delayed_bringup)
    ld.add_action(delayed_aft_pose_offset)
    ld.add_action(delayed_stand_up_sender)
    ld.add_action(delayed_mission_bt)
    ld.add_action(arm_pose_broadcaster_node)

    return ld
