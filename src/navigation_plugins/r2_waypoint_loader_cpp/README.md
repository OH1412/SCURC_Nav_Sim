# R2 Waypoint Loader C++

[![ROS 2 Humble](https://img.shields.io/badge/ROS2-Humble-22314E.svg)](https://docs.ros.org/en/humble/)
[![C++17](https://img.shields.io/badge/C%2B%2B-17-blue.svg)](https://isocpp.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

## 📖 项目简介

R2 Waypoint Loader C++ 是一个专为 Nav2 开发的航点加载器插件，支持从 YAML 配置文件加载复杂的航点序列，并通过插件化的任务执行系统实现智能的航点跟随和任务执行。

该加载器支持：
- 🔄 **复杂航点路径构建**：支持主航点、过渡点和边界点的自动生成
- 🔌 **插件化任务执行**：支持上升、降落等自定义任务
- 📊 **多线程架构**：基于 ROS 2 的异步动作客户端通信
- 📝 **YAML 配置驱动**：灵活的航点和任务配置

---

## 🚀 核心功能

### 主要特性

- **📍 智能航点加载**: 从 YAML 文件解析多层次航点配置，支持主航点和边界点
- **🔄 路径规划**: 自动构建包含过渡点的完整航点路径
- **🔌 插件化任务**: 支持到达航点时执行自定义任务（上升、降落等）
- **📡 ROS 2 集成**: 完整集成 Nav2 的 FollowWaypoints 动作接口
- **⚡ 高性能**: 基于 C++17 的高效实现，支持多线程处理

### 航点系统架构

```
YAML配置 → 航点解析 → 路径构建 → 任务执行 → Nav2动作调用
    ↓           ↓          ↓          ↓            ↓
  多层航点    主航点提取  过渡点生成  插件调用   跟随执行
```

---

## 📋 系统要求

- **操作系统**: Ubuntu 22.04 LTS
- **ROS版本**: ROS 2 Humble Hawksbill
- **编译器**: GCC 9.4+ (C++17 支持)
- **依赖包**:
  - `nav2_waypoint_follower`
  - `nav_msgs`
  - `geometry_msgs`
  - `yaml-cpp`

---

## 🛠️ 安装与编译

### 1. 依赖安装

```bash
# 安装系统依赖
sudo apt update
sudo apt install libyaml-cpp-dev

# 确保Nav2相关包已安装
sudo apt install ros-humble-nav2-waypoint-follower
```

### 2. 工作空间编译

```bash
# 进入工作空间
cd ~/SCURC_Nav_Sim

# 编译包
colcon build --packages-select r2_waypoint_loader_cpp

# 加载环境
source install/setup.bash
```

### 3. 插件注册

确保插件在 Nav2 配置中正确注册：

```yaml
waypoint_follower:
  ros__parameters:
    waypoint_task_executor_plugin: "r2_waypoint_task_plugin::R2WaypointTask"
```

---

## ⚙️ 配置说明

### 1. 航点配置文件

航点配置存储在 `config/waypoints.yaml` 文件中：

```yaml
# 航点列表（按执行顺序）
prepoints: [
  -2,-2_front,-2_back,-2_left,-2_right,
  -1,-1_front,-1_back,-1_left,-1_right,
  0,0_front,0_back,0_left,0_right,
  # ... 更多航点
]

# 主航点序列（实际执行的航点）
waypoints: [-1, 2]  # 例如：先去-1号航点，再去2号航点

# 详细航点定义
-2:
  header:
    frame_id: "map"
  pose:
    position: {x: -0.55, y: -0.15, z: 0.0}
    orientation: {x: 0.0, y: 0.0, z: 0.7071, w: 0.7071}

# 带任务的航点
-2_front:
  header: {frame_id: "map"}
  pose:
    position: {x: -0.55, y: 0.35, z: 0.0}
    orientation: {x: 0.0, y: 0.0, z: 0.7071, w: 0.7071}
  task:
    action: "ascend"
    height_mm: 400
```

### 2. 节点参数配置

```yaml
waypoint_loader:
  ros__parameters:
    # 启动延时（秒）
    start_delay: 2.0

    # 航点配置文件路径
    waypoints_path: "$(find-pkg-share r2_waypoint_loader_cpp)/config/waypoints.yaml"

    # 任务插件配置
    waypoint_task_executor_plugin: "r2_waypoint_task_plugin::R2WaypointTask"
```

### 3. 坐标系说明

航点坐标基于 `map` 坐标系：
- **基准转换**: MapX = 世界X - 4.75, MapY = 世界Y + 3.2
- **单位**: 米
- **朝向**: 四元数表示，z=0.7071, w=0.7071 表示90度旋转

---

## 🎯 使用方法

### 1. 启动航点加载器

```bash
# 启动航点加载器节点
ros2 launch r2_waypoint_loader_cpp waypoint_loader.launch.py
```

### 2. 监控执行状态

```bash
# 查看节点状态
ros2 node list | grep waypoint

# 查看航点跟随动作状态
ros2 action list | grep follow_waypoints

# 监控动作执行
ros2 action info /follow_waypoints
```

### 3. 手动触发航点执行

```bash
# 发送航点跟随目标（可选，通常由加载器自动触发）
ros2 action send_goal /follow_waypoints nav2_msgs/action/FollowWaypoints \
  "{poses: [{header: {frame_id: 'map'}, pose: {position: {x: -1.75, y: -0.15, z: 0.0}, orientation: {w: 1.0}}}] }"
```

---

## 🔧 航点任务插件

### 支持的任务类型

| 任务类型 | 描述 | 参数 |
|----------|------|------|
| `ascend` | 立即上升指定高度 | `height_mm`: 上升高度(毫米) |
| `delayed_descend` | 延时降落指定高度 | `height_mm`: 降落高度(毫米) |

### 任务执行流程

1. **到达航点**: 导航系统到达指定航点
2. **任务识别**: 根据航点ID查找对应的任务配置
3. **任务执行**: 调用相应的任务执行函数
4. **状态反馈**: 返回任务执行结果

### 自定义任务扩展

继承 `nav2_core::WaypointTaskExecutor` 类实现自定义任务：

```cpp
class CustomTask : public nav2_core::WaypointTaskExecutor
{
public:
  void initialize(const rclcpp_lifecycle::LifecycleNode::WeakPtr& parent,
                  const std::string& plugin_name) override;

  bool processAtWaypoint(const geometry_msgs::msg::PoseStamped& curr_pose,
                        const int& curr_waypoint_index) override;
};
```

---

## 📊 架构详解

### 核心组件

#### 1. WaypointLoader 主类
- **航点解析**: 从YAML文件加载航点配置
- **路径构建**: 生成包含过渡点的完整路径
- **动作客户端**: 与Nav2的FollowWaypoints动作通信
- **任务调度**: 管理航点任务的执行顺序

#### 2. R2WaypointTask 插件
- **任务执行**: 实现具体的航点任务逻辑
- **状态管理**: 监控任务执行状态和机器人高度
- **消息通信**: 发布速度命令控制机器人运动

#### 3. 航点关系系统
- **主航点**: 实际需要到达的目标点
- **边界点**: 用于过渡和避障的辅助点
- **过渡点**: 在主航点之间自动生成的连接点

### 数据流

```
YAML配置 → WaypointLoader → 路径构建 → FollowWaypoints动作 → R2WaypointTask → 任务执行
```

---

## 🔧 开发与调试

### 调试信息

```bash
# 查看航点加载器日志
ros2 node info /waypoint_loader

# 查看航点跟随器状态
ros2 lifecycle get nav2_waypoint_follower

# 查看TF变换
ros2 run tf2_ros tf2_echo map base_link
```

### 常见问题

#### 1. 插件未找到错误
```
Plugin 'r2_waypoint_task_plugin' not found
```
**解决方案**: 确保插件库已正确编译并安装在ROS包路径中

#### 2. YAML解析失败
**解决方案**: 检查YAML文件语法和路径配置

#### 3. 动作服务器未响应
**解决方案**: 确保Nav2 waypoint_follower已正确启动

---

## 📝 配置示例

### 简单航点配置

```yaml
prepoints: [0, 1, 2]
waypoints: [0, 2]

0:
  header: {frame_id: "map"}
  pose:
    position: {x: 0.0, y: 0.0, z: 0.0}
    orientation: {x: 0.0, y: 0.0, z: 0.0, w: 1.0}

2:
  header: {frame_id: "map"}
  pose:
    position: {x: 2.0, y: 0.0, z: 0.0}
    orientation: {x: 0.0, y: 0.0, z: 0.0, w: 1.0}
```

### 复杂航点配置（带任务）

```yaml
prepoints: [start, task_point, end]
waypoints: [start, task_point, end]

task_point:
  header: {frame_id: "map"}
  pose:
    position: {x: 1.0, y: 1.0, z: 0.0}
    orientation: {x: 0.0, y: 0.0, z: 0.7071, w: 0.7071}
  task:
    action: "ascend"
    height_mm: 300
```

---

## 📄 许可证

本项目采用 [Apache 2.0 许可证](LICENSE)。

---

## 📞 联系方式

- **项目主页**: [SCURC Navigation Simulation](https://github.com/OH1412/SCURC_Nav_Sim)
- **技术支持**: [GitHub Issues](https://github.com/OH1412/SCURC_Nav_Sim/issues)
- **维护者**: [Pangolin战队](https://github.com/mose1s/RC_vision_2026) @[OH](https://github.com/OH1412)
- **贡献者**: [Pangolin战队全体成员](https://github.com/mose1s/RC_vision_2026)

---

*最后更新: 2025年11月22日*
