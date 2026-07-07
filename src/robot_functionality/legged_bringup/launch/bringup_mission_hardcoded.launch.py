#!/usr/bin/env python3
# ============================================================================
# 硬编码任务 bringup — 基于 bringup_in_real，替换逐点导航为 Mission BT
#
# 与 bringup_in_real 的区别:
#   去掉 waypoint_sender (纯导航)
#   加入 mission_bt_node (fly_step: Nav2PoseNode + ArmPickNode/ArmPlaceNode)
#   加入 arm_pose_broadcaster (map_target → base_link 动态变换)
#   加入 arm_control_server (可选，串口直发模式不需要)
#
# 对应 BT:  legged_mission_bt/behavior_trees/mission_hardcoded.xml
# 对应 YAML: legged_mission_bt/config/mission_hardcoded.yaml
# ============================================================================

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
    enable_arm_pose_broadcaster = LaunchConfiguration('enable_arm_pose_broadcaster')
    enable_arm_control = LaunchConfiguration('enable_arm_control')
    arm_control_delay = LaunchConfiguration('arm_control_delay')
    bt_xml_file = LaunchConfiguration('bt_xml_file')
    waypoints_file = LaunchConfiguration('waypoints_file')
    arm_points_file = LaunchConfiguration('arm_points_file')
    udp_ip = LaunchConfiguration('udp_ip')
    udp_port = LaunchConfiguration('udp_port')
    udp_mode = LaunchConfiguration('udp_mode')
    udp_cmd_vel_topic = LaunchConfiguration('udp_cmd_vel_topic')
    udp_use_twist_stamped = LaunchConfiguration('udp_use_twist_stamped')
    udp_estop_topic = LaunchConfiguration('udp_estop_topic')

    # ---- 资源路径 ----
    legged_share = get_package_share_directory('legged_bringup')
    mission_bt_share = get_package_share_directory('legged_mission_bt')
    nav2_params_file = os.path.join(legged_share, 'params', 'nav2_params.yaml')
    mission_bt_params = os.path.join(mission_bt_share, 'config', 'mission_bt_params.yaml')

    default_bt_xml = os.path.join(
        mission_bt_share, 'behavior_trees', 'mission_hardcoded.xml')
    default_waypoints_file = os.path.join(
        mission_bt_share, 'config', 'mission_hardcoded.yaml')
    default_arm_points = os.path.join(legged_share, 'params', 'arm_points.yaml')

    # ---- 声明参数 ----
    declare_use_sim_time = DeclareLaunchArgument(
        'use_sim_time', default_value='false')
    declare_start_delay = DeclareLaunchArgument(
        'start_delay', default_value='5.0')
    declare_enable_udp_forwarding = DeclareLaunchArgument(
        'enable_udp_forwarding', default_value='true')
    declare_enable_serial_driver = DeclareLaunchArgument(
        'enable_serial_driver', default_value='true')
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
        description='Start standalone mission_bt_node (Nav+Arm fly_step)')
    declare_mission_bt_delay = DeclareLaunchArgument(
        'mission_bt_delay', default_value='15.0',
        description='Delay after bringup before starting mission BT (Nav2 lifecycle needs ~30s+)')
    declare_enable_arm_pose_broadcaster = DeclareLaunchArgument(
        'enable_arm_pose_broadcaster', default_value='true',
        description='Start arm_pose_broadcaster (map_target → base_link)')
    declare_enable_arm_control = DeclareLaunchArgument(
        'enable_arm_control', default_value='false',
        description='ArmControl Action Server (不需要串口直发模式)')
    declare_arm_control_delay = DeclareLaunchArgument(
        'arm_control_delay', default_value='12.0')
    declare_bt_xml_file = DeclareLaunchArgument(
        'bt_xml_file', default_value=default_bt_xml,
        description='Mission BT XML (Nav+Arm sequence)')
    declare_waypoints_file = DeclareLaunchArgument(
        'waypoints_file', default_value=default_waypoints_file,
        description='Nav waypoints YAML (seed to registry)')
    declare_arm_points_file = DeclareLaunchArgument(
        'arm_points_file', default_value=default_arm_points,
        description='Arm map_target points (pick 1~8, place 9~12)')
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

    # ---- 1) Livox MID360 ----
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

    # ---- 2) Serial driver (机械臂串口) ----
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

    # ---- 3) UDP bridge (cmd_vel → deploy_cpp) ----
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

    # ---- 4) bringup_all_in_one (relocalization + navigation) ----
    bringup_all_in_one_path = os.path.join(
        legged_share, 'launch', 'bringup_all_in_one.launch.py')
    start_bringup_all = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(bringup_all_in_one_path),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'use_pointcloud_to_scan': 'false',
            'enable_terrain_analysis': enable_terrain_analysis,
        }.items(),
    )
    delayed_bringup = TimerAction(period=start_delay, actions=[start_bringup_all])

    # ---- 5) aft → pose_offset 转发 ----
    aft_to_pose_offset_node = Node(
        package='legged_bringup',
        executable='aft_to_pose_offset_node.py',
        name='aft_to_pose_offset_node',
        output='screen',
    )
    delayed_aft_pose_offset = TimerAction(
        period=start_delay, actions=[aft_to_pose_offset_node])

    # ---- 6) Stand-up ----
    stand_up_sender_node = Node(
        package='legged_bringup',
        executable='stand_up_sender.py',
        name='stand_up_sender',
        output='screen',
        condition=IfCondition(enable_stand_up),
        parameters=[nav2_params_file, {
            'udp_ip': udp_ip, 'udp_port': udp_port, 'reloc_delay': reloc_delay,
        }],
    )
    delayed_stand_up_sender = TimerAction(
        period=stand_up_delay,
        actions=[stand_up_sender_node],
        condition=IfCondition(enable_stand_up),
    )

    # ---- 7) Arm pose broadcaster (map_target → base_link) ----
    arm_pose_broadcaster_node = Node(
        package='legged_bringup',
        executable='arm_pose_broadcaster.py',
        name='arm_pose_broadcaster',
        output='screen',
        condition=IfCondition(enable_arm_pose_broadcaster),
        parameters=[{'arm_points_file': arm_points_file}],
    )

    # ---- 8) Mission BT node (fly_step: Nav + Arm) ----
    mission_bt_node = Node(
        package='legged_mission_bt',
        executable='mission_bt_node',
        name='mission_bt_node',
        output='screen',
        condition=IfCondition(enable_mission_bt),
        parameters=[mission_bt_params, {
            'bt_xml_file': bt_xml_file,
            'waypoints_file': waypoints_file,
            'use_sim_time': use_sim_time,
        }],
    )
    delayed_mission_bt = TimerAction(
        period=mission_bt_delay,
        actions=[mission_bt_node],
        condition=IfCondition(enable_mission_bt),
    )

    # ---- 9) Arm Control Action Server (可选) ----
    arm_control_server_node = Node(
        package='legged_bringup',
        executable='arm_control_server.py',
        name='arm_control_server',
        output='screen',
        condition=IfCondition(enable_arm_control),
        parameters=[{
            'arm_timeout': 30.0,
            'enable_serial_publish': True,
            'arm_command_topic': '/arm_command',
        }],
    )
    delayed_arm_control = TimerAction(
        period=arm_control_delay,
        actions=[arm_control_server_node],
        condition=IfCondition(enable_arm_control),
    )

    # ================================================================
    # LaunchDescription
    # ================================================================
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
    ld.add_action(declare_enable_arm_pose_broadcaster)
    ld.add_action(declare_enable_arm_control)
    ld.add_action(declare_arm_control_delay)
    ld.add_action(declare_bt_xml_file)
    ld.add_action(declare_waypoints_file)
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
    ld.add_action(arm_pose_broadcaster_node)
    ld.add_action(delayed_mission_bt)
    ld.add_action(delayed_arm_control)

    return ld
