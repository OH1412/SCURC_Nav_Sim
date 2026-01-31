import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource, FrontendLaunchDescriptionSource
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration 

def generate_launch_description():

  config_path = os.path.join(
      get_package_share_directory('r2_bringup'), 'params') 

  fast_livo_share = get_package_share_directory('fast_livo')
  fast_livo_config_dir = os.path.join(fast_livo_share, 'config')
  camera_config = os.path.join(fast_livo_config_dir, 'camera_MARS_LVIG.yaml')
  
  # fast-livo mapping   
  fast_livo_param = os.path.join(config_path, 'fast_livo_mapping_param.yaml')
  fast_livo_node = Node(
        package='fast_livo',
        executable='fastlivo_mapping',
        arguments=['--ros-args', '--log-level', 'warn'],
        parameters=[
          fast_livo_param,
          camera_config
        ],
        output='screen',
        remappings=[('/aft_mapped_to_init','/state_estimation')]
    )

  start_octomap_server = IncludeLaunchDescription(
    PythonLaunchDescriptionSource([os.path.join(
        get_package_share_directory('r2_bringup'), 'launch', 'octomap_server_intensity.launch.py')])
  )
        
  rviz_config_file = os.path.join(
    get_package_share_directory('r2_bringup'), 'rviz', 'loam_livox.rviz')
  start_rviz = Node(
    package='rviz2',
    executable='rviz2',
    arguments=['-d', rviz_config_file,'--ros-args', '--log-level', 'warn'],
    output='screen'
  )

  delayed_start_mapping = TimerAction(
    period=5.0,
    actions=[
      fast_livo_node,
      start_octomap_server
    ]
  )

  ld = LaunchDescription()

  ld.add_action(start_rviz)
  ld.add_action(delayed_start_mapping)

  return ld