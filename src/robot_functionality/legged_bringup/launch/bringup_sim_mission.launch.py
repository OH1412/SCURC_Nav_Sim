#!/usr/bin/env python3
# ============================================================================
# 模拟定位任务 bringup — 基于 bringup_mission_hardcoded，使用模拟定位替代 Fast-LIVO
#
# 与 bringup_mission_hardcoded 的区别:
#   去掉 bringup_all_in_one (含 Fast-LIVO 重定位 + navigation)
#   替换为:
#     - map_server + lifecycle_manager_localization (地图服务)
#     - static_tf (机器人刚体 TF 树)
#     - navigation.launch.py (Nav2 导航栈)
#     - simulated_localization_node (模拟定位：速度积分 + 死区抖动)
#   保留所有 Mission BT + 机械臂相关节点
#
# 模拟定位特性:
#   - 订阅 /cmd_vel，积分速度生成模拟里程计
#   - 死区抖动偏向 cmd_vel_udp_bridge 映射规律 (vx_dz=0.45, vy_dz=0.43, wz_dz=0.85)
#   - 大幅度位置噪声 (σ=0.15m) + 随机跳跃 + 随机游走漂移
#   - 大量调试日志: Zone 切换、MP 推断、位置-目标距离、速度命令
#   - 发布 /state_estimation (里程计) + odom→base_link TF + /sim_true_pose (真值)
#
# 用法:
#   ros2 launch legged_bringup bringup_sim_mission.launch.py
#     enable_sim_localization:=true
#     sim_noise_level:=1.5           # 增大抖动
#     sim_initial_x:=0.35            # 初始 x 位置
#     sim_initial_y:=0.0             # 初始 y 位置
#     sim_log_velocity:=true         # 打印每次速度指令
# ============================================================================

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, IncludeLaunchDescription,
                            TimerAction, SetEnvironmentVariable, ExecuteProcess,
                            OpaqueFunction)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource, FrontendLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node


