#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#保存栅格地图的命令 ：ros2 run nav2_map_server map_saver_cli -t /projected_map -f ./robot_functionality/leg_bringup/maps/test_map（最后的参数为实际地图存放路径）
import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    
    # ========== 环境设置 ==========
    stdout_linebuf_envvar = SetEnvironmentVariable(
        'RCUTILS_LOGGING_BUFFERED_STREAM', '1'
    )
    
    # ========== 1. Livox 驱动路径 ==========
    livox_launch_path = os.path.join(
        os.path.dirname(__file__), 
        '/home/cd/Nav_dog/pre/estimations/dependencies_and_tools/FAST_LIVO2_relocation_revise/src/livox_ros_driver2/launch_ROS2/msg_MID360_launch.py'
    )
    
    if not os.path.exists(livox_launch_path):
        try:
            livox_share = get_package_share_directory('livox_ros_driver2')
            candidate = os.path.join(livox_share, 'launch_ROS2', 'msg_MID360_launch.py')
            if os.path.exists(candidate):
                livox_launch_path = candidate
        except Exception:
            pass
    
    start_livox = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(livox_launch_path),
    )
    
    # ========== 2. 调用 FAST-LIVO 建图 launch 文件 ==========
    fast_livo_share = get_package_share_directory('fast_livo')
    mapping_avia_launch = os.path.join(fast_livo_share, 'launch', 'mapping_avia.launch.py')
    
    if not os.path.exists(mapping_avia_launch):
        mapping_avia_launch = os.path.join(
            os.path.dirname(__file__), 
            'mapping_avia.launch.py'
        )
    
    start_fast_livo_mapping = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(mapping_avia_launch),
        launch_arguments={
            'use_rviz': 'false',  # 关闭 FAST-LIVO 自带的 RViz
        }.items(),
    )
    
    # ========== 3. 静态 TF 发布器（连接 map 和 camera_init） ==========
    tf_static = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        arguments=['0', '0', '0', '0', '0', '0', 'map', 'camera_init'],
        output='screen',
    )
    
    # ========== 4. OctoMap (3D→2D 地图转换) ==========
    start_octomap = Node(
    package="octomap_server",
    executable="octomap_server_node",
    name="octomap_server",
    parameters=[{
        "frame_id": "camera_init",
        "resolution": 0.05,
        
        # 点云接收范围（保持宽松）
        "pointcloud_min_z": -0.3,             # 低于雷达中心该值的点不要
        "pointcloud_max_z": 1.8,
        "filter_ground": False,               # 关键：关闭地面滤波（防止误判）
        
        # 传感器模型
        "sensor_model/max_range": 10.0,
        "sensor_model/hit": 0.8,              # 提高命中概率（让台阶更容易被标记）
        "sensor_model/miss": 0.35,            # 降低未命中概率
        "sensor_model/min": 0.12,
        "sensor_model/max": 0.97,
        
        # 地图发布
        "latch": True,
        "publish_occupancy_map": True,
        "publish_free_space": True,
        "occupancy_map_pub_period": 1.0,
        
        #  关键：投影范围（包含台阶高度）
        "occupancy_min_z": -0.3,              # 从台阶高度开始投影
        "occupancy_max_z": 1.8,               # 到天花板高度
        
        #  额外：体素滤波设置（可选）
        "pointcloud_filter_radius": 0.1,      # 点云滤波半径
        "pointcloud_filter_neighbors": 2,     # 最小邻居数
        
        #  额外：占据阈值（低于此值不显示为障碍）
        "occupancy_threshold": 0.3,           # 默认0.5，降低让矮障碍更容易显示
    }],
    remappings=[
        ("cloud_in", "/cloud_registered"),
       
    ],
    output="screen",
)
    
     # ========== 5. RViz2 配置文件路径 ==========
    rviz_config_file = "/home/cd/Nav_dog/pre/estimations/robot_functionality/leg_bringup/rviz/2d_map_display.rviz"
    
    start_rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        arguments=["-d", rviz_config_file],
        output="screen",
    )

    # ========== 6. 延时启动 ==========
    delayed_start_fast_livo = TimerAction(
        period=3.0,
        actions=[start_fast_livo_mapping]
    )
    
    delayed_start_octomap = TimerAction(
        period=12.0,
        actions=[start_octomap]
    )
    delayed_start_rviz = TimerAction(
        period=13.0,
        actions=[start_rviz]
    )

    
    
    # ========== 构建 LaunchDescription ==========
    ld = LaunchDescription()
    
    ld.add_action(stdout_linebuf_envvar)
    ld.add_action(start_livox)
    ld.add_action(tf_static)
    ld.add_action(delayed_start_fast_livo)
    ld.add_action(delayed_start_octomap)
    ld.add_action(delayed_start_rviz)
    
    return ld