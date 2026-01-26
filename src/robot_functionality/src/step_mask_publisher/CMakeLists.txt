cmake_minimum_required(VERSION 3.8)
project(step_mask_publisher)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_components REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(cv_bridge REQUIRED)
find_package(OpenCV REQUIRED)
find_package(yaml-cpp REQUIRED)

# 组件库（不是可执行文件）
add_library(step_mask_publisher_component SHARED
  src/step_mask_publisher.cpp
)

target_include_directories(step_mask_publisher_component PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)

ament_target_dependencies(step_mask_publisher_component
  rclcpp
  rclcpp_components
  nav_msgs
  cv_bridge
)

target_link_libraries(step_mask_publisher_component
  ${OpenCV_LIBRARIES}
  yaml-cpp
)

# 注册组件
rclcpp_components_register_nodes(step_mask_publisher_component
  "step_mask_publisher::StepMaskPublisher"
)

# 安装
install(TARGETS step_mask_publisher_component
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)

install(DIRECTORY include/
  DESTINATION include/
)



ament_package()
