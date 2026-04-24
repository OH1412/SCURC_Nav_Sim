#!/usr/bin/env python3
# Copyright (c) 2026
# Launch Livox MID360 driver first, then start the all-in-one bringup.

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction, SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression


def generate_launch_description():
    # Common launch args
    use_sim_time = LaunchConfiguration('use_sim_time')

    declare_use_sim_time = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='Use simulation time')

    # Buffer Python stdout for cleaner logs
    stdout_linebuf_envvar = SetEnvironmentVariable(
        'RCUTILS_LOGGING_BUFFERED_STREAM', '1')


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
        candidates.append(os.path.join(livox_share, 'launch_ROS2', 'rviz_MID360_launch.py'))
        # Standard launch folder
        candidates.append(os.path.join(livox_share, 'launch', 'msg_MID360_launch.py'))
        candidates.append(os.path.join(livox_share, 'launch', 'rviz_MID360_launch.py'))


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
            )
        )
    except Exception:
        start_serial_driver = None

    # 2) Our bringup (relocalization + navigation) - inlined from bringup_all_in_one
    r2_share = get_package_share_directory('leg_bringup')

    start_relocalization = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(r2_share, 'launch', 'relocalization.launch.py')),
        launch_arguments={'use_sim_time': use_sim_time}.items(),
    )

    start_navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(r2_share, 'launch', 'navigation.launch.py')),
        launch_arguments={'use_sim_time': use_sim_time}.items(),
    )

    # Delay relocalization by 5s, and navigation further by 15s (total 20s)
    delayed_start_relocalization = TimerAction(
        period=5.0,
        actions=[start_relocalization]
    )

    delayed_start_navigation = TimerAction(
        period=20.0,
        actions=[start_navigation]
    )

    ld = LaunchDescription()

    ld.add_action(stdout_linebuf_envvar)
    ld.add_action(declare_use_sim_time)

    # (removed optional pangolin_simulation startup)
    # Start Livox driver immediately
    ld.add_action(start_livox)
    # Start serial driver (if available)
    if start_serial_driver is not None:
        ld.add_action(start_serial_driver)
    # Start bringup after a short delay: relocalization then navigation
    ld.add_action(delayed_start_relocalization)
    ld.add_action(delayed_start_navigation)

    return ld
