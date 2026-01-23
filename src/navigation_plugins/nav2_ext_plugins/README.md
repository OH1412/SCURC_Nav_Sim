# Nav2 扩展插件集合 (Nav2 Extension Plugins)

[![ROS 2 Humble](https://img.shields.io/badge/ROS2-Humble-22314E.svg)](https://docs.ros.org/en/humble/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

## 📖 项目简介

Nav2 Extension Plugins 是 SCURC 机器人导航仿真系统中的导航扩展插件集合。该包基于 ROS 2 Navigation2 (Nav2) 框架，为机器人导航系统提供增强的功能和定制化的插件实现。

### 🎯 主要功能

- **🌊 速度平滑扩展**: 高级速度平滑算法，支持多种机器人运动模式
- **🗺️ 代价地图增强**: 基于强度信息的代价地图层，支持复杂地形导航
- **🔧 行为插件扩展**: 自定义行为树动作节点，支持复杂任务规划
- **🎛️ GridMap集成**: 完整的GridMap生态系统集成，支持2.5D地图处理

---

## 🏗️ 插件架构

### 核心组件

```
nav2_ext_plugins/
├── behavior_ext_plugins/     # 行为树扩展插件
│   ├── 后退避障动作 (BackUpTwzFreeAction)
│   └── 自定义行为节点
├── costmap_intensity/        # 强度代价地图层
│   ├── 障碍物层增强
│   └── 体素层优化
├── grid_map/                 # GridMap生态系统
│   ├── 核心库 (grid_map_core)
│   ├── ROS接口 (grid_map_ros)
│   ├── PCL集成 (grid_map_pcl)
│   └── RViz插件 (grid_map_rviz_plugin)
└── velocity_smoother_ext/    # 速度平滑器扩展
    └── 高级平滑算法
```

---

## 📋 系统要求

- **操作系统**: Ubuntu 22.04 LTS
- **ROS版本**: ROS 2 Humble Hawksbill
- **依赖包**:
  - `nav2_core`
  - `nav2_msgs`
  - `grid_map_core`
  - `pluginlib`

---

## 🚀 快速开始

### 1. 编译安装

```bash
# 加载ROS2环境
source /opt/ros/humble/setup.bash

# 编译所有扩展插件
colcon build --packages-select nav2_ext_plugins \
  --cmake-args -DCMAKE_BUILD_TYPE=Release

# 加载编译结果
source install/setup.bash
```

### 2. 配置Nav2使用扩展插件

编辑 `nav2_params.yaml`:

```yaml
# 代价地图配置
local_costmap:
  local_costmap:
    ros__parameters:
      plugins: ["voxel_layer", "inflation_layer"]
      voxel_layer:
        plugin: "nav2_costmap_2d::VoxelLayer"
        enabled: true

# 速度平滑器配置
velocity_smoother:
  ros__parameters:
    smoothing_frequency: 20.0
    max_velocity: [0.5, 0.0, 2.5]
    max_accel: [2.5, 0.0, 3.2]
```

---

## 📚 插件详解

### 1. 速度平滑器扩展 (velocity_smoother_ext)

#### 功能特性
- **多模式平滑**: 支持开环和闭环速度平滑
- **运动约束**: 基于速度、加速度和死区限制
- **超时保护**: 自动停止长时间无命令的机器人
- **高频插值**: 支持高于Nav2频率的平滑输出

#### 配置参数
```yaml
velocity_smoother:
  ros__parameters:
    smoothing_frequency: 20.0      # 平滑频率 (Hz)
    feedback: "OPEN_LOOP"          # 反馈模式
    max_velocity: [0.5, 0.0, 2.5] # 最大速度 [Vx, Vy, Vw]
    max_accel: [2.5, 0.0, 3.2]    # 最大加速度 [Ax, Ay, Aw]
    velocity_timeout: 1.0          # 速度超时时间 (s)
```

### 2. 代价地图强度层 (costmap_intensity)

#### 功能特性
- **强度感知**: 基于传感器强度信息的代价计算
- **3D体素**: 支持三维体素地图构建
- **实时更新**: 动态障碍物检测和更新
- **RViz可视化**: 完整的三维可视化支持

#### 使用方法
```bash
# 启动体素可视化
ros2 run costmap_intensity costmap_intensity_markers \
  voxel_grid:=/local_costmap/voxel_grid \
  visualization_marker:=/voxel_markers
```

### 3. 行为树扩展插件 (behavior_ext_plugins)

#### 功能特性
- **智能后退**: 带旋转的避障后退动作
- **任务恢复**: 复杂场景下的行为恢复机制
- **状态感知**: 基于传感器反馈的智能决策

### 4. GridMap生态系统集成

#### 核心特性
- **多层地图**: 支持elevation, variance, traversability等多层数据
- **PCL集成**: 完整的点云处理管道
- **滤波器框架**: 可扩展的地图滤波器系统
- **可视化工具**: RViz插件支持实时地图显示

---

## 🔧 开发指南

### 添加新的Nav2插件

1. **继承基类**:
   ```cpp
   #include "nav2_core/plugin_base.hpp"

   class MyPlugin : public nav2_core::PluginBase
   {
   public:
     void configure(...) override;
     void activate() override;
     void deactivate() override;
     void cleanup() override;
   };
   ```

2. **注册插件**:
   ```xml
   <plugin plugin="my_plugin::MyPlugin">
     <library>my_plugin</library>
     <class>my_plugin::MyPlugin</class>
   </plugin>
   ```

3. **导出插件**:
   ```cmake
   pluginlib_export_plugin_description_file(nav2_core plugin.xml)
   ```

---

## 🐛 故障排除

### 插件加载失败
```
原因: 插件库未正确安装或路径错误
解决: 检查pluginlib描述文件和库文件路径
```

### 速度平滑异常
```
原因: 参数配置不匹配机器人特性
解决: 根据机器人规格调整速度和加速度限制
```

### GridMap显示问题
```
原因: RViz配置或坐标系问题
解决: 检查fixed_frame设置和TF树完整性
```

---

## 📚 相关文档

- [Nav2官方文档](https://navigation.ros.org/)
- [GridMap文档](https://github.com/ANYbotics/grid_map)
- [BehaviorTree.CPP](https://www.behaviortree.dev/)

---

## 🤝 贡献指南

欢迎提交问题和改进建议！

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

---

## 📄 许可证

本项目采用 [Apache 2.0 许可证](LICENSE)。

---

## 📞 联系与支持

- **项目主页**: [SCURC Navigation Simulation](https://github.com/OH1412/SCURC_Nav_Sim)
- **技术支持**: [GitHub Issues](https://github.com/OH1412/SCURC_Nav_Sim/issues)
- **维护者**: [Pangolin战队](https://github.com/mose1s/RC_vision_2026)

---

*最后更新: 2026年1月23日*
