cmake_minimum_required(VERSION 3.8)
project(legged_bringup)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(nav2_bringup REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # the following line skips the linter which checks for copyrights
  # comment the line when a copyright and license is added to all source files
  set(ament_cmake_copyright_FOUND TRUE)
  # the following line skips cpplint (only works in a git repo)
  # comment the line when this package is in a git repo and when
  # a copyright and license is added to all source files
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()


# 1 add_executable 

# 2 ament_target_dependencies

# 3 install
install(DIRECTORY launch maps params behavior_tree rviz
  DESTINATION share/${PROJECT_NAME})

# Install python node script so it can be launched as a ROS2 Node (executable)
install(PROGRAMS
  nodes/static_tf_broadcaster.py
  nodes/aft_to_pose_offset_node.py
  nodes/position_based_param_switcher.py
  nodes/nav_zone_monitor.py
  nodes/obstacle_scale_controller.py
  nodes/waypoint_sender.py
  nodes/stand_up_sender.py
  nodes/arm_control_server.py
  nodes/arm_mission_trigger.py
  nodes/arm_pose_broadcaster.py
  nodes/arm_points_visualizer.py
  nodes/interactive_arm_pick.py
  nodes/arm_coord_monitor.py
  nodes/arm_point_id_cli.py
  nodes/arm_xyz_manual_test.py
  nodes/wait_for_ros_condition.py
  nodes/mission_session_logger.py
  nodes/mission_log_client.py
  nodes/mission_log_labels.py
  nodes/base_link_odom_publisher.py
  nodes/arm_root_odom_publisher.py
  nodes/pointcloud_range_filter.py
  nodes/velocity_calibration_recorder.py
  test/path1_nav_test.py
  test/record_waypoints.py
  test/record_waypoints_all.py
  test/save_current_point.py
  DESTINATION lib/${PROJECT_NAME}
)

# Install test/debug scripts into share/<package>/scripts so launch files can call them
install(PROGRAMS
  scripts/publish_kfs.py
  scripts/read_yaml_value.py
  DESTINATION share/${PROJECT_NAME}/scripts
)


install(DIRECTORY include/
  DESTINATION include)

install(DIRECTORY logs
  DESTINATION share/${PROJECT_NAME}
  OPTIONAL)

ament_export_include_directories(include)
ament_export_dependencies(rclcpp std_msgs)

ament_package()
