cmake_minimum_required(VERSION 3.8)
project(cmd_vel_udp_bridge)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(yaml-cpp REQUIRED)

add_executable(cmd_vel_udp_bridge_node
  src/cmd_vel_udp_bridge_node.cpp
)

ament_target_dependencies(cmd_vel_udp_bridge_node
  rclcpp
  geometry_msgs
  std_msgs
)

target_link_libraries(cmd_vel_udp_bridge_node yaml-cpp)

install(TARGETS cmd_vel_udp_bridge_node
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
