# import os

# from ament_index_python.packages import get_package_share_directory
# from launch import LaunchDescription
# from launch.actions import (
#     DeclareLaunchArgument, IncludeLaunchDescription, TimerAction,
#     GroupAction  # 新增：用于按顺序启动高度发布+控制
# )
# from launch.conditions import IfCondition
# from launch.launch_description_sources import PythonLaunchDescriptionSource
# from launch.substitutions import LaunchConfiguration, PythonExpression


# def generate_launch_description():
#     # ----- Arguments -----
#     mode = LaunchConfiguration('mode')                 # 'nav' or 'mapping'
#     delay_after_sim = LaunchConfiguration('delay_after_sim')  # 仿真启动后延迟时间（默认10秒）
#     use_rviz = LaunchConfiguration('use_rviz')         # 是否启动RViz
#     robot_model_name = LaunchConfiguration('robot_model_name')  # 新增：机器人模型名参数

#     declare_mode = DeclareLaunchArgument(
#         'mode', default_value='nav',
#         description="Run mode: 'nav' (navigation) or 'mapping' (mapping)"
#     )
#     declare_delay = DeclareLaunchArgument(
#         'delay_after_sim', default_value='10.0',
#         description='Seconds to wait after simulation starts before launching the rest'
#     )
#     declare_use_rviz = DeclareLaunchArgument(
#         'use_rviz', default_value='true',
#         description='Whether to start RViz in child launch files (if supported there)'
#     )
#     # 新增：声明机器人模型名参数（可外部传参，默认robot）
#     declare_robot_model = DeclareLaunchArgument(
#         'robot_model_name', default_value='robot',
#         description='Name of the robot model in Gazebo'
#     )

#     # ----- Paths -----
#     sim_share = get_package_share_directory('pangolin_simulation')
#     bringup_share = get_package_share_directory('r2_bringup')
#     # 修正：获取height_publish包的路径（关键！原路径错误）
#     # height_publish_share = get_package_share_directory('height_publish')

#     # 1) 启动仿真（核心基础，最先启动）
#     sim_launch = IncludeLaunchDescription(
#         PythonLaunchDescriptionSource(
#             os.path.join(sim_share, 'launch', 'pangolin_simulation.launch.py')
#         )
#     )

#     # 2) 高度发布节点（依赖仿真，需延迟）
#     sim_height_publish = IncludeLaunchDescription(  # 修正变量名拼写
#         PythonLaunchDescriptionSource(
#             # 修正路径：指向height_publish包的launch文件
#             os.path.join(bringup_share, 'launch', 'height_publish.launch.py')
#         ),
#         launch_arguments={
#             "robot_model_name": robot_model_name,
#             # 若height_publish.launch.py有其他参数可在此传递
#         }.items()
#     )

#     # 3) 高度控制节点（依赖高度发布节点，需在其之后启动）
#     start_control_height = IncludeLaunchDescription(
#         PythonLaunchDescriptionSource(
#             os.path.join(bringup_share, "launch", "height_control.launch.py")
#         )
#     )

#     # 4) 导航 / 建图（依赖仿真+高度节点，最后启动）
#     nav_launch = IncludeLaunchDescription(
#         PythonLaunchDescriptionSource(
#             os.path.join(bringup_share, 'launch', 'bringup_all_in_one.launch.py')
#         ),
#         launch_arguments={'use_rviz': use_rviz}.items()
#     )

#     mapping_launch = IncludeLaunchDescription(
#         PythonLaunchDescriptionSource(
#             os.path.join(bringup_share, 'launch', 'mapping.launch.py')
#         ),
#         launch_arguments={'use_rviz': use_rviz}.items()
#     )

#     # ---- 条件判断（修正mode引号问题）----
#     is_nav = IfCondition(PythonExpression(["'", mode, "'", " == 'nav'"]))
#     is_mapping = IfCondition(PythonExpression(["'", mode, "'", " == 'mapping'"]))

#     # ---- 核心：调整延迟逻辑和启动顺序 ----
#     # 步骤1：仿真启动后，先延迟（复用delay_after_sim）启动高度发布节点
#     delayed_height_publish = TimerAction(
#         period=delay_after_sim,  # 等仿真加载完成（默认10秒）
#         actions=[sim_height_publish]
#     )

