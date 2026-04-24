# leg_bringup/launch/simulation_bringup.launch.py
import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, GroupAction,
                            IncludeLaunchDescription, SetEnvironmentVariable, TimerAction)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource, FrontendLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import LoadComposableNodes, Node
from launch_ros.descriptions import ComposableNode, ParameterFile
from nav2_common.launch import RewrittenYaml


def generate_launch_description():
    # ========================================================================
    # 1. 基础路径与参数定义
    # ========================================================================
    bringup_dir = get_package_share_directory('leg_bringup')
    # 【新增】获取 elevation_mapping_cupy 的路径
    elevation_share = get_package_share_directory('elevation_mapping_cupy')

    # Launch Configurations
    namespace = LaunchConfiguration('namespace')
    use_sim_time = LaunchConfiguration('use_sim_time')
    autostart = LaunchConfiguration('autostart')
    elevation_nav_params = LaunchConfiguration('elevation_nav_params')
    use_composition = LaunchConfiguration('use_composition')
    container_name = LaunchConfiguration('container_name')
    container_name_full = (namespace, '/', container_name)
    use_respawn = LaunchConfiguration('use_respawn')
    log_level = LaunchConfiguration('log_level')
    delay_after_sim = LaunchConfiguration('delay_after_sim')
    use_rviz = LaunchConfiguration('use_rviz')
    start_sim = LaunchConfiguration('start_sim')

    # Declare Arguments
    declare_namespace_cmd = DeclareLaunchArgument(
        'namespace', default_value='',
        description='Top-level namespace')

    declare_use_sim_time_cmd = DeclareLaunchArgument(
        'use_sim_time', default_value='false',
        description='Use simulation (Gazebo) clock if true')

    declare_params_file_cmd = DeclareLaunchArgument(
        'elevation_nav_params',
        default_value=os.path.join(bringup_dir, 'params', 'nav2_params.yaml'),
        description='Full path to the ROS2 parameters file to use for all launched nodes')

    declare_autostart_cmd = DeclareLaunchArgument(
        'autostart', default_value='true',
        description='Automatically startup the nav2 stack')

    declare_use_composition_cmd = DeclareLaunchArgument(
        'use_composition', default_value='False',
        description='Use composed bringup if True')

    declare_container_name_cmd = DeclareLaunchArgument(
        'container_name', default_value='nav2_container',
        description='the name of conatiner that nodes will load in if use composition')

    declare_use_respawn_cmd = DeclareLaunchArgument(
        'use_respawn', default_value='True',
        description='Whether to respawn if a node crashes. Applied when composition is disabled.')

    declare_log_level_cmd = DeclareLaunchArgument(
        'log_level', default_value='warn',
        description='log level')

    declare_delay_cmd = DeclareLaunchArgument(
        'delay_after_sim', default_value='10.0',
        description='Seconds to wait after simulation starts before launching the rest'
    )

    declare_use_rviz_cmd = DeclareLaunchArgument(
        'use_rviz', default_value='true',
        description='Whether to start RViz'
    )
    declare_start_sim_cmd = DeclareLaunchArgument(
        'start_sim', default_value='false',
        description='Whether to start simulation first (default: false)'
    )

    # Set env var for logging
    stdout_linebuf_envvar = SetEnvironmentVariable(
        'RCUTILS_LOGGING_BUFFERED_STREAM', '1')

    # ========================================================================
    # 2. Nav2 参数配置 (虽然不启动Nav2，保留这部分代码以免报错)
    # ========================================================================
    lifecycle_nodes = ['map_server', 'controller_server', 'planner_server', 'bt_navigator'] # 简化列表
    remappings = [('/tf', 'tf'), ('/tf_static', 'tf_static')]
    param_substitutions = {'use_sim_time': use_sim_time, 'autostart': autostart}

    configured_params = ParameterFile(
        RewrittenYaml(
            source_file=elevation_nav_params,
            root_key=namespace,
            param_rewrites=param_substitutions,
            convert_types=True),
        allow_substs=True)

    # ========================================================================
    # 3. 定义 Nav2 节点组 (这部分定义保留，但在后面不添加到 launch 中)
    # ========================================================================
    load_nodes = GroupAction(
        condition=IfCondition(PythonExpression(['not ', use_composition])),
        actions=[
            Node(package='nav2_map_server', executable='map_server', output='screen', parameters=[configured_params]),
            Node(package='nav2_controller', executable='controller_server', output='screen', parameters=[configured_params]),
            Node(package='nav2_planner', executable='planner_server', output='screen', parameters=[configured_params]),
            Node(package='nav2_bt_navigator', executable='bt_navigator', output='screen', parameters=[configured_params]),
            Node(package='nav2_lifecycle_manager', executable='lifecycle_manager', output='screen', parameters=[{'use_sim_time': use_sim_time}, {'autostart': autostart}, {'node_names': lifecycle_nodes}]),
        ]
    )
    
    load_composable_nodes = LoadComposableNodes(
        condition=IfCondition(use_composition),
        target_container=container_name_full,
        composable_node_descriptions=[] # 简化
    )

    # ========================================================================
    # 4. 其他功能包 (Terrain Analysis & Elevation Mapping & RViz)
    # ========================================================================
    # 4.1 Terrain Analysis (CPU based) - 这是你原本就有的
    start_terrain_analysis = IncludeLaunchDescription(
        FrontendLaunchDescriptionSource(os.path.join(
        get_package_share_directory('terrain_analysis'), 'launch', 'terrain_analysis.launch')
        )
    )

    # 4.2 Elevation Mapping Cupy (GPU based) 【核心修改：添加此节点】
    elevation_mapping_param_file = os.path.join(
        bringup_dir,
        'params',
        'core_param.yaml'
    )

    start_elevation_mapping = Node(
        package='elevation_mapping_cupy',
        executable='elevation_mapping_node',
        name='elevation_mapping',
        output='screen',
        parameters=[
            elevation_mapping_param_file,
            {'use_sim_time': use_sim_time} # 确保它使用仿真时间
        ]
    )

    # 4.3 RViz
    rviz_config_file = os.path.join(bringup_dir, 'rviz', 'nav2_default_view.rviz')
    start_rviz = Node(
        condition=IfCondition(use_rviz),
        package='rviz2',
        executable='rviz2',
        arguments=['-d', rviz_config_file],
        output='screen'
    )

    # ========================================================================
    # 5. 仿真与重定位
    # ========================================================================
    # (removed optional pangolin_simulation startup)

    # 5.2 启动重定位
    relocalization_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_dir, 'launch', 'relocalization.launch.py')
        ),
        launch_arguments={'use_rviz': 'false'}.items()
    )

    # ========================================================================
    # 6. 启动时序逻辑 (Launch Sequence)
    # ========================================================================
    
    # 【核心修改】：在这里把 Nav2 的节点去掉，只保留感知和可视化
    perception_and_viz_group = GroupAction(
        actions=[
            # load_nodes,              # <--- 注释掉：不启动 Nav2 节点
            # load_composable_nodes,   # <--- 注释掉：不启动 Composable Nodes
            start_terrain_analysis,    # 保留：原有的地形分析
            start_elevation_mapping,   # 新增：Elevation Mapping 节点
            start_rviz                 # 保留：RViz
        ]
    )

    # 逻辑：重定位启动后，等待 8 秒，然后启动感知和可视化组
    delayed_perception = TimerAction(
        period=8.0, 
        actions=[perception_and_viz_group]
    )

    # 逻辑：将 重定位 和 (延时后的感知) 打包
    bringup_logic = GroupAction(
        actions=[
            relocalization_launch,
            delayed_perception
        ]
    )

    # 逻辑：仿真启动后，等待 delay_after_sim 秒，再执行 bringup_logic
    overall_delayed_start = TimerAction(
        period=delay_after_sim,
        actions=[bringup_logic],
        condition=IfCondition(start_sim)
    )

    # 不启动仿真时，直接（轻微延迟）启动重定位 -> 感知 -> RViz
    immediate_start_no_sim = TimerAction(
        period=0.5,
        actions=[bringup_logic],
        condition=IfCondition(PythonExpression(["'", start_sim, "' == 'false'"]))
    )

    # ========================================================================
    # 7. Final Launch Description
    # ========================================================================
    ld = LaunchDescription()

    # Environment
    ld.add_action(stdout_linebuf_envvar)

    # Arguments
    ld.add_action(declare_namespace_cmd)
    ld.add_action(declare_use_sim_time_cmd)
    ld.add_action(declare_params_file_cmd)
    ld.add_action(declare_autostart_cmd)
    ld.add_action(declare_use_composition_cmd)
    ld.add_action(declare_container_name_cmd)
    ld.add_action(declare_use_respawn_cmd)
    ld.add_action(declare_log_level_cmd)
    ld.add_action(declare_delay_cmd)
    ld.add_action(declare_use_rviz_cmd)
    ld.add_action(declare_start_sim_cmd)

    # Actions
    ld.add_action(overall_delayed_start)  # 2a. 仿真启用：延时后启动重定位 -> 感知 -> RViz
    ld.add_action(immediate_start_no_sim) # 2b. 仿真关闭：直接启动重定位 -> 感知 -> RViz

    return ld