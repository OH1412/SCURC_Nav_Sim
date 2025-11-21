cmake_minimum_required(VERSION 3.8)
project(my_gazebo_plugins)

# 编译选项
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

# 找到依赖包
find_package(ament_cmake REQUIRED)
find_package(gazebo_ros REQUIRED)
find_package(gazebo_dev REQUIRED)
find_package(rclcpp REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(tf2_geometry_msgs REQUIRED)
find_package(builtin_interfaces REQUIRED)

# 头文件目录
include_directories(
  include
  ${GAZEBO_INCLUDE_DIRS}
)

# 编译插件源文件
add_library(cmd_vel_z_plugin SHARED
  src/cmd_vel_z_plugin.cpp
)

# 链接依赖库
ament_target_dependencies(cmd_vel_z_plugin
  gazebo_ros
  rclcpp
  geometry_msgs
  nav_msgs
  tf2_ros
  tf2_geometry_msgs
  builtin_interfaces
)

# Gazebo 插件需要这个
target_link_libraries(cmd_vel_z_plugin
  ${GAZEBO_LIBRARIES}
)

# 插件安装路径（很重要！）
install(TARGETS cmd_vel_z_plugin
  LIBRARY DESTINATION lib
)

# include 文件安装（如果你有 .hpp）
install(DIRECTORY include/
  DESTINATION include/
)

ament_package()
