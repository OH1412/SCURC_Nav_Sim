# r2_bringup/launch/dynamic_waypoint_mission.launch.py
# 启动仿真环境 + 导航系统，支持可选的KFS规划器XML控制
#
# 使用方法：
# 1. 启动仿真和导航：ros2 launch r2_bringup dynamic_waypoint_mission.launch.py
# 2. 等待 ICP 定位完成（看到 "ICP converged!!!"）和 Nav2 激活（看到 "Managed nodes are active"）
# 3. 手动启动行为树：ros2 launch r2_bringup start_waypoint_bt.launch.py
#    或者设置 auto_start_bt:=true 自动启动（需要较长延迟）
#
# 可选参数：
# - use_planner_xml:=true  # 使用KFS规划器修改的XML文件（默认）
# - use_planner_xml:=false # 使用原始的XML文件，不受规划器影响

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction, LogInfo, ExecuteProcess
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node


def generate_launch_description():
    # ----- Arguments -----
    delay_after_sim = LaunchConfiguration('delay_after_sim')
    delay_bt = LaunchConfiguration('delay_bt')
    delay_planner = LaunchConfiguration('delay_planner')
    use_rviz = LaunchConfiguration('use_rviz')
    auto_start_bt = LaunchConfiguration('auto_start_bt')
    use_planner_xml = LaunchConfiguration('use_planner_xml')
    start_sim = LaunchConfiguration('start_sim')

    declare_delay_sim = DeclareLaunchArgument(
        'delay_after_sim', default_value='10.0',
        description='Seconds to wait after simulation starts before launching navigation'
    )
    declare_delay_bt = DeclareLaunchArgument(
        'delay_bt', default_value='20.0',
        description='Seconds to wait after simulation starts before launching behavior tree (only used if auto_start_bt is true)'
    )
    declare_delay_planner = DeclareLaunchArgument(
        'delay_planner', default_value='14.0',
        description='Seconds to wait after simulation starts before launching kfs_planner (before BT starts)'
    )
    declare_use_rviz = DeclareLaunchArgument(
        'use_rviz', default_value='true',
        description='Whether to start RViz'
    )
    declare_auto_start_bt = DeclareLaunchArgument(
        'auto_start_bt', default_value='true',
        description='Whether to automatically start the behavior tree (default: true, start manually)'
    )
    declare_publish_offset = DeclareLaunchArgument(
        'publish_offset_before_bt', default_value='5.0',
        description='Seconds before BT start to run the KFSDecision publisher (default: 5.0)'
    )
    declare_use_planner_xml = DeclareLaunchArgument(
        'use_planner_xml', default_value='true',
        description='Whether to use the XML file modified by kfs_planner (true) or the original XML file (false)'
    )
    declare_start_sim = DeclareLaunchArgument(
        'start_sim', default_value='false',
        description='Whether to start simulation (default: false for real robot)'
    )

    # ----- Package Paths -----
    sim_share = get_package_share_directory('pangolin_simulation')
    bringup_share = get_package_share_directory('r2_bringup')
    fly_step_share = get_package_share_directory('fly_step_mission')

    # ----- Behavior Tree XML Path -----
    # 根据 use_planner_xml 参数选择XML文件
    # true: 使用可能被kfs_planner修改的XML文件
    # false: 使用原始的XML文件
    bt_xml_planner_modified = os.path.join(fly_step_share, 'behavior_trees', 'dynamic_waypoint_mission.xml')
    bt_xml_original = os.path.join(fly_step_share, 'behavior_trees', 'dynamic_waypoint_mission_original.xml')

    # 默认的 waypoints 文件（来自 fly_step_mission 包）
    waypoints_file = os.path.join(fly_step_share, 'config', 'waypoints.yaml')

    # ===== 1) 启动仿真环境 =====
    sim_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(sim_share, 'launch', 'pangolin_simulation.launch.py')
        ),
        condition=IfCondition(start_sim)
    )

    # ===== 2) 启动导航系统 (重定位 + Nav2) =====
    nav_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_share, 'launch', 'bringup_in_real.launch.py')
        ),
        launch_arguments={'use_rviz': use_rviz}.items()
    )

    delayed_nav_if_sim = TimerAction(
        period=delay_after_sim,
        actions=[nav_launch],
        condition=IfCondition(start_sim)
    )

    # 如果不启动仿真，则尽快启动导航（略微延迟0.5s以保证依赖准备）
    start_nav_if_no_sim = TimerAction(
        period=0.5,
        actions=[nav_launch],
        condition=IfCondition(PythonExpression(["'", start_sim, "' == 'false'"]))
    )

    # ===== 3) 启动 fly_step_mission 行为树节点（先启动BT以确保service可用） =====
    # 根据 use_planner_xml 参数选择XML文件路径
    bt_xml_file = PythonExpression([
        "'", bt_xml_planner_modified, "' if '", use_planner_xml, "' == 'true' else '", bt_xml_original, "'"
    ])

    fly_step_bt_node = Node(
        package='fly_step_mission',
        executable='fly_step_bt_node',
        name='fly_step_bt_node',
        output='screen',
        parameters=[{
            'bt_xml_file': bt_xml_file,
            'use_sim_time': False,
            'wait_for_nav2_timeout': 30.0,  # 等待 Nav2 action server 的超时时间
            'waypoints_file': waypoints_file
        }],
        condition=IfCondition(auto_start_bt)  # 只有当 auto_start_bt=true 时才启动
    )

    delayed_bt = TimerAction(
        period=delay_bt,
        actions=[fly_step_bt_node],
        condition=IfCondition(auto_start_bt)  # 只有当 auto_start_bt=true 时才延迟启动
    )
    # ===== 3.5) 启动 kfs_planner（在 BT 之后，确保BT service已可用） =====
    # 这里使用一个最小的 start_planner.launch.py 来包含实际的 kfs_planner 启动脚本
    start_planner = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_share, 'launch', 'start_planner.launch.py')
        )
    )

    delayed_planner = TimerAction(
        period=delay_planner,
        actions=[start_planner]
    )
    # ===== 4) (测试) 将发布器安排在 BT 启动之前的一段偏移时间触发，保证消息在路径生成之前到达
    # 这个脚本期望位于 r2_bringup/scripts/publish_kfs.py；优先使用安装路径，否则回退源码路径
    launch_dir = os.path.dirname(__file__)
    publish_script_src = os.path.abspath(os.path.join(launch_dir, '..', 'scripts', 'publish_kfs.py'))
    publish_script_installed = os.path.join(bringup_share, 'scripts', 'publish_kfs.py')
    if os.path.exists(publish_script_installed):
        publish_script = publish_script_installed
    else:
        publish_script = publish_script_src

    # 在 BT 启动前 publish_offset_before_bt 秒运行发布脚本
    pre_publish_period = PythonExpression([delay_bt, ' - ', LaunchConfiguration('publish_offset_before_bt')])

    pre_publish = TimerAction(
        period=pre_publish_period,
        actions=[
            ExecuteProcess(
                cmd=['python3', publish_script, '--timeout', '30', '--interval', '1.0'],
                output='screen'
            )
        ],
        condition=IfCondition(auto_start_bt)
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
    ld.add_action(declare_delay_planner)
    ld.add_action(declare_use_rviz)
    ld.add_action(declare_auto_start_bt)
    ld.add_action(declare_publish_offset)
    ld.add_action(declare_use_planner_xml)
    ld.add_action(declare_start_sim)

    # Launch actions
    ld.add_action(sim_launch)           # 1. 可选：启动仿真（仅当 start_sim=true）
    ld.add_action(delayed_nav_if_sim)   # 2a. 仿真启用：等待后启动导航
    ld.add_action(start_nav_if_no_sim)  # 2b. 仿真关闭：立即启动导航
    ld.add_action(pre_publish)          # 3. 可选：在 BT 启动前若干秒发布 KFSDecision（测试)
    ld.add_action(delayed_bt)           # 4. 可选：自动启动行为树
    ld.add_action(delayed_planner)      # 5. 启动 planner（应在 BT 之后）

    ld.add_action(log_manual_start)     # 6. 提示手动启动

    return ld
