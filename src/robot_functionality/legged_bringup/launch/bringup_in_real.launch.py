#!/usr/bin/env python3
# Copyright (c) 2026
# Launch Livox MID360 driver first, then start the all-in-one bringup.

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction, SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    # Common launch args
    use_sim_time = LaunchConfiguration('use_sim_time')
    start_delay = LaunchConfiguration('start_delay')
    start_sim = LaunchConfiguration('start_sim')
    enable_udp_forwarding = LaunchConfiguration('enable_udp_forwarding')
    enable_serial_driver = LaunchConfiguration('enable_serial_driver')
    enable_terrain_analysis = LaunchConfiguration('enable_terrain_analysis')
    udp_ip = LaunchConfiguration('udp_ip')
    udp_port = LaunchConfiguration('udp_port')
    udp_mode = LaunchConfiguration('udp_mode')
    udp_cmd_vel_topic = LaunchConfiguration('udp_cmd_vel_topic')
    udp_use_twist_stamped = LaunchConfiguration('udp_use_twist_stamped')
    udp_estop_topic = LaunchConfiguration('udp_estop_topic')

    declare_use_sim_time = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='Use simulation time')

    declare_start_delay = DeclareLaunchArgument(
        'start_delay',
        default_value='5.0',
        description='Delay (seconds) before starting bringup_all_in_one after Livox driver starts')

    declare_start_sim = DeclareLaunchArgument(
        'start_sim',
        default_value='false',
        description='Whether to start simulation first (default: false)'
    )

    declare_enable_udp_forwarding = DeclareLaunchArgument(
        'enable_udp_forwarding',
        default_value='true',
        description='Enable UDP forwarding from nav cmd_vel to deploy_cpp'
    )

    declare_enable_serial_driver = DeclareLaunchArgument(
        'enable_serial_driver',
        default_value='false',
        description='Enable serial_driver launch'
    )

    declare_enable_terrain_analysis = DeclareLaunchArgument(
        'enable_terrain_analysis',
        default_value='false',
        description='Enable terrain analysis (local obstacle detection). Default off.'
    )

    declare_udp_ip = DeclareLaunchArgument(
        'udp_ip',
        default_value='127.0.0.1',
        description='UDP target IP for deploy_cpp'
    )

    declare_udp_port = DeclareLaunchArgument(
        'udp_port',
        default_value='9870',
        description='UDP target port for deploy_cpp'
    )

    declare_udp_mode = DeclareLaunchArgument(
        'udp_mode',
        default_value='2',
        description='deploy_cpp mode value'
    )

    declare_udp_cmd_vel_topic = DeclareLaunchArgument(
        'udp_cmd_vel_topic',
        default_value='/cmd_vel',
        description='Topic to forward to deploy_cpp UDP'
    )

    declare_udp_use_twist_stamped = DeclareLaunchArgument(
        'udp_use_twist_stamped',
        default_value='false',
        description='Set true if the input topic uses TwistStamped'
    )

    declare_udp_estop_topic = DeclareLaunchArgument(
        'udp_estop_topic',
        default_value='',
        description='Optional estop Bool topic'
    )

    # Buffer Python stdout for cleaner logs
    stdout_linebuf_envvar = SetEnvironmentVariable(
        'RCUTILS_LOGGING_BUFFERED_STREAM', '1')

    # 0) Optional: start simulation
    # try:
    #     sim_share = get_package_share_directory('pangolin_simulation')
    #     sim_launch = IncludeLaunchDescription(
    #         PythonLaunchDescriptionSource(
    #             os.path.join(sim_share, 'launch', 'pangolin_simulation.launch.py')
    #         ),
    #         condition=IfCondition(start_sim)
    #     )
    # except Exception:
    #     sim_launch = None
    sim_launch = None

    # 1) Livox driver (MID360) - try multiple likely locations
    livox_launch_path = None
    try:
        livox_share = get_package_share_directory('livox_ros_driver2')
    except Exception:
        livox_share = None

    candidates = []
    if livox_share:
        # Non-standard folder used by some repos
        candidates.append(os.path.join(livox_share, 'launch_ROS2', 'msg_MID360_launch.py'))
        # Standard launch folder
        candidates.append(os.path.join(livox_share, 'launch', 'msg_MID360_launch.py'))


    for p in candidates:
        if os.path.exists(p):
            livox_launch_path = p
            break

    if livox_launch_path is None:
        raise FileNotFoundError('Cannot find Livox MID360 launch file. Tried:\n' + '\n'.join(candidates))

    start_livox = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(livox_launch_path),
        # Pass-through args if needed in the future
        # Currently msg_MID360_launch.py usually does not consume use_sim_time
        launch_arguments={}.items(),
    )

    # 1.5) Serial driver (hardware interface)
    try:
        serial_driver_share = get_package_share_directory('serial_driver')
        start_serial_driver = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(serial_driver_share, 'launch', 'serial_driver.launch.py')
            ),
            condition=IfCondition(enable_serial_driver)
        )
    except Exception:
        start_serial_driver = None

    # 1.6) UDP forwarder for nav cmd_vel -> deploy_cpp
    cmd_vel_udp_bridge = Node(
        package='cmd_vel_udp_bridge',
        executable='cmd_vel_udp_bridge_node',
        name='cmd_vel_udp_bridge',
        output='screen',
        condition=IfCondition(enable_udp_forwarding),
        parameters=[{
            'udp_ip': udp_ip,
            'udp_port': udp_port,
            'mode': udp_mode,
            'cmd_vel_topic': udp_cmd_vel_topic,
            'use_twist_stamped': udp_use_twist_stamped,
            'estop_topic': udp_estop_topic,
        }],
    )

    # 2) Our bringup (relocalization + navigation)
    legged_share = get_package_share_directory('legged_bringup')
    bringup_all_in_one_path = os.path.join(legged_share, 'launch', 'bringup_all_in_one.launch.py')
    # start_bringup_all = IncludeLaunchDescription(
    #     PythonLaunchDescriptionSource(bringup_all_in_one_path),
    #     # Forward use_sim_time to downstream if they consume it
    #     launch_arguments={'use_sim_time': use_sim_time}.items(),
    # )

    start_bringup_all = IncludeLaunchDescription(
    PythonLaunchDescriptionSource(bringup_all_in_one_path),
    # Forward use_sim_time and disable pointcloud->scan (no pangolin required)
    launch_arguments={
        'use_sim_time': use_sim_time,
        'use_pointcloud_to_scan': 'false',
        'enable_terrain_analysis': enable_terrain_analysis,
    }.items(),
)

    delayed_bringup = TimerAction(
        period=start_delay,
        actions=[start_bringup_all]
    )

    aft_to_pose_offset_node = Node(
        package='legged_bringup',
        executable='aft_to_pose_offset_node.py',
        name='aft_to_pose_offset_node',
        output='screen',
    )

    delayed_aft_pose_offset = TimerAction(
        period=start_delay,
        actions=[aft_to_pose_offset_node]
    )

    ld = LaunchDescription()

    ld.add_action(stdout_linebuf_envvar)
    ld.add_action(declare_use_sim_time)
    ld.add_action(declare_start_delay)
    ld.add_action(declare_start_sim)
    ld.add_action(declare_enable_udp_forwarding)
    ld.add_action(declare_enable_serial_driver)
    ld.add_action(declare_enable_terrain_analysis)
    ld.add_action(declare_udp_ip)
    ld.add_action(declare_udp_port)
    ld.add_action(declare_udp_mode)
    ld.add_action(declare_udp_cmd_vel_topic)
    ld.add_action(declare_udp_use_twist_stamped)
    ld.add_action(declare_udp_estop_topic)

    # Optional: start simulation
    if sim_launch is not None:
        ld.add_action(sim_launch)
    # Start Livox driver immediately
    ld.add_action(start_livox)
    # Start serial driver (if available)
    if start_serial_driver is not None:
        ld.add_action(start_serial_driver)
    # Start UDP bridge immediately; it will wait for cmd_vel traffic from Nav2
    ld.add_action(cmd_vel_udp_bridge)
    # Start bringup after a short delay
    ld.add_action(delayed_bringup)
    # Start aft_mapped_in_map -> LIVO2/pose_offset relay after bringup delay
    ld.add_action(delayed_aft_pose_offset)

    return ld
