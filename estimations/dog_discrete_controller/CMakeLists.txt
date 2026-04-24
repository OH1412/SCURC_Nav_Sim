cmake_minimum_required(VERSION 3.8)
project(dog_discrete_controller)

# 开启编译器警告（良好的C++编程习惯）
if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# ==========================================
# 1. 寻找所有的依赖包 (Dependencies)
# ==========================================
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(nav2_core REQUIRED)
find_package(pluginlib REQUIRED)
find_package(nav2_costmap_2d REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(tf2_geometry_msgs REQUIRED)
find_package(angles REQUIRED) # 用于计算角度差的实用工具包
find_package(usart_pkg REQUIRED)

# ==========================================
# 2. 编译你的动态链接库 (Shared Library)
# 注意：这里的名字必须和 xml 文件里的 path 一致
# ==========================================
add_library(dog_discrete_controller_core SHARED
  src/dog_discrete_controller.cpp
  src/dog_collision_checker.cpp
)

# 包含你的 include 文件夹
target_include_directories(dog_discrete_controller_core
  PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

# 将依赖包链接到你的库文件上
ament_target_dependencies(dog_discrete_controller_core
  rclcpp
  nav2_core
  pluginlib
  nav2_costmap_2d
  geometry_msgs
  nav_msgs
  std_msgs
  tf2
  tf2_ros
  tf2_geometry_msgs
  angles
  usart_pkg
)

# ==========================================
# 3. 🌟 注册插件 (Pluginlib Export)
# ==========================================
pluginlib_export_plugin_description_file(nav2_core dog_discrete_plugins.xml)

# ==========================================
# 4. 安装规则 (Install Rules) - 非常重要！
# ==========================================
# 安装编译好的 .so 库文件
install(TARGETS dog_discrete_controller_core
  EXPORT export_${PROJECT_NAME}
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)

# 安装你的头文件
install(DIRECTORY include/
  DESTINATION include
)

# 将 xml 文件安装到 share 目录下，这样 Nav2 才能在系统里找到它
install(FILES dog_discrete_plugins.xml
  DESTINATION share/${PROJECT_NAME}
)

# ==========================================
# 5. 导出接口给其他包使用 (Ament Export)
# ==========================================
ament_export_include_directories(include)
ament_export_targets(export_${PROJECT_NAME} HAS_LIBRARY_TARGET)
ament_export_dependencies(
  rclcpp
  nav2_core
  pluginlib
  nav2_costmap_2d
  geometry_msgs
  nav_msgs
  std_msgs
  tf2
  tf2_ros
  tf2_geometry_msgs
  angles
)

ament_package()