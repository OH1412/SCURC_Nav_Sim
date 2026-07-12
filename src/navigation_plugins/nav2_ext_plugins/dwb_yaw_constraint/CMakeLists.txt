cmake_minimum_required(VERSION 3.5)
project(dwb_yaw_constraint)

# Default to C++14 (matching other nav2_ext_plugins)
set(CMAKE_CXX_STANDARD 14)

# Find dependencies
find_package(ament_cmake REQUIRED)
find_package(angles REQUIRED)
find_package(dwb_core REQUIRED)
find_package(dwb_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(nav2_costmap_2d REQUIRED)
find_package(nav2_util REQUIRED)
find_package(nav_2d_msgs REQUIRED)
find_package(pluginlib REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_lifecycle REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_geometry_msgs REQUIRED)
find_package(tf2_ros REQUIRED)

set(library_name ${PROJECT_NAME}_lib)

set(dependencies
  angles
  dwb_core
  dwb_msgs
  geometry_msgs
  std_msgs
  nav2_costmap_2d
  nav2_util
  nav_2d_msgs
  pluginlib
  rclcpp
  rclcpp_lifecycle
  tf2
  tf2_geometry_msgs
  tf2_ros
)

include_directories(
  include
)

add_library(${library_name} SHARED
  plugins/maintain_yaw_critic.cpp
  plugins/decoupling_critic.cpp
  plugins/maintain_vy_critic.cpp
  plugins/rotate_to_goal_xy_critic.cpp
  plugins/rotate_to_path_critic.cpp
)

target_compile_definitions(${library_name} PUBLIC "PLUGINLIB__DISABLE_BOOST_FUNCTIONS")

ament_target_dependencies(${library_name}
  ${dependencies}
)

# Export plugin description for dwb_core::TrajectoryCritic
pluginlib_export_plugin_description_file(dwb_core dwb_yaw_constraint.xml)

install(TARGETS ${library_name}
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY include/
  DESTINATION include/
)

install(FILES dwb_yaw_constraint.xml
  DESTINATION share/${PROJECT_NAME}
)

set_target_properties(${library_name} PROPERTIES
  CXX_VISIBILITY_PRESET hidden
  VISIBILITY_INLINES_HIDDEN 1
  POSITION_INDEPENDENT_CODE ON
)

ament_export_include_directories(include)
ament_export_libraries(${library_name})
ament_export_dependencies(${dependencies})

ament_package()
