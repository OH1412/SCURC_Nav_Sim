# FAST-LIVO2 ROS2 HUMBLE

[![ROS 2 Humble](https://img.shields.io/badge/ROS2-Humble-22314E.svg)](https://docs.ros.org/en/humble/)

[![Ubuntu 22.04](https://img.shields.io/badge/Ubuntu-22.04-E95420.svg)](https://releases.ubuntu.com/jammy/)

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

[![开发状态](https://img.shields.io/badge/开发状态-维护中-orange.svg)]()

## 📖 项目简介

FAST-LIVO2 is a LiDAR-Inertial Odometry and Mapping system. This repository is adapted from the original FAST-LIVO2 project to be fully compatible with ROS 2 Humble Hawksbill, optimized for Livox Mid-360 LiDAR.

### ⚠️ 重要安装说明

**注意事项**：本仓库的安装流程与 [FAST_LIVO2_ROS2](https://github.com/mose1s/RC_vision_2026/tree/main/Slam/) 基本一致，仅需注意以下特殊步骤：

1. 安装前需将仓库中 `/src/icp_relocalization` 文件夹临时移出 ROS2 工作空间的 `src` 目录；

2. 完成 `livox_ros_driver2` 编译后，再将 `icp_relocalization` 移回 `src` 目录；

3. 临时方案仅用于规避编译冲突，后续会优化 `build.sh` 脚本修复该问题。

### 🔗 参考链接

- 原始仓库：https://github.com/SuperLDG/FASTLIVO2_ROS2

- 定位模块参考：https://github.com/PolarisXQ/Fast-LIO2-Localization

- 持续更新：https://github.com/mose1s/RC_vision_2026

- 父项目：[SCURC Navigation Simulation](https://github.com/OH1412/SCURC_Nav_Sim)

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

- **维护者**: Pangolin战队 getting

---

*最后更新: 2025年11月5日*
