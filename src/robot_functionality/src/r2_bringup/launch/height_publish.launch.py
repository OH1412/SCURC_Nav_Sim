from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, TextSubstitution
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    # 1. 声明启动参数（支持外部传参，默认模型名"robot"）
    robot_model_name_arg = DeclareLaunchArgument(
        "robot_model_name",
        default_value=TextSubstitution(text="robot"),
        description="Gazebo中机器人的模型名称（需与仿真中一致）"
    )

    # 2. 配置高度发布节点
    height_publisher_node = Node(
        package="height_publish",          # 功能包名
        executable="height_publisher_gazebo",  # 可执行文件名称
        name="gazebo_height_publisher",    # 节点名（自定义）
        output="screen",                   # 日志输出到终端
        parameters=[
            {
                "robot_model_name": LaunchConfiguration("robot_model_name")  # 绑定启动参数
            }
        ],
        # 可选：延迟2秒启动（确保Gazebo先加载完成）
        # delay=2.0
    )

    # 3. 组装启动描述
    return LaunchDescription([
        robot_model_name_arg,    # 先声明参数
        height_publisher_node    # 再启动节点
    ])