#     # 步骤2：高度发布节点启动后，再延迟1秒启动高度控制节点（确保话题已发布）
#     delayed_control_height = TimerAction(
#         period=PythonExpression([delay_after_sim, " + 1.0"]),  # 比高度发布晚1秒
#         actions=[start_control_height]
#     )

#     # 步骤3：导航/建图延迟与高度控制节点同步（或稍晚）
#     delayed_nav = TimerAction(
#         period=PythonExpression([delay_after_sim, " + 2.0"]),  # 比高度控制晚1秒
#         actions=[nav_launch],
#         condition=is_nav
#     )

#     delayed_mapping = TimerAction(
#         period=PythonExpression([delay_after_sim, " + 2.0"]),
#         actions=[mapping_launch],
#         condition=is_mapping
#     )

#     # ----- 组装LaunchDescription -----
#     ld = LaunchDescription()
#     # 先声明所有参数
#     ld.add_action(declare_mode)
#     ld.add_action(declare_delay)
#     ld.add_action(declare_use_rviz)
#     ld.add_action(declare_robot_model)  # 新增：声明机器人模型名参数

#     # 启动顺序：仿真 → 延迟 → 高度发布 → 延迟1秒 → 高度控制 → 延迟1秒 → 导航/建图
#     ld.add_action(sim_launch)                # 第一步：启动仿真
#     # ld.add_action(delayed_height_publish)    # 第二步：延迟后启动高度发布
#     # ld.add_action(delayed_control_height)    # 第三步：高度发布后启动高度控制
#     ld.add_action(delayed_nav)               # 第四步：启动导航（nav模式）
#     ld.add_action(delayed_mapping)           # 第四步：启动建图（mapping模式）

#     return ld
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

    declare_mode = DeclareLaunchArgument(
        'mode', default_value='nav',
        description="Run mode: 'nav' (navigation) or 'mapping' (mapping)"
    )
    declare_delay = DeclareLaunchArgument(
        'delay_after_sim', default_value='10.0',
        description='Seconds to wait after simulation starts before launching the rest'
    )
    declare_use_rviz = DeclareLaunchArgument(
        'use_rviz', default_value='true',
        description='Whether to start RViz in child launch files (if supported there)'
    )

    # ----- Paths -----
    sim_share = get_package_share_directory('pangolin_simulation')
    bringup_share = get_package_share_directory('r2_bringup')
    kfs_share = get_package_share_directory('kfs_detection_nav')


    # 1) 启动仿真
    sim_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(sim_share, 'launch', 'pangolin_simulation.launch.py')
        )
        # 如需要，可在此处通过 launch_arguments 传入仿真额外参数
    )

    # 2) 重定位&导航 / 建图
    nav_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_share, 'launch', 'bringup_all_in_one.launch.py')
        ),
        launch_arguments={'use_rviz': use_rviz}.items()
    )

    mapping_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_share, 'launch', 'mapping.launch.py')
        ),
        launch_arguments={'use_rviz': use_rviz}.items()
    )
    # 3) 高度控制节点（依赖高度发布节点，需在其之后启动）
    control_height = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_share, "launch", "height_control.launch.py")
        )
    )
    # 4) KFS检测节点
    kfs_launch = IncludeLaunchDescription(
    PythonLaunchDescriptionSource(
        os.path.join(kfs_share, 'launch', 'kfs_detection.launch.py')
    )
)
    # ---- 修正后的条件判断（给 mode 加引号参与比较）----
    is_nav = IfCondition(PythonExpression(["'", mode, "'", " == 'nav'"]))
    is_mapping = IfCondition(PythonExpression(["'", mode, "'", " == 'mapping'"]))

    delayed_nav = TimerAction(
        period=delay_after_sim,
        actions=[nav_launch],
        condition=is_nav
    )

    delayed_mapping = TimerAction(
        period=delay_after_sim,
        actions=[mapping_launch],
        condition=is_mapping
    )

    ld = LaunchDescription()
    # ld.add_action(control_height)
    ld.add_action(declare_mode)
    ld.add_action(declare_delay)
    ld.add_action(declare_use_rviz)
 

    ld.add_action(sim_launch)          # 先起仿真
    # ld.add_action(kfs_launch)          # 起KFS检测
    ld.add_action(delayed_nav)         # 等一会再起导航或建图
    ld.add_action(delayed_mapping)

    return ld