# Copyright (c) 2018 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

from ament_index_python.packages import get_package_share_directory
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction, ExecuteProcess
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, GroupAction,
                            IncludeLaunchDescription, SetEnvironmentVariable)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource, FrontendLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from launch_ros.actions import PushRosNamespace
from nav2_common.launch import RewrittenYaml


def generate_launch_description():
    # Get the launch directory
    bringup_dir = get_package_share_directory('r2_bringup')
    use_sim_time = LaunchConfiguration('use_sim_time')
    use_pointcloud_to_scan = LaunchConfiguration('use_pointcloud_to_scan')

    # Accept use_sim_time from parent and pass it through
    declare_use_sim_time = DeclareLaunchArgument(
        'use_sim_time', default_value='false',
        description='Use simulation time for included launches'
    )
    declare_use_pc2scan = DeclareLaunchArgument(
        'use_pointcloud_to_scan', default_value='true',
        description='Enable PointCloud2->LaserScan converter if the package is installed'
    )
    
    start_relocalization = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(
            bringup_dir,'launch','relocalization.launch.py'
            )
        )
    )
    
    start_navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(
            bringup_dir,'launch','navigation.launch.py'
            )
        )
    )


    # PointCloud2 -> LaserScan converter (to feed AMCL /scan)
    start_pointcloud_to_scan = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(
            bringup_dir,'launch','pointcloud_to_scan.launch.py'
        )),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'cloud_in': '/livox/lidar/pointcloud',
            'target_frame': 'base_link',
            'raw_scan_topic': '/raw_scan',
            'output_scan_topic': '/scan',
        }.items(),
        condition=IfCondition(use_pointcloud_to_scan)
    )

    # Delay relocalization slightly so pointcloud->scan can start first
    delayed_start_relocalization = TimerAction(
        period=1.0,
        actions=[
            start_relocalization
        ]
    )

    delayed_start_navigation = TimerAction(
        period=15.0,
        actions=[
            start_navigation
        ]
    )
    
    ld = LaunchDescription()

    ld.add_action(declare_use_sim_time)
    ld.add_action(declare_use_pc2scan)

    # Start pointcloud->scan first so AMCL can consume /scan
    ld.add_action(start_pointcloud_to_scan)
    ld.add_action(delayed_start_relocalization)
    ld.add_action(delayed_start_navigation)
    return ld
