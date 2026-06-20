import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, RegisterEventHandler, TimerAction
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration
from launch.conditions import IfCondition, UnlessCondition

def generate_launch_description():

    # ========================================================================
    # 1. Launch 参数配置
    # ========================================================================
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')
    use_fast_livo = LaunchConfiguration('use_fast_livo', default='true')
    use_respawn = LaunchConfiguration('use_respawn', default='true')
    log_level = LaunchConfiguration('log_level', default='WARN')

    # ========================================================================
    # 2. 路径定义
    # ========================================================================
    bringup_dir = get_package_share_directory('legged_bringup')
    fast_livo_dir = get_package_share_directory("fast_livo")

    # 地图文件路径
    pcd_map_path = os.path.join(bringup_dir, 'maps', 'test.pcd')
    yaml_map_path = os.path.join(bringup_dir, 'maps', 'test_map.yaml')

    # 配置文件路径
    config_path = os.path.join(bringup_dir, 'params')
    fast_livo_config_dir = os.path.join(fast_livo_dir, "config")
    
    amcl_config_path = os.path.join(config_path, 'amcl_params.yaml')
    fast_livo_config = os.path.join(fast_livo_config_dir, 'avia.yaml')
    camera_config = os.path.join(fast_livo_config_dir, "camera_MARS_LVIG.yaml")
    rviz_config = os.path.join(bringup_dir, 'rviz', 'loam_livox.rviz')

    # 通用重映射 (TF)
    tf_remappings = [('/tf', 'tf'), ('/tf_static', 'tf_static')]

    # ========================================================================
    # 3. 节点定义
    # ========================================================================

    # Global relocalization using relocalization package
    transform_publisher = Node(
        package='relocalization',
        executable='transform_publisher',
        name='transform_publisher',
        output='screen',
        parameters=[{'use_sim_time': False}],
    )

    teaser_gicp_node = Node(
        package='relocalization',
        executable='teaser_gicp_node',
        name='teaser_gicp_node',
        output='screen',
        parameters=[
            {'use_sim_time': False},
            {'map_path': pcd_map_path},
            {'map_frame_id': 'map'},
            {'pcl_type': 'livox'},
            {'map_voxel_leaf_size': 0.4},
            {'cloud_voxel_leaf_size': 0.4},
            {'gicp_map_voxel_leaf_size': 0.2},
            {'gicp_cloud_voxel_leaf_size': 0.1},
            {'fpfh_normal_radius': 0.8},
            {'fpfh_feature_radius': 1.2},
            {'noise_bound': 0.3},
            {'teaser_solver_max_iter': 100},
            {'rotation_gnc_factor': 1.4},
            {'teaser_inlier_threshold': 5},
            {'teaser_success_count': 3},
            {'gicp_solver_max_iter': 50},
            {'num_threads': 16},
            {'max_correspondence_distance': 5.0},
            {'fitness_score_thre': 0.2},
            {'converged_count_thre': 10},
            {'registration_type': 'VGICP'},
        ],
    )

    # Fast-Livo (里程计) using the working fast_livo mapping launch
    fast_livo_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(fast_livo_dir, 'launch', 'mapping_avia.launch.py')
        ),
        launch_arguments={
            'avia_params_file': fast_livo_config,
            'camera_params_file': camera_config,
            'log_level': 'WARN',
            'use_respawn': 'True',
            'use_rviz': 'False'
        }.items(),
        condition=IfCondition(use_fast_livo)
    )

    static_tf_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_dir, 'launch', 'static_tf.launch.py')
        )
    )

    # Nav2 Map Server
    map_server_node = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        respawn=True,
        respawn_delay=2.0,
        parameters=[{
            'use_sim_time': False,
            'yaml_filename': yaml_map_path
        }],
        arguments=['--ros-args', '--log-level', 'info'],
        remappings=tf_remappings
    )

    # Nav2 AMCL (概率定位) - 发布 map -> odom
    # amcl_node = Node(
    #     package='nav2_amcl',
    #     executable='amcl',
    #     name='amcl',
    #     output='screen',
    #     parameters=[amcl_config_path],
    #     remappings=tf_remappings
    # )

    # Lifecycle Manager
    lifecycle_manager_node = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_localization',
        output='screen',
        parameters=[{
            'use_sim_time': False,
            'autostart': True,
            'node_names': ['map_server']  # amcl temporarily disabled
        }]
    )

    # RViz
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', rviz_config, '--ros-args', '--log-level', 'rviz:=error'],
        output='screen'
    )

    # ========================================================================
    # 4. 启动逻辑
    # ========================================================================
    ld = LaunchDescription()

    # 声明参数
    ld.add_action(DeclareLaunchArgument(
        'use_sim_time', default_value='false',
        description='Use simulation (Gazebo) clock if false'))
    
    ld.add_action(DeclareLaunchArgument(
        'use_fast_livo', default_value='true',
        description='Use Fast-Livo for odometry if true'))

    ld.add_action(DeclareLaunchArgument(
        'use_respawn', default_value='true',
        description='Respawn fast_livo if it crashes'))

    ld.add_action(DeclareLaunchArgument(
        'log_level', default_value='WARN',
        description='Log level for fast_livo nodes'))

    # 1. Nav2 定位栈 (Map Server + Lifecycle Manager)  # AMCL temporarily disabled
    ld.add_action(map_server_node)
    # ld.add_action(amcl_node)
    ld.add_action(lifecycle_manager_node)

    # 2. 延迟启动 Fast-Livo
    ld.add_action(TimerAction(period=1.0, actions=[fast_livo_node]))

    # 3. 延迟启动全局重定位
    ld.add_action(transform_publisher)
    ld.add_action(TimerAction(period=2.0, actions=[teaser_gicp_node]))
    ld.add_action(RegisterEventHandler(
        OnProcessExit(
            target_action=teaser_gicp_node,
            on_exit=[static_tf_node]
        )
    ))

    # 4. RViz
    ld.add_action(rviz_node)

    return ld