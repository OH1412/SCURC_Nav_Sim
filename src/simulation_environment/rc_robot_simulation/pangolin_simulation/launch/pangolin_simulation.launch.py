#!/usr/bin/env python3

import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory, get_package_share_path, get_package_prefix

from launch import LaunchDescription
from launch.substitutions import LaunchConfiguration, Command
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument, GroupAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch.conditions import LaunchConfigurationEquals
from launch.conditions import IfCondition
from launch.actions import ExecuteProcess, AppendEnvironmentVariable
from launch_ros.substitutions import FindPackageShare

from launch import LaunchDescription
from launch.substitutions import LaunchConfiguration, Command
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument, GroupAction, TimerAction

# Enum for world types
class WorldType:
    RoboconWithoutWall = 'RoboconWithoutWall'
    RoboconWithWall = 'RoboconWithWall'

def get_world_config(world_type):
    world_configs = {
        WorldType.RoboconWithoutWall: {
            'x': '4.7',
            'y': '-2.5',
            'z': '0.0',
            'roll':'0.0',
            'yaw': '0.0',
            'pitch': '0.0',
            'world_path': 'xzx_gazebo/robocon2026_map_foreset.world'
        },
        WorldType.RoboconWithWall: {
            'x': '4.7',
            'y': '-2.5',
            'z': '0.0',
            'roll':'0.0',
            'yaw': '0.0',  # 90 degrees in radians 3.1416
            'pitch': '0.0',
            'world_path': 'xzx_gazebo/robocon2026_map_foreset_wall.world'
        }
    }
    return world_configs.get(world_type, None)

def generate_launch_description():
    # Get the launch directory
    bringup_dir = get_package_share_directory('pangolin_simulation')
    pkg_gazebo_ros = get_package_share_directory('gazebo_ros')

    # Specify xacro path
    urdf_dir = get_package_share_path('pangolin_simulation') / 'urdf' / 'simulation_waking_robot.xacro'

    # Create the launch configuration variables
    use_sim_time = LaunchConfiguration('use_sim_time')
    use_rviz = LaunchConfiguration('rviz', default='true')
    use_joint_state_publisher = LaunchConfiguration('use_joint_state_publisher', default='false')

    # Set Gazebo plugin path
    append_enviroment = AppendEnvironmentVariable(
        'GAZEBO_PLUGIN_PATH',
        os.path.join(os.path.join(get_package_share_directory('pangolin_simulation'), 'meshes', 'obstacles', 'obstacle_plugin', 'lib'))
    )

    # 设置robot的网格路径
    mesh_path = ""

    # 在当前 Python 进程环境中确保包含 mesh_path（影响当前进程）
    if 'GAZEBO_MODEL_PATH' in os.environ:
        os.environ['GAZEBO_MODEL_PATH'] += os.pathsep + mesh_path
    else:
        os.environ['GAZEBO_MODEL_PATH'] = "/usr/share/gazebo-11/models" + os.pathsep + mesh_path

    # 通过 Launch 的 AppendEnvironmentVariable 确保子进程（gzserver/gzclient）也能继承该路径
    append_gazebo_model_path = AppendEnvironmentVariable(
        name='GAZEBO_MODEL_PATH',
        value=':' + mesh_path
    )

    declare_use_sim_time_cmd = DeclareLaunchArgument(
        'use_sim_time',
        default_value='True',
        description='Use simulation (Gazebo) clock if true'
    )

    declare_world_cmd = DeclareLaunchArgument(
        'world',
        default_value=WorldType.RoboconWithWall,
        description='Choose <RoboconWithWall> or <RoboconWithoutWall> world'
    )

    declare_rviz_config_file_cmd = DeclareLaunchArgument(
        'rviz_config_file',
        default_value=os.path.join(bringup_dir, 'rviz', 'rviz2.rviz'),
        description='Full path to the RVIZ config file to use'
    )

    declare_use_joint_state_publisher = DeclareLaunchArgument(
        'use_joint_state_publisher',
        default_value='false',
        description='Whether to start joint_state_publisher (default false). Set true only if you need it (e.g. no hardware/plugin publishing /joint_states).'
    )

    # Specify the actions
    gazebo_client_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg_gazebo_ros, 'launch', 'gzclient.launch.py')),
        launch_arguments={'gui': 'true'}.items()
    )


    start_joint_state_publisher_cmd = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        name='joint_state_publisher',
        parameters=[{
            'use_sim_time': use_sim_time,
            'robot_description': ParameterValue(
                Command(['xacro ', str(urdf_dir)]), value_type=str
            ),
            # 'robot_description': robot_description_content  # 直接传入 URDF 内容
        }],
        output='screen'
    )

    start_robot_state_publisher_cmd = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        parameters=[{
            'use_sim_time': use_sim_time,
            'robot_description': ParameterValue(
                Command(['xacro ', str(urdf_dir)]), value_type=str
            ),
        }],
        output='screen'
    )

    start_rviz_cmd = Node(
        condition=IfCondition(use_rviz),
        package='rviz2',
        namespace='',
        executable='rviz2',
        arguments=['-d' + os.path.join(bringup_dir, 'rviz', 'rviz2.rviz')]
    )

    def create_gazebo_launch_group(world_type):
        world_config = get_world_config(world_type)
        if world_config is None:
            return None

        # 定义 spawn_entity 节点
        spawn_entity_node = Node(
            package='gazebo_ros',
            executable='spawn_entity.py',
            arguments=[
                '-entity', 'robot',
                '-topic', 'robot_description',
                '-x', world_config['x'],
                '-y', world_config['y'],
                '-z', world_config['z'],
                '-Y', world_config['yaw'],
                '-timeout', '120'
            ],
            output='screen'
        )

        return GroupAction(
            condition=LaunchConfigurationEquals('world', world_type),
            actions=[
                # 先启动 gzserver（加载世界和插件）
                IncludeLaunchDescription(
                    PythonLaunchDescriptionSource(os.path.join(pkg_gazebo_ros, 'launch', 'gzserver.launch.py')),
                    launch_arguments={'world': os.path.join(bringup_dir, 'world', world_config['world_path'])}.items(),
                ),
                # 延迟1秒启动 spawn_entity（给URDF解析和服务初始化留时间）
                TimerAction(
                    period=1.0,
                    actions=[spawn_entity_node]
                )
            ]
        )


    bringup_RoboconWithoutWall_cmd_group = create_gazebo_launch_group(WorldType.RoboconWithoutWall)
    bringup_RoboconWithWall_cmd_group = create_gazebo_launch_group(WorldType.RoboconWithWall)

    # Create the launch description and populate
    ld = LaunchDescription()

    # Set environment variables
    ld.add_action(append_enviroment)
    ld.add_action(append_gazebo_model_path)

    ld.add_action(declare_use_sim_time_cmd)
    ld.add_action(declare_world_cmd)
    ld.add_action(declare_rviz_config_file_cmd)
    ld.add_action(declare_use_joint_state_publisher)


    ld.add_action(start_robot_state_publisher_cmd)
    ld.add_action(start_joint_state_publisher_cmd)
    ld.add_action(gazebo_client_launch)
    ld.add_action(bringup_RoboconWithWall_cmd_group)  # 有墙赛道（默认激活）
    ld.add_action(bringup_RoboconWithoutWall_cmd_group)  # 无墙赛道

    # Uncomment this line if you want to start RViz
    ld.add_action(start_rviz_cmd)

    return ld
