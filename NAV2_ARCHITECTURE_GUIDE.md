# SCURC 四足机器人 Navigation2 中枢架构详解

> **ROS2 Humble | Ubuntu 22.04 | 最后更新: 2026-06-26**

---

## 目录

1. [项目概览](#1-项目概览)
2. [系统总体架构](#2-系统总体架构)
3. [TF 坐标树](#3-tf-坐标树)
4. [定位集成详解](#4-定位集成详解)
5. [地图绘制与加载](#5-地图绘制与加载)
6. [导航栈详解](#6-导航栈详解)
7. [代价地图配置](#7-代价地图配置)
8. [关键参数速查](#8-关键参数速查)
9. [机器人控制链路](#9-机器人控制链路)
10. [启动流程](#10-启动流程)
11. [自定义插件说明](#11-自定义插件说明)
12. [文件快速跳转索引](#12-文件快速跳转索引)

---

## 1. 项目概览

SCURC_Nav_Sim 是面向 **ROS 2 Humble** 的四足机器人基础导航仓库。导航系统以 **Navigation2 (Nav2)** 为中枢，集成了 FAST-LIVO 定位、地形分析、串口/UDP 控制桥接，实现对四足机器人的全自主导航控制。

### 核心模块

| 模块                         | 路径                                                                                                                                                                                            | 功能                                                   |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| **legged_bringup**     | [src/robot_functionality/legged_bringup/](src/robot_functionality/legged_bringup/)                                                                                                                 | 启动文件、参数配置、地图、行为树                       |
| **serial_driver**      | [src/robot_functionality/serial_driver_ros2/](src/robot_functionality/serial_driver_ros2/)                                                                                                         | 串口驱动，将 cmd_vel 发送到下位机                      |
| **cmd_vel_udp_bridge** | [src/robot_functionality/cmd_vel_udp_bridge/](src/robot_functionality/cmd_vel_udp_bridge/)                                                                                                         | UDP 桥接，将 cmd_vel 转发到 deploy_cpp                 |
| **nav2_ext_plugins**   | [src/navigation_plugins/nav2_ext_plugins/](src/navigation_plugins/nav2_ext_plugins/)                                                                                                               | 自定义 Nav2 插件（代价地图层、DWB 评价器、行为树节点） |
| **terrain_analysis**   | [src/dependencies_and_tools/autonomous_exploration_development_environment/src/terrain_analysis/](src/dependencies_and_tools/autonomous_exploration_development_environment/src/terrain_analysis/) | 地形可通行性分析                                       |
| **FAST-LIVO** (外部)   | 独立工作空间                                                                                                                                                                                    | LiDAR-惯性-视觉里程计，提供定位和里程计                |

### 硬件配置

- **激光雷达**: Livox Mid-360 (实机) / Avia
- **计算平台**: Ubuntu 22.04 + ROS 2 Humble
- **下位机**: STM32/ESP32 系列，通过串口接收 cmd_vel

---

## 2. 系统总体架构

### 2.1 数据流全景图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           感知层 (Perception)                                  │
│                                                                             │
│  ┌──────────────┐    ┌──────────────────┐    ┌──────────────────────┐       │
│  │ Livox 雷达    │───▶│ pointcloud_to_   │───▶│ terrain_analysis      │       │
│  │ /livox/lidar │    │ laserscan        │    │ /terrain_map          │       │
│  └──────┬───────┘    └────────┬─────────┘    └──────────┬───────────┘       │
│         │                     │                         │                    │
│         ▼                     ▼                         ▼                    │
│  ┌──────────────┐    ┌──────────────┐         ┌──────────────────┐          │
│  │ FAST-LIVO    │    │ /scan        │         │ 局部代价地图       │          │
│  │ 里程计+定位   │    │ (LaserScan)  │         │ (local_costmap)   │          │
│  └──────┬───────┘    └──────────────┘         └──────────────────┘          │
└─────────┼───────────────────────────────────────────────────────────────────┘
          │
          │ /aft_mapped_to_init (Odometry)
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         定位与重定位层 (Localization)                          │
│                                                                             │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐       │
│  │ relay_state_     │    │ TEASER + GICP    │    │ static_tf_       │       │
│  │ estimation       │───▶│ 全局重定位        │───▶│ broadcaster      │       │
│  │ → /state_est     │    │ (test.pcd 地图)   │    │ map→odom         │       │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘       │
│                                                                             │
│  ┌──────────────────┐    ┌──────────────────┐                               │
│  │ nav2_map_server  │    │ aft_to_pose_     │                               │
│  │ /map (test_map)  │    │ offset_node      │                               │
│  │                  │    │ → /LIVO2/pose_   │                               │
│  │                  │    │   offset          │                               │
│  └──────────────────┘    └──────────────────┘                               │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          │ TF: map → odom → base_link  (完整 TF 树)
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         导航中枢层 (Navigation2)                               │
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ planner_    │  │ controller_ │  │ behavior_    │  │ bt_navigator │      │
│  │ server      │  │ server      │  │ server       │  │              │      │
│  │ (Theta*)    │  │ (DWB)       │  │ (Spin/Back/  │  │ (行为树引擎)  │      │
│  │             │  │             │  │  Wait/...)   │  │              │      │
│  └──────┬──────┘  └──────┬──────┘  └──────────────┘  └──────────────┘      │
│         │                │                                                  │
│         │  全局路径       │  局部速度指令                                     │
│         ▼                ▼                                                  │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │                    velocity_smoother                             │      │
│  │         cmd_vel_nav (raw) ──▶ cmd_vel (smoothed)                 │      │
│  └──────────────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          │ /cmd_vel (geometry_msgs/Twist)
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         控制桥接层 (Control Bridge)                           │
│                                                                             │
│  ┌─────────────────────────┐     ┌──────────────────────────┐              │
│  │ serial_cmd_sender       │     │ cmd_vel_udp_bridge       │              │
│  │ (串口驱动)               │     │ (UDP 转发)               │              │
│  │ /dev/ttyUSB0 @ 115200   │     │ 127.0.0.1:9870          │              │
│  │ 协议: 0x0F 0xF0 + cmd   │     │ → deploy_cpp             │              │
│  └────────────┬────────────┘     └────────────┬─────────────┘              │
│               │                               │                             │
│               ▼                               ▼                             │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │              机器人下位机 / deploy_cpp                            │      │
│  │              四足机器人步态控制 + 电机驱动                         │      │
│  └──────────────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 核心数据流总结

| 数据流向         | 话题/机制                                          | 说明                                         |
| ---------------- | -------------------------------------------------- | -------------------------------------------- |
| 雷达 → 定位     | FAST-LIVO 直读`/livox/lidar`                     | LiDAR-惯性里程计                             |
| 定位 → 导航     | TF`map→odom→base_link` + `/state_estimation` | 位姿提供给 Nav2                              |
| 雷达 → 代价地图 | `/terrain_map` PointCloud2                       | 经 terrain_analysis 处理后进入 local_costmap |
| 雷达 → 扫描     | `/scan` LaserScan                                | pointcloud_to_laserscan 转换（可选）         |
| 地图 → 导航     | `/map` OccupancyGrid                             | map_server 加载 PGM 地图                     |
| 导航 → 控制     | `/cmd_vel` Twist                                 | 平滑后的速度指令                             |
| 控制 → 机器人   | 串口 / UDP                                         | velocity 命令到达下位机                      |

---

## 3. TF 坐标树

### 3.1 完整 TF 树

```
map                       ← 全局固定坐标系（地图原点）
 │
 │  static TF (identity)  ← 由 static_tf_broadcaster 发布
 │  参数文件: static_tf_params.yaml (transform t0)
 │
 ▼
odom                      ← FAST-LIVO 里程计坐标系
 │
 │  FAST-LIVO 实时发布     ← 由 FAST-LIVO 的 /aft_mapped_to_init 提供
 │  (通过 relay 转发为
 │   /state_estimation)
 │
 ▼
aft_mapped                ← FAST-LIVO 当前扫描匹配位姿
 │
 │  static TF              ← 由 static_tf_broadcaster 发布
 │  trans: (-0.21368, 0, -0.12978)  参数文件: static_tf_params.yaml (transform t1)
 │  yaw: 0.05 rad
 │
 ▼
base_link                 ← 机器人本体坐标系（footprint 中心）
```

### 3.2 关键 TF 参数

| 变换   | 父帧           | 子帧           | 类型    | 参数                                      | 参数文件                                                                                                |
| ------ | -------------- | -------------- | ------- | ----------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| t0     | `map`        | `odom`       | Static  | identity (0,0,0, yaw=0)                   | [static_tf_params.yaml:11-21](src/robot_functionality/legged_bringup/params/static_tf_params.yaml#L11-L21) |
| t1     | `aft_mapped` | `base_link`  | Static  | (-0.21368, 0, -0.12978), yaw=0.05         | [static_tf_params.yaml:23-33](src/robot_functionality/legged_bringup/params/static_tf_params.yaml#L23-L33) |
| 里程计 | `odom`       | `aft_mapped` | Dynamic | FAST-LIVO 实时发布`/aft_mapped_to_init` | [fast_livo_mapping_param.yaml](src/robot_functionality/legged_bringup/params/fast_livo_mapping_param.yaml) |

### 3.3 TF 发布节点

| 节点                       | 文件                                                                                           | 功能                                                   |
| -------------------------- | ---------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| `static_tf_broadcaster`  | [static_tf_broadcaster.py](src/robot_functionality/legged_bringup/nodes/static_tf_broadcaster.py) | 发布`map→odom` 和 `aft_mapped→base_link` 静态 TF |
| FAST-LIVO                  | (外部包)                                                                                       | 发布`odom→aft_mapped` 动态 TF                       |
| `relay_state_estimation` | (topic_tools/relay)                                                                            | 将`/aft_mapped_to_init` 转发为 `/state_estimation` |

> **重要**: 当前 AMCL 已**禁用**（在 nav2_params.yaml 和 global_relocalization.launch.py 中均被注释），定位完全由 FAST-LIVO + TEASER/GICP 重定位 + 静态 TF 提供。这意味着 `map→odom` 是固定的 identity transform，机器人的绝对位姿由重定位对准后直接使用 FAST-LIVO 里程计。

---

## 4. 定位集成详解

### 4.1 定位方案概览

本项目的定位采用 **先全局重定位 + 后里程计递推** 的方案，不使用 AMCL 粒子滤波：

```
启动时:
  FAST-LIVO 里程计运行 → TEASER/GICP 全局重定位（匹配当前扫描到 test.pcd 地图）
  → teaser_gicp 成功退出 → static_tf_broadcaster 发布 map→odom (identity)
  → Nav2 获得完整的 map → odom → base_link TF 链 → 导航启动

运行时:
  FAST-LIVO 持续发布 /aft_mapped_to_init (odom → aft_mapped)
  → static TF: aft_mapped → base_link
  → Nav2 通过 TF 树获取 robot_base_frame(base_link) 在 global_frame(map) 中的位姿
```

### 4.2 重定位流程

**启动文件**: [global_relocalization.launch.py](src/robot_functionality/legged_bringup/launch/global_relocalization.launch.py)

```
步骤 1: map_server 启动，加载 test_map.yaml (PGM 代价地图)
         lifecycle_manager_localization 管理 map_server

步骤 2: FAST-LIVO 启动 (mapping_avia.launch.py, 延迟 1s)
         发布 /aft_mapped_to_init (里程计 Odometry)

步骤 3: transform_publisher 启动 (relocalization 包)
         负责发布重定位结果 TF

步骤 4: teaser_gicp_node 启动 (延迟 2s)
         - 使用 TEASER++ 算法进行全局点云配准
         - 使用 VGICP 进行精细配准
         - 将当前 LiDAR 扫描匹配到 test.pcd (先验地图)
         - 配准成功后退出
       
步骤 5: teaser_gicp 退出后 → static_tf.launch.py 启动 (EventHandle)
         发布 map→odom 和 aft_mapped→base_link 静态 TF
```

### 4.3 TEASER/GICP 重定位关键参数

配置文件在 [global_relocalization.launch.py:57-85](src/robot_functionality/legged_bringup/launch/global_relocalization.launch.py#L57-L85)

| 参数                       | 值                | 说明                   |
| -------------------------- | ----------------- | ---------------------- |
| `map_path`               | `maps/test.pcd` | 先验点云地图           |
| `map_frame_id`           | `map`           | 地图坐标系             |
| `pcl_type`               | `livox`         | 点云类型（Livox 雷达） |
| `map_voxel_leaf_size`    | 0.4               | 地图降采样体素尺寸     |
| `cloud_voxel_leaf_size`  | 0.4               | 扫描降采样体素尺寸     |
| `teaser_solver_max_iter` | 100               | TEASER 求解器最大迭代  |
| `registration_type`      | `VGICP`         | 精细配准算法           |
| `fitness_score_thre`     | 0.2               | 配准适应度阈值         |
| `converged_count_thre`   | 10                | 收敛帧数阈值           |

### 4.4 与 Nav2 的位姿接口

Nav2 通过两种方式获取机器人位姿：

1. **TF 树** (主要): Nav2 各节点通过 TF 查找 `base_link` 在 `map` 中的位姿

   - `global_frame: map` → `robot_base_frame: base_link`
   - 路径: `map → odom → aft_mapped → base_link`
2. **里程计话题** (辅助): Nav2 订阅 `/state_estimation` 作为里程计数据

   - 用于 DWB 控制器速度反馈
   - 用于 velocity_smoother 闭环反馈
   - 参数: `odom_topic: "state_estimation"` (在 controller_server, bt_navigator, velocity_smoother 中配置)

### 4.5 Pose Offset 转发

**节点**: [aft_to_pose_offset_node.py](src/robot_functionality/legged_bringup/nodes/aft_to_pose_offset_node.py)

将 `/aft_mapped_in_map` (Odometry) 转换为 `/LIVO2/pose_offset` (PoseStamped)，供串口驱动发送给下位机做位置闭环控制。

---

## 5. 地图绘制与加载

### 5.1 两种地图

| 地图类型               | 文件                                                                                                                                                 | 用途                    | 使用者             |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------- | ------------------ |
| **PCD 点云地图** | [maps/test.pcd](src/robot_functionality/legged_bringup/maps/test.pcd)                                                                                   | 全局重定位先验地图      | TEASER/GICP 重定位 |
| **PGM 栅格地图** | [maps/test_map.pgm](src/robot_functionality/legged_bringup/maps/test_map.pgm) + [test_map.yaml](src/robot_functionality/legged_bringup/maps/test_map.yaml) | Nav2 全局代价地图静态层 | nav2_map_server    |

### 5.2 地图文件说明

**test_map.yaml** — [查看文件](src/robot_functionality/legged_bringup/maps/test_map.yaml):

```yaml
image: test.pgm          # PGM 图像文件
mode: trinary            # 三值模式（free/occupied/unknown）
resolution: 0.05         # 分辨率 5cm/像素
origin: [-5.05, -2.15, 0]  # 地图原点在世界坐标系中的位置
negate: 0
occupied_thresh: 0.65    # 占据阈值
free_thresh: 0.25        # 空闲阈值
```

### 5.3 如何绘制新地图

**方法 1: SLAM 建图**

```bash
# 终端 1: 启动 Livox 驱动和 FAST-LIVO 定位
ros2 launch fast_livo mapping_avia.launch.py

# 终端 2: 启动建图 (仅 FAST-LIVO + 地形分析 + OctoMap)
ros2 launch legged_bringup mapping.launch.py
```

建图启动文件: [mapping.launch.py](src/robot_functionality/legged_bringup/launch/mapping.launch.py)

- 启动 FAST-LIVO mapping 节点
- 启动 OctoMap 服务器（点云→八叉树地图）
- 启动 RViz 可视化

建图参数: [fast_livo_mapping_param.yaml](src/robot_functionality/legged_bringup/params/fast_livo_mapping_param.yaml)

- `pcd_save_en: true` — 自动保存 PCD 点云地图
- `filter_size_surf: 0.5` — 面特征滤波尺寸
- `cube_side_length: 1000.0` — 地图立方体边长

**方法 2: 保存 Navigation2 代价地图**

```bash
# 使用 nav2_map_saver 保存当前 SLAM 地图
ros2 run nav2_map_server map_saver_cli -f ~/my_map
```

### 5.4 如何更换地图

修改以下两处：

1. **重定位 PCD 地图** — [global_relocalization.launch.py:29](src/robot_functionality/legged_bringup/launch/global_relocalization.launch.py#L29):

   ```python
   pcd_map_path = os.path.join(bringup_dir, 'maps', 'test.pcd')
   ```
2. **Nav2 PGM 地图** — [nav2_params.yaml:435](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L430-L435):

   ```yaml
   map_server:
     ros__parameters:
       yaml_filename: "$(find-pkg-share legged_bringup)/maps/test_map.yaml"
   ```

---

## 6. 导航栈详解

Nav2 导航栈包含 **8 个核心节点**，全部在 [navigation.launch.py](src/robot_functionality/legged_bringup/launch/navigation.launch.py) 中启动，参数统一从 [nav2_params.yaml](src/robot_functionality/legged_bringup/params/nav2_params.yaml) 加载。

### 6.1 节点总览

```
                    ┌──────────────────────┐
                    │   lifecycle_manager  │  ← 管理所有节点的生命周期
                    │   _navigation        │
                    └──────────┬───────────┘
                               │ 激活/停用
    ┌──────────────┬───────────┼───────────┬──────────────┬──────────────┐
    ▼              ▼           ▼           ▼              ▼              ▼
┌────────┐  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐
│planner │  │controller│ │smoother  │ │behavior  │ │bt_       │ │waypoint_     │
│_server │  │_server   │ │_server   │ │_server   │ │navigator │ │follower      │
│全局规划│  │局部规划   │ │路径平滑  │ │恢复行为  │ │行为树引擎│ │航点跟随      │
└───┬────┘  └─────┬────┘ └──────────┘ └─────┬────┘ └─────┬────┘ └──────────────┘
    │             │                         │            │
    │  /plan      │  /cmd_vel_nav           │            │
    ▼             ▼                         ▼            ▼
┌────────┐  ┌──────────────────────────────────────────────────────┐
│ global │  │              velocity_smoother                       │
│ path   │  │   cmd_vel_nav ──▶ [平滑 + 限速 + 限加速度] ──▶ cmd_vel│
└────────┘  └──────────────────────────────────────────────────────┘
```

### 6.2 planner_server (全局规划器)

**功能**: 在全局代价地图上规划从当前位置到目标位置的路径。

**配置** — [nav2_params.yaml:445-479](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L445-L479):

```yaml
planner_server:
  ros__parameters:
    planner_plugins: ["GridBased"]
    GridBased:
      plugin: "nav2_theta_star_planner/ThetaStarPlanner"
      how_many_corners: 8
      w_euc_cost: 1.0        # 欧几里得距离权重
      w_traversal_cost: 2.0  # 穿越代价权重（越大越避开高代价区域）
      w_heuristic_cost: 1.0  # 启发式权重
```

**当前使用**: **Theta\* 规划器** — 一种改进的 A\* 算法，可以在任意角度生成路径（不需要仅限于 8 邻域），路径更平滑自然。

**备选方案** (已注释在配置中):

- `nav2_navfn_planner/NavfnPlanner` — Dijkstra / A\*
- `nav2_smac_planner/SmacPlanner2D` — 2D A\* with 平滑

### 6.3 controller_server (局部规划器)

**功能**: 跟踪全局路径，根据传感器数据和代价地图实时生成速度指令。

**配置** — [nav2_params.yaml:125-325](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L125-L325):

```yaml
controller_server:
  ros__parameters:
    controller_frequency: 10.0       # 控制频率 10Hz
    controller_plugins: ["FollowPath"]
    FollowPath:
      plugin: "dwb_core::DWBLocalPlanner"  # DWB 局部规划器
```

**当前使用**: **DWB (Dynamic Window Based) 局部规划器** — ROS2 的 DWA 改进版，通过采样速度空间、评估轨迹、选择最优轨迹来控制机器人。

#### DWB 速度限制

| 参数                            | 值         | 说明                 |
| ------------------------------- | ---------- | -------------------- |
| `min_vel_x` / `max_vel_x`   | -1.0 / 1.0 | X 方向速度范围 (m/s) |
| `min_vel_y` / `max_vel_y`   | -1.0 / 1.0 | Y 方向速度范围 (m/s) |
| `max_vel_theta`               | 5.0        | 最大旋转速度 (rad/s) |
| `acc_lim_x` / `acc_lim_y`   | 3.0        | X/Y 加速度限制       |
| `acc_lim_theta`               | 20.0       | 角加速度限制         |
| `vx_samples` / `vy_samples` | 20         | X/Y 速度采样数       |
| `vtheta_samples`              | 20         | 角速度采样数         |
| `sim_time`                    | 0.51       | 前向模拟时间 (s)     |

> **重要**: 实际速度限制在实机启动时由 [navigation.launch.py:81-88](src/robot_functionality/legged_bringup/launch/navigation.launch.py#L81-L88) 从 deploy_cpp 配置文件**动态覆盖**：
>
> ```python
> 'max_vel_x': Command(['python3 ', yaml_value_script, ' ', deploy_config_file, ' ', 'cmd_vx_max'])
> ```
>
> 实机默认配置路径: `/home/dog12/HIMLocoWithDeploy/deploy_cpp/config/robots/mybot_v2_real.yaml`

#### DWB 评价器 (Critics)

每个评价器给候选轨迹打分，最终选择总分最低（最优）的轨迹：

| 评价器                | scale                                    | 功能                              |
| --------------------- | ---------------------------------------- | --------------------------------- |
| `RotateToGoal`      | **0.0** (中间区) / 32.0 (边缘区)   | 奖励朝向目标旋转的轨迹            |
| `Oscillation`       | 默认                                     | 惩罚来回振荡的轨迹                |
| `ObstacleFootprint` | 50.0                                     | 惩罚靠近障碍物的轨迹（最高权重）  |
| `GoalAlign`         | **0.0** (中间区) / 24.0 (边缘区)   | 奖励对齐目标方向的轨迹            |
| `PathAlign`         | **0.0** (中间区) / 32.0 (边缘区)   | 奖励对齐全局路径方向的轨迹        |
| `PathDist`          | 32.0                                     | 奖励靠近全局路径的轨迹            |
| `GoalDist`          | 24.0                                     | 奖励靠近目标的轨迹                |
| `MaintainYawCritic` | **5000.0** (中间区) / 0.0 (边缘区) | 强制保持固定 yaw 角（自定义插件） |

**区域切换策略**: 系统支持两种 DWB 行为模式，通过切换 critic scale 值实现：

| 区域             | 行为                                                              | X 范围      | 适用场景                             |
| ---------------- | ----------------------------------------------------------------- | ----------- | ------------------------------------ |
| **中间区** | yaw 锁定为 0°，禁止旋转 (MaintainYawCritic=5000, 旋转 critics=0) | 0.9m ~ 4.9m | 狭窄走廊，需要机器人保持固定朝向侧移 |
| **边缘区** | 允许自由旋转 (MaintainYawCritic=0, 旋转 critics 激活)             | 其他范围    | 开阔区域，需要旋转对准目标           |

> 当前默认使用**中间区配置**，切换器 (position_based_param_switcher) 已被注释。如需启用区域切换，取消 [navigation.launch.py:372-386](src/robot_functionality/legged_bringup/launch/navigation.launch.py#L372-L386) 中的注释。

### 6.4 behavior_server (恢复行为)

**功能**: 当机器人卡住或无法规划时，执行一系列恢复动作。

**配置** — [nav2_params.yaml:492-521](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L492-L521):

```yaml
behavior_server:
  ros__parameters:
    behavior_plugins: ["spin", "backup", "drive_on_heading", "assisted_teleop", "wait"]
```

| 恢复行为             | 插件                              | 说明                                   |
| -------------------- | --------------------------------- | -------------------------------------- |
| `spin`             | `nav2_behaviors/Spin`           | 原地旋转 45° (0.785 rad) 寻找可行路径 |
| `backup`           | `nav2_behaviors/BackUpTwzFree`  | 向自由空间方向后退（自定义插件）       |
| `drive_on_heading` | `nav2_behaviors/DriveOnHeading` | 沿固定方向行驶                         |
| `wait`             | `nav2_behaviors/Wait`           | 等待 1 秒                              |
| `assisted_teleop`  | `nav2_behaviors/AssistedTeleop` | 辅助遥控                               |

**后退行为参数**:

| 参数               | 值    | 说明                 |
| ------------------ | ----- | -------------------- |
| `robot_radius`   | 0.3 m | 机器人半径           |
| `max_radius`     | 3.5 m | 最大搜索自由空间半径 |
| `free_threshold` | 3     | 自由空间最小栅格数   |

### 6.5 bt_navigator (行为树导航器)

**功能**: 行为树引擎，协调规划、控制、恢复等行为。

**配置** — [nav2_params.yaml:53-115](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L53-L115):

```yaml
bt_navigator:
  ros__parameters:
    bt_loop_duration: 10           # 行为树 tick 周期 (ms)
    default_server_timeout: 20     # 动作服务器超时 (s)
    transform_tolerance: 1.0       # TF 查找容差 (s)
    odom_topic: state_estimation   # 里程计话题
```

**行为树 XML 文件**:

| 行为树               | 文件                                                                                                                                                         | 用途         |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------ |
| NavigateToPose       | [navigate_to_pose_w_replanning_and_recovery.xml](src/robot_functionality/legged_bringup/behavior_tree/navigate_to_pose_w_replanning_and_recovery.xml)           | 单目标点导航 |
| NavigateThroughPoses | [navigate_through_pose_w_replanning_and_recovery.xml](src/robot_functionality/legged_bringup/behavior_tree/navigate_through_pose_w_replanning_and_recovery.xml) | 多航点导航   |

**NavigateToPose 行为树流程**:

```
RateController (1Hz)
  └─ RecoveryNode (最多 6 次重试)
       ├─ PipelineSequence
       │    ├─ GoalUpdater
       │    ├─ ComputePathToPose (调用 planner_server)
       │    └─ SmoothPath (调用 smoother_server)
       └─ Recovery (恢复动作序列)
            ├─ ClearGlobalCostmap
            ├─ ClearLocalCostmap
            ├─ BackUp (0.3m @ 0.4m/s → 0.5m @ 0.4m/s)
            └─ Spin (已注释)
```

### 6.6 waypoint_follower (航点跟随器)

**功能**: 按顺序执行多个导航目标点。

**配置** — [nav2_params.yaml:539-548](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L539-L548):

```yaml
waypoint_follower:
  ros__parameters:
    loop_rate: 20
    waypoint_task_executor_plugin: "wait_at_waypoint"
    wait_at_waypoint:
      plugin: "nav2_waypoint_follower::WaitAtWaypoint"
      waypoint_pause_duration: 8   # 到达航点后等待 8s
```

### 6.7 velocity_smoother (速度平滑器)

**功能**: 对 raw cmd_vel 进行平滑、限速、限加速度，防止机器人急停急启。

**配置** — [nav2_params.yaml:550-563](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L550-L563):

```yaml
velocity_smoother:
  ros__parameters:
    smoothing_frequency: 5.0       # 平滑频率 5Hz
    feedback: "CLOSED_LOOP"        # 闭环反馈（使用里程计）
    max_velocity: [2.5, 2.5, 12.0]   # 最大速度 [vx, vy, vtheta]
    min_velocity: [-2.5, -2.5, -12.0]
    max_accel: [5.0, 5.0, 15.0]      # 最大加速度
    max_decel: [-5.0, -5.0, -15.0]   # 最大减速度
    odom_topic: "Odometry"
    velocity_timeout: 1.0          # 超时 1s 后停止
```

**关键话题映射** (在 [navigation.launch.py:152-153](src/robot_functionality/legged_bringup/launch/navigation.launch.py#L152-L153)):

```
controller_server → /cmd_vel_nav (raw)
velocity_smoother → /cmd_vel (smoothed, 最终输出)
```

---

## 7. 代价地图配置

### 7.1 两层代价地图对比

| 属性               | global_costmap                 | local_costmap                                   |
| ------------------ | ------------------------------ | ----------------------------------------------- |
| **坐标系**   | `map`                        | `odom`                                        |
| **类型**     | 固定窗口 (全地图)              | 滚动窗口                                        |
| **尺寸**     | 全地图                         | 10m × 10m                                      |
| **分辨率**   | 0.1 m                          | 0.05 m                                          |
| **更新频率** | 1 Hz                           | 20 Hz                                           |
| **插件层**   | static_layer + inflation_layer | static_layer + obstacle_layer + inflation_layer |

### 7.2 global_costmap 详解

**配置** — [nav2_params.yaml:389-427](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L389-L427):

```
global_costmap (frame: map, 分辨率 0.1m)
├── static_layer           ← 加载 PGM 地图 (标准 nav2 StaticLayer)
│   map_subscribe_transient_local: True
│
└── global_inflation_layer ← 膨胀层
    cost_scaling_factor: 3.0
    inflation_radius: 1.0m  ← 障碍物膨胀 1m
```

### 7.3 local_costmap 详解

**配置** — [nav2_params.yaml:327-387](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L327-L387):

```
local_costmap (frame: odom, 分辨率 0.05m, 10m×10m 滚动窗口)
├── static_layer (costmap_intensity::StaticLayerNonLethal)
│   ← 从 PGM 地图加载，占据代价=200 (非致命，橙色显示)
│   ← 不触发碰撞检测，仅做参考
│
├── local_obstacle_layer (costmap_intensity::ObstacleLayerIntensity)
│   ← 订阅 /terrain_map (PointCloud2)
│   ← 强度过滤: min=0.2 ~ max=2.0
│   ← 高度过滤: -0.5m ~ 0.5m
│   ← 障碍物范围: 0.2m ~ 4.5m
│
└── local_inflation_layer
    inflation_radius: 0.01m  ← 极小膨胀（依赖 footprint 保证安全）
    cost_scaling_factor: 3.0
```

### 7.4 Robot Footprint

**配置** — [nav2_params.yaml:339](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L339):

```
footprint: [[0.2971, 0.19185], [0.2971, -0.19185], [-0.44518, -0.19185], [-0.44518, 0.19185]]
```

这是一个 **矩形 footprint**:

- 前方宽度: 0.3837m (中心到前端约 0.297m)
- 后方宽度: 0.3837m (中心到后端约 0.445m)
- 总长约 0.742m, 总宽约 0.384m

> ⚠️ **注意**: 配置文件中有注释提示——`ObstacleFootprint` 的内切圆是 0.2971m，但后腿需要 0.44518m 的通过空间。膨胀层设置了极小值(0.01m)，碰撞主要靠 DWB `ObstacleFootprint` critic (scale=50) 来避免。

---

## 8. 关键参数速查

### 8.1 全局规划参数

| 参数                 | 位置                                                                                     | 默认值 | 说明                 | 调参建议                             |
| -------------------- | ---------------------------------------------------------------------------------------- | ------ | -------------------- | ------------------------------------ |
| `w_euc_cost`       | [nav2_params.yaml:477](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L477) | 1.0    | 路径距离代价         | 增大=更短路径，减小=更安全但可能绕路 |
| `w_traversal_cost` | [nav2_params.yaml:478](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L478) | 2.0    | 穿越高代价区域代价   | 增大=更远离障碍物                    |
| `w_heuristic_cost` | [nav2_params.yaml:479](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L479) | 1.0    | 启发式权重           | 1.0=标准 A\* 启发式                  |
| `how_many_corners` | [nav2_params.yaml:476](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L476) | 8      | Theta\* 的搜索方向数 | 越大路径越平滑但越慢                 |

### 8.2 局部规划 (DWB) 参数

| 参数                        | 位置                                                                                     | 默认值    | 说明               | 调参建议                            |
| --------------------------- | ---------------------------------------------------------------------------------------- | --------- | ------------------ | ----------------------------------- |
| `controller_frequency`    | [nav2_params.yaml:128](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L128) | 10.0 Hz   | 控制频率           | 更大的机器人可以用更低频率          |
| `max_vel_x`               | [nav2_params.yaml:263](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L263) | 1.0 m/s   | 最大前进速度       | **实机由 deploy_config 覆盖** |
| `max_vel_theta`           | [nav2_params.yaml:265](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L265) | 5.0 rad/s | 最大旋转速度       | **实机由 deploy_config 覆盖** |
| `sim_time`                | [nav2_params.yaml:278](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L278) | 0.51 s    | 轨迹前向模拟时间   | 增大=看得更远但计算更慢             |
| `vx_samples`              | [nav2_params.yaml:275](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L275) | 20        | X 速度采样数       | 增大=更精确但计算量大               |
| `ObstacleFootprint.scale` | [nav2_params.yaml:293](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L293) | 50.0      | 障碍物碰撞惩罚权重 | 最重要的安全参数                    |
| `xy_goal_tolerance`       | [nav2_params.yaml:282](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L282) | 0.25 m    | 目标到达容差       | 减小=更精确但更难到达               |

### 8.3 代价地图参数

| 参数                           | 位置                                                                                              | 默认值     | 说明                                        |
| ------------------------------ | ------------------------------------------------------------------------------------------------- | ---------- | ------------------------------------------- |
| `local_costmap.width/height` | [nav2_params.yaml:336-337](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L336-L337) | 10m × 10m | 局部代价地图尺寸                            |
| `local_costmap.resolution`   | [nav2_params.yaml:338](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L338)          | 0.05 m     | 局部代价地图分辨率                          |
| `global_costmap.resolution`  | [nav2_params.yaml:398](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L398)          | 0.1 m      | 全局代价地图分辨率                          |
| `inflation_radius` (local)   | [nav2_params.yaml:364](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L364)          | 0.01 m     | 局部膨胀半径（极小的原因见 footprint 注释） |
| `inflation_radius` (global)  | [nav2_params.yaml:407](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L407)          | 1.0 m      | 全局膨胀半径                                |

### 8.4 恢复行为参数

| 参数                    | 位置                                                                                     | 默认值 | 说明                     |
| ----------------------- | ---------------------------------------------------------------------------------------- | ------ | ------------------------ |
| `robot_radius`        | [nav2_params.yaml:517](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L517) | 0.3 m  | 后退行为使用的机器人半径 |
| `max_radius`          | [nav2_params.yaml:518](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L518) | 3.5 m  | 后退搜索自由空间最大半径 |
| `free_threshold`      | [nav2_params.yaml:520](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L520) | 3      | 自由空间栅格阈值         |
| `transform_tolerance` | [nav2_params.yaml:510](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L510) | 1.0 s  | TF 转换容差              |

### 8.5 速度平滑器参数

| 参数                 | 位置                                                                                     | 默认值           | 说明             |
| -------------------- | ---------------------------------------------------------------------------------------- | ---------------- | ---------------- |
| `max_velocity`     | [nav2_params.yaml:556](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L556) | [2.5, 2.5, 12.0] | 最终速度上限     |
| `max_accel`        | [nav2_params.yaml:558](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L558) | [5.0, 5.0, 15.0] | 最大加速度限制   |
| `velocity_timeout` | [nav2_params.yaml:563](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L563) | 1.0 s            | 无指令超时后急停 |

---

## 9. 机器人控制链路

### 9.1 cmd_vel 完整流转路径

```
controller_server              velocity_smoother             控制桥接
(DWB Local Planner)           (速度平滑+限速)               (二选一或同时)
      │                              │                          │
      │ /cmd_vel_nav                 │ /cmd_vel                 │
      │ (raw Twist)                  │ (smoothed Twist)         │
      ▼                              ▼                          ▼
┌──────────────┐   remap    ┌──────────────────┐    ┌────────────────────┐
│ DWB 输出     │───────────▶│ 平滑 + 限速 +     │───▶│ serial_cmd_sender  │
│ 速度指令     │            │ 限加速度          │    │ /dev/ttyUSB0       │
│              │            │                   │    │ 协议帧编码         │
│              │            │                   │    └────────┬───────────┘
│              │            │                   │             │
│              │            │                   │    ┌────────▼───────────┐
│              │            │                   │───▶│ cmd_vel_udp_bridge │
│              │            │                   │    │ UDP → deploy_cpp   │
└──────────────┘            └──────────────────┘    └─────────────────────┘
```

### 9.2 串口驱动 (serial_driver)

**包位置**: [src/robot_functionality/serial_driver_ros2/](src/robot_functionality/serial_driver_ros2/)

#### 话题接口

| 方向 | 话题                          | 消息类型                           | 说明                        |
| ---- | ----------------------------- | ---------------------------------- | --------------------------- |
| 订阅 | `/cmd_vel`                  | `geometry_msgs/msg/Twist`        | 接收速度指令 (cmd_id=0)     |
| 订阅 | `/LIVO2/pose_offset`        | `geometry_msgs/msg/PoseStamped`  | 接收位姿偏移 (cmd_id=1)     |
| 订阅 | `/LIVO2/specific_distances` | `std_msgs/msg/Float64MultiArray` | 接收距离数据 (cmd_id=2)     |
| 发布 | (无)                          | —                                 | 纯串口下发，不发布 ROS 话题 |

#### 串口协议 (PC → 下位机)

**配置文件**: [serial_main.cpp](src/robot_functionality/serial_driver_ros2/src/serial_main.cpp), [serial_driver.cpp](src/robot_functionality/serial_driver_ros2/src/serial_driver.cpp)

```
帧格式:
┌─────────┬─────────┬─────────┬─────────┬──────────────┬─────────┐
│ 0x0F    │ 0xF0    │ cmd_id  │ data_len│ data[10]     │checksum │
│ 帧头1   │ 帧头2   │ 命令ID  │ 数据长度│ 数据体(10B)  │ 校验和  │
│ 1 byte  │ 1 byte  │ 1 byte  │ 1 byte  │ 10 bytes     │ 1 byte  │
└─────────┴─────────┴─────────┴─────────┴──────────────┴─────────┘

数据编码: float × 1000 → int16_t → big-endian 2 bytes

命令ID:
  0x00 = 速度指令 [vx, vy, wz]（来自 /cmd_vel）
  0x01 = 位姿偏移 [x, y, yaw]（来自 /LIVO2/pose_offset）
  0x02 = 距离数据 [dist1, dist2]（来自 /LIVO2/specific_distances）
```

#### 串口配置

**配置文件**: [serial_config.yaml](src/robot_functionality/serial_driver_ros2/config/serial_config.yaml)

```yaml
port: "/dev/ttyUSB0"
baudrate: 115200
```

### 9.3 UDP 桥接 (cmd_vel_udp_bridge)

**包位置**: [src/robot_functionality/cmd_vel_udp_bridge/](src/robot_functionality/cmd_vel_udp_bridge/)

用于将 `/cmd_vel` 通过 UDP 转发给 deploy_cpp（机器人步态控制程序）。

**默认参数** (在 [bringup_in_real.launch.py:67-76](src/robot_functionality/legged_bringup/launch/bringup_in_real.launch.py#L67-L76)):

```python
udp_ip: '127.0.0.1'
udp_port: '9870'
udp_mode: '2'
```

### 9.4 控制方式选择

在实机启动时，通过启动参数选择控制方式：

```bash
# 同时启用串口和 UDP（默认）
ros2 launch legged_bringup bringup_in_real.launch.py

# 仅 UDP，不启动串口（默认配置）
# enable_serial_driver 默认为 false
# enable_udp_forwarding 默认为 true

# 启用串口驱动
ros2 launch legged_bringup bringup_in_real.launch.py enable_serial_driver:=true
```

---

## 10. 启动流程

### 10.1 实机启动 (bringup_in_real.launch.py)

**启动文件**: [bringup_in_real.launch.py](src/robot_functionality/legged_bringup/launch/bringup_in_real.launch.py)

```
时刻 T=0s:
  ├── Livox MID360 雷达驱动启动       ← 最先启动
  ├── serial_driver 串口驱动启动       ← 条件启动 (enable_serial_driver:=true)
  ├── cmd_vel_udp_bridge UDP 桥接启动  ← 条件启动 (enable_udp_forwarding:=true)

时刻 T=5s (start_delay 默认值):
  ├── bringup_all_in_one.launch.py 启动
  │   │
  │   ├── pointcloud_to_scan 启动 (可选)
  │   ├── relay_state_estimation 启动     ← /aft_mapped_to_init → /state_estimation
  │   │
  │   ├── 时刻 T=6s (延迟 1s):
  │   │   └── global_relocalization.launch.py 启动
  │   │       ├── map_server (PGM 地图加载)
  │   │       ├── lifecycle_manager_localization
  │   │       ├── FAST-LIVO 里程计 (延迟 1s)
  │   │       ├── transform_publisher
  │   │       ├── teaser_gicp_node (延迟 2s) → 重定位成功后 static_tf 启动
  │   │       └── RViz (loam_livox.rviz)
  │   │
  │   └── 时刻 T=20s (延迟 15s):
  │       └── navigation.launch.py 启动
  │           ├── terrain_analysis 启动
  │           ├── Nav2 全部节点 (planner/controller/behavior/bt/waypoint/velocity_smoother)
  │           ├── lifecycle_manager_navigation
  │           ├── RViz (nav2_default_view.rviz)
  │           └── position_based_param_switcher (当前已注释)
  │
  └── aft_to_pose_offset_node 启动     ← /aft_mapped_in_map → /LIVO2/pose_offset
```

### 10.2 导航节点启动顺序

导航节点由 `lifecycle_manager_navigation` 统一管理生命周期，按顺序激活：

```
lifecycle_manager_navigation
  管理节点列表:
    1. controller_server
    2. smoother_server
    3. planner_server
    4. behavior_server
    5. bt_navigator
    6. waypoint_follower
    7. velocity_smoother
```

### 10.3 问答总结

| 问题                                         | 答案                                                                                                                                             |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| **串口驱动是否在导航启动时一起启动？** | 是的。在实机模式下，`serial_driver` 在 T=0s 最先启动（与雷达同时），比导航栈早约 20 秒。由 `enable_serial_driver` 参数控制（默认为 false）。 |
| **雷达驱动是否一起启动？**             | 是的。Livox MID360 驱动在 T=0s 最先启动。                                                                                                        |
| **导航中的串口是否使用？**             | 串口驱动**独立订阅** `/cmd_vel` 话题，在导航的 velocity_smoother 发布 `/cmd_vel` 后自动接收速度指令。不直接依赖导航启动。              |
| **UDP 桥接是否使用？**                 | 默认启用。UDP 桥接也独立订阅`/cmd_vel`，与串口驱动并行工作。                                                                                   |

---

## 11. 自定义插件说明

### 11.1 插件清单

| 插件包                          | 路径                                                                                  | 类型              | 功能                              |
| ------------------------------- | ------------------------------------------------------------------------------------- | ----------------- | --------------------------------- |
| **costmap_intensity**     | [costmap_intensity/](src/navigation_plugins/nav2_ext_plugins/costmap_intensity/)         | Costmap Layer ×3 | 强度过滤的障碍物层 + 非致命静态层 |
| **dwb_yaw_constraint**    | [dwb_yaw_constraint/](src/navigation_plugins/nav2_ext_plugins/dwb_yaw_constraint/)       | DWB Critic        | 强制保持固定 yaw 角               |
| **behavior_ext_plugins**  | [behavior_ext_plugins/](src/navigation_plugins/nav2_ext_plugins/behavior_ext_plugins/)   | Behavior Node     | 朝自由空间方向后退                |
| **velocity_smoother_ext** | [velocity_smoother_ext/](src/navigation_plugins/nav2_ext_plugins/velocity_smoother_ext/) | Lifecycle Node    | 带速度倍率的速度平滑器            |

### 11.2 StaticLayerNonLethal

**文件**: [static_layer_non_lethal.cpp](src/navigation_plugins/nav2_ext_plugins/costmap_intensity/plugins/static_layer_non_lethal.cpp)

**作用**: 加载 PGM 静态地图到局部代价地图，但使用 **200** (非致命) 代替 **254** (致命) 作为占据代价值。

**为什么需要？** 标准 StaticLayer 将地图中的黑色障碍物标记为 LETHAL_OBSTACLE (254)，DWB 会完全避开。但这个值是致命代价，可能导致机器人因为地图标注不精确而被卡住。使用 200 可以让静态障碍物在 RViz 中可见（橙色），但不会触发碰撞（碰撞阈值是 253）。

**关键参数**:

| 参数                    | 值  | 位置                                                                                     |
| ----------------------- | --- | ---------------------------------------------------------------------------------------- |
| `occupied_cost_value` | 200 | [nav2_params.yaml:384](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L384) |

### 11.3 ObstacleLayerIntensity

**文件**: [obstacle_layer.cpp](src/navigation_plugins/nav2_ext_plugins/costmap_intensity/plugins/obstacle_layer.cpp)

**作用**: 基于点云 intensity 字段过滤的动态障碍物层。只有 intensity 在 `[min, max]` 范围内的点才会被标记为障碍物。

**关键参数**:

| 参数                       | 值  | 位置                                                                                     |
| -------------------------- | --- | ---------------------------------------------------------------------------------------- |
| `min_obstacle_intensity` | 0.2 | [nav2_params.yaml:370](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L370) |
| `max_obstacle_intensity` | 2.0 | [nav2_params.yaml:369](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L369) |

### 11.4 MaintainYawCritic

**文件**: [maintain_yaw_critic.cpp](src/navigation_plugins/nav2_ext_plugins/dwb_yaw_constraint/plugins/maintain_yaw_critic.cpp)

**作用**: DWB 轨迹评价器，强制机器人保持固定的 yaw 角度（在 map 坐标系中），适用于**全向移动**的四足机器人。在中间区（狭窄通道），机器人侧移但不旋转，保持固定的 0° 朝向。

**关键参数**:

| 参数                | 值                             | 位置                                                                                     |
| ------------------- | ------------------------------ | ---------------------------------------------------------------------------------------- |
| `scale`           | 5000.0 (中间区) / 0.0 (边缘区) | [nav2_params.yaml:308](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L308) |
| `desired_yaw`     | 0.0                            | [nav2_params.yaml:309](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L309) |
| `reference_frame` | "map"                          | [nav2_params.yaml:310](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L310) |

### 11.5 BackUpTwzFree

**文件**: [back_up_twz_free_action.cpp](src/navigation_plugins/nav2_ext_plugins/behavior_ext_plugins/plugins/back_up_twz_free_action.cpp)

**作用**: 改进的后退恢复行为。不同于标准 `BackUp` 行为的直线后退，它通过查询局部代价地图找到最近的自由空间，然后向自由空间的**质心方向**后退。

---

## 12. 文件快速跳转索引

### 12.1 启动文件

| 文件                                                                                                          | 说明                           | 关键用途                         |
| ------------------------------------------------------------------------------------------------------------- | ------------------------------ | -------------------------------- |
| [bringup_in_real.launch.py](src/robot_functionality/legged_bringup/launch/bringup_in_real.launch.py)             | 🚀**实机全系统启动入口** | 一键启动所有模块                 |
| [bringup_all_in_one.launch.py](src/robot_functionality/legged_bringup/launch/bringup_all_in_one.launch.py)       | 仿真全系统启动                 | 重定位+导航编排                  |
| [navigation.launch.py](src/robot_functionality/legged_bringup/launch/navigation.launch.py)                       | Nav2 导航栈启动                | 启动所有 Nav2 节点               |
| [global_relocalization.launch.py](src/robot_functionality/legged_bringup/launch/global_relocalization.launch.py) | 全局重定位启动                 | TEASER/GICP + map_server         |
| [mapping.launch.py](src/robot_functionality/legged_bringup/launch/mapping.launch.py)                             | SLAM 建图启动                  | FAST-LIVO mapping                |
| [pointcloud_to_scan.launch.py](src/robot_functionality/legged_bringup/launch/pointcloud_to_scan.launch.py)       | 点云转扫描                     | Livox → LaserScan               |
| [static_tf.launch.py](src/robot_functionality/legged_bringup/launch/static_tf.launch.py)                         | 静态 TF 发布                   | map→odom, aft_mapped→base_link |
| [serial_driver.launch.py](src/robot_functionality/serial_driver_ros2/launch/serial_driver.launch.py)             | 串口驱动启动                   | 独立启动串口                     |

### 12.2 参数配置文件

| 文件                                                                                                                  | 说明                        | 关键调参项                        |
| --------------------------------------------------------------------------------------------------------------------- | --------------------------- | --------------------------------- |
| [nav2_params.yaml](src/robot_functionality/legged_bringup/params/nav2_params.yaml)                                       | 🔧**Nav2 主参数文件** | 规划器/控制器/代价地图/速度平滑器 |
| [amcl_params.yaml](src/robot_functionality/legged_bringup/params/amcl_params.yaml)                                       | AMCL 参数                   | 已禁用，备用                      |
| [static_tf_params.yaml](src/robot_functionality/legged_bringup/params/static_tf_params.yaml)                             | 静态 TF 参数                | 坐标系变换                        |
| [fast_livo_mapping_param.yaml](src/robot_functionality/legged_bringup/params/fast_livo_mapping_param.yaml)               | FAST-LIVO 建图参数          | 点云滤波、IMU 参数                |
| [fast_livo_relocalization_param.yaml](src/robot_functionality/legged_bringup/params/fast_livo_relocalization_param.yaml) | FAST-LIVO 重定位参数        | 重定位模式                        |
| [core_param.yaml](src/robot_functionality/legged_bringup/params/core_param.yaml)                                         | 高程地图参数                | 地形可通行性                      |
| [segmentation_params.yaml](src/robot_functionality/legged_bringup/params/segmentation_params.yaml)                       | 地面分割参数                | 线拟合分割                        |
| [serial_config.yaml](src/robot_functionality/serial_driver_ros2/config/serial_config.yaml)                               | 串口配置                    | 端口/波特率                       |

### 12.3 行为树 XML

| 文件                                                                                                                                                         | 说明           |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------- |
| [navigate_to_pose_w_replanning_and_recovery.xml](src/robot_functionality/legged_bringup/behavior_tree/navigate_to_pose_w_replanning_and_recovery.xml)           | 单点导航行为树 |
| [navigate_through_pose_w_replanning_and_recovery.xml](src/robot_functionality/legged_bringup/behavior_tree/navigate_through_pose_w_replanning_and_recovery.xml) | 多点导航行为树 |

### 12.4 串口驱动文件

| 文件                                                                                                 | 说明                        |
| ---------------------------------------------------------------------------------------------------- | --------------------------- |
| [serial_main.cpp](src/robot_functionality/serial_driver_ros2/src/serial_main.cpp)                       | 串口节点入口 (3 个话题订阅) |
| [serial_driver.cpp](src/robot_functionality/serial_driver_ros2/src/serial_driver.cpp)                   | 串口通信实现 (帧编码/解码)  |
| [protocol_defs.hpp](src/robot_functionality/serial_driver_ros2/include/serial_driver/protocol_defs.hpp) | 协议常量定义 (帧头/校验)    |
| [serial_comm.hpp](src/robot_functionality/serial_driver_ros2/include/serial_driver/serial_comm.hpp)     | 串口通信类声明              |

### 12.5 Python 工具节点

| 文件                                                                                                           | 说明                          |
| -------------------------------------------------------------------------------------------------------------- | ----------------------------- |
| [static_tf_broadcaster.py](src/robot_functionality/legged_bringup/nodes/static_tf_broadcaster.py)                 | 静态 TF 广播                  |
| [aft_to_pose_offset_node.py](src/robot_functionality/legged_bringup/nodes/aft_to_pose_offset_node.py)             | 里程计→位姿偏移转发          |
| [position_based_param_switcher.py](src/robot_functionality/legged_bringup/nodes/position_based_param_switcher.py) | 基于位置的参数切换器 (已禁用) |

### 12.6 地图文件

| 文件                                                                    | 说明                |
| ----------------------------------------------------------------------- | ------------------- |
| [test_map.yaml](src/robot_functionality/legged_bringup/maps/test_map.yaml) | Nav2 栅格地图元数据 |
| [test_map.pgm](src/robot_functionality/legged_bringup/maps/test_map.pgm)   | Nav2 栅格地图图像   |
| [test.pcd](src/robot_functionality/legged_bringup/maps/test.pcd)           | 重定位先验点云地图  |

### 12.7 自定义插件源码

| 文件                                                                                                                                                      | 说明               |
| --------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ |
| [costmap_intensity/plugins/](src/navigation_plugins/nav2_ext_plugins/costmap_intensity/plugins/)                                                             | 代价地图强度层实现 |
| [dwb_yaw_constraint/plugins/maintain_yaw_critic.cpp](src/navigation_plugins/nav2_ext_plugins/dwb_yaw_constraint/plugins/maintain_yaw_critic.cpp)             | DWB yaw 约束实现   |
| [behavior_ext_plugins/plugins/back_up_twz_free_action.cpp](src/navigation_plugins/nav2_ext_plugins/behavior_ext_plugins/plugins/back_up_twz_free_action.cpp) | 后退行为实现       |

---

## 附录 A: 常用调试命令

```bash
# 加载环境
source ./load_all.sh

# 启动实机全系统
ros2 launch legged_bringup bringup_in_real.launch.py

# 仅启动导航（不含雷达/串口）
ros2 launch legged_bringup navigation.launch.py

# 启动建图
ros2 launch legged_bringup mapping.launch.py

# 检查 TF 树
ros2 run rqt_tf_tree rqt_tf_tree

# 检查节点图
ros2 run rqt_graph rqt_graph

# 监控 cmd_vel 输出
ros2 topic echo /cmd_vel

# 检查 TF 链完整性
ros2 run tf2_ros tf2_echo map base_link

# 监控导航状态
ros2 topic echo /navigate_to_pose/_action/feedback

# 发送导航目标
ros2 run nav2_simple_commander demo_navigate_to_pose
```

## 附录 B: 关键问题排查

### TF 链断裂

```bash
ros2 run tf2_ros tf2_echo map base_link
# 如果报错 "frame does not exist"，检查：
# 1. FAST-LIVO 是否正常运行，发布 /aft_mapped_to_init
# 2. static_tf_broadcaster 是否发布静态 TF
# 3. teaser_gicp 重定位是否完成
```

### 机器人不移动

```bash
# 1. 检查 cmd_vel 是否有输出
ros2 topic echo /cmd_vel

# 2. 检查 velocity_smoother 是否超时（1秒无指令则停止）
ros2 topic echo /cmd_vel_nav  # 对比 raw 和 smoothed

# 3. 检查 behavior_server 是否卡在恢复行为
ros2 topic echo /behavior_server/transition_event

# 4. 检查串口/UDP 是否正常工作
ls /dev/ttyUSB0
```

### 全局规划失败

```bash
# 1. 检查地图是否加载
ros2 service call /map_server/map nav2_msgs/srv/GetMap

# 2. 检查 costmap 是否有障碍物挡住
# 在 RViz 中添加 "Map" 和 "GlobalCostmap" 显示
```

---

*文档基于 SCURC_Nav_Sim v1.0.0，ROS 2 Humble，最后更新 2026-06-26*
