cmake_minimum_required(VERSION 3.8)
project(height_control_plugins)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(nav2_behavior_tree REQUIRED)
find_package(behaviortree_cpp_v3 REQUIRED)
find_package(pluginlib REQUIRED)

include_directories(include)

add_library(${PROJECT_NAME} SHARED
  src/height_control_action.cpp
)

ament_target_dependencies(${PROJECT_NAME}
  rclcpp
  behaviortree_cpp_v3
  nav2_behavior_tree
)

# ---- 关键点 ----
# Nav2 的 BT 插件不使用 pluginlib，不需要 XML，不需要导出
# 只需要把库安装好即可
# -----------------

install(TARGETS ${PROJECT_NAME}
        LIBRARY DESTINATION lib)

install(DIRECTORY include/
        DESTINATION include)

pluginlib_export_plugin_description_file(nav2_behavior_tree height_control_plugins.xml)


ament_package()
