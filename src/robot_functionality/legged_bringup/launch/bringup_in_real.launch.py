#!/usr/bin/env python3
# Copyright (c) 2026
# Launch Livox MID360 driver first, then start the all-in-one bringup.

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
    # Common launch args
    use_sim_time = LaunchConfiguration('use_sim_time')
    start_delay = LaunchConfiguration('start_delay')
    start_sim = LaunchConfiguration('start_sim')
    enable_udp_forwarding = LaunchConfiguration('enable_udp_forwarding')
    enable_serial_driver = LaunchConfiguration('enable_serial_driver')
    enable_terrain_analysis = LaunchConfiguration('enable_terrain_analysis')
    enable_waypoint_mission = LaunchConfiguration('enable_waypoint_mission')
    waypoint_file = LaunchConfiguration('waypoint_file')
    waypoint_start_delay = LaunchConfiguration('waypoint_start_delay')
    enable_stand_up = LaunchConfiguration('enable_stand_up')
    stand_up_delay = LaunchConfiguration('stand_up_delay')
    enable_base_link_odom = LaunchConfiguration('enable_base_link_odom')
    base_link_odom_topic = LaunchConfiguration('base_link_odom_topic')
    enable_arm_control = LaunchConfiguration('enable_arm_control')
    arm_control_delay = LaunchConfiguration('arm_control_delay')
    udp_ip = LaunchConfiguration('udp_ip')
    udp_port = LaunchConfiguration('udp_port')
    udp_mode = LaunchConfiguration('udp_mode')
    udp_cmd_vel_topic = LaunchConfiguration('udp_cmd_vel_topic')
    udp_use_twist_stamped = LaunchConfiguration('udp_use_twist_stamped')
    udp_estop_topic = LaunchConfiguration('udp_estop_topic')
    reloc_delay = LaunchConfiguration('reloc_delay')

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
        default_value='true',
        description='Enable serial_driver launch'
    )

    declare_enable_terrain_analysis = DeclareLaunchArgument(
        'enable_terrain_analysis',
        default_value='false',
        description='Enable terrain analysis (local obstacle detection). Default off.'
    )

    declare_enable_waypoint_mission = DeclareLaunchArgument(
        'enable_waypoint_mission',
        default_value='true',
        description='Auto-start waypoint_sender (NavigateToPose, pure navigation BT)'
    )

    declare_waypoint_file = DeclareLaunchArgument(
        'waypoint_file',
        default_value=os.path.join(
            get_package_share_directory('legged_bringup'), 'params', 'waypoints.yaml'),
        description='Path to waypoints.yaml.'
    )

    declare_waypoint_start_delay = DeclareLaunchArgument(
        'waypoint_start_delay',
        default_value='25.0',
        description='Delay (seconds) after bringup before waypoint_sender starts NavigateToPose sequence.'
    )

    declare_enable_stand_up = DeclareLaunchArgument(
        'enable_stand_up',
        default_value='true',
        description='Send STAND_UP command to deploy_cpp before navigation.'
    )

    declare_stand_up_delay = DeclareLaunchArgument(
        'stand_up_delay',
        default_value='3.0',
        description='Delay (seconds) before starting stand_up_sender (node internally waits for relocalization + reloc_delay).'
    )
    declare_reloc_delay = DeclareLaunchArgument(
        'reloc_delay',
        default_value='0.0',
        description='Seconds to wait AFTER relocalization signal before sending stand_up.'
    )

    declare_enable_base_link_odom = DeclareLaunchArgument(
        'enable_base_link_odom',
        default_value='false',
        description='Publish base_link→map Odometry via TF (替代 /aft_mapped_to_init 当 Fast-LIVO 未运行时)'
    )

    declare_base_link_odom_topic = DeclareLaunchArgument(
        'base_link_odom_topic',
        default_value='/base_link_in_map',
        description='Topic to publish base_link odometry. Set to /aft_mapped_to_init to replace Fast-LIVO output.'
    )

    declare_enable_arm_control = DeclareLaunchArgument(
        'enable_arm_control',
        default_value='false',
        description='ArmControl Action Server (enable for navigate_waypoints_with_task BT)'
    )

    declare_arm_control_delay = DeclareLaunchArgument(
        'arm_control_delay',
        default_value='12.0',
        description='Delay (seconds) after bringup before starting arm control server (must start before bt_navigator)'
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

    # Path to centralized parameter file (shared with navigation.launch.py)
    nav2_params_file = os.path.join(
        get_package_share_directory('legged_bringup'), 'params', 'nav2_params.yaml')

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
    # 包含死区补偿：当速度非零但低于 deadzone 阈值时，自动提升到 min_effective
    cmd_vel_udp_bridge = Node(
        package='cmd_vel_udp_bridge',
        executable='cmd_vel_udp_bridge_node',
        name='cmd_vel_udp_bridge',
        output='screen',
        condition=IfCondition(enable_udp_forwarding),
        parameters=[nav2_params_file,
                    # Launch arg overrides (覆盖 YAML 默认值)
                    {
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

    # ── base_link → map Odometry 发布 (可替代 /aft_mapped_to_init) ────
    base_link_odom_node = Node(
        package='legged_bringup',
        executable='base_link_odom_publisher.py',
        name='base_link_odom_publisher',
        output='screen',
        condition=IfCondition(enable_base_link_odom),
        parameters=[{
            'target_topic': base_link_odom_topic,
            'publish_rate': 50.0,
            'base_frame': 'base_link',
            'map_frame': 'map',
        }],
    )

    delayed_base_link_odom = TimerAction(
        period=start_delay,
        actions=[base_link_odom_node],
        condition=IfCondition(enable_base_link_odom)
    )

    # Stand-up command sender (UDP to deploy_cpp, before navigation)
    stand_up_sender_node = Node(
        package='legged_bringup',
        executable='stand_up_sender.py',
        name='stand_up_sender',
        output='screen',
        condition=IfCondition(enable_stand_up),
        parameters=[nav2_params_file,
                    {'udp_ip': udp_ip, 'udp_port': udp_port, 'reloc_delay': reloc_delay}],
    )

    delayed_stand_up_sender = TimerAction(
        period=stand_up_delay,
        actions=[stand_up_sender_node],
        condition=IfCondition(enable_stand_up)
    )

    # Arm Control Action Server (optional, controlled by enable_arm_control)
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
        condition=IfCondition(enable_arm_control)
    )

    # 逐点导航：waypoint_sender → NavigateToPose → bt_navigator
    # 行为树: navigate_to_pose_w_replanning_and_recovery.xml (纯导航)
    waypoint_sender_node = Node(
        package='legged_bringup',
        executable='waypoint_sender.py',
        name='waypoint_sender',
        output='screen',
        condition=IfCondition(enable_waypoint_mission),
        parameters=[{
            'waypoint_file': waypoint_file,
            'startup_delay': 0.0,  # TimerAction 已做延迟
        }],
    )

    delayed_waypoint_sender = TimerAction(
        period=waypoint_start_delay,
        actions=[waypoint_sender_node],
        condition=IfCondition(enable_waypoint_mission)
    )

    ld = LaunchDescription()

    ld.add_action(stdout_linebuf_envvar)
    ld.add_action(declare_use_sim_time)
    ld.add_action(declare_start_delay)
    ld.add_action(declare_start_sim)
    ld.add_action(declare_enable_udp_forwarding)
    ld.add_action(declare_enable_serial_driver)
    ld.add_action(declare_enable_terrain_analysis)
    ld.add_action(declare_enable_waypoint_mission)
    ld.add_action(declare_waypoint_file)
    ld.add_action(declare_waypoint_start_delay)
    ld.add_action(declare_enable_stand_up)
    ld.add_action(declare_stand_up_delay)
    ld.add_action(declare_reloc_delay)
    ld.add_action(declare_enable_arm_control)
    ld.add_action(declare_arm_control_delay)
    ld.add_action(declare_enable_base_link_odom)
    ld.add_action(declare_base_link_odom_topic)
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
    # Start base_link→map Odometry publisher (替代 /aft_mapped_to_init)
    ld.add_action(delayed_base_link_odom)
    # Stand up before navigation (UDP to deploy_cpp)
    ld.add_action(delayed_stand_up_sender)
    # Arm Control Action Server for manipulator tasks
    ld.add_action(delayed_arm_control)
    # Waypoint 逐点导航 (NavigateToPose + navigate_waypoints_with_task BT)
    ld.add_action(delayed_waypoint_sender)

    return ld
