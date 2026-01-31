# fly_step_mission/launch/fly_step_bt_only.launch.py
# 单独启动行为树节点
# 
# 使用前提：仿真和导航系统已经启动并准备好
# 使用方法：ros2 launch fly_step_mission fly_step_bt_only.launch.py
#
# 可选参数：
#   bt_xml_file: 指定行为树 XML 文件路径
#   main_waypoints: 主航点列表，如 "[-1,2]"

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    # ----- Package Path -----
    fly_step_share = get_package_share_directory('fly_step_mission')
    
    # ----- Arguments -----
    bt_xml_file = LaunchConfiguration('bt_xml_file')

    waypoints_file = LaunchConfiguration('waypoints_file')
    
    declare_bt_xml = DeclareLaunchArgument(
        'bt_xml_file',
        default_value=os.path.join(fly_step_share, 'behavior_trees', 'dynamic_waypoint_mission.xml'),
        description='Path to the behavior tree XML file'
    )

    declare_waypoints = DeclareLaunchArgument(
        'waypoints_file',
        default_value=os.path.join(fly_step_share, 'config', 'waypoints.yaml'),
        description='Path to the waypoints YAML file'
    )

    # ----- Log Info -----
    log_start = LogInfo(
        msg="\n" + "="*60 + "\n" +
            "正在启动行为树节点...\n" +
            "确保以下条件已满足：\n" +
            "  1. ICP 定位已完成\n" +
            "  2. Nav2 节点已激活\n" +
            "  3. TF 树正常（map -> odom -> base_link）\n" +
            "="*60 + "\n"
    )

    # ----- Behavior Tree Node -----
    fly_step_bt_node = Node(
        package='fly_step_mission',
        executable='fly_step_bt_node',
        name='fly_step_bt_node',
        output='screen',
        parameters=[{
            'bt_xml_file': bt_xml_file,
            'use_sim_time': False,
            'wait_for_nav2_timeout': 60.0,
            'waypoints_file': waypoints_file
        }]
    )

    # ===== Build Launch Description =====
    ld = LaunchDescription()
    
    ld.add_action(declare_bt_xml)
    ld.add_action(declare_waypoints)
    ld.add_action(log_start)
    ld.add_action(fly_step_bt_node)

    return ld
