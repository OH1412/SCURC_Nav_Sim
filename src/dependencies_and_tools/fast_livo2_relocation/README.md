# FAST-LIVO2 ROS2 Humble (快速重定位系统)

[![ROS 2 Humble](https://img.shields.io/badge/ROS2-Humble-22314E.svg)](https://docs.ros.org/en/humble/)
[![Ubuntu 22.04](https://img.shields.io/badge/Ubuntu-22.04-E95420.svg)](https://releases.ubuntu.com/jammy/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Status](https://img.shields.io/badge/Status-Maintained-orange.svg)]()

## 📖 项目简介

FAST-LIVO2 ROS2 Humble 是基于 FAST-LIVO2 算法的 LiDAR-Inertial Odometry 和 Mapping 系统。该版本已完全适配 ROS 2 Humble Hawksbill，专为 Livox Mid-360 激光雷达优化，提供高精度的实时定位和建图功能。

### 🎯 核心特性

- **🔥 高性能SLAM**: 基于FAST-LIVO2算法的实时激光-惯性里程计和建图
- **🤖 重定位功能**: 集成ICP重定位模块，支持大范围环境下的快速重定位
- **📊 实时性能**: 针对Livox Mid-360优化，提供稳定的高频里程计输出
- **🔗 ROS2集成**: 完全兼容ROS 2 Humble，支持现代机器人框架

---

## 🏗️ 系统架构

### 核心组件

```
fast_livo2_relocation/
├── fast_livo/               # FAST-LIVO2核心SLAM算法
│   ├── src/                 # 核心算法实现
│   ├── launch/              # 启动配置文件
│   └── config/              # 参数配置文件
├── livox_ros_driver2/       # Livox雷达ROS2驱动
│   ├── src/                 # 驱动源码
│   ├── launch/              # 驱动启动配置
│   └── config/              # 雷达配置
├── icp_relocalization/      # ICP重定位模块
│   ├── src/                 # 重定位算法
│   └── config/              # 重定位参数
└── vikit/                   # 视觉工具库依赖
```

---

## 📋 系统要求

- **操作系统**: Ubuntu 22.04 LTS
- **ROS版本**: ROS 2 Humble Hawksbill
- **硬件要求**:
  - Livox Mid-360 激光雷达 (推荐) 或其他Livox系列雷达
  - IMU传感器 (可选，用于提高定位精度)
  - CPU: Intel i5 或 AMD Ryzen 5 以上
  - 内存: 8GB RAM 以上

---

## 🛠️ 安装指南

### ⚠️ 重要安装说明

**编译顺序注意事项**：由于包间依赖关系，建议按以下顺序安装：

1. **确保已加载livox_ros_driver2安装路径**
2. **先编译icp_relocalization工作包**

### 1. 环境准备

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装基础依赖
sudo apt install -y libpcl-dev libeigen3-dev libopencv-dev

# 安装Sophus (李代数库)
sudo apt install ros-humble-sophus
```

### 2. 工作空间准备

```bash
# 创建ROS2工作空间 (如果不存在)
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws/src

# 复制项目文件到工作空间
cp -r /path/to/fast_livo2_relocation/* ./

# 临时移出icp_relocalization (避免编译冲突)
mv icp_relocalization ~/temp_icp_relocalization
```

### 3. 编译Livox驱动

```bash
# 加载ROS2环境
source /opt/ros/humble/setup.bash

# 编译livox_ros_driver2
cd livox_ros_driver2
./build.sh humble

# 验证编译成功
ls build/
```

### 4. 完整编译

```bash
# 移回icp_relocalization
mv ~/temp_icp_relocalization ./icp_relocalization

# 返回工作空间根目录
cd ~/ros2_ws

# 编译所有包
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release

# 加载环境
source install/setup.bash
```

---

## 🚀 使用指南

### 1. 启动雷达驱动

```bash
# 启动Livox Mid-360雷达
ros2 launch livox_ros_driver2 msg_MID360_launch.py
```

### 2. 启动SLAM建图

```bash
# 启动FAST-LIVO2建图 (带RViz可视化)
ros2 launch fast_livo mapping_avia.launch.py use_rviz:=true

# 或不带可视化 (轻量级模式)
ros2 launch fast_livo mapping_avia.launch.py
```

### 3. 重定位模式

```bash
# 启动重定位节点
ros2 launch icp_relocalization relocalization.launch.py
```

### 4. 功能验证

```bash
# 检查节点状态
ros2 node list | grep -E "(fast_livo|icp_reloc)"

# 监控里程计输出
ros2 topic hz /Odometry

# 查看TF变换
ros2 run tf2_ros tf2_echo map odom
```

---

## ⚙️ 配置说明

### FAST-LIVO2 参数配置

编辑 `fast_livo/config/avia.yaml`:

```yaml
# 激光雷达参数
lidar_type: 1                    # Livox Avia = 1
blind: 0.1                       # 盲区距离 (米)

# IMU参数
imu_topic: "/livox/imu"          # IMU话题
imu_rate: 200                    # IMU频率 (Hz)

# 地图参数
map_resolution: 0.4              # 地图分辨率
cube_side_length: 1000           # 立方体边长

# 算法参数
runtime_pos_log_enable: 0        # 位置日志
pcd_save_enable: 0              # PCD保存
```

### 重定位参数配置

编辑 `icp_relocalization/config/relocalization.yaml`:

```yaml
# ICP参数
icp_max_iterations: 50           # 最大迭代次数
icp_transformation_epsilon: 1e-8  # 变换收敛阈值
icp_euclidean_fitness_epsilon: 1e-8  # 欧几里得适应度阈值

# 匹配参数
max_correspondence_distance: 1.0  # 最大对应距离
voxel_grid_size: 0.05            # 体素网格大小
```

---

## 🔍 话题和服务接口

### 发布话题

| 话题名 | 类型 | 描述 |
|--------|------|------|
| `/cloud_registered` | `sensor_msgs/PointCloud2` | 去畸变后的点云数据 |
| `/Odometry` | `nav_msgs/Odometry` | 里程计信息 |
| `/path` | `nav_msgs/Path` | 轨迹路径 |
| `/map` | `sensor_msgs/PointCloud2` | 全局地图点云 |

### 订阅话题

| 话题名 | 类型 | 描述 |
|--------|------|------|
| `/livox/lidar` | `livox_ros_driver2/CustomMsg` | Livox雷达原始数据 |
| `/livox/imu` | `sensor_msgs/Imu` | IMU传感器数据 |

### 服务接口

| 服务名 | 类型 | 描述 |
|--------|------|------|
| `/save_map` | `std_srvs/Empty` | 保存当前地图 |
| `/relocalize` | `icp_relocalization/Relocalize` | 触发重定位 |

---

## 🔧 故障排除

### 1. 找不到 livox_lidar_sdk_shared 库

```bash
# 查找库文件
find /usr/lib /usr/local/lib ~/ros2_ws -name "liblivox_lidar_sdk_shared.so"

# 添加到库路径
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib

# 或者重新安装Livox-SDK
git clone https://github.com/Livox-SDK/Livox-SDK2.git
cd Livox-SDK2 && mkdir build && cd build
cmake .. && make -j$(nproc) && sudo make install
```

### 2. 编译 Sophus 失败

```bash
# 使用预编译版本
sudo apt install ros-humble-sophus

# 或源码编译 (如果版本不匹配)
git clone https://github.com/strasdat/Sophus.git
cd Sophus && git checkout a621ff
mkdir build && cd build
cmake .. && make -j$(nproc) && sudo make install
```

### 3. RViz 显示异常

```bash
# 检查TF树完整性
ros2 run tf2_tools view_frames.py

# 手动启动RViz并加载配置
rviz2 -d $(ros2 pkg prefix fast_livo)/share/fast_livo/rviz_cfg/mapping.rviz
```

---

## 📊 性能指标

- **定位精度**: < 10cm (相对误差)
- **实时性能**: 100Hz 里程计输出
- **内存占用**: ~500MB (取决于地图大小)
- **支持雷达**: Livox Mid-360, Avia, Horizon

---

## 🔗 参考链接

- **原始仓库**: https://github.com/SuperLDG/FASTLIVO2_ROS2
- **定位模块**: https://github.com/PolarisXQ/Fast-LIO2-Localization
- **团队项目**: https://github.com/mose1s/RC_vision_2026
- **父项目**: https://github.com/OH1412/SCURC_Nav_Sim

---

## 📄 许可证

本项目采用 [Apache 2.0 许可证](LICENSE)。

---

## 📞 联系与支持

- **项目地址**: https://github.com/OH1412/SCURC_Nav_Sim
- **技术支持**: https://github.com/OH1412/SCURC_Nav_Sim/issues
- **维护团队**: [Pangolin战队](https://github.com/mose1s/RC_vision_2026)
- **贡献者**: [Pangolin战队全体成员](https://github.com/mose1s/RC_vision_2026)

---

*最后更新: 2026年1月23日*

## 2. 环境依赖 (Prerequisites)

### 2.1 Ubuntu & ROS 2

- 系统版本：Ubuntu 22.04 LTS

- ROS 2 安装：[ROS 2 Humble 官方安装指南](https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debians.html)（务必选择ROS2，而非ROS1）

### 2.2 基础库依赖

```bash
# 一键安装PCL、Eigen、OpenCV（Ubuntu 22.04 预装版本满足要求）
sudo apt install -y libpcl-dev libeigen3-dev libopencv-dev
```

- PCL ≥ 1.12（Ubuntu 22.04 默认版本为1.12，无需手动编译）

- Eigen ≥ 3.4（Ubuntu 22.04 默认版本为3.4，无需手动编译）

- OpenCV ≥ 4.5（Ubuntu 22.04 默认版本为4.5，无需手动编译）

### 2.3 Sophus

#### 方式1：二进制安装（推荐）

```bash
sudo apt install ros-humble-sophus
```

#### 方式2：源码编译（解决版本冲突）

```bash
git clone https://github.com/strasdat/Sophus.git
cd Sophus && git checkout a621ff
mkdir build && cd build && cmake .. && make -j$(nproc)
sudo make install
```

**编译报错修复**：若出现 `so2.cpp:32:26: error: lvalue required as left operand of assignment`，修改 `so2.cpp`：

```diff
namespace Sophus
{
SO2::SO2()
{
  unit_complex_.real(1.);
  unit_complex_.imag(0.);
}
```

### 2.4 Vikit

直接使用本仓库 `/src/vikit` 目录下的源码，无需额外下载。编译时会随工作空间一起构建，无需单独安装。

### 2.5 livox_ros_driver2

Livox雷达驱动（ROS2版本），兼容CustomMsg格式：

```bash
# 克隆源码（若已从本仓库复制则跳过）
git clone https://github.com/Livox-SDK/livox_ros_driver2.git
```

**为什么不用 livox_ros_driver？**

`livox_ros_driver` 无原生ROS2支持，而 `livox_ros_driver2` 的CustomMsg格式与前者一致，且完全适配ROS2 Humble。

## 3. 编译构建 (Build)

### 3.1 工作空间准备

```bash
# 创建ROS2工作空间（若已存在则跳过）
mkdir -p ~/ros2_ws/src && cd ~/ros2_ws/src

# 克隆本仓库（或复制仓库内3个核心文件夹：fast_livo、livox_ros_driver2、vikit）
git clone https://github.com/OH1412/FAST-LIVO2-ROS2-Humble.git

# 临时移出icp_relocalization（解决编译冲突）
mv FAST-LIVO2-ROS2-Humble/src/icp_relocalization ~/temp_icp_relocalization
```

### 3.2 编译livox_ros_driver2

```bash
# 加载ROS2环境
source /opt/ros/humble/setup.bash

# 进入livox_ros_driver2目录编译
cd ~/ros2_ws/src/FAST-LIVO2-ROS2-Humble/src/livox_ros_driver2
./build.sh humble

# 移回icp_relocalization
mv ~/temp_icp_relocalization ~/ros2_ws/src/FAST-LIVO2-ROS2-Humble/src/icp_relocalization
```

### 3.3 编译整个工作空间

```bash
# 回到工作空间根目录
cd ~/ros2_ws

# 编译（--symlink-install 方便调试）
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release

# 加载编译结果
source install/setup.bash
```

## 4. 运行测试 (Run)

### 4.1 启动Livox雷达驱动

```bash
# 启动Mid-360雷达（livox_ros_driver2包）
ros2 launch livox_ros_driver2 msg_MID360_launch.py
```

### 4.2 启动FAST-LIVO2建图

```bash
# 启动SLAM建图（fast_livo包），启用RViz可视化
ros2 launch fast_livo mapping_avia.launch.py use_rviz:=True
```

## 5. 常见报错解决

### 5.1 找不到 `liblivox_lidar_sdk_shared.so` 共享库

#### 步骤1：查找库文件

```bash
# 全局搜索库文件
find /usr/lib /usr/local/lib ~/ros2_ws -name "liblivox_lidar_sdk_shared.so"
```

#### 步骤2：添加库路径（以找到 `/usr/local/lib` 为例）

```bash
# 临时生效
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib

# 永久生效（写入.bashrc）
echo 'export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib' >> ~/.bashrc
source ~/.bashrc
```

#### 步骤3：库文件缺失时重新安装Livox-SDK2

```bash
git clone https://github.com/Livox-SDK/Livox-SDK2.git
cd Livox-SDK2 && mkdir build && cd build
cmake .. && make -j$(nproc) && sudo make install
```

### 5.2 image_transport/compressed_sub 插件缺失

```bash
# 安装ROS2图像压缩传输插件
sudo apt install -y ros-humble-image-transport-plugins
```

## 📞 联系与支持

- **本仓库地址**: [FAST-LIVO2-ROS2-Humble](https://github.com/OH1412/SCURC_Nav_Sim)

- **父项目文档**: [SCURC Navigation Simulation](https://github.com/mose1s/RC_vision_2026)

- **技术支持**: [GitHub Issues](https://github.com/OH1412/FAST-LIVO2-ROS2-Humble/issues)

- **维护者**: [Pangolin战队](https://github.com/mose1s/RC_vision_2026) @[Getting](https://github.com/Getting05)

- **贡献者**: [Pangolin战队全体成员](https://github.com/mose1s/RC_vision_2026)
---

*最后更新: 2025年11月5日*
