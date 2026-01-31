import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
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

    # ========================================================================
    # 2. 路径定义
    # ========================================================================
    bringup_dir = get_package_share_directory('r2_bringup')
    fast_livo_dir = get_package_share_directory("fast_livo")

    # 地图文件路径
    pcd_map_path = os.path.join(bringup_dir, 'maps', 'test.pcd')
    yaml_map_path = os.path.join(bringup_dir, 'maps', 'test_map.yaml')

    # 配置文件路径
    config_path = os.path.join(bringup_dir, 'params')
    fast_livo_config_dir = os.path.join(fast_livo_dir, "config")
    
    amcl_config_path = os.path.join(config_path, 'amcl_params.yaml')
    fast_livo_config = os.path.join(config_path, 'avia_relocation.yaml')
    camera_config = os.path.join(fast_livo_config_dir, "camera_MARS_LVIG.yaml")
    rviz_config = os.path.join(bringup_dir, 'rviz', 'loam_livox.rviz')

    # 通用重映射 (TF)
    tf_remappings = [('/tf', 'tf'), ('/tf_static', 'tf_static')]

    # ========================================================================
    # 3. 节点定义
    # ========================================================================

    # ICP Relocalization (初始定位)
    icp_node = Node(
        package='icp_relocalization',
        executable='icp_node',
        name='icp_node',
        output='screen',
        remappings=[('icp_result', '/initialpose')],
        parameters=[
            {'use_sim_time': False},
            {'initial_x': 0.0},
            {'initial_y': 0.0},
            {'initial_z': 0.0},
            {'initial_a': 0.0},
            {'map_voxel_leaf_size': 0.1},
            {'cloud_voxel_leaf_size': 0.1},
            {'map_frame_id': 'map'},
            {'solver_max_iter': 75},
            {'map_path': pcd_map_path},
            {'fitness_score_thre': 0.2},
        ],
    )

    # Fast-Livo (里程计)
    fast_livo_node = Node(
        package='fast_livo',
        executable='fastlivo_mapping',
        parameters=[
            fast_livo_config,
            camera_config,
            {'use_sim_time': False}
        ],
        output='screen',
        arguments=['--ros-args', '--log-level', 'warn'],
        remappings=[('/aft_mapped_to_init', '/state_estimation')],
        condition=IfCondition(use_fast_livo)
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
    amcl_node = Node(
        package='nav2_amcl',
        executable='amcl',
        name='amcl',
        output='screen',
        parameters=[amcl_config_path],
        remappings=tf_remappings
    )

    # Lifecycle Manager
    lifecycle_manager_node = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_localization',
        output='screen',
        parameters=[{
            'use_sim_time': False,
            'autostart': True,
            'node_names': ['map_server', 'amcl']
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

    # 1. Nav2 定位栈 (Map Server + AMCL + Lifecycle Manager)
    ld.add_action(map_server_node)
    ld.add_action(amcl_node)
    ld.add_action(lifecycle_manager_node)

    # 2. 延迟启动 Fast-Livo
    ld.add_action(TimerAction(period=1.0, actions=[fast_livo_node]))

    # 3. 延迟启动 ICP
    ld.add_action(TimerAction(period=2.0, actions=[icp_node]))

    # 4. RViz
    ld.add_action(rviz_node)

    return ld