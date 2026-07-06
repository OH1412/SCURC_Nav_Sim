#!/usr/bin/env python3
# ============================================================================
# 硬编码任务 bringup
#
# 启动策略 (use_event_gating=true，默认):
#   · 无强依赖的组件全部 t=0 并行启动
#   · 仅 mission_bt_node 走强依赖门控:
#       - 若 enable_stand_up: 必须等 stand_up 完成 (/bringup/stand_up_done)
#       - 必须等 Nav2 ACTIVE + navigate_to_pose + /arm_status 发布者
#       - 可选: wait_for_bt_config:=true 时再等 /mission/bt_config_ready（默认 false，不等待）
#
# use_event_gating=false 时回退 TimerAction 固定延迟。
# ============================================================================

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    GroupAction,
    IncludeLaunchDescription,
    SetEnvironmentVariable,
    TimerAction,
)
from launch.conditions import AndCondition, IfCondition, Unless
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from launch_gates import on_process_exit_if, wait_for_ros_condition


def _wait_mission_ready(name: str, timeout, *, skip_stand_up: bool, wait_bt_config: bool):
    extra = [
        '--lifecycle-node', 'bt_navigator',
        '--action-name', 'navigate_to_pose',
        '--publisher-topic', '/arm_status',
    ]
    if skip_stand_up:
        extra.append('--skip-stand-up')
    if wait_bt_config:
        extra.extend(['--bt-config-ready-topic', '/mission/bt_config_ready'])
    return wait_for_ros_condition(name=name, timeout=timeout, extra_args=extra)


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    use_event_gating = LaunchConfiguration('use_event_gating')
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
    mission_ready_timeout = LaunchConfiguration('mission_ready_timeout')
    wait_for_bt_config = LaunchConfiguration('wait_for_bt_config')

    legged_share = get_package_share_directory('legged_bringup')
    mission_bt_share = get_package_share_directory('legged_mission_bt')
    nav2_params_file = os.path.join(legged_share, 'params', 'nav2_params.yaml')
    mission_bt_params = os.path.join(mission_bt_share, 'config', 'mission_bt_params.yaml')

    default_bt_xml = os.path.join(mission_bt_share, 'behavior_trees', 'mission_hardcoded.xml')
    default_waypoints_file = os.path.join(mission_bt_share, 'config', 'mission_hardcoded.yaml')
    default_arm_points = os.path.join(legged_share, 'params', 'arm_points.yaml')

    declare_use_sim_time = DeclareLaunchArgument('use_sim_time', default_value='false')
    declare_use_event_gating = DeclareLaunchArgument(
        'use_event_gating', default_value='true',
        description='Gate mission_bt_node on readiness signals (not fixed delays)')
    declare_start_delay = DeclareLaunchArgument('start_delay', default_value='5.0')
    declare_enable_udp_forwarding = DeclareLaunchArgument(
        'enable_udp_forwarding', default_value='true')
    declare_enable_serial_driver = DeclareLaunchArgument(
        'enable_serial_driver', default_value='true')
    declare_enable_terrain_analysis = DeclareLaunchArgument(
        'enable_terrain_analysis', default_value='false')
    declare_enable_stand_up = DeclareLaunchArgument('enable_stand_up', default_value='true')
    declare_stand_up_delay = DeclareLaunchArgument('stand_up_delay', default_value='3.0')
    declare_reloc_delay = DeclareLaunchArgument('reloc_delay', default_value='0.0')
    declare_enable_mission_bt = DeclareLaunchArgument('enable_mission_bt', default_value='true')
    declare_mission_bt_delay = DeclareLaunchArgument('mission_bt_delay', default_value='25.0')
    declare_enable_arm_pose_broadcaster = DeclareLaunchArgument(
        'enable_arm_pose_broadcaster', default_value='true')
    declare_enable_arm_control = DeclareLaunchArgument('enable_arm_control', default_value='false')
    declare_arm_control_delay = DeclareLaunchArgument('arm_control_delay', default_value='12.0')
    declare_bt_xml_file = DeclareLaunchArgument('bt_xml_file', default_value=default_bt_xml)
    declare_waypoints_file = DeclareLaunchArgument(
        'waypoints_file', default_value=default_waypoints_file)
    declare_arm_points_file = DeclareLaunchArgument(
        'arm_points_file', default_value=default_arm_points)
    declare_udp_ip = DeclareLaunchArgument('udp_ip', default_value='127.0.0.1')
    declare_udp_port = DeclareLaunchArgument('udp_port', default_value='9870')
    declare_udp_mode = DeclareLaunchArgument('udp_mode', default_value='2')
    declare_udp_cmd_vel_topic = DeclareLaunchArgument(
        'udp_cmd_vel_topic', default_value='/cmd_vel')
    declare_udp_use_twist_stamped = DeclareLaunchArgument(
        'udp_use_twist_stamped', default_value='false')
    declare_udp_estop_topic = DeclareLaunchArgument('udp_estop_topic', default_value='')
    declare_mission_ready_timeout = DeclareLaunchArgument(
        'mission_ready_timeout', default_value='180.0')
    declare_wait_for_bt_config = DeclareLaunchArgument(
        'wait_for_bt_config', default_value='false',
        description='If true, mission_bt_node also waits for /mission/bt_config_ready (quintuple→BT 转换完成). Default false.')

    stdout_linebuf_envvar = SetEnvironmentVariable('RCUTILS_LOGGING_BUFFERED_STREAM', '1')

    livox_launch_path = None
    try:
        livox_share = get_package_share_directory('livox_ros_driver2')
    except Exception:
        livox_share = None

    for rel in ('launch_ROS2/msg_MID360_launch.py', 'launch/msg_MID360_launch.py'):
        if livox_share:
            p = os.path.join(livox_share, *rel.split('/'))
            if os.path.exists(p):
                livox_launch_path = p
                break

    if livox_launch_path is None:
        raise FileNotFoundError('Cannot find Livox MID360 launch file.')

    start_livox = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(livox_launch_path),
        launch_arguments={}.items(),
    )

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

    aft_to_pose_offset_node = Node(
        package='legged_bringup',
        executable='aft_to_pose_offset_node.py',
        name='aft_to_pose_offset_node',
        output='screen',
    )

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

    arm_pose_broadcaster_node = Node(
        package='legged_bringup',
        executable='arm_pose_broadcaster.py',
        name='arm_pose_broadcaster',
        output='screen',
        condition=IfCondition(enable_arm_pose_broadcaster),
        parameters=[{'arm_points_file': arm_points_file}],
    )

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

    # mission_bt 强依赖门控（其余组件无门控，t=0 并行）
    wait_after_stand_up = _wait_mission_ready(
        'wait_mission_ready_after_stand_up',
        mission_ready_timeout,
        skip_stand_up=False,
        wait_bt_config=False,
    )
    wait_after_stand_up_bt = _wait_mission_ready(
        'wait_mission_ready_after_stand_up_bt',
        mission_ready_timeout,
        skip_stand_up=False,
        wait_bt_config=True,
    )
    wait_parallel_no_stand_up = _wait_mission_ready(
        'wait_mission_ready_parallel',
        mission_ready_timeout,
        skip_stand_up=True,
        wait_bt_config=False,
    )
    wait_parallel_no_stand_up_bt = _wait_mission_ready(
        'wait_mission_ready_parallel_bt',
        mission_ready_timeout,
        skip_stand_up=True,
        wait_bt_config=True,
    )

    delayed_bringup = TimerAction(period=start_delay, actions=[start_bringup_all])
    delayed_aft_pose_offset = TimerAction(period=start_delay, actions=[aft_to_pose_offset_node])
    delayed_stand_up_sender = TimerAction(
        period=stand_up_delay,
        actions=[stand_up_sender_node],
        condition=IfCondition(enable_stand_up),
    )
    delayed_mission_bt = TimerAction(
        period=mission_bt_delay,
        actions=[mission_bt_node],
        condition=IfCondition(enable_mission_bt),
    )
    delayed_arm_control = TimerAction(
        period=arm_control_delay,
        actions=[arm_control_server_node],
        condition=IfCondition(enable_arm_control),
    )

    event_gating = IfCondition(use_event_gating)
    legacy = Unless(use_event_gating)

    ld = LaunchDescription()

    for decl in (
        declare_use_sim_time,
        declare_use_event_gating,
        declare_start_delay,
        declare_enable_udp_forwarding,
        declare_enable_serial_driver,
        declare_enable_terrain_analysis,
        declare_enable_stand_up,
        declare_stand_up_delay,
        declare_reloc_delay,
        declare_enable_mission_bt,
        declare_mission_bt_delay,
        declare_enable_arm_pose_broadcaster,
        declare_enable_arm_control,
        declare_arm_control_delay,
        declare_bt_xml_file,
        declare_waypoints_file,
        declare_arm_points_file,
        declare_udp_ip,
        declare_udp_port,
        declare_udp_mode,
        declare_udp_cmd_vel_topic,
        declare_udp_use_twist_stamped,
        declare_udp_estop_topic,
        declare_mission_ready_timeout,
        declare_wait_for_bt_config,
    ):
        ld.add_action(decl)

    ld.add_action(stdout_linebuf_envvar)

    # ---- t=0 并行（无强依赖门控）----
    parallel_stack = GroupAction([
        start_livox,
        cmd_vel_udp_bridge,
        start_bringup_all,
        aft_to_pose_offset_node,
        stand_up_sender_node,
        arm_pose_broadcaster_node,
        arm_control_server_node,
    ], condition=event_gating)
    ld.add_action(parallel_stack)
    if start_serial_driver is not None:
        ld.add_action(GroupAction([start_serial_driver], condition=event_gating))

    # stand_up 关闭时：mission 就绪等待与上面并行启动
    ld.add_action(GroupAction([wait_parallel_no_stand_up], condition=AndCondition([
        event_gating, Unless(enable_stand_up), Unless(wait_for_bt_config),
    ])))
    ld.add_action(GroupAction([wait_parallel_no_stand_up_bt], condition=AndCondition([
        event_gating, Unless(enable_stand_up), IfCondition(wait_for_bt_config),
    ])))

    # stand_up 开启时：等 stand_up 进程退出后再等 Nav2/serial
    ld.add_action(on_process_exit_if(
        stand_up_sender_node,
        wait_after_stand_up,
        AndCondition([event_gating, IfCondition(enable_stand_up), Unless(wait_for_bt_config)]),
    ))
    ld.add_action(on_process_exit_if(
        stand_up_sender_node,
        wait_after_stand_up_bt,
        AndCondition([event_gating, IfCondition(enable_stand_up), IfCondition(wait_for_bt_config)]),
    ))

    # mission_bt 强依赖：就绪等待完成后再启动
    for wait_proc, extra_conds in (
        (wait_after_stand_up, [IfCondition(enable_stand_up), Unless(wait_for_bt_config)]),
        (wait_after_stand_up_bt, [IfCondition(enable_stand_up), IfCondition(wait_for_bt_config)]),
        (wait_parallel_no_stand_up, [Unless(enable_stand_up), Unless(wait_for_bt_config)]),
        (wait_parallel_no_stand_up_bt, [Unless(enable_stand_up), IfCondition(wait_for_bt_config)]),
    ):
        ld.add_action(on_process_exit_if(
            wait_proc,
            mission_bt_node,
            AndCondition([event_gating, IfCondition(enable_mission_bt), *extra_conds]),
        ))

    # ---- 旧版固定延迟回退 ----
    ld.add_action(GroupAction([
        start_livox,
        cmd_vel_udp_bridge,
        arm_pose_broadcaster_node,
        delayed_bringup,
        delayed_aft_pose_offset,
        delayed_stand_up_sender,
        delayed_mission_bt,
        delayed_arm_control,
    ], condition=legacy))
    if start_serial_driver is not None:
        ld.add_action(GroupAction([start_serial_driver], condition=legacy))

    return ld
