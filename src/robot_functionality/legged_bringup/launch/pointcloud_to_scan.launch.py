#!/usr/bin/env python3

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')
    cloud_in = LaunchConfiguration('cloud_in', default='/livox/lidar/pointcloud')
    target_frame = LaunchConfiguration('target_frame', default='base_link')
    raw_scan_topic = LaunchConfiguration('raw_scan_topic', default='/raw_scan')
    output_scan_topic = LaunchConfiguration('output_scan_topic', default='/scan')

    declare_use_sim_time = DeclareLaunchArgument(
        'use_sim_time', default_value='false', description='Use simulation time')

    declare_cloud_in = DeclareLaunchArgument(
        'cloud_in', default_value='/livox/lidar/pointcloud',
        description='Input PointCloud2 topic to convert to LaserScan')

    declare_target_frame = DeclareLaunchArgument(
        'target_frame', default_value='base_link',
        description='Target TF frame for LaserScan projection')

    declare_raw_scan_topic = DeclareLaunchArgument(
        'raw_scan_topic', default_value='/raw_scan',
        description='Intermediate LaserScan topic before filtering')

    declare_output_scan_topic = DeclareLaunchArgument(
        'output_scan_topic', default_value='/scan',
        description='Final LaserScan topic after filtering')

    # PointCloud2 -> LaserScan
    pointcloud_to_laserscan_node = Node(
        package='pointcloud_to_laserscan',
        executable='pointcloud_to_laserscan_node',
        name='pointcloud_to_laserscan',
        remappings=[
            ('cloud_in', cloud_in),
            ('scan', raw_scan_topic),
        ],
        parameters=[{
            'use_sim_time': use_sim_time,
            'target_frame': target_frame,
            'transform_tolerance': 0.01,
            'min_height': -0.06,
            'max_height': 0.5,
            'angle_min': -3.14159,
            'angle_max': 3.14159,
            'angle_increment': 0.0087,
            'scan_time': 0.1,
            'range_min': 0.5,
            'range_max': 25.0,
            'use_inf': True,
            'inf_epsilon': 1.0,
        }],
        output='screen'
    )

    # LaserScan filter to produce final /scan
    scan_filter_node = Node(
        package='pangolin_simulation',
        executable='scan_filter_node.py',
        name='scan_filter',
        parameters=[{
            'use_sim_time': use_sim_time,
            'valid_ratio_threshold': 0.7,
            'input_topic': raw_scan_topic,
            'output_topic': output_scan_topic,
            'log_filtered': False,
        }],
        output='screen'
    )

    ld = LaunchDescription()
    ld.add_action(declare_use_sim_time)
    ld.add_action(declare_cloud_in)
    ld.add_action(declare_target_frame)
    ld.add_action(declare_raw_scan_topic)
    ld.add_action(declare_output_scan_topic)

    ld.add_action(pointcloud_to_laserscan_node)
    ld.add_action(scan_filter_node)

    return ld
