# leg_bringup/launch/simulation_bringup.launch.py
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
    use_sim_time = LaunchConfiguration('use_sim_time')
    use_rviz = LaunchConfiguration('use_rviz')         # only effective if child launch supports it

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
    declare_use_sim_time = DeclareLaunchArgument(
        'use_sim_time', default_value='true',
        description='Use simulation time in child launch files where supported'
    )

    # ----- Paths -----
    sim_share = get_package_share_directory('pangolin_simulation')
    bringup_share = get_package_share_directory('leg_bringup')

    # 1) 启动仿真
    sim_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(sim_share, 'launch', 'pangolin_simulation.launch.py')
        )
        # 如需要，可在此处通过 launch_arguments 传入仿真额外参数
    )

    # 2) 重定位&导航 / 建图
    relocalization_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_share, 'launch', 'relocalization.launch.py')
        ),
        launch_arguments={'use_sim_time': use_sim_time}.items()
    )

    navigation_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_share, 'launch', 'navigation.launch.py')
        ),
        launch_arguments={'use_sim_time': use_sim_time}.items()
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
        actions=[relocalization_launch, navigation_launch],
        condition=is_nav
    )

    delayed_mapping = TimerAction(
        period=delay_after_sim,
        actions=[mapping_launch],
        condition=is_mapping
    )

    ld = LaunchDescription()
    ld.add_action(declare_mode)
    ld.add_action(declare_delay)
    ld.add_action(declare_use_rviz)
    ld.add_action(declare_use_sim_time)

    ld.add_action(sim_launch)          # 先起仿真
    ld.add_action(delayed_nav)         # 等一会再起导航或建图
    ld.add_action(delayed_mapping)

    return ld