def generate_launch_description():
    # ---- 基础参数 ----
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
    enable_start_nav_gate = LaunchConfiguration('enable_start_nav_gate')
    start_nav_topic = LaunchConfiguration('start_nav_topic')
    wait_for_start_nav_timeout = LaunchConfiguration('wait_for_start_nav_timeout')
    enable_arm_pose_broadcaster = LaunchConfiguration('enable_arm_pose_broadcaster')
    enable_arm_control = LaunchConfiguration('enable_arm_control')
    arm_control_delay = LaunchConfiguration('arm_control_delay')
    enable_base_link_odom = LaunchConfiguration('enable_base_link_odom')
    base_link_odom_topic = LaunchConfiguration('base_link_odom_topic')
    enable_arm_root_odom = LaunchConfiguration('enable_arm_root_odom')
    bt_xml_file = LaunchConfiguration('bt_xml_file')
    waypoints_file = LaunchConfiguration('waypoints_file')
    arm_points_file = LaunchConfiguration('arm_points_file')
    arm_points_viz_frame = LaunchConfiguration('arm_points_viz_frame')
    enable_arm_points_viz = LaunchConfiguration('enable_arm_points_viz')
    udp_ip = LaunchConfiguration('udp_ip')
    udp_port = LaunchConfiguration('udp_port')
    udp_mode = LaunchConfiguration('udp_mode')
    udp_cmd_vel_topic = LaunchConfiguration('udp_cmd_vel_topic')
    udp_use_twist_stamped = LaunchConfiguration('udp_use_twist_stamped')
    udp_estop_topic = LaunchConfiguration('udp_estop_topic')

    # ---- 模拟定位专用参数 ----
    enable_sim_localization = LaunchConfiguration('enable_sim_localization')
    sim_noise_level = LaunchConfiguration('sim_noise_level')
    sim_initial_x = LaunchConfiguration('sim_initial_x')
    sim_initial_y = LaunchConfiguration('sim_initial_y')
    sim_initial_yaw = LaunchConfiguration('sim_initial_yaw')
    sim_log_velocity = LaunchConfiguration('sim_log_velocity')
    sim_progress_interval = LaunchConfiguration('sim_progress_interval')

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

    # ---- 地图路径 ----
    yaml_map_path = os.path.join(legged_share, 'maps', 'test_map.yaml')

    # ---- 模拟定位节点脚本路径 ----
    # 脚本放在 launch/ 目录下，CMakeLists 的 install(DIRECTORY launch ...)
    # 会自动安装到 share/，无需修改任何现有文件。
    _launch_dir = os.path.dirname(os.path.realpath(__file__))
    _sim_node_script = os.path.join(_launch_dir, 'sim_localization_node.py')
    # 安装路径（colcon build 后自动存在）
    _sim_node_install = os.path.join(legged_share, 'launch', 'sim_localization_node.py')
    if os.path.exists(_sim_node_script):
        sim_node_path = _sim_node_script
    elif os.path.exists(_sim_node_install):
        sim_node_path = _sim_node_install
    else:
        sim_node_path = _sim_node_script  # 默认值，运行时找不到会报错

    # ---- 静态 TF 参数文件 ----
    _static_tf_source = os.path.join(_launch_dir, '..', 'params', 'static_tf_params.yaml')
    _static_tf_install = os.path.join(legged_share, 'params', 'static_tf_params.yaml')
    static_tf_params = _static_tf_source if os.path.exists(_static_tf_source) else _static_tf_install

    # ========================================================================
    # 声明参数
    # ========================================================================
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
        'mission_bt_delay', default_value='10.0',
        description='Delay after bringup before starting mission_bt_node')
    declare_enable_start_nav_gate = DeclareLaunchArgument(
        'enable_start_nav_gate', default_value='false',
        description='Wait for /start_nav before mission BT nav+arm tick loop '
                    '(仿真模式默认 false=立即出发)')
    declare_start_nav_topic = DeclareLaunchArgument(
        'start_nav_topic', default_value='/start_nav')
    declare_wait_for_start_nav_timeout = DeclareLaunchArgument(
        'wait_for_start_nav_timeout', default_value='0.0')
    declare_enable_arm_pose_broadcaster = DeclareLaunchArgument(
        'enable_arm_pose_broadcaster', default_value='true')
    declare_enable_arm_control = DeclareLaunchArgument(
        'enable_arm_control', default_value='false')
    declare_arm_control_delay = DeclareLaunchArgument(
        'arm_control_delay', default_value='12.0')
    declare_enable_base_link_odom = DeclareLaunchArgument(
        'enable_base_link_odom', default_value='true',
        description='Publish base_link→map Odometry via TF (备用，模拟模式可关闭)')
    declare_base_link_odom_topic = DeclareLaunchArgument(
        'base_link_odom_topic', default_value='/base_link_in_map')
    declare_enable_arm_root_odom = DeclareLaunchArgument(
        'enable_arm_root_odom', default_value='true',
        description='Publish arm_root→map Odometry via TF')
    declare_bt_xml_file = DeclareLaunchArgument(
        'bt_xml_file', default_value=default_bt_xml)
    declare_waypoints_file = DeclareLaunchArgument(
        'waypoints_file', default_value=default_waypoints_file)
    declare_arm_points_file = DeclareLaunchArgument(
        'arm_points_file', default_value=default_arm_points)
    declare_arm_points_viz_frame = DeclareLaunchArgument(
        'arm_points_viz_frame', default_value='map')
    declare_enable_arm_points_viz = DeclareLaunchArgument(
        'enable_arm_points_viz', default_value='true')
    declare_udp_ip = DeclareLaunchArgument('udp_ip', default_value='127.0.0.1')
    declare_udp_port = DeclareLaunchArgument('udp_port', default_value='9870')
    declare_udp_mode = DeclareLaunchArgument('udp_mode', default_value='2')
    declare_udp_cmd_vel_topic = DeclareLaunchArgument(
        'udp_cmd_vel_topic', default_value='/cmd_vel')
    declare_udp_use_twist_stamped = DeclareLaunchArgument(
        'udp_use_twist_stamped', default_value='false')
    declare_udp_estop_topic = DeclareLaunchArgument(
        'udp_estop_topic', default_value='')

    # ---- 模拟定位参数声明 ----
    declare_enable_sim_localization = DeclareLaunchArgument(
        'enable_sim_localization', default_value='true',
        description='Enable simulated localization (replaces Fast-LIVO). '
                    'Publishes /state_estimation + odom→base_link TF.')
    declare_sim_noise_level = DeclareLaunchArgument(
        'sim_noise_level', default_value='1.0',
        description='Simulation noise multiplier (>1 = more jitter)')
    declare_sim_initial_x = DeclareLaunchArgument(
        'sim_initial_x', default_value='0.35',
        description='Initial simulated robot x position in map frame (default: nav_p0_wp0)')
    declare_sim_initial_y = DeclareLaunchArgument(
        'sim_initial_y', default_value='0.0',
        description='Initial simulated robot y position in map frame')
    declare_sim_initial_yaw = DeclareLaunchArgument(
        'sim_initial_yaw', default_value='0.0',
        description='Initial simulated robot yaw in radians')
    declare_sim_log_velocity = DeclareLaunchArgument(
        'sim_log_velocity', default_value='true',
        description='Log every cmd_vel command with deadzone analysis')
    declare_sim_progress_interval = DeclareLaunchArgument(
        'sim_progress_interval', default_value='5.0',
        description='Interval (seconds) for periodic position/zone progress logging')

    stdout_linebuf_envvar = SetEnvironmentVariable(
        'RCUTILS_LOGGING_BUFFERED_STREAM', '1')

    # ========================================================================
    # 1) Livox MID360
    # ========================================================================
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

    start_livox = None
    if livox_launch_path is not None:
        start_livox = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(livox_launch_path),
            launch_arguments={}.items(),
        )

    # ========================================================================
    # 2) Serial driver (机械臂串口)
    # ========================================================================
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

    # ========================================================================
    # 3) UDP bridge (cmd_vel → deploy_cpp)
    # ========================================================================
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

    # ========================================================================
    # 4) Map Server + Lifecycle Manager (替代 global_relocalization 的 map_server)
    # ========================================================================
    map_server_node = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        respawn=True,
        respawn_delay=2.0,
        parameters=[{
            'use_sim_time': use_sim_time,
            'yaml_filename': yaml_map_path,
        }],
        arguments=['--ros-args', '--log-level', 'info'],
    )

    lifecycle_manager_localization_node = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_localization',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'autostart': True,
            'node_names': ['map_server'],
        }],
    )

    # ========================================================================
    # 5) 静态 TF (机器人刚体 TF 树: base_link→livox_frame, etc.)
    # ========================================================================
    static_tf_broadcaster_node = Node(
        package='legged_bringup',
        executable='static_tf_broadcaster.py',
        name='static_tf_broadcaster',
        output='screen',
        parameters=[static_tf_params],
    )
    # 延迟启动，确保 map_server 先初始化
    delayed_static_tf = TimerAction(
        period=3.0,
        actions=[static_tf_broadcaster_node],
    )

    # ========================================================================
    # 6) Navigation (Nav2 导航栈)
    # ========================================================================
    start_navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(legged_share, 'launch', 'navigation.launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'enable_terrain_analysis': enable_terrain_analysis,
            # 默认 warn 会吞掉 CRITIC_SCALE_SYNC / FORCE_ALIGN（均为 INFO）
            'log_level': 'info',
        }.items(),
    )
    # 延迟 15s，确保 sim localization + map_server 完全就绪
    # 避免 controller_server 初始化时被 odom 消息淹没导致 lifecycle 超时
    delayed_navigation = TimerAction(
        period=15.0,
        actions=[start_navigation],
    )

    # ========================================================================
    # 7) 模拟定位节点 (替代 Fast-LIVO，发布 /state_estimation + odom→base_link TF)
    # ========================================================================
    # 使用 OpaqueFunction + ExecuteProcess 避免修改 CMakeLists.txt
    # 参数通过 context.perform_substitution() 在运行时解析
    # 脚本路径：开发环境用源路径，安装环境用安装路径，都不行则回退到 Node 方式
    def _make_sim_localization_cmd(context):
        """构建模拟定位节点命令（python3 直接执行 + ROS2 参数传递）"""
        script = sim_node_path
        if not os.path.exists(script):
            script = _sim_node_install

        # 解析参数
        _enable_sim = context.perform_substitution(enable_sim_localization)
        if _enable_sim.lower() in ('false', '0'):
            return []

        _initial_x = context.perform_substitution(sim_initial_x)
        _initial_y = context.perform_substitution(sim_initial_y)
        _initial_yaw = context.perform_substitution(sim_initial_yaw)
        _noise_level = context.perform_substitution(sim_noise_level)
        _log_vel = context.perform_substitution(sim_log_velocity)
        _prog_int = context.perform_substitution(sim_progress_interval)

        if not os.path.exists(script):
            # 脚本未找到，回退到 Node 方式（需 CMakeLists 已注册）
            return [
                Node(
                    package='legged_bringup',
                    executable='simulated_localization_node.py',
                    name='simulated_localization',
                    output='screen',
                    parameters=[{
                        'odom_topic': '/state_estimation',
                        'cmd_vel_topic': '/cmd_vel',
                        'nav_zone_topic': '/mission_bt/nav_zone',
                        'nav_segment_yaw_topic': '/mission_bt/nav_segment_yaw',
                        'base_frame': 'base_link',
                        'odom_frame': 'odom',
                        'map_frame': 'map',
                        'publish_rate': 50.0,
                        'initial_x': float(_initial_x),
                        'initial_y': float(_initial_y),
                        'initial_yaw': float(_initial_yaw),
                        'enable_noise': True,
                        'noise_level': float(_noise_level),
                        'log_velocity_detail': _log_vel.lower() in ('true', '1'),
                        'progress_log_interval': float(_prog_int),
                    }],
                )
            ]

        # 使用 python3 直接执行脚本
        # --ros-args -p key:=value 传递给节点的 declare_parameter
        return [
            ExecuteProcess(
                cmd=[
                    'python3', script,
                    '--ros-args',
                    '-p', 'odom_topic:=/state_estimation',
                    '-p', 'cmd_vel_topic:=/cmd_vel',
                    '-p', 'nav_zone_topic:=/mission_bt/nav_zone',
                    '-p', 'nav_segment_yaw_topic:=/mission_bt/nav_segment_yaw',
                    '-p', 'base_frame:=base_link',
                    '-p', 'odom_frame:=odom',
                    '-p', 'map_frame:=map',
                    '-p', 'publish_rate:=50.0',
                    '-p', f'initial_x:={_initial_x}',
                    '-p', f'initial_y:={_initial_y}',
                    '-p', f'initial_yaw:={_initial_yaw}',
                    '-p', 'enable_noise:=true',
                    '-p', f'noise_level:={_noise_level}',
                    '-p', f'log_velocity_detail:={_log_vel}',
                    '-p', f'progress_log_interval:={_prog_int}',
                    '--ros-args',
                    '--log-level', 'info',
                ],
                output='screen',
                shell=False,
            )
        ]

    sim_localization_action = OpaqueFunction(function=_make_sim_localization_cmd)

    # ========================================================================
    # 8) aft → pose_offset 转发 (模拟模式下可保留，发布额外的 pose offset)
    # ========================================================================
    aft_to_pose_offset_node = Node(
        package='legged_bringup',
        executable='aft_to_pose_offset_node.py',
        name='aft_to_pose_offset_node',
        output='screen',
    )
    delayed_aft_pose_offset = TimerAction(
        period=start_delay, actions=[aft_to_pose_offset_node])

    # ========================================================================
    # 9) base_link → map Odometry 发布 (备用，模拟模式下 sim localization 已发布)
    # ========================================================================
    # 模拟定位节点已经发布了 /state_estimation 和 odom→base_link TF，
    # 此处保留 base_link_odom_publisher 作为备用（发布到 /base_link_in_map）
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

    # ========================================================================
    # 10) arm_root → map Odometry 发布 (机械臂工作空间原点)
    # ========================================================================
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

    # ========================================================================
    # 11) Stand-up
    # ========================================================================
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

    # ========================================================================
    # 12) Arm pose broadcaster (map_target → base_link)
    # ========================================================================
    arm_pose_broadcaster_node = Node(
        package='legged_bringup',
        executable='arm_pose_broadcaster.py',
        name='arm_pose_broadcaster',
        output='screen',
        condition=IfCondition(enable_arm_pose_broadcaster),
        parameters=[{'arm_points_file': arm_points_file}],
    )

    # ========================================================================
    # 13) Arm points RViz visualizer
    # ========================================================================
    arm_points_viz_node = Node(
        package='legged_bringup',
        executable='arm_points_visualizer.py',
        name='arm_points_visualizer',
        output='screen',
        condition=IfCondition(enable_arm_points_viz),
        parameters=[{
            'arm_points_file': arm_points_file,
            'frame_id': arm_points_viz_frame,
            'publish_rate': 1.0,
        }],
    )

    # ========================================================================
    # 14) Mission BT node (fly_step: Nav + Arm)
    # ========================================================================
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
            'enable_start_nav_gate': enable_start_nav_gate,
            'start_nav_topic': start_nav_topic,
            'wait_for_start_nav_timeout': wait_for_start_nav_timeout,
        }],
    )
    delayed_mission_bt = TimerAction(
        period=mission_bt_delay,
        actions=[mission_bt_node],
        condition=IfCondition(enable_mission_bt),
    )

    # ========================================================================
    # 15) Arm Control Action Server (可选)
    # ========================================================================
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
    # LaunchDescription 组装
    # ================================================================
    ld = LaunchDescription()

    # ---- 环境变量 ----
    ld.add_action(stdout_linebuf_envvar)

    # ---- 基础参数声明 ----
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
    ld.add_action(declare_enable_start_nav_gate)
    ld.add_action(declare_start_nav_topic)
    ld.add_action(declare_wait_for_start_nav_timeout)
    ld.add_action(declare_enable_arm_pose_broadcaster)
    ld.add_action(declare_enable_arm_control)
    ld.add_action(declare_arm_control_delay)
    ld.add_action(declare_enable_base_link_odom)
    ld.add_action(declare_base_link_odom_topic)
    ld.add_action(declare_enable_arm_root_odom)
    ld.add_action(declare_bt_xml_file)
    ld.add_action(declare_waypoints_file)
    ld.add_action(declare_arm_points_file)
    ld.add_action(declare_arm_points_viz_frame)
    ld.add_action(declare_enable_arm_points_viz)
    ld.add_action(declare_udp_ip)
    ld.add_action(declare_udp_port)
    ld.add_action(declare_udp_mode)
    ld.add_action(declare_udp_cmd_vel_topic)
    ld.add_action(declare_udp_use_twist_stamped)
    ld.add_action(declare_udp_estop_topic)

    # ---- 模拟定位参数声明 ----
    ld.add_action(declare_enable_sim_localization)
    ld.add_action(declare_sim_noise_level)
    ld.add_action(declare_sim_initial_x)
    ld.add_action(declare_sim_initial_y)
    ld.add_action(declare_sim_initial_yaw)
    ld.add_action(declare_sim_log_velocity)
    ld.add_action(declare_sim_progress_interval)

    # ---- 启动节点（按依赖顺序）----

    # Livox MID360 (如果硬件已连接)
    if start_livox is not None:
        ld.add_action(start_livox)

    # 机械臂串口驱动
    if start_serial_driver is not None:
        ld.add_action(start_serial_driver)

    # UDP 速度桥接
    ld.add_action(cmd_vel_udp_bridge)

    # 地图服务器 + 生命周期管理器（替代 Fast-LIVO）
    ld.add_action(map_server_node)
    ld.add_action(lifecycle_manager_localization_node)

    # 静态 TF（机器人刚体 TF 树）
    ld.add_action(delayed_static_tf)

    # 模拟定位（替代 Fast-LIVO odometry）
    ld.add_action(sim_localization_action)

    # Nav2 导航栈（延迟启动，等 map_server 就绪）
    ld.add_action(delayed_navigation)

    # aft → pose_offset 转发
    ld.add_action(delayed_aft_pose_offset)

    # base_link / arm_root odometry 发布（备用）
    ld.add_action(delayed_base_link_odom)
    ld.add_action(delayed_arm_root_odom)

    # 起立命令
    ld.add_action(delayed_stand_up_sender)

    # 机械臂位姿广播 + 可视化
    ld.add_action(arm_pose_broadcaster_node)
    ld.add_action(arm_points_viz_node)

    # Mission BT（导航+机械臂任务序列）
    ld.add_action(delayed_mission_bt)

    # 机械臂控制服务器（可选）
    ld.add_action(delayed_arm_control)

    return ld
