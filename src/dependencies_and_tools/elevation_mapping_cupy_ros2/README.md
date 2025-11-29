## ROS2 Elevation Mapping Cupy 
 **Status**: Under Development 🚧
### Features 
- **Point cloud-based map update**: *Functional*
- **Image-based map update**: *Ongoing development*

### Dependencies -
- **ROS 2 Humble**
- **CUDA 12.4**
- **PyTorch 2.4.0**
# Elevation Mapping Cupy (ROS 2 Humble)

**Elevation Mapping Cupy** 是一个基于 GPU 加速的机器人 2.5D 高程建图功能包。它利用 Python 的 CuPy 库调用 NVIDIA CUDA 进行并行计算，能够实时处理大量点云数据，构建以机器人为中心的高程地图 (Grid Map)。

该版本适配 **ROS 2 Humble** (Ubuntu 22.04)，适用于需要高性能地形感知的足式机器人或轮式机器人。

---

## 1. 核心功能 (Features)

* **GPU 加速**：利用 CuPy 进行地图更新、漂移补偿和光线追踪清理，速度远快于 CPU 版本。
* **机器人中心 (Robot-centric)**：地图跟随机器人移动，始终维护机器人周围的局部地形。
* **多层地图**：支持 `elevation` (高度), `variance` (方差), `traversability` (可通行度), `normal` (法向量) 等多层数据。
* **数据融合**：使用卡尔曼滤波融合多帧点云，消除传感器噪声。
* **Nav2 对接**：支持发布 3D 点云供 Nav2 代价地图 (Costmap) 进行避障。

---

## 2. 安装指南 (Installation)

### 2.1 系统要求
* **OS**: Ubuntu 22.04
* **ROS**: ROS 2 Humble
* **GPU**: NVIDIA 显卡 (需安装 CUDA 驱动，推荐 CUDA 12.x)

### 2.2 安装系统依赖
```bash
sudo apt update
sudo apt install ros-humble-grid-map-core ros-humble-grid-map-ros ros-humble-grid-map-rviz-plugin
sudo apt install libeigen3-dev libopencv-dev python3-pip python3-pybind11

### 2.3 配置 Python 环境 (关键步骤)

**⚠️ 重要提示**：此包对 Python 库版本极其敏感。错误的 Numpy 或 Cupy 版本会导致节点崩溃 (Process died) 或编译错误。请务必在 Conda 环境中按以下顺序安装：

1.  **创建并激活 Conda 环境**

    ```bash
    conda create -n elevation_mapping python=3.10
    conda activate elevation_mapping
    ```

2.  **安装 ROS 2 基础依赖**

    ```bash
    pip install rospkg empy==3.3.4 catkin_pkg lxml transforms3d netifaces psutil
    ```

3.  **安装核心计算库 (版本锁定)**

      * **Numpy**: 必须降级到 2.0 以下，否则会与 ROS 2 底层库冲突。
      * **CuPy**: 必须使用 12.x 版本 (如 12.3.0)，13.x 版本会导致 NVRTC C++17 编译错误。
      * **Shapely**: 建议安装 1.8+ 以避免 `libgeos` 缺失错误。

    <!-- end list -->

    ```bash
    # 1. 锁定 Numpy 和 OpenCV 版本 (兼容性关键)
    pip install "numpy<2.0" "opencv-python<=4.9.0.80"

    # 2. 安装 GPU 加速库 (根据您的 CUDA 版本调整，推荐 12.x)
    pip install "cupy-cuda12x<13.0.0"

    # 3. 安装几何与数学库
    pip install "shapely>=1.8.0" scipy chainer
    ```

### 2.4 编译工作空间

```bash
cd <your_ws>
# 仅编译核心包，忽略不兼容的 ROS 1 遗留包 (如 plane_segmentation)
colcon build --packages-select elevation_mapping_cupy elevation_map_msgs --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
source install/setup.bash
```

-----

## 3\. 配置说明 (Configuration)

核心参数文件位于：`src/elevation_mapping_cupy/config/core/core_param.yaml`

### 3.1 连接传感器 (Subscribers)

修改 `subscribers` 部分，将 `topic_name` 指向您的雷达或 SLAM 输出的点云话题：

```yaml
subscribers:
  pointcloud1:
    topic_name: '/cloud_registered'  # 修改为您实际的点云话题，例如 /livox/lidar
    data_type: 'pointcloud'
