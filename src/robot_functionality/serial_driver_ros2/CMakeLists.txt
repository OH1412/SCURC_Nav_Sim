cmake_minimum_required(VERSION 3.5)
project(serial_driver)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 14)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(serial REQUIRED)

include_directories(include)

add_executable(serial_cmd_sender
  src/serial_driver.cpp
  src/serial_main.cpp
)

ament_target_dependencies(serial_cmd_sender
  rclcpp
  geometry_msgs
  std_msgs
  serial
)

install(TARGETS
  serial_cmd_sender
  DESTINATION lib/${PROJECT_NAME}
)


install(DIRECTORY launch
  DESTINATION share/${PROJECT_NAME}/
)

install(DIRECTORY config
  DESTINATION share/${PROJECT_NAME}/
)

install(DIRECTORY include/
  DESTINATION include/
)

ament_package()
