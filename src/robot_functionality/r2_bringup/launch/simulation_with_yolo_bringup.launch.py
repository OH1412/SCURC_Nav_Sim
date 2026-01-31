#!/usr/bin/env python3

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch.conditions import IfCondition
from launch.substitutions import PythonExpression


def generate_launch_description():
    # Arguments
    delay_after_sim = LaunchConfiguration('delay_after_sim')  # seconds before starting YOLO
    delay_after_yolo = LaunchConfiguration('delay_after_yolo')  # seconds before starting KFS
    use_rviz = LaunchConfiguration('use_rviz')
    start_sim = LaunchConfiguration('start_sim')

    declare_delay_sim = DeclareLaunchArgument(
        'delay_after_sim', default_value='8.0',
        description='Seconds to wait after simulation before launching YOLO'
    )
    declare_delay_yolo = DeclareLaunchArgument(
        'delay_after_yolo', default_value='2.0',
        description='Seconds to wait after YOLO before launching KFS processing'
    )
    declare_use_rviz = DeclareLaunchArgument(
        'use_rviz', default_value='false',
        description='Whether to enable RViz in downstream launches'
    )
    declare_start_sim = DeclareLaunchArgument(
        'start_sim', default_value='false',
        description='Whether to start simulation (default: false)'
    )

    # Package share dirs
    r2_bringup_share = get_package_share_directory('r2_bringup')
    pangolin_sim_share = get_package_share_directory('pangolin_simulation')

    # YOLO package: assume package name 'yolov8_ros2' and launch file 'yolov8_launch.py'
    yolov8_share = get_package_share_directory('yolov8_ros2')

    # KFS detection package
    kfs_share = get_package_share_directory('kfs_detection_nav')

    # Include simulation_bringup (this will start Gazebo and spawn robot)
    sim_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(r2_bringup_share, 'launch', 'simulation_bringup.launch.py')
        ),
        condition=IfCondition(start_sim)
    )

    # Include yolov8 launch after a delay (so simulation is up first)
    yolov8_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(yolov8_share, 'launch', 'yolov8_launch.py')
        ),
        # pass log_level=error and node_output=log so when launched from this bringup
        # the YOLO nodes won't print their stdout to the parent terminal
        launch_arguments={'use_sim_time': 'false', 'log_level': 'info', 'node_output': 'log'}.items()
    )

    delayed_yolo = TimerAction(
        period=delay_after_sim,
        actions=[yolov8_launch]
    )

    # Include KFS detection launch (use the YOLO-integrated launch if available)
    # Prefer kfs_with_yolo_sim.launch.py if present
    kfs_launch_file = os.path.join(kfs_share, 'launch', 'kfs_with_yolo_sim.launch.py')
    if not os.path.exists(kfs_launch_file):
        kfs_launch_file = os.path.join(kfs_share, 'launch', 'kfs_detection.launch.py')

    kfs_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(kfs_launch_file),
        launch_arguments={'use_sim_time': 'false'}.items()
    )

    delayed_kfs = TimerAction(
        period=LaunchConfiguration('delay_after_sim'),
        actions=[TimerAction(period=delay_after_yolo, actions=[kfs_launch])]
    )

    ld = LaunchDescription()
    ld.add_action(declare_delay_sim)
    ld.add_action(declare_delay_yolo)
    ld.add_action(declare_use_rviz)
    ld.add_action(declare_start_sim)

    # order: start sim immediately, then yolov8 after delay_after_sim, then kfs after additional delay
    ld.add_action(sim_launch)
    ld.add_action(delayed_yolo)
    ld.add_action(delayed_kfs)

    return ld
