# Gazebo for Humble - 机器人仿真环境

[![ROS 2 Humble](https://img.shields.io/badge/ROS2-Humble-22314E.svg)](https://docs.ros.org/en/humble/)
[![Gazebo 11](https://img.shields.io/badge/Gazebo-11-orange.svg)](https://gazebosim.org/)
[![Ubuntu 22.04](https://img.shields.io/badge/Ubuntu-22.04-E95420.svg)](https://releases.ubuntu.com/jammy/)

## 📖 项目简介

Gazebo for Humble 是专为 ROS 2 Humble 优化的机器人仿真环境包，提供完整的 Gazebo 仿真生态系统，包括自定义机器人控制器插件、多样化的机器人模型和专业的比赛场地环境。

该包采用经典的全向轮机器人模型（不使用商业机器人模型），通过自定义的 `cmd_vel_z_plugin` 插件实现精确的速度控制，是机器人导航算法开发和测试的理想平台。

### 🎯 核心特性

- **🔧 自定义控制器插件**: 专为全向轮机器人设计的速度控制插件
- **🤖 多型号机器人**: 支持多种机器人URDF模型（全向轮、阿克曼转向等）
- **🏁 专业比赛场地**: 包含完整的RoboCon2026比赛场地仿真
- **📡 ROS 2 完美集成**: 深度集成ROS 2 Humble的通信机制
- **⚡ 高性能仿真**: 优化后的Gazebo配置，支持实时仿真

---

## 🏗️ 系统架构

### 包结构概览

```
gazebo_for_humble/
├── src/
│   ├── my_gazebo_plugins/           # 🔧 自定义Gazebo插件
│   │   ├── include/                 # 插件头文件
│   │   ├── src/                     # 插件源代码
│   │   │   ├── cmd_vel_z_plugin.cpp # 速度控制插件
│   │   │   └── hello_plugin.cpp     # 示例插件
│   │   ├── urdf/                    # 示例URDF模型
│   │   └── world/                   # 示例世界文件
│   ├── rc_2026_description/         # 🤖 RoboCon2026机器人模型
│   │   ├── urdf/                    # 机器人URDF描述
│   │   │   ├── try_mecanum.urdf     # 全向轮机器人
│   │   │   ├── sentry_description.urdf # 哨兵机器人
│   │   │   └── GuangdianCar.urdf    # 光电车模型
│   │   └── world/                   # 世界环境文件
│   └── robocon2026map/              # 🏁 比赛地图资源
│       └── meshes/                  # 地图网格和纹理
├── CMakeLists.txt                   # 构建配置
├── package.xml                      # 包描述
└── README.md
```

### 技术栈

| 组件 | 版本 | 说明 |
|------|------|------|
| **ROS 2** | Humble Hawksbill | 机器人操作系统框架 |
| **Gazebo** | 11.x | 物理仿真引擎 |
| **编译工具** | Colcon + CMake | ROS 2 标准构建工具 |
| **插件框架** | Gazebo Plugin API | 自定义仿真插件接口 |

---

## 📋 系统要求

### 硬件要求
- **CPU**: Intel i5 / AMD Ryzen 5 以上
- **内存**: 8GB RAM 以上
- **GPU**: 支持OpenGL 3.3+的显卡（用于Gazebo渲染）
- **存储**: 5GB 可用空间

### 软件依赖
- **操作系统**: Ubuntu 22.04 LTS
- **ROS 2**: Humble Hawksbill
- **Gazebo**: 11.x (随ROS 2 Humble自动安装)
- **编译工具**: Colcon, CMake, GCC 9.4+

---

## 🛠️ 安装指南

### 1. 系统依赖安装

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装ROS 2 Humble（如果尚未安装）
sudo apt install ros-humble-desktop

# 安装Gazebo相关依赖
sudo apt install ros-humble-gazebo-ros-pkgs ros-humble-gazebo-ros

# 安装编译依赖
sudo apt install build-essential cmake python3-colcon-common-extensions
```

### 2. 工作空间准备

```bash
# 克隆项目到工作空间
cd ~/SCURC_Nav_Sim/src
git clone https://github.com/OH1412/SCURC_Nav_Sim.git .

# 或者直接进入gazebo包目录
cd ~/SCURC_Nav_Sim/src/simulation_environment/gazebo_for_humble
```

### 3. 编译插件

```bash
# 加载ROS 2环境
source /opt/ros/humble/setup.bash

# 编译自定义插件包
colcon build --packages-select my_gazebo_plugins

# 或者编译整个工作空间
cd ~/SCURC_Nav_Sim
colcon build --symlink-install
```

### 4. 插件部署

编译完成后，需要将插件部署到系统路径以便Gazebo识别：

```bash
# 复制插件到系统库目录
sudo cp install/my_gazebo_plugins/lib/libcmd_vel_z_plugin.so /opt/ros/humble/lib/

# 更新动态链接库缓存
sudo ldconfig

# 验证插件是否存在
ls -la /opt/ros/humble/lib/libcmd_vel_z_plugin.so
```

---

## 🎯 使用指南

### 1. 启动基本仿真环境

#### 使用内置世界文件
```bash
# 启动空的Gazebo世界
gazebo --verbose

# 或使用ROS 2启动
ros2 launch gazebo_ros gazebo.launch.py world:=$(ros2 pkg prefix gazebo_for_humble)/share/rc_2026_description/world/robocon2026_new.world
```

#### 使用机器人模型
```bash
# 启动包含机器人的仿真环境
ros2 launch gazebo_for_humble robot_simulation.launch.py
```

### 2. 启动自定义机器人

#### 全向轮机器人
```bash
# 启动全向轮机器人模型
ros2 launch gazebo_for_humble mecanum_robot.launch.py
```

#### 其他机器人模型
```bash
# 启动哨兵机器人
ros2 launch gazebo_for_humble sentry_robot.launch.py

# 启动光电车
ros2 launch gazebo_for_humble guangdian_car.launch.py
```

### 3. 比赛场地仿真

```bash
# 启动RoboCon2026比赛场地（完整版）
ros2 launch gazebo_for_humble robocon2026_full.launch.py

# 启动比赛场地（轻量版）
ros2 launch gazebo_for_humble robocon2026_light.launch.py

# 启动比赛场地（无重力模式，用于调试）
ros2 launch gazebo_for_humble robocon2026_no_gravity.launch.py
```

---

## ⚙️ 插件配置详解

### CmdVelZPlugin 参数说明

插件支持以下配置参数：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `command_topic` | string | `/cmd_vel` | 订阅的速度指令话题 |
| `odometry_topic` | string | `/odom` | 发布的里程计话题 |
| `robot_base_frame` | string | `base_link` | 机器人基坐标系 |
| `odometry_frame` | string | `odom` | 里程计坐标系 |
| `update_rate` | double | `100.0` | 控制更新频率(Hz) |
| `publish_rate` | double | `10.0` | 里程计发布频率(Hz) |
| `max_linear_velocity` | double | `0.5` | 最大线速度(m/s) |
| `max_angular_velocity` | double | `1.57` | 最大角速度(rad/s) |

### URDF集成示例

在机器人URDF文件中添加插件：

```xml
<!-- 添加到机器人URDF的<gazebo>标签内 -->
<gazebo>
  <plugin name="cmd_vel_z_controller" filename="libcmd_vel_z_plugin.so">
    <command_topic>/cmd_vel</command_topic>
    <odometry_topic>/odom</odometry_topic>
    <robot_base_frame>base_link</robot_base_frame>
    <odometry_frame>odom</odometry_frame>
    <update_rate>100</update_rate>
    <max_linear_velocity>1.0</max_linear_velocity>
    <max_angular_velocity>2.0</max_angular_velocity>
  </plugin>
</gazebo>
```

### 世界文件集成示例

```xml
<!-- 在.world文件中添加机器人模型 -->
<include>
  <uri>model://your_robot</uri>
  <pose>0 0 0 0 0 0</pose>
</include>
```

---

## 🔧 功能验证

### 1. 插件加载测试

```bash
# 启动仿真环境后，检查插件是否正确加载
rosservice list | grep gazebo
```

### 2. 速度控制测试

```bash
# 发布速度指令测试机器人运动
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.2, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.5}}"

# 监控里程计输出
ros2 topic echo /odom
```

### 3. TF变换验证

```bash
# 检查坐标变换链
ros2 run tf2_ros tf2_echo odom base_link

# 查看所有可用的TF变换
ros2 run tf2_tools view_frames.py
```

---

## 📚 机器人模型说明

### 支持的机器人类型

#### 1. 全向轮机器人 (`try_mecanum.urdf`)
- **特点**: 支持全方位移动（前后左右+旋转）
- **适用场景**: 室内导航、复杂环境探索
- **控制方式**: 通过 `/cmd_vel` 话题控制

#### 2. 哨兵机器人 (`sentry_description.urdf`)
- **特点**: 巡逻型机器人，适合边界巡逻
- **传感器**: 集成激光雷达和摄像头
- **用途**: 安全监控、边界防御

#### 3. 光电车 (`GuangdianCar.urdf`)
- **特点**: 阿克曼转向机构，适合室外环境
- **性能**: 模拟真实车辆动力学
- **应用**: 室外导航、自动驾驶测试

### 模型文件位置

```
rc_2026_description/urdf/
├── try_mecanum.urdf      # 全向轮机器人
├── sentry_description.urdf # 哨兵机器人
├── GuangdianCar.urdf     # 光电车
├── car.urdf             # 基础小车模型
└── fishbot_base.urdf    # FishBot基础模型
```

---

## 🏁 比赛场地说明

### RoboCon2026 场地特性

#### 完整版场地 (`robocon2026_new.world`)
- **包含**: 所有比赛元素、复杂地形、障碍物
- **用途**: 完整比赛仿真、算法测试
- **资源消耗**: 高（推荐高性能计算机）

#### 轻量版场地 (`robocon2026map_light.world`)
- **包含**: 基础场地结构，简化障碍物
- **用途**: 快速测试、算法验证
- **资源消耗**: 中等

#### 调试版场地 (`robocon2026map_without_gravity.world`)
- **特点**: 无重力模式，便于调试
- **用途**: 运动学调试、路径规划测试
- **注意**: 非物理真实环境

### 场地文件位置

```
rc_2026_description/world/
├── robocon2026_new.world          # 完整比赛场地
├── robocon2026_light.world        # 轻量版场地
├── robocon2026_no_gravity.world   # 无重力调试版
├── robocon2026_gh.world          # GH版本场地
└── robocon2026_1.world           # 基础版本
```

---

## 🔧 开发与调试

### 添加新机器人模型

1. **创建URDF文件**
   ```bash
   # 在urdf目录下创建新的机器人描述文件
   touch rc_2026_description/urdf/new_robot.urdf
   ```

2. **集成控制器插件**
   ```xml
   <!-- 在URDF中添加插件配置 -->
   <gazebo>
     <plugin name="controller" filename="libcmd_vel_z_plugin.so">
       <!-- 参数配置 -->
     </plugin>
   </gazebo>
   ```

3. **创建启动文件**
   ```python
   # 在launch目录下创建启动脚本
   # 参考现有launch文件的结构
   ```

### 自定义比赛场地

1. **使用Gazebo编辑器**
   ```bash
   gazebo --verbose  # 启动Gazebo编辑器
   ```

2. **导出世界文件**
   ```bash
   # 保存为.world格式文件
   cp custom_world.world rc_2026_description/world/
   ```

### 插件开发

参考 `cmd_vel_z_plugin.cpp` 的实现：

```cpp
// 继承自gazebo::ModelPlugin
class CustomPlugin : public gazebo::ModelPlugin
{
public:
    void Load(gazebo::physics::ModelPtr model, sdf::ElementPtr sdf) override;
    void OnUpdate(const gazebo::common::UpdateInfo &info);
};
```

---

## 🐛 常见问题

### 1. 插件无法加载
```
错误: Failed to load plugin libcmd_vel_z_plugin.so
```
**解决**: 检查插件是否正确复制到 `/opt/ros/humble/lib/` 目录

### 2. 机器人无响应
```
现象: 发布/cmd_vel后机器人不动
```
**解决**:
- 检查插件是否正确配置在URDF中
- 验证话题名称是否匹配
- 检查Gazebo物理引擎是否启动

### 3. TF变换缺失
```
错误: Lookup would require extrapolation into the past
```
**解决**:
- 确保 `use_sim_time` 参数设置为 `true`
- 检查时钟同步设置

### 4. 编译失败
```
错误: Could not find a package configuration file for gazebo
```
**解决**:
```bash
sudo apt install ros-humble-gazebo-dev
```

---

## 📞 联系与支持

- **项目主页**: [RC_vision_2026](https://github.com/mose1s/RC_vision_2026)
- **技术支持**: [GitHub Issues](https://github.com/mose1s/RC_vision_2026/issues)
- **维护者**: [Pangolin战队](https://github.com/mose1s/RC_vision_2026) @[ixgnozeix](https://github.com/ixgnozeix)
- **贡献者**: [Pangolin战队全体成员](https://github.com/mose1s/RC_vision_2026)
---

*最后更新: 2025年11月8日*