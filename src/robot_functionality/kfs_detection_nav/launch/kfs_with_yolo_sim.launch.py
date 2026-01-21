# kfs_with_yolo_sim.launch.py
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        # 启动 YOLO 模拟器
        Node(
            package='yolo_simulator',
            executable='yolo_simulator_node',
            name='yolo_simulator',
            output='screen'
        ),
        # 启动 KFS 管理器
        Node(
            package='kfs_detection_nav',
            executable='kfs_detection_node',
            name='kfs_manager',
            output='screen'
        )
    ])