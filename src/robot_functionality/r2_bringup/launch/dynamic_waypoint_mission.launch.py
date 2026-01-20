# r2_bringup/launch/dynamic_waypoint_mission.launch.py
# 启动仿真环境 + 导航系统，行为树需要手动启动
# 
# 使用方法：
# 1. 启动仿真和导航：ros2 launch r2_bringup dynamic_waypoint_mission.py
# 2. 等待 ICP 定位完成（看到 "ICP converged!!!"）和 Nav2 激活（看到 "Managed nodes are active"）
# 3. 手动启动行为树：ros2 launch r2_bringup start_waypoint_bt.launch.py
#    或者设置 auto_start_bt:=true 自动启动（需要较长延迟）

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction, LogInfo
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node


def generate_launch_description():
    # ----- Arguments -----
    delay_after_sim = LaunchConfiguration('delay_after_sim')
    delay_bt = LaunchConfiguration('delay_bt')
    use_rviz = LaunchConfiguration('use_rviz')
    auto_start_bt = LaunchConfiguration('auto_start_bt')

    declare_delay_sim = DeclareLaunchArgument(
        'delay_after_sim', default_value='10.0',
        description='Seconds to wait after simulation starts before launching navigation'
    )
    declare_delay_bt = DeclareLaunchArgument(
        'delay_bt', default_value='90.0',
        description='Seconds to wait after simulation starts before launching behavior tree (only used if auto_start_bt is true)'
    )
    declare_use_rviz = DeclareLaunchArgument(
        'use_rviz', default_value='true',
        description='Whether to start RViz'
    )
    declare_auto_start_bt = DeclareLaunchArgument(
        'auto_start_bt', default_value='true',
        description='Whether to automatically start the behavior tree (default: true, start manually)'
    )

    # ----- Package Paths -----
    sim_share = get_package_share_directory('pangolin_simulation')
    bringup_share = get_package_share_directory('r2_bringup')
    fly_step_share = get_package_share_directory('fly_step_mission')

    # ----- Behavior Tree XML Path -----
    bt_xml_file = os.path.join(fly_step_share, 'behavior_trees', 'dynamic_waypoint_mission.xml')

    # ===== 1) 启动仿真环境 =====
    sim_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(sim_share, 'launch', 'pangolin_simulation.launch.py')
        )
    )

    # ===== 2) 启动导航系统 (重定位 + Nav2) =====
    nav_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_share, 'launch', 'bringup_all_in_one.launch.py')
        ),
        launch_arguments={'use_rviz': use_rviz}.items()
    )

    delayed_nav = TimerAction(
        period=delay_after_sim,
        actions=[nav_launch]
    )

    # ===== 3) 启动 fly_step_mission 行为树节点 =====
    fly_step_bt_node = Node(
        package='fly_step_mission',
        executable='fly_step_bt_node',
        name='fly_step_bt_node',
        output='screen',
        parameters=[{
            'bt_xml_file': bt_xml_file,
            'use_sim_time': True,
            'wait_for_nav2_timeout': 60.0  # 等待 Nav2 action server 的超时时间
        }],
        condition=IfCondition(auto_start_bt)  # 只有当 auto_start_bt=true 时才启动
    )

    delayed_bt = TimerAction(
        period=delay_bt,
        actions=[fly_step_bt_node],
        condition=IfCondition(auto_start_bt)  # 只有当 auto_start_bt=true 时才延迟启动
    )

    # 提示用户手动启动行为树（仅当 auto_start_bt=false 时显示）
    log_manual_start = LogInfo(
        msg="\n" + "="*60 + "\n" +
            "仿真和导航已启动！行为树未自动启动。\n" +
            "请等待以下条件满足后手动启动行为树：\n" +
            "  1. ICP 定位完成（看到 'ICP converged!!!'）\n" +
            "  2. Nav2 激活（看到 'Managed nodes are active'）\n" +
            "\n" +
            "手动启动行为树命令：\n" +
            "  ros2 launch fly_step_mission fly_step_bt_only.launch.py\n" +
            "="*60 + "\n",
        condition=IfCondition(PythonExpression(["'", auto_start_bt, "' == 'false'"]))
    )

    # ===== Build Launch Description =====
    ld = LaunchDescription()

    # Declare arguments
    ld.add_action(declare_delay_sim)
    ld.add_action(declare_delay_bt)
    ld.add_action(declare_use_rviz)
    ld.add_action(declare_auto_start_bt)

    # Launch actions
    ld.add_action(sim_launch)           # 1. 先启动仿真
    ld.add_action(delayed_nav)          # 2. 等待后启动导航
    ld.add_action(delayed_bt)           # 3. 可选：自动启动行为树
    ld.add_action(log_manual_start)     # 4. 提示手动启动

    return ld
