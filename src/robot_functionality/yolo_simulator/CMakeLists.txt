cmake_minimum_required(VERSION 3.8)
project(yolo_simulator)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)
find_package(yolov8_ros2_msgs REQUIRED)

# 添加可执行文件
add_executable(yolo_simulator_node src/yolo_simulator_node.cpp)

# 链接依赖库
ament_target_dependencies(yolo_simulator_node
  rclcpp
  std_msgs
  yolov8_ros2_msgs
)

# 安装可执行文件
install(TARGETS yolo_simulator_node
  DESTINATION lib/${PROJECT_NAME}
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
