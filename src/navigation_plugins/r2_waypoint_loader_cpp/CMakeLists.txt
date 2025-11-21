cmake_minimum_required(VERSION 3.5)
project(r2_waypoint_loader_cpp)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
  # 添加调试编译选项（-g生成调试符号，-O0关闭优化）
  add_compile_options(-g -O0)
endif()

set(CMAKE_BUILD_TYPE Debug CACHE STRING "Build type" FORCE)

# 查找依赖
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_action REQUIRED)
find_package(rclcpp_lifecycle REQUIRED)  # 插件需要的生命周期节点依赖
find_package(geometry_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(nav2_msgs REQUIRED)
find_package(nav2_waypoint_follower REQUIRED)
find_package(nav2_core REQUIRED)  # Nav2插件核心接口
find_package(tf2 REQUIRED)
find_package(yaml-cpp REQUIRED)
find_package(rclcpp_components REQUIRED)
find_package(pluginlib REQUIRED)  # 插件加载必需
find_package(lifecycle_msgs REQUIRED)

add_library(
  r2_waypoint_task_plugin SHARED
  ./plugins/r2_waypoint_task.cpp
)

ament_target_dependencies(r2_waypoint_task_plugin
  rclcpp
  rclcpp_lifecycle
  nav2_core
  pluginlib
  geometry_msgs
  nav_msgs
  nav2_msgs
  lifecycle_msgs
)
target_include_directories(r2_waypoint_task_plugin PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)

add_executable(waypoint_loader src/waypoint_loader.cpp)
ament_target_dependencies(waypoint_loader
  rclcpp
  rclcpp_action
  geometry_msgs
  nav_msgs
  nav2_msgs
  nav2_waypoint_follower
  tf2
  yaml-cpp
  rclcpp_components 
  lifecycle_msgs
)
target_link_libraries(waypoint_loader
  yaml-cpp
  r2_waypoint_task_plugin  # 链接插件库（若主程序中直接使用插件类）
)

install(TARGETS
  r2_waypoint_task_plugin
  waypoint_loader
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION lib/${PROJECT_NAME}
)
install(FILES plugin_description/r2_waypoint_task_plugin.xml
  DESTINATION share/${PROJECT_NAME}/plugin_description
)
pluginlib_export_plugin_description_file(nav2_core 
  plugin_description/r2_waypoint_task_plugin.xml
)

ament_package()