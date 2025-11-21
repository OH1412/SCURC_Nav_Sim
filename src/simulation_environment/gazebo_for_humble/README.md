# Pangolin_gazebo_2026

川山甲战队2026年视觉组Gazebo仿真仓库

## 项目介绍

本仓库为战队视觉组专用Gazebo仿真环境，**不使用fishrobot模型**，采用经典全向轮车模作为仿真载体，核心提供自定义速度控制插件 `libcmd_vel_z_plugin.so`，用于解析 `/cmd_vel` 话题驱动机器人运动。

## 核心功能

- 经典全向轮车模仿真（支持前后、左右平移、原地旋转）

- 自定义 Gazebo 插件 `libcmd_vel_z_plugin.so`（解析 `geometry_msgs/msg/Twist` 消息）

- 插件可直接集成到 Gazebo 场景/机器人模型中调用

## 环境依赖

- Ubuntu 22.04 LTS

- ROS 2 Humble

- Gazebo 11+（ROS 2 Humble 默认配套版本）

- Colcon Build 工具

## 编译与安装步骤

### 1. 进入到工作空间

```bash

# 进入你的 ROS 2 工作空间 src 目录
cd ~/SCURC_Nav_Sim/src/simulation_environment/gazebo_for_humble
```

### 2. 编译自定义插件

进入 `gazebo_for_humble` 目录，使用 `colcon build` 编译核心功能包 `my_gazebo_plugins`：

```bash

# 仅编译 my_gazebo_plugins 功能包
colcon build --packages-select my_gazebo_plugins
```

### 3. 插件部署（推荐方式）

编译完成后，插件文件 `libcmd_vel_z_plugin.so` 会生成在工作空间的 `install/my_gazebo_plugins/lib` 目录下。为方便 Gazebo 全局调用，建议复制到 ROS 2 系统库目录：

```bash

# 替换 {YOURNAME} 为你的 Ubuntu 用户名
sudo cp /home/{YOURNAME}/SCURC_Nav_Sim/src/simulation_environment/gazebo_for_humble/install/my_gazebo_plugins/lib/libcmd_vel_z_plugin.so /opt/ros/humble/lib/

# 更新动态链接库缓存，确保系统识别新插件
sudo ldconfig
```

### 4. 环境变量配置

确保 ROS 2 环境变量生效，可通过以下命令快速加载：

```bash

# 加载 ROS 2 Humble 系统环境变量
source /opt/ros/humble/setup.bash
# （可选）若已将 ROS 环境变量添加到 .bashrc，直接刷新即可
source ~/.bashrc
```

## 插件调用说明

插件编译并部署后，可在 Gazebo 的 `.world` 文件或机器人 `.urdf`/`.sdf` 文件中直接调用，示例配置：

```xml

<!-- Gazebo 插件配置示例（添加到 <model> 或 <gazebo> 标签内） -->
<plugin name="cmd_vel_z_controller" filename="libcmd_vel_z_plugin.so">
  <!-- 核心参数：话题与坐标系配置（根据实际需求调整） -->
  <command_topic>/cmd_vel</command_topic>  <!-- 订阅的速度指令话题 -->
  <odometry_topic>/odom</odometry_topic>    <!-- 发布的里程计话题 -->
  <robot_base_frame>base_link</robot_base_frame>  <!-- 机器人基坐标系 -->
  <odometry_frame>odom</odometry_frame>      <!-- 里程计坐标系 -->
  
  <!-- 可选参数：控制频率与速度限制 -->
  <update_rate>100</update_rate>             <!-- 控制更新频率（Hz） -->
  <max_linear_velocity>0.5</max_linear_velocity>  <!-- 最大线速度（m/s） -->
  <max_angular_velocity>1.57</max_angular_velocity>  <!-- 最大角速度（rad/s） -->
</plugin>
```

## 验证插件是否生效

1. 启动 Gazebo 仿真环境（包含配置好插件的机器人/场景）

2. 在终端发布 `/cmd_vel` 速度指令，验证机器人是否响应：

```bash

# 示例：控制机器人向前运动（线速度 0.2m/s）
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
```

## 注意事项

1. 插件复制到 `/opt/ros/humble/lib/` 需管理员权限（`sudo`），若后续修改插件代码，需重新编译并再次执行复制命令；

2. 若无需全局调用，也可通过 `source` 工作空间环境变量直接使用（无需复制）：
        `source ~/home/{YOURNAME}/SCURC_Nav_Sim/src/simulation_environment/gazebo_for_humble/install/setup.bash`

3. 确保编译前已安装所有依赖，若编译报错，可先安装基础依赖：
        `sudo apt install ros-humble-gazebo-ros ros-humble-geometry-msgs ros-humble-nav-msgs`

## 维护者

川山甲战队视觉组