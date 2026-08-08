from launch import LaunchDescription
from launch.actions import ExecuteProcess


def generate_launch_description():
    """启动航点标定编辑器。

    导出路径由代码内部通过 git root 自动定位到工作空间源码目录，
    无需通过命令行参数指定 —— 无论 symlink-install 还是拷贝安装都能正确写入。
    """
    return LaunchDescription([
        ExecuteProcess(
            cmd=[
                'ros2', 'run', 'legged_mission_planner_f_r', 'waypoint_editor_fr',
            ],
            output='screen',
        )
    ])
