#!/usr/bin/env python3
# ============================================================================
# 交互式机械臂抓取/放置 bringup — 基于 bringup_mission_hardcoded，去掉 BT 与 Nav2
#
# 保留: Livox + 定位 + 串口 + arm_pose_broadcaster + 遥控/站立 等
# 去掉: bringup_all_in_one 中的 navigation、mission_bt_node
# 新增: interactive_arm_pick（手柄 X 键交替抓取/放置最近点）
#
# 一键启动（等同 ~/start_arm_pick_interactive.sh，含坐标监视终端）:
#   source FAST + SCURC + HIM 工作空间后:
#   ros2 launch legged_bringup bringup_arm_pick_interactive.launch.py
#
# 操作: 遥控到位后按手柄 X 键 — 第1次抓取最近点，第2次放置最近点，之后交替。
# 坐标输出在 [arm_coords] 独立终端（/interactive_arm/coord_report）。
# ============================================================================

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, IncludeLaunchDescription,
                            TimerAction, SetEnvironmentVariable, ExecuteProcess)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    start_delay = LaunchConfiguration('start_delay')
    enable_udp_forwarding = LaunchConfiguration('enable_udp_forwarding')
    enable_serial_driver = LaunchConfiguration('enable_serial_driver')
    enable_stand_up = LaunchConfiguration('enable_stand_up')
    stand_up_delay = LaunchConfiguration('stand_up_delay')
    reloc_delay = LaunchConfiguration('reloc_delay')
    enable_arm_pose_broadcaster = LaunchConfiguration('enable_arm_pose_broadcaster')
    enable_interactive_arm_pick = LaunchConfiguration('enable_interactive_arm_pick')
    enable_base_link_odom = LaunchConfiguration('enable_base_link_odom')
    base_link_odom_topic = LaunchConfiguration('base_link_odom_topic')
    enable_arm_root_odom = LaunchConfiguration('enable_arm_root_odom')
    interactive_pick_delay = LaunchConfiguration('interactive_pick_delay')
    arm_points_file = LaunchConfiguration('arm_points_file')
    arm_timeout = LaunchConfiguration('arm_timeout')
    enable_joy = LaunchConfiguration('enable_joy')
    enable_deploy = LaunchConfiguration('enable_deploy')
    joy_start_delay = LaunchConfiguration('joy_start_delay')
    deploy_start_delay = LaunchConfiguration('deploy_start_delay')
    robot_config_file = LaunchConfiguration('robot_config_file')
    libtorch_lib_path = LaunchConfiguration('libtorch_lib_path')
    enable_coord_terminal = LaunchConfiguration('enable_coord_terminal')
    coord_terminal_delay = LaunchConfiguration('coord_terminal_delay')
    udp_ip = LaunchConfiguration('udp_ip')
    udp_port = LaunchConfiguration('udp_port')
    udp_mode = LaunchConfiguration('udp_mode')
    udp_cmd_vel_topic = LaunchConfiguration('udp_cmd_vel_topic')
    udp_use_twist_stamped = LaunchConfiguration('udp_use_twist_stamped')
    udp_estop_topic = LaunchConfiguration('udp_estop_topic')

    legged_share = get_package_share_directory('legged_bringup')
    nav2_params_file = os.path.join(legged_share, 'params', 'nav2_params.yaml')
    default_arm_points = os.path.join(legged_share, 'params', 'arm_points.yaml')
    default_robot_config = '/home/dog12/HIMLocoWithDeploy/deploy_cpp/config/robots/mybot_arm.yaml'
    default_libtorch = '/home/dog12/libtorch/lib'
    default_fast_ws = '/home/dog12/FAST_LIVO2_ROS2_relocation_ultra'
    default_scurc_ws = '/home/dog12/SCURC_Nav_Sim'
    default_ros_base = '/opt/ros/humble'

    declare_use_sim_time = DeclareLaunchArgument('use_sim_time', default_value='false')
    declare_start_delay = DeclareLaunchArgument('start_delay', default_value='5.0')
    declare_enable_udp_forwarding = DeclareLaunchArgument(
        'enable_udp_forwarding', default_value='true')
    declare_enable_serial_driver = DeclareLaunchArgument(
        'enable_serial_driver', default_value='true')
    declare_enable_stand_up = DeclareLaunchArgument(
        'enable_stand_up', default_value='false',
        description='Auto STAND_UP via UDP (disable when controlling pose manually)')
    declare_stand_up_delay = DeclareLaunchArgument(
        'stand_up_delay', default_value='3.0')
    declare_reloc_delay = DeclareLaunchArgument(
        'reloc_delay', default_value='0.0')
    declare_enable_arm_pose_broadcaster = DeclareLaunchArgument(
        'enable_arm_pose_broadcaster', default_value='true')
    declare_enable_base_link_odom = DeclareLaunchArgument(
        'enable_base_link_odom', default_value='true',
        description='Publish base_link→map Odometry via TF')
    declare_base_link_odom_topic = DeclareLaunchArgument(
        'base_link_odom_topic', default_value='/base_link_in_map')
    declare_enable_arm_root_odom = DeclareLaunchArgument(
        'enable_arm_root_odom', default_value='true',
        description='Publish arm_root→map Odometry via TF (机械臂工作空间原点)')
    declare_enable_interactive_arm_pick = DeclareLaunchArgument(
        'enable_interactive_arm_pick', default_value='true',
        description='X button alternating nearest pick/place via interactive_arm_pick')
    declare_interactive_pick_delay = DeclareLaunchArgument(
        'interactive_pick_delay', default_value='15.0',
        description='Delay before starting interactive pick prompt (wait for localization)')
    declare_arm_points_file = DeclareLaunchArgument(
        'arm_points_file', default_value=default_arm_points)
    declare_arm_timeout = DeclareLaunchArgument(
        'arm_timeout', default_value='30.0')
    declare_enable_joy = DeclareLaunchArgument(
        'enable_joy', default_value='true',
        description='Start joy_node in this launch (start_arm_pick_interactive.sh uses separate terminal)')
    declare_enable_deploy = DeclareLaunchArgument(
        'enable_deploy', default_value='true',
        description='Start deploy_node in this launch (mybot_arm motion control)')
    declare_joy_start_delay = DeclareLaunchArgument(
        'joy_start_delay', default_value='5.0')
    declare_deploy_start_delay = DeclareLaunchArgument(
        'deploy_start_delay', default_value='5.0')
    declare_robot_config_file = DeclareLaunchArgument(
        'robot_config_file', default_value=default_robot_config)
    declare_libtorch_lib_path = DeclareLaunchArgument(
        'libtorch_lib_path', default_value=default_libtorch)
    declare_enable_coord_terminal = DeclareLaunchArgument(
        'enable_coord_terminal', default_value='true',
        description='Open gnome-terminal for arm_coord_monitor (coord output)')
    declare_coord_terminal_delay = DeclareLaunchArgument(
        'coord_terminal_delay', default_value='3.0')
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

    # ---- 4) 定位 only（无 Nav2 navigation）----
    relocalization_path = os.path.join(
        legged_share, 'launch', 'global_relocalization.launch.py')
    start_relocalization = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(relocalization_path),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'enable_relocalization': 'false',
        }.items(),
    )
    delayed_relocalization = TimerAction(period=start_delay, actions=[start_relocalization])

    relay_odom = Node(
        package='topic_tools',
        executable='relay',
        name='relay_state_estimation',
        output='screen',
        arguments=['/aft_mapped_in_map', '/state_estimation'],
    )

    # ---- 5) aft → pose_offset 转发 ----
    aft_to_pose_offset_node = Node(
        package='legged_bringup',
        executable='aft_to_pose_offset_node.py',
        name='aft_to_pose_offset_node',
        output='screen',
    )
    delayed_aft_pose_offset = TimerAction(
        period=start_delay, actions=[aft_to_pose_offset_node])

    # ---- 5.5) base_link → map Odometry ----
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
        condition=IfCondition(enable_base_link_odom),
    )

    # ---- 5.6) arm_root → map Odometry ----
    arm_root_odom_node = Node(
        package='legged_bringup',
        executable='arm_root_odom_publisher.py',
        name='arm_root_odom_publisher',
        output='screen',
        condition=IfCondition(enable_arm_root_odom),
        parameters=[{
            'target_topic': '/arm_root_in_map',
            'publish_rate': 50.0,
            'base_frame': 'base_link',
            'map_frame': 'map',
            'publish_tf': True,
        }],
    )
    delayed_arm_root_odom = TimerAction(
        period=start_delay,
        actions=[arm_root_odom_node],
        condition=IfCondition(enable_arm_root_odom),
    )

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

    # ---- 7) Arm pose broadcaster ----
    arm_pose_broadcaster_node = Node(
        package='legged_bringup',
        executable='arm_pose_broadcaster.py',
        name='arm_pose_broadcaster',
        output='screen',
        condition=IfCondition(enable_arm_pose_broadcaster),
        parameters=[{'arm_points_file': arm_points_file}],
    )

    # ---- 8) 手柄 X 键交替抓取/放置（无 BT）----
    interactive_arm_pick_node = Node(
        package='legged_bringup',
        executable='interactive_arm_pick.py',
        name='interactive_arm_pick',
        output='screen',
        condition=IfCondition(enable_interactive_arm_pick),
        parameters=[{
            'arm_points_file': arm_points_file,
            'arm_timeout': arm_timeout,
        }],
    )
    delayed_interactive_arm_pick = TimerAction(
        period=interactive_pick_delay,
        actions=[interactive_arm_pick_node],
        condition=IfCondition(enable_interactive_arm_pick),
    )

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

    coord_monitor_cmd = (
        f'source {default_ros_base}/setup.bash && '
        f'source {default_scurc_ws}/install/setup.bash && '
        'ros2 run legged_bringup arm_coord_monitor.py; exec bash'
    )
    coord_monitor_terminal = ExecuteProcess(
        cmd=[
            'gnome-terminal', '--title=arm_coords', '--',
            'bash', '-lc', coord_monitor_cmd,
        ],
        condition=IfCondition(enable_coord_terminal),
    )
    delayed_coord_terminal = TimerAction(
        period=coord_terminal_delay,
        actions=[coord_monitor_terminal],
        condition=IfCondition(enable_coord_terminal),
    )

    ld = LaunchDescription()
    ld.add_action(stdout_linebuf_envvar)
    ld.add_action(declare_use_sim_time)
    ld.add_action(declare_start_delay)
    ld.add_action(declare_enable_udp_forwarding)
    ld.add_action(declare_enable_serial_driver)
    ld.add_action(declare_enable_stand_up)
    ld.add_action(declare_stand_up_delay)
    ld.add_action(declare_reloc_delay)
    ld.add_action(declare_enable_arm_pose_broadcaster)
    ld.add_action(declare_enable_base_link_odom)
    ld.add_action(declare_base_link_odom_topic)
    ld.add_action(declare_enable_arm_root_odom)
    ld.add_action(declare_enable_interactive_arm_pick)
    ld.add_action(declare_interactive_pick_delay)
    ld.add_action(declare_arm_points_file)
    ld.add_action(declare_arm_timeout)
    ld.add_action(declare_enable_joy)
    ld.add_action(declare_enable_deploy)
    ld.add_action(declare_joy_start_delay)
    ld.add_action(declare_deploy_start_delay)
    ld.add_action(declare_robot_config_file)
    ld.add_action(declare_libtorch_lib_path)
    ld.add_action(declare_enable_coord_terminal)
    ld.add_action(declare_coord_terminal_delay)
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
    ld.add_action(relay_odom)
    ld.add_action(delayed_relocalization)
    ld.add_action(delayed_aft_pose_offset)
    ld.add_action(delayed_base_link_odom)
    ld.add_action(delayed_arm_root_odom)
    ld.add_action(delayed_stand_up_sender)
    ld.add_action(arm_pose_broadcaster_node)
    ld.add_action(delayed_interactive_arm_pick)
    ld.add_action(delayed_joy)
    ld.add_action(delayed_deploy)
    ld.add_action(delayed_coord_terminal)

    return ld
