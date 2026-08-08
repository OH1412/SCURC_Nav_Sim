# SCURC 机器人导航仿真系统 (SCURC Navigation Simulation)

[![ROS 2 Humble](https://img.shields.io/badge/ROS2-Humble-22314E.svg)](https://docs.ros.org/en/humble/)

[![Ubuntu 22.04](https://img.shields.io/badge/Ubuntu-22.04-E95420.svg)](https://releases.ubuntu.com/jammy/)

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

- **版本**: 1.0.0
- **状态**: 开发中 🚧
- **ROS版本**: ROS 2 Humble Hawksbill
- **Ubuntu版本**: Ubuntu 22.04 LTS
- **最后更新**: 2026年1月24日

### 📝 重要说明

1. **文档状态**: 本README暂未人工修正，仅作参考；项目构建步骤、依赖需自行验证。
2. **构建指南**: 项目构建步骤已在本文档中说明，如遇问题可优先参考各模块内的README.md。
3. **版本兼容**: 当前文档基于ROS 2 Humble + Ubuntu 22.04环境编写。
4. **技术支持**: 如遇问题，请查看[常见问题](#-常见问题-faq)部分或提交[GitHub Issue](https://github.com/OH1412/SCURC_Nav_Sim/issues)。
5. **基础导航说明**: 该仓库为基础导航功能。只需先构建 Getting 上传的 FAST-LIVO 功能包，`source` 其工作空间后，再构建本仓库即可运行。

### 🔍 快速导航

#### 📋 基础信息
- [📖 项目简介](#-项目简介)
- [🚀 核心功能](#-核心功能)
- [📋 系统要求](#-系统要求)

#### 🛠️ 部署指南
- [🛠️ 安装指南](#️-安装指南)
- [🎯 使用指南](#-使用指南)
- [📊 核心配置](#-核心配置)
- [🚗 实车使用指南](#-实车使用指南)

#### 🔧 开发与维护
- [📚 关键组件详解](#-关键组件详解)
- [🔧 开发与调试](#-开发与调试)
- [❓ 常见问题 (FAQ)](#-常见问题-faq)
- [🤝 贡献指南](#-贡献指南)

#### 📞 联系与支持
- [📄 许可证](#-许可证)
- [📞 联系方式](#-联系方式)

## 📖 项目简介

SCURC_Nav_Sim 是基础导航功能仓库，面向 **ROS 2 Humble**。当前保留基础导航相关模块：导航启动、Nav2 扩展插件、地形分析/局部规划、串口驱动，以及激光/车辆仿真与可视化工具。定位与里程计由 Getting 上传的 FAST-LIVO 功能包提供，需先构建并 `source` 该工作空间后再构建本仓库。

### 系统概览

- `legged_bringup`: 启动文件、参数与 RViz 配置
- `nav2_ext_plugins`: 行为插件、强度代价地图层、速度平滑器扩展
- `autonomous_exploration_development_environment`: 地形分析、局部规划与仿真/可视化工具
- `serial` / `serial_driver`: 串口库与 ROS2 串口驱动桥接

### 核心模块架构

<details>
<summary>点击展开完整目录结构</summary>

```
SCURC_Nav_Sim/
├── src/
│   ├── dependencies_and_tools/          # 依赖工具和算法包
│   │   ├── autonomous_exploration_development_environment/
│   │   │   └── src/
│   │   │       ├── loam_interface/
│   │   │       ├── local_planner/
│   │   │       ├── sensor_scan_generation/
│   │   │       ├── terrain_analysis/
│   │   │       ├── terrain_analysis_ext/
│   │   │       ├── vehicle_simulator/
│   │   │       ├── velodyne_simulator/
│   │   │       ├── visualization_tools/
│   │   │       ├── waypoint_example/
│   │   │       └── waypoint_rviz_plugin/
│   │   └── control_panel/               # 控制面板 (开发中)
│   ├── navigation_plugins/              # 导航扩展插件
│   │   └── nav2_ext_plugins/            # Nav2扩展插件集合
│   │       ├── behavior_ext_plugins/    # 行为插件扩展
│   │       ├── costmap_intensity/       # 强度代价地图层
│   │       └── velocity_smoother_ext/   # 速度平滑器扩展
│   ├── robot_functionality/             # 机器人功能模块
│   │   ├── legged_bringup/              # 机器人启动配置 (Launch/Params)
│   │   ├── serial-ros2/                 # 串口库
│   │   └── serial_driver_ros2/          # 串口驱动
├── load_all.sh                         # 环境加载脚本
└── README.md
```

</details>

### 技术栈

| 核心组件 | 技术栈 | 版本要求 | 关键特性 |
|----------|--------|----------|----------|
| **基础环境** | Ubuntu + ROS 2 | 22.04 LTS + Humble | Jammy + LTS版本 + DDS通信 |
| **编程语言** | C++14/17 + Python | GCC 11+ + 3.10 | ROS2原生接口 + 常用脚本支持 |
| **导航控制** | Navigation2 + Nav2插件 | ROS2原生 + 扩展 | 插件化架构 + 代价地图层 + 速度平滑 |
| **地形处理** | terrain_analysis 系列 | 无特殊版本 | 地形可通行性评估与障碍处理 |
| **仿真与可视化** | velodyne_simulator 等 | 无特殊版本 | 激光/车辆仿真与可视化工具 |
| **串口通信** | serial + serial_driver | 无特殊版本 | `cmd_vel` 串口桥接 |

---

## 🚀 核心功能

### 1. 🎯 定位/里程计对接
- **外部 FAST-LIVO 功能包**: 由 Getting 上传的 FAST-LIVO 提供定位与里程计
- **loam_interface**: 对接外部定位结果并提供必要话题

### 2. 🧭 导航控制与扩展插件
- **Navigation2**: ROS2 官方导航框架
- **Nav2 扩展插件**: 强度代价地图层、速度平滑器、行为插件

### 3. 🗺️ 地形分析与局部规划
- **terrain_analysis/terrain_analysis_ext**: 地形可通行性评估
- **local_planner**: 局部规划与避障控制

### 4. 🧰 启动与可视化
- **legged_bringup**: 启动文件、参数与 RViz 配置
- **visualization_tools**: 可视化工具与 RViz 插件

### 5. 🔌 串口通信
- **serial + serial_driver**: `cmd_vel` 串口桥接与驱动

---

## 📋 系统要求

### 硬件配置

| 组件 | 最低配置 | 推荐配置 | 说明 |
|------|----------|----------|------|
| **CPU** | Intel i5 / AMD Ryzen 5 | Intel i7 / AMD Ryzen 7 | 编译和运行需要多核支持 |
| **内存** | 8GB RAM | 16GB RAM | 基础导航与仿真运行 |
| **GPU** | (可选) | 任意支持 OpenGL 的显卡 | 仅用于 RViz/仿真显示 |
| **存储** | 5GB SSD | 100GB SSD | 包含所有依赖和构建产物 |
| **网络** | 千兆以太网 | 万兆以太网 | 大量传感器数据传输 |

### 传感器配置

- **激光雷达**: Livox Mid-360 或其他激光雷达
- **IMU**: 支持 ROS 标准 IMU 消息格式
- **计算平台**: 支持 Ubuntu 22.04 的硬件平台

### 软件依赖

- **操作系统**: Ubuntu 22.04 LTS (Jammy Jellyfish)
- **ROS版本**: ROS 2 Humble Hawksbill (官方LTS)
- **Python版本**: 3.10 (ROS 2 Humble要求)

---

## 🚀 快速开始

### 5分钟快速部署 (推荐新用户)

```bash
# 1. 构建 FAST-LIVO 功能包 (Getting 上传)
cd /path/to/fastlivo_ws
colcon build --symlink-install
source install/setup.bash

# 2. 构建本仓库
cd ~/SCURC_Nav_Sim
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

**成功标志**: RViz中显示机器人模型、地图和导航路径，导航节点正常运行。

---

## 🚗 实车使用指南

### 环境准备（实车）

- 时间配置：全局使用真实时间（use_sim_time=false，已在各 Launch 默认）
- 依赖安装：点云转激光扫描（AMCL 需要 /scan）

```bash
sudo apt install ros-humble-pointcloud-to-laserscan
```

- 驱动与桥接：`serial_driver` 串口桥接已在 `bringup_in_real.launch.py` 自动启动

### 一键启动（默认真实时间）

```bash
source ./load_all.sh
ros2 launch legged_bringup bringup_in_real.launch.py
```

可选：需要同时起仿真（不推荐与实车同开）

```bash
ros2 launch legged_bringup bringup_in_real.launch.py start_sim:=true
```

### 验证与自检

```bash
# 检查 TF 链（必须存在 map -> odom -> base_link）
ros2 run tf2_ros tf2_echo map base_link | head

# 检查 /scan 是否存在（frame_id=base_link，时间戳持续更新）
ros2 topic echo /scan --once

# 检查速度指令桥接（Nav2 输出 → 串口驱动订阅）
ros2 topic echo /cmd_vel
```

### 常见问题（简要）

- /scan 的 inf 过多导致 AMCL 不稳：请调整 `pointcloud_to_laserscan` 参数
  - `angle_increment`: 0.01745〜0.026（1°〜1.5°）
  - `min_height/max_height`: 围绕安装高度的窄窗口（如 -0.2〜0.3）
  - `range_min/max`: 0.3〜15/20（按场景）
  - 示例：

    ```bash
    ros2 launch legged_bringup pointcloud_to_scan.launch.py \
      angle_increment:=0.026 range_min:=0.3 range_max:=15.0 \
      min_height:=-0.15 max_height:=0.25 valid_ratio_threshold:=0.5
    ```

更多排查与说明，请参考 `src/robot_functionality/legged_bringup/README.md` 的“常见问题（实车）”。

---

## 🛠️ 安装指南

### 1. 基础环境准备

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装ROS 2 Humble (如遇密钥错误请参考ROS官方文档)
sudo apt install -y software-properties-common
sudo add-apt-repository universe
sudo apt update && sudo apt install -y curl
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(source /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
sudo apt update
sudo apt install -y ros-humble-desktop ros-humble-grid-map-* ros-humble-gazebo-ros-pkgs ros-humble-pointcloud-to-laserscan
```

### 2. 工作空间搭建

```bash
mkdir -p ~/SCURC_Nav_Sim/src
cd ~/SCURC_Nav_Sim

# 克隆项目
git clone https://github.com/OH1412/SCURC_Nav_Sim.git src
```

### 3. 前置构建 (FAST-LIVO 功能包)

该仓库是基础导航功能，需先构建 Getting 上传的 FAST-LIVO 功能包，并在本仓库编译前 `source` 其工作空间。

```bash
# 进入 FAST-LIVO 功能包工作空间
cd /path/to/fastlivo_ws
# 注意这里具体构建参考Getting的README
colcon build --symlink-install
source install/setup.bash
```

### 4. 编译工作空间

```bash
# 加载ROS2环境
source /opt/ros/humble/setup.bash

# 首次编译可能较慢，请耐心等待
colcon build --symlink-install

# 加载编译结果
source install/setup.bash
```

### 5. 一键环境加载

项目提供了 `load_all.sh` 脚本，自动加载 ROS 2 环境、工作空间及 Gazebo 模型路径。

```bash
chmod +x load_all.sh
# 每次打开新终端时执行
source ./load_all.sh
```

---

## 🎯 使用指南

### 1. 启动定位与建图 (SLAM + Mapping)

```bash
# 终端 1: 启动Livox驱动与FAST-LIVO定位
ros2 launch fast_livo mapping_avia.launch.py

```

### 2. 启动导航栈 (Nav2)

```bash
# 终端 2: 启动Nav2及相关节点
ros2 launch legged_bringup navigation.launch.py
```

---

## 📊 核心配置

### 导航参数配置

编辑 `src/robot_functionality/legged_bringup/params/nav2_params.yaml`:

```yaml
# 全局规划器
planner_server:
  ros__parameters:
    planner_plugins: ["GridBased"]
    GridBased:
      plugin: "nav2_navfn_planner/NavfnPlanner"
      use_astar: true

# 局部规划器
controller_server:
  ros__parameters:
    controller_plugins: ["FollowPath"]
    FollowPath:
      plugin: "dwb_core::DWBLocalPlanner"
```

---

## ❓ 常见问题 (FAQ)

### 1. Nav2 报错 `Computing map coords failed`？

  * **原因**：TF 树断裂或时钟不同步。
  * **解决**：
    1. 检查 `fast_livo` 是否正常发布 `/odom` 到 `/map` 的变换。
    2. 如果使用仿真，确保所有 Launch 文件中 `use_sim_time` 都设置为 `true`。

---

## 🔧 开发与调试

### RViz可视化配置

1. 启动RViz2
2. 加载 `legged_bringup/rviz/nav2_default_view.rviz`
3. 确认 Fixed Frame 与定位发布一致（通常为 `map` 或 `odom`）

### 日志与调试

```bash
# 查看节点状态
ros2 node list

# 查看话题列表
ros2 topic list

# 查看服务列表
ros2 service list

# 监控特定话题
ros2 topic echo /cmd_vel
```

### 性能监控

```bash
# 监控系统资源使用
ros2 run rqt_runtime_monitor rqt_runtime_monitor

# 查看节点计算图
ros2 run rqt_graph rqt_graph
```

---

## 📚 关键组件详解

### 1. 🎯 定位/里程计对接

- **FAST-LIVO 功能包**: 由 Getting 上传，提供定位与里程计话题
- **loam_interface**: 对接外部定位输出，作为导航系统输入

### 2. 🗺️ 地形分析与局部规划

- **terrain_analysis / terrain_analysis_ext**: 地形可通行性评估
- **sensor_scan_generation**: 点云/扫描数据整理与话题转换
- **local_planner**: 局部规划与避障控制

### 3. 🧭 Nav2 扩展插件

- **costmap_intensity**: 强度代价地图层
- **velocity_smoother_ext**: 速度平滑器扩展
- **behavior_ext_plugins**: 行为插件扩展

### 4. 🧰 启动与串口驱动

- **legged_bringup**: 启动文件、参数与 RViz 配置
- **serial / serial_driver**: 串口库与 ROS2 串口驱动桥接

---

## 🤝 贡献指南

### 开发流程

1. **准备工作**
   - Fork 项目到个人仓库
   - 克隆到本地：`git clone https://github.com/YOUR_USERNAME/SCURC_Nav_Sim.git`
   - 创建功能分支：`git checkout -b feature/amazing-feature`

2. **代码开发**
   - 遵循ROS2和C++/Python编码规范
   - 添加必要的单元测试和文档
   - 确保代码通过编译和运行测试

3. **提交规范**
   ```bash
   # 提交信息格式
   git commit -m "feat: 添加新的导航算法优化
   - 实现A*路径规划改进
   - 添加地形代价函数
   - 更新相关配置文件"
   ```

4. **测试验证**
   - 在仿真环境中测试新功能
   - 验证与现有模块的兼容性
   - 性能测试确保无性能退化

5. **提交PR**
   - 推送到个人仓库：`git push origin feature/amazing-feature`
   - 在GitHub上创建Pull Request
   - 详细描述变更内容和测试结果

### 代码规范

#### ROS2 包开发规范
- **包命名**: 使用snake_case，清晰表达功能
- **消息定义**: 在interface包中统一管理
- **参数配置**: 使用YAML文件，支持运行时调整
- **日志输出**: 使用ROS2日志系统，适当设置日志级别

#### C++ 编码规范
- **标准**: C++17, 使用智能指针和STL容器
- **命名**: 类使用PascalCase，函数和变量使用snake_case
- **注释**: Doxygen格式，函数接口要有完整说明
- **异常处理**: 使用适当的异常处理，避免程序崩溃

#### Python 编码规范
- **标准**: PEP 8, 使用类型注解
- **导入**: 分层导入，标准库→第三方库→本地模块
- **文档**: 使用Google风格docstring
- **测试**: 提供完整的单元测试覆盖

### 文档要求

- **README**: 为新增模块提供完整的README文档
- **API文档**: 重要接口要有详细的参数说明和使用示例
- **配置说明**: 参数文件要有清晰的注释和取值范围
- **使用指南**: 提供从安装到运行的完整教程

### 测试要求

- **单元测试**: 为核心算法提供单元测试
- **集成测试**: 验证模块间接口的正确性
- **性能测试**: 确保功能优化不影响系统性能
- **回归测试**: 修改现有功能时要验证兼容性

### 评审标准

PR评审将检查：
- ✅ 代码质量和规范性
- ✅ 功能完整性和正确性
- ✅ 文档完整性和准确性
- ✅ 测试覆盖率和有效性
- ✅ 对现有功能的兼容性
- ✅ 性能影响评估

---

## 📄 许可证

本项目采用 [Apache 2.0 许可证](LICENSE) 开源。第三方依赖包遵循其原始协议。

---


---

## 📞 联系方式

- **项目维护者**: [Pangolin战队](https://github.com/mose1s/RC_vision_2026) @[OH](https://github.com/OH1412)
- **贡献者**: [Pangolin战队全体成员](https://github.com/mose1s/RC_vision_2026)
- **技术支持**: [GitHub Issues](https://github.com/OH1412/SCURC_Nav_Sim/issues)  
- **文档**: [项目Wiki](https://github.com/OH1412/SCURC_Nav_Sim/wiki)

---

## 🗺️ 路线图 (Roadmap)

### 已完成 ✅
- [x] 基础导航构建与启动流程
- [x] Nav2 扩展插件（强度层/速度平滑/行为插件）
- [x] 地形分析与局部规划集成
- [x] 串口驱动与基础控制链路

### 进行中 🚧
- [ ] 启动脚本整理与文档精简
- [ ] 关键参数默认值梳理

### 计划中 📋
- [ ] 运行时诊断与日志优化
- [ ] 基础仿真流程补充说明

### 长期愿景 🎯
- [ ] 持续完善基础导航能力

---

*最后更新: 2026年5月19日*
