# Elevation Mapping Cupy (ROS 2 Humble)

[![ROS 2 Humble](https://img.shields.io/badge/ROS2-Humble-22314E.svg)](https://docs.ros.org/en/humble/)
[![CUDA 12.x](https://img.shields.io/badge/CUDA-12.x-76B900.svg)](https://developer.nvidia.com/cuda-toolkit)
[![Status](https://img.shields.io/badge/Status-Under%20Development-orange.svg)]()

## 📖 项目简介

**Elevation Mapping Cupy** 是一个基于 GPU 加速的机器人 2.5D 高程建图功能包。它利用 Python 的 CuPy 库调用 NVIDIA CUDA 进行并行计算，能够实时处理大量点云数据，构建以机器人为中心的高程地图 (Grid Map)。

该版本适配 **ROS 2 Humble** (Ubuntu 22.04)，适用于需要高性能地形感知的足式机器人或轮式机器人。

## 🚀 核心功能

### 主要特性
- **🔥 GPU 加速**：利用 CuPy 进行地图更新、漂移补偿和光线追踪清理，速度远快于 CPU 版本
- **🤖 机器人中心**：地图跟随机器人移动，始终维护机器人周围的局部地形
- **📊 多层地图**：支持 `elevation` (高度), `variance` (方差), `traversability` (可通行度), `normal` (法向量) 等多层数据
- **🔄 数据融合**：使用卡尔曼滤波融合多帧点云，消除传感器噪声
- **🔗 Nav2 对接**：支持发布 3D 点云供 Nav2 代价地图进行避障

### 开发状态
- ✅ **点云基础地图更新**: 功能完整
- 🚧 **图像基础地图更新**: 开发中

## 📋 系统要求

- **操作系统**: Ubuntu 22.04 LTS
- **ROS版本**: ROS 2 Humble Hawksbill
- **GPU**: NVIDIA 显卡 (必须支持 CUDA 12.x，显存 4GB+)
- **内存**: 8GB RAM 以上
- **Python**: 3.10

## 🛠️ 安装指南

### 1. 安装系统依赖

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装ROS 2相关包
sudo apt install ros-humble-grid-map-core ros-humble-grid-map-ros ros-humble-grid-map-rviz-plugin

# 安装编译依赖
sudo apt install libeigen3-dev libopencv-dev python3-pip python3-pybind11
```

### 2. 配置Python环境 (⚠️ 关键步骤)

**⚠️ 重要提示**：此包对Python库版本极其敏感。错误的Numpy或CuPy版本会导致节点崩溃或编译错误。请务必在Conda环境中按以下顺序安装：

#### 2.1 创建Conda环境

```bash
conda create -n elevation_mapping python=3.10
conda activate elevation_mapping
```

#### 2.2 安装ROS 2基础依赖

```bash
pip install rospkg empy==3.3.4 catkin_pkg lxml transforms3d netifaces psutil
```

#### 2.3 安装核心计算库 (版本锁定)

| 库名 | 版本要求 | 说明 |
|------|----------|------|
| **Numpy** | `< 2.0` | 必须降级，否则与ROS 2底层库冲突 |
| **CuPy** | `12.x` | CUDA 12.x专用，13.x会导致NVRTC编译错误 |
| **Shapely** | `>= 1.8.0` | 避免libgeos缺失错误 |

```bash
# 1. 锁定版本 (兼容性关键)
pip install "numpy<2.0" "opencv-python<=4.9.0.80"

# 2. 安装GPU加速库 (根据CUDA版本调整，推荐12.x)
pip install "cupy-cuda12x<13.0.0"

# 3. 安装几何与数学库
pip install "shapely>=1.8.0" scipy chainer
```

### 3. 编译工作空间

```bash
# 进入工作空间根目录
cd <your_workspace>

# 编译核心包 (忽略不兼容的ROS 1遗留包)
colcon build --packages-select elevation_mapping_cupy elevation_map_msgs --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release

# 加载编译结果
source install/setup.bash
```

## ⚙️ 配置说明

核心参数文件位于：`src/elevation_mapping_cupy/config/core/core_param.yaml`

### 1. 连接传感器

修改 `subscribers` 部分，将 `topic_name` 指向您的雷达或 SLAM 输出的点云话题：

```yaml
subscribers:
  pointcloud1:
    topic_name: '/cloud_registered'  # 修改为您实际的点云话题，例如 /livox/lidar
    data_type: 'pointcloud'
```

### 2. 地图精度与范围优化

建议使用 **5cm (0.05m)** 分辨率以平衡精度与性能。过高的分辨率会导致显存不足。

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| `resolution` | `0.05` | 分辨率 (米) |
| `map_length` | `20.0` | 地图边长 (米) |
| `cell_n` | `160000` | 总格子数 (自动计算) |
| `min_valid_distance` | `0.2` | 盲区半径 |
| `sensor_noise_factor` | `0.005` | 噪声因子，越小越灵敏 |
| `enable_visibility_cleanup` | `false` | 关闭可见性清理 |

```yaml
# 性能优化配置
resolution: 0.05                    # 分辨率 (米)
map_length: 20.0                    # 地图边长 (米)
cell_n: 160000                      # 总格子数 = (map_length / resolution)^2
min_valid_distance: 0.2             # 盲区半径
sensor_noise_factor: 0.005          # 传感器噪声因子
enable_visibility_cleanup: false    # 关闭可见性清理，防止地图闪烁
```

### 3. 坐标系设置

确保 TF 树完整，并正确设置初始化参考系：

```yaml
# TF 坐标系配置
map_frame: 'odom'                   # 固定坐标系
base_frame: 'base_link'             # 机器人基座坐标系
initialize_frame_id: ['base_link']  # 初始化参考系
initialize_tf_offset: [0.0]         # 初始化偏移
```

### 4. 开启 Nav2 支持

如果需要 Nav2 避障，请开启点云发布：

```yaml
# Nav2 集成配置
enable_pointcloud_publishing: true  # 发布 /elevation_mapping/elevation_map_points
```

## 🎯 使用方法

### 1. 启动节点

使用 Launch 文件启动节点。

**⚠️ 关键提示**：如果使用真实雷达数据，请务必设置 `use_sim_time:=false`，否则会报错 "Extrapolation into the past"。

```bash
# 启动高程建图节点
ros2 launch elevation_mapping_cupy elevation_mapping.launch.py use_sim_time:=false
```

### 2. 地图重置与初始化

如果地图未显示或需要清空重建，可以调用服务：

```bash
# 手动重置地图 (使用当前位置重新初始化)
ros2 service call /clear_map_with_initializer std_srvs/srv/Empty {}
```

### 3. RViz 可视化

1. **启动 RViz2**
2. **添加插件**：点击左下角 `Add` → 选择 `GridMap` 插件
3. **配置参数**：
   - **Topic**: `/elevation_mapping/elevation_map_filter` (推荐) 或 `_raw`
   - **Layer**: `elevation`
   - **Fixed Frame**: `odom`

## 🔗 话题与服务

### 订阅话题 (Subscribed Topics)

| 话题名 | 类型 | 描述 |
|--------|------|------|
| `/cloud_registered` | `sensor_msgs/PointCloud2` | 输入的点云数据 |
| `/odom` | `nav_msgs/Odometry` | 机器人的里程计位姿 |
| `/tf`, `/tf_static` | `tf2_msgs/TFMessage` | 坐标变换 |

### 发布话题 (Published Topics)

| 话题名 | 类型 | 描述 |
|--------|------|------|
| `/elevation_mapping/elevation_map_raw` | `grid_map_msgs/GridMap` | 包含所有图层的原始地图 |
| `/elevation_mapping/elevation_map_filter` | `grid_map_msgs/GridMap` | **推荐**：经过平滑、去噪、补洞处理后的地图 |
| `/elevation_mapping/elevation_map_points` | `sensor_msgs/PointCloud2` | 用于Nav2避障的3D点云地图 |
| `/elevation_mapping/normal` | `visualization_msgs/MarkerArray` | 地形法向量可视化箭头 |

### 服务接口 (Services)

| 服务名 | 类型 | 描述 |
|--------|------|------|
| `/initialize` | `elevation_map_msgs/Initialize` | 使用指定点初始化地图 |
| `/clear_map` | `std_srvs/Empty` | 清除地图数据 |
| `/clear_map_with_initializer` | `std_srvs/Empty` | **推荐**：清除并重新初始化地图 |

---

## 📞 联系与支持

- **项目主页**: [SCURC Navigation Simulation](https://github.com/OH1412/SCURC_Nav_Sim)
- **技术支持**: [GitHub Issues](https://github.com/OH1412/SCURC_Nav_Sim/issues)
- **维护者**: Pangolin战队 OH

---

*最后更新: 2025年12月6日*