```

### 3.2 调整地图精度与范围 (性能优化)

建议使用 **5cm (0.05m)** 分辨率以平衡精度与性能。过高的分辨率（如 2cm）会导致显存不足或丢帧。

```yaml
resolution: 0.05            # 分辨率 (米)
map_length: 20.0            # 地图边长 (米)
cell_n: 160000              # 总格子数 = (map_length / resolution)^2，务必对应修改
min_valid_distance: 0.2     # 盲区半径，建议设小一点(0.2)以填补脚下空洞
sensor_noise_factor: 0.005  # 越小地图更新越灵敏
enable_visibility_cleanup: false # 建议关闭，防止稀疏点云导致地图闪烁/空洞
```

### 3.3 坐标系设置 (TF)

确保 TF 树完整，并正确设置初始化参考系：

```yaml
map_frame: 'odom'           # 固定坐标系
base_frame: 'base_link'     # 机器人基座坐标系
initialize_frame_id: ['base_link'] # 初始化参考系，使用 base_link 最稳定
initialize_tf_offset: [0.0]
```

### 3.4 开启 Nav2 支持

如果需要 Nav2 避障，请开启点云发布：

```yaml
enable_pointcloud_publishing: true # 开启后会发布 /elevation_mapping/elevation_map_points
```

-----

## 4\. 使用方法 (Usage)

### 4.1 启动节点

使用 Launch 文件启动。
**⚠️ 关键提示**：如果您的雷达数据或里程计使用的是真实系统时间（System Time），请务必设置 `use_sim_time:=false`，否则会报错 "Extrapolation into the past"。

```bash
ros2 launch elevation_mapping_cupy elevation_mapping.launch.py use_sim_time:=false
```

### 4.2 手动重置地图

如果地图未显示或需要清空重建，可以调用服务。这会自动使用 `base_link` 当前位置作为地面高度重新初始化：

```bash
ros2 service call /clear_map_with_initializer std_srvs/srv/Empty {}
```

### 4.3 在 RViz 中可视化

1.  启动 RViz2。
2.  点击左下角 **Add** -\> 选择 **`GridMap`** 插件 (注意：不是 Grid，也不是 PointCloud2)。
3.  **Topic** 设置为 `/elevation_mapping/elevation_map_filter` (推荐) 或 `_raw`。
4.  **Layer** 设置为 `elevation`。
5.  将 **Fixed Frame** 设置为 `odom`。

-----

## 5\. 话题与服务 (Topics & Services)

### 订阅 (Subscribed Topics)

  * `/cloud_registered` (`sensor_msgs/PointCloud2`): 输入的点云数据。
  * `/odom` (`nav_msgs/Odometry`): 机器人的里程计位姿。
  * `/tf`, `/tf_static`: 坐标变换。

### 发布 (Published Topics)

  * `/elevation_mapping/elevation_map_raw` (`grid_map_msgs/GridMap`): 包含所有图层的原始地图。
  * `/elevation_mapping/elevation_map_filter` (`grid_map_msgs/GridMap`): **[推荐]** 经过平滑、去噪、补洞处理后的地图，适合导航。
  * `/elevation_mapping/elevation_map_points` (`sensor_msgs/PointCloud2`): 用于 Nav2 避障的 3D 点云形式地图 (需在配置中开启)。
  * `/elevation_mapping/normal` (`visualization_msgs/MarkerArray`): 地形法向量可视化箭头。

### 服务 (Services)

  * `/initialize`: 使用指定点初始化地图。
  * `/clear_map`: 清除地图数据。
  * `/clear_map_with_initializer`: 清除并根据当前位置重新初始化地图（推荐使用）。

<!-- end list -->

```
```