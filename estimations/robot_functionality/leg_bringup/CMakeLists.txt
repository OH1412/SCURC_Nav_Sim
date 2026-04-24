cmake_minimum_required(VERSION 3.8)
project(leg_bringup)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(nav2_bringup REQUIRED)

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

# Install the static TF broadcaster as a normal ROS2 node executable
# so it can be launched via launch_ros.actions.Node.
install(PROGRAMS
  nodes/static_tf_broadcaster.py
  DESTINATION lib/${PROJECT_NAME}
)

# Create a no-extension symlink for the executable to satisfy ros2 launch/ros2 run expectations
install(CODE "execute_process(COMMAND ${CMAKE_COMMAND} -E create_symlink ${CMAKE_INSTALL_PREFIX}/lib/${PROJECT_NAME}/static_tf_broadcaster.py ${CMAKE_INSTALL_PREFIX}/lib/${PROJECT_NAME}/static_tf_broadcaster)")


# 4 include 

ament_package()
