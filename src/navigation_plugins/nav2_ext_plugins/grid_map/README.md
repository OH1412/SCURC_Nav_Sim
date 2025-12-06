# Grid Map 栅格地图库

[![ROS 2 Humble](https://img.shields.io/badge/ROS2-Humble-22314E.svg)](https://docs.ros.org/en/humble/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

## 📖 概述 (Overview)

这是一个带 **[ROS] 接口的 C++ 库**，用于管理多层二维栅格地图。它专为移动机器人建图设计，用于存储**高程 (elevation)**、**方差 (variance)**、**颜色 (color)**、**可通行度 (traversability)**、**表面法向量 (surface normal)** 等多种数据层。该库是 [ANYbotics/elevation_mapping](https://github.com/ANYbotics/elevation_mapping)（专为崎岖地形导航设计）等包的核心组成部分。

### 🚀 核心特性 (Features)

- **🔄 多层支持 (Multi-layered)**: 为通用的 2.5 维栅格建图开发，支持任意数量的数据层
- **⚡ 高效重定位 (Efficient map re-positioning)**: 数据存储采用**二维循环缓冲区 (Circular Buffer)** 实现。这允许地图位置的非破坏性平移（例如跟随机器人移动），无需在内存中复制数据，效率极高
- **🧮 基于 Eigen**: 栅格地图数据以 [Eigen](https://eigen.tuxfamily.org/) 数据类型存储。用户可以直接对地图数据应用现有的 Eigen 算法，实现通用且高效的数据处理
- **🔧 便捷函数 (Convenience functions)**: 实现了多种迭代器，支持对矩形、圆形、多边形区域和线条的数据进行方便且内存安全的访问
- **🔗 丰富的 ROS 接口**: 栅格地图可以直接转换为多种 [ROS](https://www.ros.org/) 消息类型，如 **PointCloud2**、**OccupancyGrid**、**GridCells**，以及我们自定义的 **GridMap 消息**。提供了兼容 [costmap_2d](https://wiki.ros.org/costmap_2d)、[PCL](https://pointclouds.org/) 和 [OctoMap](https://octomap.github.io/) 等数据类型的转换包
- **📷 OpenCV 接口**: 可以与 [OpenCV](https://opencv.org/) 图像类型无缝转换，以便利用 [OpenCV](https://opencv.org/) 提供的图像处理工具
- **👁️ 可视化 (Visualizations)**: `grid_map_rviz_plugin` 可在 [RViz](https://wiki.ros.org/rviz) 中将地图渲染为 3D 表面图（高度图）。`grid_map_visualization` 包可将地图转换为点云、占据栅格等用于可视化
- **🔍 过滤器 (Filters)**: `grid_map_filters` 提供一系列过滤器，可以对地图进行序列化处理。它支持解析数学表达式，可灵活实现阈值处理、法向量计算、平滑、方差、修补 (inpainting) 和矩阵核卷积等功能

### ✅ 兼容性

该库已在 **ROS 2 Foxy (Ubuntu 20.04)** 上进行了测试，并且持续适配 ROS 2 更高版本。

-----

## 📚 发布与引用 (Publications)

如果您在学术环境中使用此工作，请引用以下出版物：

> P. Fankhauser and M. Hutter,
> **"A Universal Grid Map Library: Implementation and Use Case for Rough Terrain Navigation"**,
> in Robot Operating System (ROS) – The Complete Reference (Volume 1), A. Koubaa (Ed.), Springer, 2016. ([PDF](http://www.researchgate.net/publication/284415855))

```bibtex
@incollection{Fankhauser2016GridMapLibrary,
  author = {Fankhauser, P{\'{e}}ter and Hutter, Marco},
  booktitle = {Robot Operating System (ROS) – The Complete Reference (Volume 1)},
  title = {{A Universal Grid Map Library: Implementation and Use Case for Rough Terrain Navigation}},
  chapter = {5},
  editor = {Koubaa, Anis},
  publisher = {Springer},
  year = {2016},
  isbn = {978-3-319-26052-5},
  doi = {10.1007/978-3-319-26054-9{\_}5},
  url = {http://www.springer.com/de/book/9783319260525}
}
```

-----

## 📦 包概览 (Packages Overview)

该仓库由以下包组成：

### 🏗️ 核心与 ROS 接口

- ***grid_map***：栅格地图库的元包 (meta-package)
- ***grid_map_core***：实现了栅格地图库的**核心算法**，提供 `GridMap` 类和迭代器等。**无 ROS 依赖**
- ***grid_map_ros***：主 ROS 依赖包，提供将栅格地图与多种 ROS 消息类型进行转换的接口
- ***grid_map_msgs***：包含围绕 `grid_map_msg/msg/GridMap` 消息类型定义的 ROS 消息和服务

### 🛠️ 工具、过滤器与可视化

- ***grid_map_demos***：包含多个用于演示目的的节点
- ***grid_map_filters***：基于 [ROS Filters](https://wiki.ros.org/filters)，用于对栅格地图应用各种计算过滤器
- ***grid_map_rviz_plugin***：[RViz](https://wiki.ros.org/rviz) 插件，将地图可视化为 3D 表面图
- ***grid_map_visualization***：节点，用于将 GridMap 消息转换为 PointCloud2 或 OccupancyGrid 等格式，用于 RViz 可视化

### 🔄 转换包 (Conversion Packages)

- ***grid_map_costmap_2d***：提供从 [costmap_2d](https://wiki.ros.org/costmap_2d) 地图类型进行转换的功能（用于 **Nav2 代价地图集成**）
- ***grid_map_cv***：提供栅格地图与 [OpenCV](https://opencv.org/) 图像类型之间的转换
- ***grid_map_octomap***：提供栅格地图与 [OctoMap](https://octomap.github.io/) 之间的转换
- ***grid_map_pcl***：提供栅格地图与 [PCL](https://pointclouds.org/) 点云和多边形网格之间的转换

-----

## ⚠️ ROS 2 Humble 编译说明

### 📋 依赖与构建

请确保您已安装 ROS 2 Humble，并加载了 ROS 2 的依赖环境。

### 🔧 C++ 源码兼容性修正 (cv_bridge 路径)

在 ROS 2 Humble 版本中，由于 `cv_bridge` 的头文件结构存在差异，直接使用 `<cv_bridge/cv_bridge.hpp>` 可能会导致编译失败。

**【关键修正】**：如果您在编译过程中遇到 `cv_bridge/cv_bridge.hpp: 没有那个文件或目录` 的错误，请检查您的 C++ 源码并进行路径修正：

- **错误代码：** `#include <cv_bridge/cv_bridge.hpp>` (或类似的 `.hpp` 路径)
- **实际路径：** 对应文件在系统中的实际路径可能是 `/opt/ros/humble/include/cv_bridge/cv_bridge/cv_bridge.h`
- **修改建议：** 将 `cv_bridge.h` 复制到前一级文件夹下 `/opt/ros/humble/include/cv_bridge/cv_bridge.h`

为了解决此问题，在 `grid_map_cv`、`grid_map_ros`、`grid_map_demos` 等包含 `cv_bridge` 的头文件中，可能需要将包含路径修改为：

```cpp
#include <cv_bridge/cv_bridge.h> // 使用 .h 扩展名和嵌套路径
```

### ⚡ 性能优化

为了最大化性能，请确保在 **Release** 模式下进行编译：

```bash
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
```

---

## 📞 联系与支持

- **项目主页**: [SCURC Navigation Simulation](https://github.com/OH1412/SCURC_Nav_Sim)
- **技术支持**: [GitHub Issues](https://github.com/OH1412/SCURC_Nav_Sim/issues)
- **维护者**: Pangolin战队 OH

---

*最后更新: 2025年12月6日*