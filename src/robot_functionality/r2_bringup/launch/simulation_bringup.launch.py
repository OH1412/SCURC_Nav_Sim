# r2_bringup/launch/simulation_bringup.launch.py
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression


def generate_launch_description():
    # ----- Arguments -----
    mode = LaunchConfiguration('mode')                 # 'nav' or 'mapping'
    delay_after_sim = LaunchConfiguration('delay_after_sim')  # seconds (string -> float)
    use_rviz = LaunchConfiguration('use_rviz')         # only effective if child launch supports it
    start_sim = LaunchConfiguration('start_sim')

    declare_mode = DeclareLaunchArgument(
        'mode', default_value='nav',
        description="Run mode: 'nav' (navigation) or 'map' (mapping)"
    )
    declare_delay = DeclareLaunchArgument(
        'delay_after_sim', default_value='10.0',
        description='Seconds to wait after simulation starts before launching the rest'
    )
    declare_use_rviz = DeclareLaunchArgument(
        'use_rviz', default_value='true',
        description='Whether to start RViz in child launch files (if supported there)'
    )
    declare_start_sim = DeclareLaunchArgument(
        'start_sim', default_value='false',
        description='Whether to start simulation (default: false)'
    )

    # ----- Paths -----
    sim_share = get_package_share_directory('pangolin_simulation')
    bringup_share = get_package_share_directory('r2_bringup')

    # 1) 启动仿真
    sim_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(sim_share, 'launch', 'pangolin_simulation.launch.py')
        ),
        condition=IfCondition(start_sim)
        # 如需要，可在此处通过 launch_arguments 传入仿真额外参数
    )

    # 2) 重定位&导航 / 建图
    nav_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_share, 'launch', 'bringup_in_real.launch.py')
        ),
        launch_arguments={'use_rviz': use_rviz}.items()
    )

    mapping_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_share, 'launch', 'mapping.launch.py')
        ),
        launch_arguments={'use_rviz': use_rviz}.items()
    )

    # ---- 修正后的条件判断（给 mode 加引号参与比较）----
    is_nav = IfCondition(PythonExpression(["'", mode, "'", " == 'nav'"]))
    is_mapping = IfCondition(PythonExpression(["'", mode, "'", " == 'map'"]))

    delayed_nav = TimerAction(
        period=delay_after_sim,
        actions=[nav_launch],
        condition=IfCondition(PythonExpression(["'", start_sim, "' == 'true' and '", mode, "' == 'nav' "]))
    )

    delayed_mapping = TimerAction(
        period=delay_after_sim,
        actions=[mapping_launch],
        condition=IfCondition(PythonExpression(["'", start_sim, "' == 'true' and '", mode, "' == 'map' "]))
    )

    # 若不启动仿真，则立即启动对应模式（略微延迟 0.5s）
    start_nav_no_sim = TimerAction(
        period=0.5,
        actions=[nav_launch],
        condition=IfCondition(PythonExpression(["'", start_sim, "' == 'false' and '", mode, "' == 'nav' "]))
    )
    start_mapping_no_sim = TimerAction(
        period=0.5,
        actions=[mapping_launch],
        condition=IfCondition(PythonExpression(["'", start_sim, "' == 'false' and '", mode, "' == 'map' "]))
    )

    ld = LaunchDescription()
    ld.add_action(declare_mode)
    ld.add_action(declare_delay)
    ld.add_action(declare_use_rviz)
    ld.add_action(declare_start_sim)

    ld.add_action(sim_launch)          # 可选：先起仿真
    ld.add_action(delayed_nav)         # 仿真模式：等一会再起导航或建图
    ld.add_action(delayed_mapping)
    ld.add_action(start_nav_no_sim)    # 非仿真模式：直接起导航
    ld.add_action(start_mapping_no_sim)# 非仿真模式：直接起建图

    return ld
