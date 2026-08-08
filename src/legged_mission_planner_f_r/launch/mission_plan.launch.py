from launch import LaunchDescription
from launch.actions import ExecuteProcess
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import PathJoinSubstitution


def generate_launch_description():
    config = PathJoinSubstitution([
        FindPackageShare('legged_mission_planner_f_r'),
        'config',
        'field_layout.yaml',
    ])
    params = PathJoinSubstitution([
        FindPackageShare('legged_mission_planner_f_r'),
        'config',
        'mission_params.yaml',
    ])
    return LaunchDescription([
        ExecuteProcess(
            cmd=[
                'ros2', 'run', 'legged_mission_planner_f_r', 'mission_plan_fr',
                '--field-layout', config,
                '--mission-params', params,
            ],
            output='screen',
        )
    ])
