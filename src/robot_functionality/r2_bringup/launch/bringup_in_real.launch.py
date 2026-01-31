#!/usr/bin/env python3
# Copyright (c) 2026
# Launch Livox MID360 driver first, then start the all-in-one bringup.

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction, SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    # Common launch args
    use_sim_time = LaunchConfiguration('use_sim_time')
    start_delay = LaunchConfiguration('start_delay')
    start_sim = LaunchConfiguration('start_sim')

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

    # Buffer Python stdout for cleaner logs
    stdout_linebuf_envvar = SetEnvironmentVariable(
        'RCUTILS_LOGGING_BUFFERED_STREAM', '1')

    # 0) Optional: start simulation
    try:
        sim_share = get_package_share_directory('pangolin_simulation')
        sim_launch = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(sim_share, 'launch', 'pangolin_simulation.launch.py')
            ),
            condition=IfCondition(start_sim)
        )
    except Exception:
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
            )
        )
    except Exception:
        start_serial_driver = None

    # 2) Our bringup (relocalization + navigation)
    r2_share = get_package_share_directory('r2_bringup')
    bringup_all_in_one_path = os.path.join(r2_share, 'launch', 'bringup_all_in_one.launch.py')
    start_bringup_all = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(bringup_all_in_one_path),
        # Forward use_sim_time to downstream if they consume it
        launch_arguments={'use_sim_time': use_sim_time}.items(),
    )

    delayed_bringup = TimerAction(
        period=start_delay,
        actions=[start_bringup_all]
    )

    ld = LaunchDescription()

    ld.add_action(stdout_linebuf_envvar)
    ld.add_action(declare_use_sim_time)
    ld.add_action(declare_start_delay)
    ld.add_action(declare_start_sim)

    # Optional: start simulation
    if sim_launch is not None:
        ld.add_action(sim_launch)
    # Start Livox driver immediately
    ld.add_action(start_livox)
    # Start serial driver (if available)
    if start_serial_driver is not None:
        ld.add_action(start_serial_driver)
    # Start bringup after a short delay
    ld.add_action(delayed_bringup)

    return ld
