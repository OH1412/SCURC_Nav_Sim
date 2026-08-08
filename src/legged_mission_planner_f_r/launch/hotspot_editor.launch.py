from launch import LaunchDescription
from launch.actions import ExecuteProcess


def generate_launch_description():
    return LaunchDescription([
        ExecuteProcess(
            cmd=['ros2', 'run', 'legged_mission_planner_f_r', 'hotspot_editor_fr'],
            output='screen',
        )
    ])
