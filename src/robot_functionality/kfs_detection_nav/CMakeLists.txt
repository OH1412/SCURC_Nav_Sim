cmake_minimum_required(VERSION 3.8)
project(kfs_detection_nav)

# 编译选项
if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# 查找依赖包
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(nav2_msgs REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(yolov8_ros2_msgs REQUIRED)


include_directories(
  include  # 声明include目录是头文件搜索路径
)

# 生成可执行文件（对应你的kfs_manager.cpp）
add_executable(kfs_detection_node 
  src/kfs_manager.cpp
)

# 链接依赖库
ament_target_dependencies(kfs_detection_node
  rclcpp
  std_msgs
  geometry_msgs
  nav2_msgs
  tf2
  tf2_ros
  sensor_msgs
  yolov8_ros2_msgs
)

# 安装可执行文件（核心：必须安装到lib/${PROJECT_NAME}目录）
install(TARGETS
  kfs_detection_node
  DESTINATION lib/${PROJECT_NAME}
)

# 安装 launch 文件
install(
  DIRECTORY launch
  DESTINATION share/${PROJECT_NAME}
)

# 安装头文件（可选，若有外部调用需求）
install(DIRECTORY include/
  DESTINATION include/${PROJECT_NAME}
)

# 测试配置（可选）
if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

# 声明包
ament_package()
