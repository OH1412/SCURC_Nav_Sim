# r2_bringup/launch/fly_step_simulation.launch.py
# 启动仿真环境 + 导航系统 + fly_step_mission 行为树
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
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
        'delay_bt', default_value='20.0',
        description='Seconds to wait after simulation starts before launching behavior tree'
    )
    declare_use_rviz = DeclareLaunchArgument(
        'use_rviz', default_value='true',
        description='Whether to start RViz'
    )
    declare_auto_start_bt = DeclareLaunchArgument(
        'auto_start_bt', default_value='true',
        description='Whether to automatically start the behavior tree'
    )

    # ----- Package Paths -----
    sim_share = get_package_share_directory('pangolin_simulation')
    bringup_share = get_package_share_directory('r2_bringup')
    fly_step_share = get_package_share_directory('fly_step_mission')

    # ----- Behavior Tree XML Path -----
    bt_xml_file = os.path.join(fly_step_share, 'behavior_trees', 'fly_step_mission.xml')

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
        }]
    )

    delayed_bt = TimerAction(
        period=delay_bt,
        actions=[fly_step_bt_node]
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
    ld.add_action(delayed_bt)           # 3. 再等待后启动行为树

    return ld
