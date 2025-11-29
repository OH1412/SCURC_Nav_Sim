import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource, FrontendLaunchDescriptionSource
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration 

def generate_launch_description():

  map_path = os.path.join(
      get_package_share_directory('r2_bringup'),
      'maps',
      'test.pcd'
  )

  # icp relocalization
  map_odom_trans = Node(
      package='icp_relocalization',
      executable='transform_publisher',
      name='transform_publisher',
      output='screen'
  )

  icp_node = Node(
      package='icp_relocalization',
      executable='icp_node',
      name='icp_node',
      output='screen',
      parameters=[
          {'initial_x':0.0},
          {'initial_y':0.0},
          {'initial_z':0.0},
          {'initial_a':0.0},
          # {'initial_roll':0.0},
          # {'initial_pitch':0.0},
          # {'initial_yaw':0.0},
          {'map_voxel_leaf_size':0.1},
          {'cloud_voxel_leaf_size':0.1},
          {'map_frame_id':'map'},
          {'solver_max_iter':75},
          {'map_path': map_path},
          {'fitness_score_thre':0.2}, # 是最近点距离的平均值，越小越严格
      ],
  )
  
  # Find path
  config_path = os.path.join(get_package_share_directory('r2_bringup'), 'params') 
  config_file_dir = os.path.join(get_package_share_directory("fast_livo"), "config")

  #Load parameters
  avia_config_cmd = os.path.join(config_file_dir, "MARS_LVIG.yaml")
  camera_config_cmd = os.path.join(config_file_dir, "camera_MARS_LVIG.yaml")

  # fast-livo2 localization   
  fast_livo_param = os.path.join(
      config_path, 'avia_relocation.yaml')
  fast_livo_node = Node(
      package='fast_livo',
      executable='fastlivo_mapping',
      parameters=[
          fast_livo_param,
          camera_config_cmd
      ],
      output='screen',
      arguments=['--ros-args', '--log-level', 'warn'], 
      remappings=[('/aft_mapped_to_init','/state_estimation')]
  )
        
  rviz_config_file = os.path.join(
    get_package_share_directory('r2_bringup'), 'rviz', 'loam_livox.rviz')
  start_rviz = Node(
    package='rviz2',
    executable='rviz2',
    arguments=['-d', rviz_config_file],
    output='screen'
  )

  delayed_start_livo = TimerAction(
    period=1.0,
    actions=[
      fast_livo_node
    ]
  )

  ld = LaunchDescription()

  ld.add_action(map_odom_trans)
  ld.add_action(icp_node)
  ld.add_action(start_rviz)
  ld.add_action(delayed_start_livo)

  return ld