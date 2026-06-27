#!/usr/bin/env python3
# ============================================================================
# 机械臂目标坐标发送 Launch 文件 — 持续按固定频率发送
#
# 协议规定: /arm_target (geometry_msgs/msg/Point) 的值单位为 mm
# ============================================================================
# 用法:
#   ros2 launch serial_driver arm_target_send.launch.py
#
# 参数:
#   x, y, z    - 目标坐标 (mm, base_link 坐标系)
#   rate       - 发送频率 Hz (默认 10)
#   port       - 串口设备路径 (默认 /dev/ttyUSB0)
#   baudrate   - 波特率 (默认 115200)
#   checksum_offset - 校验和偏移 (默认 0)
#
# 示例:
#   # 默认: (100, 200, 50) mm @ 10 Hz
#   ros2 launch serial_driver arm_target_send.launch.py
#
#   # 自定义坐标和频率
#   ros2 launch serial_driver arm_target_send.launch.py x:=150 y:=200 z:=100 rate:=20
#
#   # 直接等价于:
#   # ros2 topic pub --rate 20 /arm_target geometry_msgs/msg/Point "{x: 150.0, y: 200.0, z: 100.0}"
# ============================================================================

from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, ExecuteProcess,
                            TimerAction, OpaqueFunction)
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import os
from ament_index_python.packages import get_package_share_directory


def make_publisher(context):
    """解析坐标值并构造 ros2 topic pub 持续发布命令"""
    x_val = LaunchConfiguration('x').perform(context)
    y_val = LaunchConfiguration('y').perform(context)
    z_val = LaunchConfiguration('z').perform(context)

    print(f'''
========================================
  机械臂目标坐标 — 单次发送
  X: {x_val} mm
  Y: {y_val} mm
  Z: {z_val} mm
========================================
''')

    pub_cmd = [
        'ros2', 'topic', 'pub', '--once',
        '/arm_target',
        'geometry_msgs/msg/Point',
        f'{{x: {x_val}.0, y: {y_val}.0, z: {z_val}.0}}'
    ]

    return [ExecuteProcess(
        cmd=pub_cmd,
        output='screen',
        name='arm_target_publisher',
    )]


def generate_launch_description():
    declare_x = DeclareLaunchArgument(
        'x', default_value='-100',
        description='X 坐标 (mm, base_link 前方为正)')

    declare_y = DeclareLaunchArgument(
        'y', default_value='200',
        description='Y 坐标 (mm, base_link 左侧为正)')

    declare_z = DeclareLaunchArgument(
        'z', default_value='50',
        description='Z 坐标 (mm, base_link 上方为正)')

    declare_port = DeclareLaunchArgument(
        'port', default_value='/dev/ttyUSB2',
        description='串口设备路径')

    declare_baudrate = DeclareLaunchArgument(
        'baudrate', default_value='115200',
        description='串口波特率')

    declare_checksum_offset = DeclareLaunchArgument(
        'checksum_offset', default_value='0',
        description='校验和偏移 (0=标准算法)')

    config_path = os.path.join(
        get_package_share_directory('serial_driver'),
        'config',
        'serial_config.yaml',
    )

    serial_node = Node(
        package='serial_driver',
        executable='serial_cmd_sender',
        name='serial_cmd_sender',
        parameters=[config_path, {
            'port': LaunchConfiguration('port'),
            'baudrate': LaunchConfiguration('baudrate'),
            'arm_checksum_offset': LaunchConfiguration('checksum_offset'),
        }],
        output='screen',
    )

    delayed_pub = TimerAction(
        period=2.0,
        actions=[OpaqueFunction(function=make_publisher)],
    )

    return LaunchDescription([
        declare_x,
        declare_y,
        declare_z,
        declare_port,
        declare_baudrate,
        declare_checksum_offset,
        serial_node,
        delayed_pub,
    ])
