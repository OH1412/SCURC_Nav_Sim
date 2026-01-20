cmake_minimum_required(VERSION 3.8)
project(fly_step_mission)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_action REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(nav2_msgs REQUIRED)
find_package(behaviortree_cpp_v3 REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_geometry_msgs REQUIRED)
find_package(yaml-cpp REQUIRED)

# 可执行文件：一个 cpp 里同时写 BT 节点 + tick 主函数
add_executable(fly_step_bt_node
  src/fly_step_bt_node.cpp
  src/nav2_pose_node.cpp
  src/ascend_node.cpp
  src/descend_node.cpp
  src/path_generator_node.cpp
  src/dynamic_path_task_executor.cpp
)
ament_target_dependencies(fly_step_bt_node
  rclcpp
  rclcpp_action
  geometry_msgs
  nav2_msgs
  behaviortree_cpp_v3
  tf2
  tf2_geometry_msgs
  tf2_ros
)
target_link_libraries(fly_step_bt_node yaml-cpp)
install(TARGETS
  fly_step_bt_node
  DESTINATION lib/${PROJECT_NAME}
)
# 安装行为树 XML、launch、config
install(DIRECTORY
  behavior_trees
  launch
  config
  include
  DESTINATION share/${PROJECT_NAME}
)

target_include_directories(fly_step_bt_node PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)
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

ament_package()
