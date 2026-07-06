#!/usr/bin/env python3
# Copyright (c) 2026
# 真机 bringup + 手动机械臂联调（无导航航点，Enter 确认到位 + 输入 arm_point_id）
#
# 推荐一键启动（4 个 gnome 终端，含 FAST/HIM/SCURC 环境）:
#   ~/start_arm_manual_test.sh
#
# 或手动（需先 source FAST + HIM + SCURC 工作空间）:
#   ros2 launch legged_bringup bringup_arm_manual_test.launch.py
#
# 操作流程（在 arm_keyboard 独立终端，避免 bringup 日志刷屏）:
#   1. 等待 BT 提示「步骤 N: 抓取/放置」
#   2. 遥控机器人到位 → 按 Enter
#   3. 输入 arm_point_id（抓取 0~7 / 放置 8~15）→ 回车
#   4. 机械臂执行完成后，重复下一步（共 6 步：抓-放-抓-放-抓-放）

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
    mission_bt_delay = LaunchConfiguration('mission_bt_delay')
    bt_xml_file = LaunchConfiguration('bt_xml_file')
    arm_points_file = LaunchConfiguration('arm_points_file')
    enable_manual_keyboard = LaunchConfiguration('enable_manual_keyboard')
    enable_joy = LaunchConfiguration('enable_joy')
    enable_deploy = LaunchConfiguration('enable_deploy')
    joy_start_delay = LaunchConfiguration('joy_start_delay')
    deploy_start_delay = LaunchConfiguration('deploy_start_delay')
    robot_config_file = LaunchConfiguration('robot_config_file')
    libtorch_lib_path = LaunchConfiguration('libtorch_lib_path')
    udp_ip = LaunchConfiguration('udp_ip')
    udp_port = LaunchConfiguration('udp_port')
    udp_mode = LaunchConfiguration('udp_mode')
    udp_cmd_vel_topic = LaunchConfiguration('udp_cmd_vel_topic')
    udp_use_twist_stamped = LaunchConfiguration('udp_use_twist_stamped')
    udp_estop_topic = LaunchConfiguration('udp_estop_topic')

    legged_share = get_package_share_directory('legged_bringup')
    mission_bt_share = get_package_share_directory('legged_mission_bt')
    default_bt_xml = os.path.join(mission_bt_share, 'behavior_trees', 'arm_manual_test.xml')
    nav2_params_file = os.path.join(legged_share, 'params', 'nav2_params.yaml')
    mission_bt_params = os.path.join(mission_bt_share, 'config', 'arm_manual_test_params.yaml')
    default_arm_points = os.path.join(legged_share, 'params', 'arm_points.yaml')
    default_robot_config = '/home/dog12/HIMLocoWithDeploy/deploy_cpp/config/robots/mybot_arm.yaml'
    default_libtorch = '/home/dog12/libtorch/lib'

    declare_use_sim_time = DeclareLaunchArgument('use_sim_time', default_value='false')
    declare_start_delay = DeclareLaunchArgument(
        'start_delay', default_value='5.0',
        description='Livox 启动后延迟再启动 bringup_all_in_one')
    declare_enable_udp_forwarding = DeclareLaunchArgument(
        'enable_udp_forwarding', default_value='true')
    declare_enable_serial_driver = DeclareLaunchArgument(
        'enable_serial_driver', default_value='true',
        description='机械臂串口 (/arm_command, /arm_status)')
    declare_enable_terrain_analysis = DeclareLaunchArgument(
        'enable_terrain_analysis', default_value='false')
    declare_enable_stand_up = DeclareLaunchArgument(
        'enable_stand_up', default_value='true')
    declare_stand_up_delay = DeclareLaunchArgument(
        'stand_up_delay', default_value='3.0')
    declare_reloc_delay = DeclareLaunchArgument(
        'reloc_delay', default_value='0.0')
    declare_mission_bt_delay = DeclareLaunchArgument(
        'mission_bt_delay', default_value='45.0',
        description='Livox 启动后延迟再启动手动 BT（等待定位/串口就绪）')
    declare_bt_xml_file = DeclareLaunchArgument(
        'bt_xml_file', default_value=default_bt_xml,
        description='手动机械臂 BT（默认 3 抓 + 3 放）')
    declare_arm_points_file = DeclareLaunchArgument(
        'arm_points_file', default_value=default_arm_points)
    declare_enable_manual_keyboard = DeclareLaunchArgument(
        'enable_manual_keyboard', default_value='false',
        description='在 launch 内启动 manual_arm_keyboard（推荐用独立终端，默认 false）')
    declare_enable_joy = DeclareLaunchArgument(
        'enable_joy', default_value='false',
        description='在本 launch 内启动 joy_node（start_arm_manual_test.sh 会在独立终端启动）')
    declare_enable_deploy = DeclareLaunchArgument(
        'enable_deploy', default_value='false',
        description='在本 launch 内启动 deploy_node（start_arm_manual_test.sh 会在独立终端启动）')
    declare_joy_start_delay = DeclareLaunchArgument(
        'joy_start_delay', default_value='5.0')
    declare_deploy_start_delay = DeclareLaunchArgument(
        'deploy_start_delay', default_value='15.0')
    declare_robot_config_file = DeclareLaunchArgument(
        'robot_config_file', default_value=default_robot_config)
    declare_libtorch_lib_path = DeclareLaunchArgument(
        'libtorch_lib_path', default_value=default_libtorch)
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

    arm_pose_broadcaster_node = Node(
        package='legged_bringup',
        executable='arm_pose_broadcaster.py',
        name='arm_pose_broadcaster',
        output='screen',
        parameters=[{'arm_points_file': arm_points_file}],
    )

    manual_arm_keyboard_node = Node(
        package='legged_mission_bt',
        executable='manual_arm_keyboard.py',
        name='manual_arm_keyboard',
        output='screen',
        emulate_tty=True,
        condition=IfCondition(enable_manual_keyboard),
    )

    mission_bt_node = Node(
        package='legged_mission_bt',
        executable='mission_bt_node',
        name='mission_bt_node',
        output='screen',
        parameters=[
            mission_bt_params,
            {
                'bt_xml_file': bt_xml_file,
                'use_sim_time': use_sim_time,
            },
        ],
    )
    delayed_mission_bt = TimerAction(period=mission_bt_delay, actions=[mission_bt_node])

    joy_node = Node(
        package='joy',
        executable='joy_node',
        name='joy_node',
        output='screen',
        condition=IfCondition(enable_joy),
    )
    delayed_joy = TimerAction(
        period=joy_start_delay,
        actions=[joy_node],
        condition=IfCondition(enable_joy),
    )

    deploy_node = Node(
        package='deploy_cpp',
        executable='deploy_node',
        name='deploy_node',
        output='screen',
        condition=IfCondition(enable_deploy),
        parameters=[{'robot_config_file': robot_config_file}],
        additional_env={
            'LD_LIBRARY_PATH': f'{default_libtorch}:{os.environ.get("LD_LIBRARY_PATH", "")}',
        },
    )
    delayed_deploy = TimerAction(
        period=deploy_start_delay,
        actions=[deploy_node],
        condition=IfCondition(enable_deploy),
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
    ld.add_action(declare_mission_bt_delay)
    ld.add_action(declare_bt_xml_file)
    ld.add_action(declare_arm_points_file)
    ld.add_action(declare_enable_manual_keyboard)
    ld.add_action(declare_enable_joy)
    ld.add_action(declare_enable_deploy)
    ld.add_action(declare_joy_start_delay)
    ld.add_action(declare_deploy_start_delay)
    ld.add_action(declare_robot_config_file)
    ld.add_action(declare_libtorch_lib_path)
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
    ld.add_action(manual_arm_keyboard_node)
    ld.add_action(delayed_mission_bt)
    ld.add_action(delayed_joy)
    ld.add_action(delayed_deploy)

    return ld
