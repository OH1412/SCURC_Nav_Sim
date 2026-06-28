# Nav2 参数详解参考手册

> **文件**: [nav2_params.yaml](src/robot_functionality/legged_bringup/params/nav2_params.yaml)
> **ROS2 Humble | DWB Local Planner | Theta\* Global Planner**
> **最后更新**: 2026-06-28

---

## 目录

- [1. 快速导航](#1-快速导航)
- [2. controller_server（局部控制器）](#2-controller_server局部控制器)
  - [2.1 通用控制参数](#21-通用控制参数)
  - [2.2 DWB 速度限制](#22-dwb-速度限制)
  - [2.3 DWB 加速度限制](#23-dwb-加速度限制)
  - [2.4 DWB 采样器参数](#24-dwb-采样器参数)
  - [2.5 DWB 评价器 (Critics)](#25-dwb-评价器-critics)
  - [2.6 目标检查器](#26-目标检查器)
  - [2.7 进度检查器](#27-进度检查器)
- [3. local_costmap（局部代价地图）](#3-local_costmap局部代价地图)
  - [3.1 基础参数](#31-基础参数)
  - [3.2 static_layer（非致命静态层）](#32-static_layer非致命静态层)
  - [3.3 local_obstacle_layer（强度障碍物层）](#33-local_obstacle_layer强度障碍物层)
  - [3.4 local_inflation_layer（局部膨胀层）](#34-local_inflation_layer局部膨胀层)
- [4. global_costmap（全局代价地图）](#4-global_costmap全局代价地图)
  - [4.1 基础参数](#41-基础参数)
  - [4.2 static_layer](#42-static_layer)
  - [4.3 global_inflation_layer（全局膨胀层）](#43-global_inflation_layer全局膨胀层)
- [5. planner_server（全局规划器 — Theta\*）](#5-planner_server全局规划器--theta)
- [6. behavior_server（恢复行为）](#6-behavior_server恢复行为)
- [7. bt_navigator（行为树导航器）](#7-bt_navigator行为树导航器)
- [8. velocity_smoother（速度平滑器）](#8-velocity_smoother速度平滑器)
- [9. waypoint_follower（航点跟随器）](#9-waypoint_follower航点跟随器)
- [10. map_server / map_saver](#10-map_server--map_saver)
- [11. 附录：区域切换参数对照表](#11-附录区域切换参数对照表)
- [12. 自定义节点参数（从 Launch 文件提取）](#12-自定义节点参数从-launch-文件提取)
  - [12.1 位置切换器](#121-position_based_param_switcher)
  - [12.2 障碍物尺度控制器](#122-obstacle_scale_controller)
  - [12.3 UDP 速度桥接](#123-cmd_vel_udp_bridge)
  - [12.4 机械臂控制服务器](#124-arm_control_server)
  - [12.5 机械臂使命触发器](#125-arm_mission_trigger)
  - [12.6 起立命令发送器](#126-stand_up_sender)
  - [12.7 启动时序参数](#127-bringup_timing)

---

## 图例

| 标记 | 含义 |
|------|------|
| 🔄 | 由 [position_based_param_switcher.py](src/robot_functionality/legged_bringup/nodes/position_based_param_switcher.py) 动态切换 |
| ⚠️ | 危险参数 — 调错可能导致碰撞、卡死或不稳定 |
| 🟠 | 中间区 (1.35m ≤ x ≤ 3.35m) 专用值 |
| 🟢 | 边缘区 (x < 1.35m 或 x > 3.35m) 专用值 |
| 🔵 | 两区共有值（不随区域切换改变） |

---

## 1. 快速导航

### 按调参目的跳转

| 我想... | 跳转到 |
|---------|--------|
| 让机器人走得更快/更慢 | [DWB 速度限制](#22-dwb-速度限制) |
| 让机器人加速/减速更猛 | [DWB 加速度限制](#23-dwb-加速度限制) |
| 机器人离障碍物太近/太远 | [ObstacleFootprint critic](#251-obstaclefootprint-) 或 [膨胀层](#34-local_inflation_layer局部膨胀层) |
| 机器人到目标点不停/提前停 | [目标检查器](#26-目标检查器) |
| 机器人旋转太猛/不旋转 | [RotateToGoal](#252-rotatetogoal-) / [MaintainYawCritic](#258-maintainyawcritic-) |
| 机器人不走直线、蛇形摆动 | [PathAlign](#255-pathalign-) / [PathDist](#256-pathdist-) |
| 全局路径规划绕远路/撞墙 | [planner_server](#5-planner_server全局规划器--theta) |
| 局部代价地图范围不够大 | [local_costmap 基础参数](#31-基础参数) |
| cmd_vel 突变/不平滑 | [velocity_smoother](#8-velocity_smoother速度平滑器) |
| 机器人卡住不恢复 | [behavior_server](#6-behavior_server恢复行为) |
| 中间区/边缘区行为切换不正常 | [区域切换参数对照表](#11-附录区域切换参数对照表) |
| 调整死区补偿、UDP 桥接、启动时序 | [自定义节点参数](#12-自定义节点参数从-launch-文件提取) |

---

## 2. controller_server（局部控制器）

**YAML 路径**: `controller_server.ros__parameters`
**插件**: `dwb_core::DWBLocalPlanner`（DWB = Dynamic Window Based 局部规划器）
**控制频率**: 10 Hz（每 0.1 秒输出一次 cmd_vel）

DWB 的工作原理：
1. **采样** — 在速度空间 (vx, vy, vtheta) 中采样数千条候选轨迹
2. **评分** — 每条轨迹经过多个 Critics（评价器）打分
3. **选优** — 选总分最低（最优）的轨迹，输出其速度指令

---

### 2.1 通用控制参数

#### `controller_frequency`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `controller_server.ros__parameters.controller_frequency` |
| **当前值** | `10.0` |
| **单位** | Hz |
| **作用** | DWB 控制循环频率。每秒输出 10 次 cmd_vel。 |
| **调大** | 控制更密集，轨迹跟踪更精确，但 CPU 负载更高 |
| **调小** | CPU 负载低，但可能在高速时跟踪精度下降 |
| **注意** | 需与 `sim_time` 配合：频率降低时应增大 sim_time 保证前瞻距离 |

#### `min_x_velocity_threshold`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `controller_server.ros__parameters.min_x_velocity_threshold` |
| **当前值** | `0.05` |
| **单位** | m/s |
| **作用** | 当 DWB 输出的 vx 绝对值低于此阈值时，视为 0（不发 X 方向速度） |
| **调大** | 过滤更多小速度噪声，但可能无法精细调节 |
| **调小** | 允许更小的速度输出，但可能引入抖动 |
| **相关参数** | [trans_stopped_velocity](#trans_stopped_velocity) |

#### `min_y_velocity_threshold`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `controller_server.ros__parameters.min_y_velocity_threshold` |
| **当前值** | `0.05` |
| **单位** | m/s |
| **作用** | 当 DWB 输出的 vy 绝对值低于此阈值时，视为 0。对全向移动机器人的侧移噪声过滤很重要。 |
| **注意** | 在中间区 vy 已被 `min_vel_y=0, max_vel_y=0` 强制为 0，这个阈值是额外保障 |

#### `min_theta_velocity_threshold`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `controller_server.ros__parameters.min_theta_velocity_threshold` |
| **当前值** | `0.1` |
| **单位** | rad/s |
| **作用** | 当 DWB 输出的 vtheta 绝对值低于此阈值时，视为 0 |

#### `failure_tolerance`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `controller_server.ros__parameters.failure_tolerance` |
| **当前值** | `0.3` |
| **单位** | 秒 |
| **作用** | 控制器允许的连续失败时间。超过此时间无有效控制指令，触发恢复行为 |
| **调大** | 给 DWB 更多时间自行恢复，减少不必要的 behavior 介入 |
| **调小** | 更快触发恢复行为（spin/backup），但可能频繁打断正常导航 |

#### `odom_topic`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `controller_server.ros__parameters.odom_topic` |
| **当前值** | `"state_estimation"` |
| **作用** | DWB 获取机器人当前速度的里程计话题。本项目使用 FAST-LIVO 转发的里程计 |

#### `transform_tolerance`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `controller_server.ros__parameters.transform_tolerance` |
| **当前值** | `1.0` |
| **单位** | 秒 |
| **作用** | TF 变换查找的时间容差。设为 1.0 秒较为宽松，容忍 FAST-LIVO 可能出现的 TF 延迟 |

---

### 2.2 DWB 速度限制

> **物理意义**: DWB 在这些边界构成的"速度窗口"内采样轨迹。如果 min=max，则该轴被完全锁定。

#### `min_vel_x` / `max_vel_x`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `FollowPath.min_vel_x` / `FollowPath.max_vel_x` |
| **当前值** | `-2.0` / `2.0` |
| **单位** | m/s |
| **作用** | X 方向（前后）速度范围。负值 = 允许后退（全向移动） |
| **max_vel_x=2.0 意义** | 机器人最快向前 2 m/s |
| **min_vel_x=-2.0 意义** | 机器人最快后退 2 m/s |
| **注意** | 实机启动时，[navigation.launch.py](src/robot_functionality/legged_bringup/launch/navigation.launch.py) 可能从 deploy_cpp 配置文件动态覆盖此值 |

#### `min_vel_y` / `max_vel_y` 🔄 ⚠️
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `FollowPath.min_vel_y` / `FollowPath.max_vel_y` |
| **当前值（默认=中间区）** | 🟠 `0.0` / `0.0` |
| **边缘区值** | 🟢 `-1.4` / `1.4` |
| **单位** | m/s |
| **作用** | Y 方向（左右侧移）速度范围 |
| **中间区=0** | 采样器不生成任何带 vy 的轨迹 → 只能走 X 方向直线 |
| **边缘区=±1.4** | 恢复全向移动，允许侧移 |
| **⚠️ 警告** | 如果中间区也设为非零，机器人可能在狭窄通道中侧移撞墙 |

#### `max_vel_theta`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `FollowPath.max_vel_theta` |
| **当前值** | `1.2` |
| **单位** | rad/s（≈ 69°/s） |
| **作用** | 最大旋转速度。DWB 不能输出超过此值的角速度 |
| **调大** | 旋转更灵活，但四足机器人可能失稳 |
| **调小** | 旋转更平稳，但转向慢 |

#### `min_speed_xy`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `FollowPath.min_speed_xy` |
| **当前值** | `0.4` |
| **单位** | m/s |
| **作用** | 最小 XY 合速度 `sqrt(vx² + vy²)`。低于此值的轨迹被丢弃 |
| **为什么需要** | 四足机器人存在最小有效速度——速度太小时无法克服静摩擦/死区，机器人不动 |
| **调大** | 确保机器人一定动起来，但失去精细接近能力 |
| **调小** | 允许更慢的精细移动，但可能输出无效小速度 |
| **相关参数** | [UDP 死区补偿](#) — `min_effective_vx=0.4` 与此值配合 |

#### `max_speed_xy`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `FollowPath.max_speed_xy` |
| **当前值** | `3.0` |
| **单位** | m/s |
| **作用** | 最大 XY 合速度上限。即使 vx=2.0, vy=1.4，合速度也不会超过 3.0 |
| **计算** | `sqrt(max_vel_x² + max_vel_y²)` = `sqrt(4 + 1.96)` ≈ 2.44 < 3.0，实际不被触发 |

#### `min_speed_theta`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `FollowPath.min_speed_theta` |
| **当前值** | `-1.2` |
| **单位** | rad/s |
| **作用** | 最小角速度（负值=允许反向旋转）。与 `max_vel_theta` 对称 |

---

### 2.3 DWB 加速度限制

> **物理意义**: 限制 cmd_vel 在相邻控制周期（0.1s）之间的最大变化量。
> 例：`acc_lim_x=12.0` → 每 0.1s 最大速度增量 = 12.0 × 0.1 = 1.2 m/s²

#### `acc_lim_x`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `FollowPath.acc_lim_x` |
| **当前值** | `12.0` |
| **单位** | m/s²（瞬时加速度上限） |
| **作用** | X 方向加速度上限。值很大（12 m/s² ≈ 1.2g），意味着几乎不限制加速 |
| **为什么这么大** | 四足机器人可以瞬间加速，不需要 DWB 层面限加速度；实际平滑由 velocity_smoother 完成 |
| **相关参数** | [velocity_smoother.max_accel](#max_accel--) |

#### `acc_lim_y`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `FollowPath.acc_lim_y` |
| **当前值** | `6.0` |
| **单位** | m/s² |
| **作用** | Y 方向（侧移）加速度上限。约为 X 方向的一半，因为侧移加速能力较弱 |

#### `acc_lim_theta`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `FollowPath.acc_lim_theta` |
| **当前值** | `20.0` |
| **单位** | rad/s² |
| **作用** | 角加速度上限。值很大，几乎不限制 |

#### `decel_lim_x` / `decel_lim_y` / `decel_lim_theta`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `FollowPath.decel_lim_x/y/theta` |
| **当前值** | `-4.0` / `-3.0` / `-20.0` |
| **单位** | m/s² 或 rad/s² |
| **作用** | 减速度上限（负值 = 减速方向）。限制 DWB 输出减速的幅度 |
| **注意** | 减速度限制比加速度限制更严格（4 vs 12），这可能影响急停能力。如需更快速的刹车，可增大绝对值 |

---

### 2.4 DWB 采样器参数

> **关键概念**: DWB 在速度空间内均匀采样 `vx_samples × vy_samples × vtheta_samples` 条轨迹。
> 当前配置 = 20 × 20 × 20 = **8000 条轨迹**，每条模拟 `sim_time` 秒（1.5s）。
> 速度步长：vx 步长 = (2.0 - (-2.0)) / 19 ≈ **0.2105 m/s**，vy 类似。

#### `vx_samples`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `FollowPath.vx_samples` |
| **当前值** | `20` |
| **作用** | X 方向速度采样数量。在 [min_vel_x, max_vel_x] 区间内均匀采样 |
| **调大** | 更精细的速度选择，但计算量 O(n³) 增长（20→30 意味着 8000→18000 轨迹） |
| **调小** | 减少计算量，但可能跳过最优速度 |

#### `vy_samples`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `FollowPath.vy_samples` |
| **当前值** | `20` |
| **作用** | Y 方向速度采样数量 |
| **中间区影响** | 虽然 vy_samples=20，但 min_vel_y=max_vel_y=0，实际上只有 vy=0 被采样 |

#### `vtheta_samples`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `FollowPath.vtheta_samples` |
| **当前值** | `20` |
| **作用** | 角速度采样数量。在 [-max_vel_theta, max_vel_theta] 区间均匀采样 |
| **步长** | 1.2 × 2 / 19 ≈ 0.126 rad/s = 7.2°/s 每步 |

#### `sim_time` ⚠️
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `FollowPath.sim_time` |
| **当前值** | `1.5` |
| **单位** | 秒 |
| **作用** | DWB 对每条候选轨迹进行前向模拟的时间长度 |
| **物理意义** | 最大前瞻距离 = sim_time × max_vel_x = 1.5 × 2.0 = **3.0 米** |
| **调大** | "看得更远"，能提前避开障碍物，但模拟更长的轨迹耗时更多，且远处预测不准 |
| **调小** | 反应更快，但可能"短视"——撞上突然出现的障碍物 |
| **⚠️ 注意** | 需确保 local_costmap 尺寸 ≥ 前瞻距离 × 2。当前 costmap 10m×10m，前瞻 3m 绰绰有余 |

#### `linear_granularity`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `FollowPath.linear_granularity` |
| **当前值** | `0.05` |
| **单位** | 米 |
| **作用** | 轨迹模拟时沿路径的采样间距。每 5cm 取一个点评估代价 |
| **调大** | 减少评分计算量，但可能漏掉小障碍物 |
| **调小** | 更精确的碰撞检测，但计算量增大 |

#### `angular_granularity`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `FollowPath.angular_granularity` |
| **当前值** | `0.025` |
| **单位** | 弧度（≈ 1.4°） |
| **作用** | 轨迹模拟时角度采样间距 |

#### `transform_tolerance` (DWB)
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `FollowPath.transform_tolerance` |
| **当前值** | `0.2` |
| **单位** | 秒 |
| **作用** | DWB 内部 TF 查找容差。比 controller_server 级别的 1.0s 更严格 |

#### `xy_goal_tolerance` (DWB)
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `FollowPath.xy_goal_tolerance` |
| **当前值** | `0.08` |
| **单位** | 米 |
| **作用** | DWB 内部判定到达目标的 XY 距离容差 |
| **注意** | 这与 `general_goal_checker.xy_goal_tolerance` (0.10m) 是不同的检查器。DWB 会先用自己的容差判断，再由 goal_checker 最终确认 |

#### `trans_stopped_velocity`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `FollowPath.trans_stopped_velocity` |
| **当前值** | `0.08` |
| **单位** | m/s |
| **作用** | 判定机器人"已停止"的线速度阈值。低于此值认为机器人静止 |
| **作用场景** | DWB 在机器人停止时允许切换运动模式（如从前进变为原地旋转） |

#### `short_circuit_trajectory_evaluation`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `FollowPath.short_circuit_trajectory_evaluation` |
| **当前值** | `True` |
| **作用** | 短路评估优化。当某条轨迹的某个 critic 得分已经超过当前最优轨迹总分时，不再对该轨迹计算剩余 critics |
| **效果** | 大幅减少无效计算，8000 条轨迹中很多在第一个 critic 就被淘汰 |
| **建议** | 保持 True，除非调试 critic 行为时需要看完整评分 |

#### `stateful`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `FollowPath.stateful` |
| **当前值** | `True` |
| **作用** | 保持 DWB 跨周期的内部状态（如上周期选中的速度），用于加速度限制和振荡检测 |

#### `debug_trajectory_details`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `FollowPath.debug_trajectory_details` |
| **当前值** | `False` |
| **作用** | 是否发布详细的轨迹评分信息（用于 RViz 可视化调试） |
| **建议** | 平时 False；调参时打开可以看每条轨迹的评分分解 |

---

### 2.5 DWB 评价器 (Critics)

> **核心概念**: 每个 critic 给候选轨迹打分，**分数越低越好**（DWB 做最小化）。
> 最终轨迹得分 = Σ (scale × critic_score)。
> 9 个 critics 的加载顺序就是评分顺序，`short_circuit` 开启后，排前面的 critic 先评分。

**Critics 列表** ([nav2_params.yaml:295](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L295)):
```
["RotateToGoal", "Oscillation", "ObstacleFootprint", "GoalAlign",
 "PathAlign", "PathDist", "GoalDist", "MaintainYawCritic", "DecouplingCritic"]
```

#### 评分优先级分析

| 顺序 | Critic | 典型得分范围 | 作用阶段 |
|------|--------|-------------|----------|
| 1 | RotateToGoal | 0 ~ 32×π | 全程（中间区=0） |
| 2 | Oscillation | 0 ~ 大值 | 全程检测振荡 |
| 3 | ObstacleFootprint | 0 ~ 50×100 | ⚠️ 安全第一 |
| 4 | GoalAlign | 0 ~ 24×距离 | 接近目标时 |
| 5 | PathAlign | 0 ~ 32×角度 | 路径跟踪 |
| 6 | PathDist | 0 ~ 32×距离 | 路径跟踪 |
| 7 | GoalDist | 0 ~ 16×距离 | 全程趋近目标 |
| 8 | MaintainYawCritic | 0 ~ 5000×角度 | 🟠中间区 yaw 锁定 |
| 9 | DecouplingCritic | 0 ~ 30×1.0 | 🟢边缘区速度解耦 |

---

#### 2.5.1 `ObstacleFootprint` ⚠️ 🔵

| 字段 | 内容 |
|------|------|
| **YAML 路径** | `FollowPath.ObstacleFootprint.scale` |
| **当前值** | `50.0` 🔵（两区相同） |
| **作用** | **最重要的安全 critic**。将机器人 footprint 投影到 costmap 上，检查是否与障碍物碰撞。代价 = 碰撞栅格数 × costmap 代价值 × scale |
| **为什么 scale 最大** | 安全第一——宁可绕路也不能撞。ObstacleFootprint 的 scale(50) 在所有非零 critic 中最高 |
| **⚠️ 调小** | 机器人会更激进地靠近障碍物——**危险！**除非你同时增大了膨胀层半径 |
| **调大** | 机器人离障碍物更远，但可能过于保守，窄通道无法通过 |
| **相关参数** | [costmap footprint](#footprint-), [膨胀层](#34-local_inflation_layer局部膨胀层) |

---

#### 2.5.2 `RotateToGoal` 🔄

| 字段 | 内容 |
|------|------|
| **YAML 路径** | `FollowPath.RotateToGoal.scale` |
| **中间区值** | 🟠 `0.0` |
| **边缘区值** | 🟢 `32.0` |
| **作用** | 奖励（惩罚小=奖励）朝向目标方向旋转的轨迹。计算轨迹末端朝向与目标方向的夹角，`cost = scale × angle_diff` |
| **中间区=0** | 不关心朝向——机器人可以侧移到达目标 |
| **边缘区=32** | 强奖励朝向目标——到达目标时已经对准了正确方向 |
| **相关参数** | `RotateToGoal.slowing_factor`, `RotateToGoal.lookahead_time` |

##### `RotateToGoal.slowing_factor`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `FollowPath.RotateToGoal.slowing_factor` |
| **当前值** | `5.0` |
| **作用** | 接近目标时的减速因子。值越大，越靠近目标时旋转速度越小 |
| **物理意义** | 有效速度 = 原速度 / (1 + slowing_factor × dist_to_goal) |

##### `RotateToGoal.lookahead_time`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `FollowPath.RotateToGoal.lookahead_time` |
| **当前值** | `-1.0` |
| **作用** | 旋转朝向的前瞻时间。-1 表示使用默认值（由 DWB 内部计算） |

---

#### 2.5.3 `Oscillation` 🔵

| 字段 | 内容 |
|------|------|
| **YAML 路径** | `FollowPath.Oscillation.scale` |
| **当前值** | （使用 DWB 默认值，未在 YAML 中显式设置） |
| **作用** | 检测并惩罚来回振荡的轨迹（如正负速度交替）。防止机器人在原地"哆嗦" |
| **原理** | 比较当前选中的速度与历史速度，如果符号频繁反转则扣分 |

---

#### 2.5.4 `GoalAlign` 🔄

| 字段 | 内容 |
|------|------|
| **YAML 路径** | `FollowPath.GoalAlign.scale` |
| **中间区值** | 🟠 `0.0` |
| **边缘区值** | 🟢 `24.0` |
| **作用** | 奖励轨迹末端朝向与目标姿态对齐。与 RotateToGoal 类似但更关注轨迹终态 |
| **中间区=0** | 不需对齐朝向 |
| **边缘区=24** | 到达目标时朝向已对齐，可以直接开始下一段导航 |

##### `GoalAlign.forward_point_distance`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `FollowPath.GoalAlign.forward_point_distance` |
| **当前值** | `0.1` |
| **单位** | 米 |
| **作用** | 从轨迹末端沿朝向方向前推的距离，用于计算对齐误差 |

---

#### 2.5.5 `PathAlign` 🔄

| 字段 | 内容 |
|------|------|
| **YAML 路径** | `FollowPath.PathAlign.scale` |
| **中间区值** | 🟠 `0.0` |
| **边缘区值** | 🟢 `32.0` |
| **作用** | 奖励轨迹方向与全局路径方向对齐。`cost = scale × angle_diff(轨迹朝向, 路径朝向)` |
| **中间区=0** | 不需要对齐路径方向（机器人 locked yaw=0 侧移走过） |
| **边缘区=32** | 强奖励沿路径方向行驶 |
| **相关参数** | [PathDist](#256-pathdist-) |

##### `PathAlign.forward_point_distance`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `FollowPath.PathAlign.forward_point_distance` |
| **当前值** | `0.1` |
| **单位** | 米 |
| **作用** | 前推距离，用于计算轨迹与路径的夹角 |

---

#### 2.5.6 `PathDist` 🔵

| 字段 | 内容 |
|------|------|
| **YAML 路径** | `FollowPath.PathDist.scale` |
| **当前值** | `32.0` 🔵（两区相同） |
| **作用** | 惩罚偏离全局路径的轨迹。cost = 轨迹终点到最近路径点的距离 × scale |
| **为什么两区相同** | 无论中间还是边缘区，都不能偏离路径太远 |
| **调大** | 机器人紧贴路径走，但可能"死板" |
| **调小** | 机器人更灵活，但可能绕远路 |

---

#### 2.5.7 `GoalDist` 🔵

| 字段 | 内容 |
|------|------|
| **YAML 路径** | `FollowPath.GoalDist.scale` |
| **当前值** | `16.0` 🔵（两区相同） |
| **作用** | 惩罚远离目标的轨迹。cost = 轨迹末端到目标点的距离 × scale |
| **为什么 scale 比 PathDist(32) 小** | 不能让 GoalDist 压倒 PathDist——否则机器人可能直接穿过障碍物走近路 |
| **调大** | 机器人更积极地接近目标，但可能忽视路径和障碍物 |
| **调小** | 机器人更依赖路径指引 |

---

#### 2.5.8 `MaintainYawCritic` 🔄 ⚠️

| 字段 | 内容 |
|------|------|
| **YAML 路径** | `FollowPath.dwb_yaw_constraint::MaintainYawCritic.scale` |
| **中间区值** | 🟠 `5000.0` |
| **边缘区值** | 🟢 `0.0` |
| **作用** | **自定义插件** — 强制机器人在 map 坐标系中保持固定 yaw=0°。`cost = scale × |当前yaw - 目标yaw|` |
| **scale=5000 的意义** | yaw 偏差 0.1 rad (≈5.7°) → cost=500。这个值远超 PathDist(~32) 和 GoalDist(~16)，确保 DWB 优先满足 yaw=0 约束 |
| **中间区** | 锁定朝向 0°，机器人只能用侧移(X方向)通过狭窄通道 |
| **边缘区=0** | 完全放开的旋转自由 |
| **⚠️ 注意** | scale=5000 是极端值——任何偏离 yaw=0 的轨迹都会获得天文数字的代价，本质上是被"不可选择" |

##### `MaintainYawCritic.desired_yaw`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `FollowPath.dwb_yaw_constraint::MaintainYawCritic.desired_yaw` |
| **当前值** | `0.0` |
| **单位** | 弧度 |
| **作用** | 目标 yaw 角（map 坐标系）。0.0 = 朝向地图 +X 方向 |

##### `MaintainYawCritic.reference_frame`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `FollowPath.dwb_yaw_constraint::MaintainYawCritic.reference_frame` |
| **当前值** | `"map"` |
| **作用** | yaw 角的参考坐标系。设为 "map" 表示在全局地图坐标系中保持固定朝向 |

---

#### 2.5.9 `DecouplingCritic` 🔄

| 字段 | 内容 |
|------|------|
| **YAML 路径** | `FollowPath.dwb_yaw_constraint::DecouplingCritic.scale` |
| **中间区值** | 🟠 `0.0` |
| **边缘区值** | 🟢 `30.0` |
| **作用** | **自定义插件** — 惩罚同时混合多轴速度的轨迹。鼓励"单轴优先"运动 |
| **算法** | 将 vx/vy/vtheta 各自归一化（除以 max），找**第二大的归一化分量**作为代价 |
| **效果** | 如果只有 vx 非零（纯前进）→ cost≈0，无惩罚。如果 vx=0.5, vy=0.3 → 第二大分量惩罚，轻微抑制。如果 vx=1.0, vy=1.0 同时全速 → heavy penalty |
| **边缘区=30** | 鼓励解耦运动，避免不稳定的多轴混合 |
| **中间区=0** | 不启用——因为 vy 已被速度边界锁死，且 yaw 被 MaintainYawCritic 锁死，不需要额外解耦 |

##### `DecouplingCritic.max_vx / max_vy / max_vtheta`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `FollowPath.dwb_yaw_constraint::DecouplingCritic.max_vx / max_vy / max_vtheta` |
| **当前值** | `2.0` / `1.4` / `1.2` |
| **作用** | 分别用于归一化 vx/vy/vtheta，使其在 [0,1] 范围内可比 |
| **注意** | 必须与 DWB 的实际速度限制一致，否则归一化失真 |

---

### 2.6 目标检查器

#### `general_goal_checker` 🔄

| 字段 | 内容 |
|------|------|
| **YAML 路径** | `controller_server.ros__parameters.general_goal_checker` |
| **插件** | `nav2_controller::SimpleGoalChecker` |

##### `xy_goal_tolerance`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `general_goal_checker.xy_goal_tolerance` |
| **当前值** | `0.10` 🔵（两区相同） |
| **单位** | 米 |
| **作用** | 判定"到达目标"的 XY 距离容差。机器人距离目标 10cm 以内即视为到达 |
| **调大** | 更容易判定到达，但可能在目标点还有偏差时就停止 |
| **调小** | 更精确到达，但可能因定位噪声导致迟迟无法判定到达 |

##### `yaw_goal_tolerance` 🔄
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `general_goal_checker.yaw_goal_tolerance` |
| **中间区值** | 🟠 `6.28`（= 2π ≈ 360°）|
| **边缘区值** | 🟢 `0.05236`（≈ 3°） |
| **单位** | 弧度 |
| **作用** | 判定"到达目标朝向"的角度容差 |
| **中间区=360°** | 完全不管朝向——只要 XY 到了就算完成 |
| **边缘区=3°** | 必须精确对准目标朝向才算到达。确保进入中间区前朝向正确 |

##### `stateful`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `general_goal_checker.stateful` |
| **当前值** | `False` |
| **作用** | 是否保持跨周期的目标检查状态。False = 每次独立判断 |

---

### 2.7 进度检查器

#### `progress_checker`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `controller_server.ros__parameters.progress_checker` |
| **插件** | `nav2_controller::SimpleProgressChecker` |
| **作用** | 监测机器人是否在向目标移动。如果长时间没有足够移动，触发 controller 失败 → behavior_server 接管 |

##### `required_movement_radius`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `progress_checker.required_movement_radius` |
| **当前值** | `0.5` |
| **单位** | 米 |
| **作用** | 在 `movement_time_allowance` 时间内，机器人必须移动至少这么远，否则判定为"卡住" |
| **调大** | 更容易触发卡住判定（需要移动更多才不算卡） |
| **调小** | 更宽容——小幅挪动也算有进展 |

##### `movement_time_allowance`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `progress_checker.movement_time_allowance` |
| **当前值** | `60.0` |
| **单位** | 秒 |
| **作用** | 允许机器人不移动的最长时间。超时后触发恢复行为 |
| **为什么是 60 秒** | DWB 可能在障碍物前"思考"很久，给予充足时间自行找到出路。60 秒很长——意味着机器人可以原地犹豫一分钟 |
| **调小** | 更快触发 backup/spin 恢复，但可能打断正在寻找最优路径的 DWB |

---

## 3. local_costmap（局部代价地图）

**YAML 路径**: `local_costmap.local_costmap.ros__parameters`
**坐标系**: `odom`（滚动窗口，跟随机器人移动）
**更新频率**: 20 Hz

局部代价地图是 DWB 做碰撞检测和轨迹评分的主战场。三层叠加：

```
local_costmap (10m×10m, 0.05m 分辨率, odom 坐标系)
  ├── static_layer        ← PGM 静态地图（非致命代价=200）
  ├── local_obstacle_layer ← /terrain_map 动态障碍物（强度过滤）
  └── local_inflation_layer ← 极小膨胀 (0.01m)，安全靠 footprint critic
```

---

### 3.1 基础参数

#### `update_frequency` / `publish_frequency`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `local_costmap.local_costmap.ros__parameters.update_frequency` / `publish_frequency` |
| **当前值** | `20.0` / `20.0` |
| **单位** | Hz |
| **作用** | 代价地图更新和发布频率。20Hz = 每 50ms 更新一次 |
| **注意** | 需与 `controller_frequency`(10Hz) 配合——代价地图更新频率应 ≥ 控制频率 |

#### `global_frame`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `local_costmap.local_costmap.ros__parameters.global_frame` |
| **当前值** | `odom` |
| **作用** | 局部代价地图的参考坐标系。使用 odom 而非 map，因为 local_costmap 是滚动窗口，随机器人移动 |

#### `robot_base_frame`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `local_costmap.local_costmap.ros__parameters.robot_base_frame` |
| **当前值** | `base_link` |
| **作用** | 机器人本体坐标系。代价地图以此为中心展开滚动窗口 |

#### `rolling_window`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `local_costmap.local_costmap.ros__parameters.rolling_window` |
| **当前值** | `true` |
| **作用** | 局部代价地图是否随机器人移动而滚动。必须为 true |

#### `width` / `height`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `local_costmap.local_costmap.ros__parameters.width` / `height` |
| **当前值** | `10` / `10` |
| **单位** | 米 |
| **作用** | 局部代价地图尺寸。10m × 10m 的方形窗口 |
| **与 sim_time 的关系** | 地图半径 5m > 最大前瞻距离 3m (sim_time × max_vel_x)，留有安全余量 |
| **调大** | 能检测更远的障碍物，但更新 200×200=40000 个栅格(0.05m分辨率)，计算量增大 |
| **调小** | 更快更新，但可能因为看不到远处的障碍物而撞上 |

#### `resolution`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `local_costmap.local_costmap.ros__parameters.resolution` |
| **当前值** | `0.05` |
| **单位** | 米/像素 |
| **作用** | 每个栅格代表 5cm。10m/0.05 = 200×200 栅格 |
| **调大** | 粗分辨率 → 更少栅格 → 更快，但障碍物表示精度下降 |
| **调小** | 细分辨率 → 更精确，但栅格数平方增长 |

#### `footprint` ⚠️
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `local_costmap.local_costmap.ros__parameters.footprint` |
| **当前值** | `[[0.2971, 0.19185], [0.2971, -0.19185], [-0.44518, -0.19185], [-0.44518, 0.19185]]` |
| **作用** | 机器人的外轮廓多边形（4个顶点 = 矩形）。DWB 把这个形状投影到代价地图上检测碰撞 |
| **几何意义** | 前宽 0.384m，后长 0.445m，总长约 0.742m。机器人中心偏向后方（前0.297 vs 后0.445） |
| **⚠️ 内切圆** | 前向 0.297m / 后向 0.445m。后腿需要更大的通过空间 |
| **⚠️ 注意** | footprint 直接决定碰撞检测精度——设太小会撞，设太大窄通道过不去 |

---

### 3.2 `static_layer`（非致命静态层）

| 字段 | 内容 |
|------|------|
| **YAML 路径** | `local_costmap.local_costmap.ros__parameters.static_layer` |
| **插件** | `costmap_intensity::StaticLayerNonLethal`（自定义插件） |

#### `occupied_cost_value`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `static_layer.occupied_cost_value` |
| **当前值** | `200` |
| **作用** | PGM 地图中黑色障碍物在局部代价地图中的代价值。200 = INSCRIBED（内切区域），**不是致命代价(254)** |
| **为什么用 200 而不是 254** | 标准 StaticLayer 用 254(LETHAL)，但地图标注不精确可能导致误触发碰撞。200 让障碍物在 RViz 中可见（橙色），但不一定触发 DWB 的碰撞判断 |
| **⚠️ 注意** | DWB 的 ObstacleFootprint critic 的碰撞阈值是 253+——所以值为 200 的静态障碍物**不会**触发碰撞。这是一个设计选择：静态地图仅做参考 |

---

### 3.3 `local_obstacle_layer`（强度障碍物层）

| 字段 | 内容 |
|------|------|
| **YAML 路径** | `local_costmap.local_costmap.ros__parameters.local_obstacle_layer` |
| **插件** | `costmap_intensity::ObstacleLayerIntensity`（自定义插件） |
| **数据源** | `/terrain_map` PointCloud2 |
| **作用** | 基于点云 intensity 字段过滤动态障碍物。只有 intensity 在 [min, max] 范围内的点才会被标记为致命障碍物(254) |

#### `enabled`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `local_obstacle_layer.enabled` |
| **当前值** | `True` |
| **作用** | 是否启用动态障碍物检测。这是实际生效的障碍物检测层 |

#### `max_obstacle_intensity` / `min_obstacle_intensity`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `local_obstacle_layer.max_obstacle_intensity` / `min_obstacle_intensity` |
| **当前值** | `2.0` / `0.2` |
| **作用** | 障碍物 intensity 过滤窗口。intensity 在此范围内的点被认为是障碍物 |
| **调大 max** | 更多点被识别为障碍物 → 更保守 |
| **调小 min** | 更多低强度点被识别（可能包含地面噪声） |

#### `pointcloud.topic`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `local_obstacle_layer.observation_sources.pointcloud.topic` |
| **当前值** | `/terrain_map` |
| **作用** | 订阅的点云话题。来自 terrain_analysis 的地形分析结果 |

#### `pointcloud.max_obstacle_height` / `min_obstacle_height`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `pointcloud.max_obstacle_height` / `min_obstacle_height` |
| **当前值** | `0.5` / `-0.5` |
| **单位** | 米 |
| **作用** | 障碍物高度过滤。只关心机器人高度范围内的障碍物 |
| **为什么 ±0.5m** | 四足机器人步态高度约 0.3-0.4m，±0.5m 覆盖了可能碰撞的高度范围 |

#### `pointcloud.obstacle_max_range` / `obstacle_min_range`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `pointcloud.obstacle_max_range` / `obstacle_min_range` |
| **当前值** | `4.5` / `0.2` |
| **单位** | 米 |
| **作用** | 障碍物检测的雷达距离范围。4.5m 内的点才被考虑，0.2m 以内的忽略（可能是机器人自身） |
| **与 costmap 尺寸的关系** | costmap 半径 5m，障碍物检测 4.5m——给地图边界留 0.5m 余量 |

#### `pointcloud.clearing` / `marking`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `pointcloud.clearing` / `marking` |
| **当前值** | `True` / `True` |
| **作用** | clearing=True：在射线路径上清除障碍物标记（动态障碍物移走后清除）。marking=True：在新检测到障碍物的位置标记 |

---

### 3.4 `local_inflation_layer`（局部膨胀层）

| 字段 | 内容 |
|------|------|
| **YAML 路径** | `local_costmap.local_costmap.ros__parameters.local_inflation_layer` |
| **插件** | `nav2_costmap_2d::InflationLayer` |

#### `inflation_radius` ⚠️
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `local_inflation_layer.inflation_radius` |
| **当前值** | `0.01` |
| **单位** | 米 |
| **作用** | 障碍物膨胀半径——在致命障碍物周围扩展多少距离作为"不可靠近区域" |
| **为什么只有 0.01m?** | 几乎不膨胀！碰撞安全完全依赖 DWB 的 `ObstacleFootprint` critic 通过 footprint 投影检测碰撞。局部膨胀层的极小值说明设计上信任 footprint critic 而不是代价地图膨胀 |
| **⚠️ 注意** | 这是一个激进的设计选择。如果 ObstacleFootprint critic 失效或被关闭，机器人没有任何膨胀层保护 |

#### `cost_scaling_factor`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `local_inflation_layer.cost_scaling_factor` |
| **当前值** | `3.0` |
| **作用** | 代价衰减因子。代价值 = e^(-factor × distance) × 253。值越大，代价随距离衰减越快 |
| **调大** | 代价衰减更快，靠近障碍物时代价急剧上升（更"硬"的边界） |
| **调小** | 代价衰减更平缓，更"软"的避障 |
| **由于 radius=0.01** | 这个参数实际上几乎没有效果——膨胀半径太小了 |

---

## 4. global_costmap（全局代价地图）

**YAML 路径**: `global_costmap.global_costmap.ros__parameters`
**坐标系**: `map`
**更新频率**: 1 Hz（全局地图不需要高频更新）

```
global_costmap (全地图尺寸, 0.1m 分辨率, map 坐标系)
  ├── static_layer          ← 加载 PGM 地图（标准 StaticLayer）
  └── global_inflation_layer ← 膨胀半径 0.3m
```

---

### 4.1 基础参数

#### `update_frequency` / `publish_frequency`
| 字段 | 内容 |
|------|------|
| **当前值** | `1.0` / `1.0` Hz |
| **作用** | 全局代价地图只需 1Hz 更新——静态地图不会变 |

#### `global_frame` / `robot_base_frame`
| 字段 | 内容 |
|------|------|
| **当前值** | `map` / `base_link` |
| **作用** | 使用 map 坐标系（全局固定），与 local_costmap 的 odom 坐标系不同 |

#### `resolution`
| 字段 | 内容 |
|------|------|
| **当前值** | `0.1` (10cm/像素) |
| **作用** | 比 local_costmap(0.05) 粗一倍。全局规划不需要厘米级精度 |

#### `track_unknown_space`
| 字段 | 内容 |
|------|------|
| **当前值** | `true` |
| **作用** | 是否将未知区域视为可通过（但高代价）。true = 可以通过未知区域但代价高 |

#### `footprint`
| 字段 | 内容 |
|------|------|
| **当前值** | 与 local_costmap 相同 |
| **作用** | 全局规划时也使用相同的 robot footprint |

---

### 4.2 `static_layer`

| 字段 | 内容 |
|------|------|
| **插件** | `nav2_costmap_2d::StaticLayer`（标准插件，非自定义） |
| **作用** | 加载 PGM 地图到全局代价地图。与 local_costmap 的自定义 StaticLayerNonLethal 不同，这里使用标准层——障碍物值=254 (LETHAL) |

---

### 4.3 `global_inflation_layer`（全局膨胀层）

#### `inflation_radius`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `global_inflation_layer.inflation_radius` |
| **当前值** | `0.3` |
| **单位** | 米 |
| **作用** | 全局规划时的障碍物膨胀半径。比局部膨胀层的 0.01m 大得多 |
| **为什么全局=0.3m?** | 全局规划需要安全余量。Theta\* 规划路径时，路径会离膨胀后的障碍物至少 0.3m（加上 footprint 内切圆 0.3m = 总共约 0.6m 安全距离） |

#### `cost_scaling_factor`
| 字段 | 内容 |
|------|------|
| **当前值** | `3.0` |
| **作用** | 与局部膨胀层相同的衰减因子 |

---

## 5. planner_server（全局规划器 — Theta\*）

**YAML 路径**: `planner_server.ros__parameters`
**插件**: `nav2_theta_star_planner/ThetaStarPlanner`

Theta\* 是 A\* 的改进版——可以在任意角度转向（不限 8 邻域），生成更平滑的路径。

#### `expected_planner_frequency`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `planner_server.ros__parameters.expected_planner_frequency` |
| **当前值** | `10.0` |
| **单位** | Hz |
| **作用** | 规划器的期望运行频率。实际规划只在收到新 goal 或重规划时触发 |

#### `how_many_corners` ⚠️
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `GridBased.how_many_corners` |
| **当前值** | `8` |
| **作用** | Theta\* 在栅格的每条边上检查多少个角点。8 表示每个栅格边上有 8 个候选过渡点 |
| **调大** | 路径更平滑，可以在更多角度穿越栅格，但规划时间增加 |
| **调小** | 路径更粗糙（接近 A\* 的 8 邻域），但规划更快 |
| **8 的含义** | 每个栅格边划分 8 段 → 9 个候选点，提供丰富的穿越角度选择 |

#### `w_euc_cost`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `GridBased.w_euc_cost` |
| **当前值** | `1.0` |
| **作用** | 欧几里得距离权重。路径总代价 += w_euc × 路径长度 |
| **调大** | 更重视缩短路径距离——可能选择更直接但靠近障碍物的路径 |
| **调小** | 更愿意绕路 |

#### `w_traversal_cost`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `GridBased.w_traversal_cost` |
| **当前值** | `2.0` |
| **作用** | 穿越代价权重。路径总代价 += w_traversal × costmap 代价值 |
| **为什么 > w_euc(1.0)?** | 优先安全——穿越高代价区域的惩罚是距离代价的 2 倍 |
| **调大** | 更远离障碍物，路径更安全但可能更长 |
| **调小** | 更激进，可能贴近障碍物走捷径 |

#### `w_heuristic_cost`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `GridBased.w_heuristic_cost` |
| **当前值** | `1.0` |
| **作用** | A\* 启发式权重。1.0 = 标准 A\* 启发式（保证最优）。>1.0 = 加权 A\*（更快但非最优） |

---

## 6. behavior_server（恢复行为）

**YAML 路径**: `behavior_server.ros__parameters`
**作用**: 当控制器失败（卡住、无法规划）时，执行一系列恢复动作。

#### 恢复行为加载顺序
```yaml
behavior_plugins: ["spin", "backup", "drive_on_heading", "assisted_teleop", "wait"]
```

#### `cycle_frequency`
| 字段 | 内容 |
|------|------|
| **当前值** | `10.0` Hz |
| **作用** | 恢复行为服务器的循环频率 |

#### `costmap_topic`
| 字段 | 内容 |
|------|------|
| **当前值** | `local_costmap/costmap_raw` |
| **作用** | 恢复行为检查的代价地图话题。用于 BackUp 行为寻找自由空间方向 |

#### `simulate_ahead_time`
| 字段 | 内容 |
|------|------|
| **当前值** | `2.0` 秒 |
| **作用** | 恢复行为模拟前瞻时间（如 DriveOnHeading 的前瞻） |

#### `max_rotational_vel` / `min_rotational_vel`
| 字段 | 内容 |
|------|------|
| **当前值** | `1.0` / `0.4` rad/s |
| **作用** | Spin 行为使用的旋转速度范围 |

#### `robot_radius` ⚠️
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `behavior_server.ros__parameters.robot_radius` |
| **当前值** | `0.3` |
| **单位** | 米 |
| **作用** | BackUpTwzFree 使用的机器人半径。在代价地图上搜索以此半径为中心的圆形自由空间 |
| **⚠️ 注意** | 0.3m < footprint 后半径 0.445m！这意味着 BackUp 行为可能认为可以通过的区域实际上不够宽 |

#### `max_radius`
| 字段 | 内容 |
|------|------|
| **当前值** | `3.5` |
| **单位** | 米 |
| **作用** | BackUp 搜索自由空间的最大半径。在 3.5m 范围内找最近的自由空间质心方向 |

#### `free_threshold`
| 字段 | 内容 |
|------|------|
| **当前值** | `3` |
| **作用** | 判定"自由空间"的最小栅格数。至少需要 3 个连续的空闲栅格才认为是可后退的方向 |

#### `rotational_acc_lim`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `behavior_server.ros__parameters.rotational_acc_lim` |
| **当前值** | `3.2` |
| **单位** | rad/s² |
| **作用** | Spin 行为的角加速度限制。限制原地旋转时的加速度 |

#### `service_name`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `behavior_server.ros__parameters.service_name` |
| **当前值** | `"local_costmap/get_costmap"` |
| **作用** | BackUpTwzFree 获取代价地图的服务名称 |

#### `visualization`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `behavior_server.ros__parameters.visualization` |
| **当前值** | `True` |
| **作用** | 是否在 RViz 中发布恢复行为的可视化标记（如 BackUp 搜索的自由空间方向箭头） |

#### `footprint_topic`
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `behavior_server.ros__parameters.footprint_topic` |
| **当前值** | `local_costmap/published_footprint` |
| **作用** | BackUp 行为获取 robot footprint 的话题 |

---

## 7. bt_navigator（行为树导航器）

**YAML 路径**: `bt_navigator.ros__parameters`

#### `bt_loop_duration`
| 字段 | 内容 |
|------|------|
| **当前值** | `10` |
| **单位** | 毫秒 |
| **作用** | 行为树 tick 周期。每 10ms tick 一次行为树 |

#### `default_server_timeout`
| 字段 | 内容 |
|------|------|
| **当前值** | `20` |
| **单位** | 秒 |
| **作用** | Action Server 的默认超时。等待 action 完成的最长时间 |

#### `transform_tolerance`
| 字段 | 内容 |
|------|------|
| **当前值** | `1.0` 秒 |
| **作用** | BT 节点的 TF 查找容差 |

#### `default_nav_to_pose_bt_xml`
| 字段 | 内容 |
|------|------|
| **当前值** | `navigate_to_pose_w_replanning_and_recovery.xml` |
| **作用** | NavigateToPose 使用的行为树 XML。当前配置为简单重规划+跟随（无机械臂任务） |
| **备选** | `navigate_with_arm_grasp.xml` — 包含 3 waypoints + 机械臂抓取的自包含 BT |

#### `default_nav_through_poses_bt_xml`
| 字段 | 内容 |
|------|------|
| **当前值** | `navigate_through_pose_w_replanning_and_recovery.xml` |
| **作用** | NavigateThroughPoses（多点导航）使用的行为树 XML |

---

## 8. velocity_smoother（速度平滑器）

**YAML 路径**: `velocity_smoother.ros__parameters`
**作用**: 对 DWB 输出的原始 cmd_vel (`/cmd_vel_nav`) 进行平滑、限速、限加速度，输出平滑后的 `/cmd_vel`。

#### `smoothing_frequency`
| 字段 | 内容 |
|------|------|
| **当前值** | `5.0` Hz |
| **作用** | 平滑器自身的运行频率。每 0.2s 更新一次输出 |
| **与控制频率(10Hz)的关系** | 平滑器比 DWB 慢——DWB 每 0.1s 输出一次，平滑器每 0.2s 平滑一次。这种差异本身提供了低频滤波效果 |

#### `scale_velocities`
| 字段 | 内容 |
|------|------|
| **当前值** | `False` |
| **作用** | 是否在接近目标时自动缩放速度。False = 保持原始速度比例 |

#### `feedback`
| 字段 | 内容 |
|------|------|
| **当前值** | `"CLOSED_LOOP"` |
| **作用** | 闭环反馈模式。使用 odom_topic 的里程计数据作为实际速度反馈，实现更精确的速度跟踪 |
| **备选** | `OPEN_LOOP` — 不使用里程计反馈 |

#### `max_velocity` ⚠️
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `velocity_smoother.ros__parameters.max_velocity` |
| **当前值** | `[2.0, 1.4, 1.2]` — [vx, vy, vtheta] |
| **单位** | m/s, m/s, rad/s |
| **作用** | 平滑后的**最终**速度上限。这是 cmd_vel 经过所有处理后的硬限制 |
| **与 DWB 速度限制的关系** | 这些值应 ≥ DWB 的 max_vel 值，否则平滑器会截断 DWB 的输出 |

#### `min_velocity`
| 字段 | 内容 |
|------|------|
| **当前值** | `[-2.0, -1.4, -1.2]` |
| **作用** | 反向速度下限。与 max_velocity 对称 |

#### `max_accel` ⚠️
| 字段 | 内容 |
|------|------|
| **YAML 路径** | `velocity_smoother.ros__parameters.max_accel` |
| **当前值** | `[5.0, 5.0, 15.0]` — [ax, ay, atheta] |
| **单位** | m/s², m/s², rad/s² |
| **作用** | 最大加速度限制。这是真正生效的加速度平滑——比 DWB 内部的 acc_lim (12/6/20) 更严格 |
| **物理意义** | 从 0 加速到 2.0 m/s 需要 2.0/5.0 = 0.4 秒 |
| **与 DWB acc_lim 的关系** | smoother 的 max_accel(5.0) < DWB 的 acc_lim_x(12.0)——实际加速由 smoother 控制 |

#### `max_decel`
| 字段 | 内容 |
|------|------|
| **当前值** | `[-5.0, -5.0, -15.0]` |
| **作用** | 最大减速度限制。与 max_accel 对称 |

#### `odom_topic`
| 字段 | 内容 |
|------|------|
| **当前值** | `"state_estimation"` |
| **作用** | 闭环反馈使用的里程计话题 |

#### `odom_duration`
| 字段 | 内容 |
|------|------|
| **当前值** | `0.1` 秒 |
| **作用** | 里程计数据有效时间窗口 |

#### `deadband_velocity`
| 字段 | 内容 |
|------|------|
| **当前值** | `[0.0, 0.0, 0.0]` |
| **作用** | 速度死区。低于此值的速度输出强制为 0。当前未启用（全 0） |

#### `velocity_timeout`
| 字段 | 内容 |
|------|------|
| **当前值** | `1.0` 秒 |
| **作用** | 无新 cmd_vel 输入的超时时间。超过 1 秒没收到 DWB 的指令，将速度平滑到 0（紧急停止） |

---

## 9. waypoint_follower（航点跟随器）

**YAML 路径**: `waypoint_follower.ros__parameters`

| 参数 | 值 | 作用 |
|------|-----|------|
| `loop_rate` | `20` Hz | 航点跟随循环频率 |
| `stop_on_failure` | `true` | 任何航点失败则终止整个任务 |
| `waypoint_pause_duration` | `0` 秒 | 到达航点后等待时间。0 = 立即前往下一个 |

---

## 10. map_server / map_saver

#### map_server
| 参数 | 值 | 作用 |
|------|-----|------|
| `yaml_filename` | `maps/test_map.yaml` | PGM 地图配置文件路径 |

#### map_saver
| 参数 | 值 | 作用 |
|------|-----|------|
| `save_map_timeout` | `5.0` s | 保存地图超时 |
| `free_thresh_default` | `0.25` | 空闲栅格阈值（PGM 像素值 < 0.25 → 空闲） |
| `occupied_thresh_default` | `0.65` | 占据栅格阈值（PGM 像素值 > 0.65 → 占据） |

---

## 11. 附录：区域切换参数对照表

> 这些参数由 [position_based_param_switcher.py](src/robot_functionality/legged_bringup/nodes/position_based_param_switcher.py) 根据机器人 X 坐标动态切换。

### 区域定义

| 区域 | X 范围 | 滞后 |
|------|--------|------|
| 🟢 边缘区 | x < 1.35m 或 x > 3.35m | ±0.1m |
| 🟠 中间区 | 1.35m ≤ x ≤ 3.35m | ±0.1m |

### 8 个动态参数一览

| # | 参数名 | 🟠 中间区值 | 🟢 边缘区值 | 作用简述 |
|---|--------|------------|------------|----------|
| 1 | `general_goal_checker.yaw_goal_tolerance` | **6.28** (360°) | **0.05236** (3°) | 目标朝向容差 |
| 2 | `FollowPath.RotateToGoal.scale` | **0.0** | **32.0** | 旋转对齐目标 |
| 3 | `FollowPath.GoalAlign.scale` | **0.0** | **24.0** | 目标方向对齐 |
| 4 | `FollowPath.PathAlign.scale` | **0.0** | **32.0** | 路径方向对齐 |
| 5 | `FollowPath.MaintainYawCritic.scale` | **5000.0** | **0.0** | Yaw 锁定 |
| 6 | `FollowPath.DecouplingCritic.scale` | **0.0** | **30.0** | 速度解耦 |
| 7 | `FollowPath.min_vel_y` | **0.0** | **-1.4** | Y 速度下限 |
| 8 | `FollowPath.max_vel_y` | **0.0** | **1.4** | Y 速度上限 |

### 两区共有的不变参数 🔵

| 参数 | 值 |
|------|-----|
| `ObstacleFootprint.scale` | 50.0 |
| `PathDist.scale` | 32.0 |
| `GoalDist.scale` | 16.0 |
| `general_goal_checker.xy_goal_tolerance` | 0.10 |

### 中间区行为总结

```
🟠 中间区 (1.35m ≤ x ≤ 3.35m):
  - vy 被速度边界锁死 (min=max=0) → 只能纯 X 方向移动
  - yaw 被 MaintainYawCritic(5000) 锁定为 0° → 不能旋转
  - 所有旋转 critic (RotateToGoal/GoalAlign/PathAlign) 关闭 → 不关心朝向
  - DecouplingCritic 关闭 → vy 已经为 0，不需要解耦
  - yaw_goal_tolerance=360° → 到了 XY 就算完成，不管朝向
  - 结果: 机器人保持 yaw=0°，沿 X 轴侧移通过狭窄通道
```

### 边缘区行为总结

```
🟢 边缘区 (x < 1.35m 或 x > 3.35m):
  - vy 允许 ±1.4 m/s → 全向移动
  - MaintainYawCritic=0 → 不限制旋转
  - RotateToGoal(32) + GoalAlign(24) + PathAlign(32) 激活 → 主动对齐朝向
  - DecouplingCritic(30) 激活 → 鼓励单轴运动
  - yaw_goal_tolerance=3° → 精确对准目标朝向
  - 结果: 机器人自由旋转，对准目标方向后再进入中间区
```

---

## 12. 自定义节点参数（从 Launch 文件提取）

> **来源**: [bringup_in_real.launch.py](src/robot_functionality/legged_bringup/launch/bringup_in_real.launch.py) 和 [navigation.launch.py](src/robot_functionality/legged_bringup/launch/navigation.launch.py)
> 这些参数原先硬编码在 launch 文件中，现已集中到 `nav2_params.yaml` 统一管理。

---

### 12.1 `position_based_param_switcher`

**YAML 路径**: `position_based_param_switcher.ros__parameters`
**节点**: `position_based_param_switcher`（[源码](src/robot_functionality/legged_bringup/nodes/position_based_param_switcher.py)）
**功能**: 根据机器人 X 坐标动态切换 DWB critic 参数，实现三区导航

#### `lower_boundary` 🔄

| 字段 | 内容 |
|------|------|
| **YAML 路径** | `position_based_param_switcher.ros__parameters.lower_boundary` |
| **当前值** | `1.35`（代码默认 0.9，launch 文件覆盖） |
| **单位** | 米 |
| **作用** | 中间区下边界。x < 1.35m → 边缘区（允许旋转和横向移动） |
| **调大** | 中间区缩小，边缘区更大，机器人更早进入旋转对齐模式 |
| **调小** | 中间区扩大，更长的距离内保持 yaw=0° 直走 |
| **注意** | ⚠️ 代码中 `declare_parameter` 默认值为 0.9，但 YAML 中为 1.35，以 YAML 为准 |

#### `upper_boundary` 🔄

| 字段 | 内容 |
|------|------|
| **YAML 路径** | `position_based_param_switcher.ros__parameters.upper_boundary` |
| **当前值** | `3.35`（代码默认 4.9，launch 文件覆盖） |
| **单位** | 米 |
| **作用** | 中间区上边界。x > 3.35m → 边缘区（允许旋转和横向移动） |
| **调大** | 中间区更长，延长 yaw 锁定时间 |
| **调小** | 中间区更短，更早恢复旋转自由 |
| **注意** | ⚠️ 代码中默认值为 4.9，但 YAML 中为 3.35，以 YAML 为准 |

#### `hysteresis_margin` 🔄

| 字段 | 内容 |
|------|------|
| **YAML 路径** | `position_based_param_switcher.ros__parameters.hysteresis_margin` |
| **当前值** | `0.1` |
| **单位** | 米 |
| **作用** | 迟滞边界。防止机器人在边界附近来回振荡（边缘↔中间反复切换） |
| **调大** | 切换更稳定，但切换延迟更大，可能在边界处行为短暂不一致 |
| **调小** | 切换更灵敏，但在边界附近可能频繁抖动 |
| **原理** | 从边缘→中间需要进入边界内 0.1m，从中间→边缘需要超出边界 0.1m |

#### `odom_topic`

| 字段 | 内容 |
|------|------|
| **YAML 路径** | `position_based_param_switcher.ros__parameters.odom_topic` |
| **当前值** | `"state_estimation"` |
| **作用** | 订阅的里程计话题，用于获取机器人 X 坐标 |

#### `target_node`

| 字段 | 内容 |
|------|------|
| **YAML 路径** | `position_based_param_switcher.ros__parameters.target_node` |
| **当前值** | `"controller_server"` |
| **作用** | 通过 `/<target_node>/set_parameters` 服务动态修改参数的 ROS2 节点名 |

---

### 12.2 `obstacle_scale_controller`

**YAML 路径**: `obstacle_scale_controller.ros__parameters`
**节点**: `obstacle_scale_controller`（[源码](src/robot_functionality/legged_bringup/nodes/obstacle_scale_controller.py)）
**功能**: 监控局部代价地图，当致命障碍物侵入机器人 footprint 时，动态降低 `ObstacleFootprint.scale` 让机器人挤过去

#### `normal_scale` 🔄

| 字段 | 内容 |
|------|------|
| **YAML 路径** | `obstacle_scale_controller.ros__parameters.normal_scale` |
| **当前值** | `50.0` |
| **作用** | 无障碍物时恢复的 `ObstacleFootprint.scale` 正常值 |
| **注意** | 必须与 `nav2_params.yaml` 中 `ObstacleFootprint.scale` 的默认值一致 |

#### `push_through_scale` 🔄

| 字段 | 内容 |
|------|------|
| **YAML 路径** | `obstacle_scale_controller.ros__parameters.push_through_scale` |
| **当前值** | `0.01` |
| **作用** | 障碍物侵入时 `ObstacleFootprint.scale` 降低到的值。0.01 ≈ 基本禁用障碍物代价 |
| **原理** | 当局部代价地图的致命代价（254）出现在 footprint 区域内时，将 ObstacleFootprint.scale 从 50.0 降到 0.01，让 DWB 不再排斥该轨迹，机器人"硬挤过去" |
| **调大** | 保留一定障碍物排斥力，更安全但可能卡住 |
| **调为 0** | 完全禁用 footprint 代价，风险较高 |
| ⚠️ | **仅在确保障碍物不会损坏机器人时使用低值！** |

#### `hysteresis_count`

| 字段 | 内容 |
|------|------|
| **YAML 路径** | `obstacle_scale_controller.ros__parameters.hysteresis_count` |
| **当前值** | `5` |
| **作用** | 连续 N 次检测到障碍物侵入后才触发切换，防止单帧噪声误触发 |
| **调大** | 更稳定，但切换延迟更大（每次检测 ~0.1s，5 次 = 0.5s） |
| **调小** | 更快响应，但可能被传感器噪声误触发 |

#### `costmap_topic`

| 字段 | 内容 |
|------|------|
| **YAML 路径** | `obstacle_scale_controller.ros__parameters.costmap_topic` |
| **当前值** | `"/local_costmap/costmap"` |
| **作用** | 订阅的局部代价地图话题 |

#### `target_node`

| 字段 | 内容 |
|------|------|
| **YAML 路径** | `obstacle_scale_controller.ros__parameters.target_node` |
| **当前值** | `"controller_server"` |
| **作用** | 目标参数节点名，与 position switcher 相同机制 |

---

### 12.3 `cmd_vel_udp_bridge`

**YAML 路径**: `cmd_vel_udp_bridge.ros__parameters`
**节点**: `cmd_vel_udp_bridge`（`cmd_vel_udp_bridge_node`）
**功能**: 将 Nav2 输出的 `/cmd_vel` 通过 UDP 转发给 deploy_cpp（机器人底盘），包含死区补偿

#### UDP 通信配置

| 参数 | 当前值 | 作用 |
|------|--------|------|
| `udp_ip` | `"127.0.0.1"` | deploy_cpp UDP 目标 IP（由 launch arg 覆盖） |
| `udp_port` | `9870` | deploy_cpp UDP 目标端口（由 launch arg 覆盖） |
| `mode` | `2` | deploy_cpp 模式值（由 launch arg 覆盖） |
| `cmd_vel_topic` | `"/cmd_vel"` | 订阅的速度指令话题 |
| `use_twist_stamped` | `false` | 输入话题是否使用 TwistStamped 类型 |
| `estop_topic` | `""` | 急停 Bool 话题（空 = 不使用） |

#### 死区补偿参数 ⚠️

> **背景**: 实测底盘死区为 vx≈0.105, vy≈0.8 m/s, wz≈0.7 rad/s。
> 当 Nav2 输出速度低于死区但非零时，底盘无法响应。死区补偿检测到非零小速度后自动提升到 `min_effective` 值。

#### `deadzone_vx`

| 字段 | 内容 |
|------|------|
| **YAML 路径** | `cmd_vel_udp_bridge.ros__parameters.deadzone_vx` |
| **当前值** | `0.05` |
| **单位** | m/s |
| **作用** | X 方向死区阈值。vx 低于此值但非零时，提升到 `min_effective_vx` |
| **调大** | 更积极地补偿，但也可能放大噪声 |
| **调小** | 更保守，但可能仍有小速度被死区吞掉 |

#### `deadzone_vy`

| 字段 | 内容 |
|------|------|
| **YAML 路径** | `cmd_vel_udp_bridge.ros__parameters.deadzone_vy` |
| **当前值** | `0.3` |
| **单位** | m/s |
| **作用** | Y 方向死区阈值 |

#### `deadzone_wz`

| 字段 | 内容 |
|------|------|
| **YAML 路径** | `cmd_vel_udp_bridge.ros__parameters.deadzone_wz` |
| **当前值** | `0.2` |
| **单位** | rad/s |
| **作用** | 旋转方向死区阈值 |

#### `min_effective_vx`

| 字段 | 内容 |
|------|------|
| **YAML 路径** | `cmd_vel_udp_bridge.ros__parameters.min_effective_vx` |
| **当前值** | `0.4` |
| **单位** | m/s |
| **作用** | 触发死区补偿时 vx 提升到的目标值 |
| **注意** | ⚠️ 此值需大于底盘实际死区（0.105），否则补偿无效 |

#### `min_effective_vy`

| 字段 | 内容 |
|------|------|
| **YAML 路径** | `cmd_vel_udp_bridge.ros__parameters.min_effective_vy` |
| **当前值** | `0.7` |
| **单位** | m/s |
| **作用** | 触发死区补偿时 vy 提升到的目标值 |

#### `min_effective_wz`

| 字段 | 内容 |
|------|------|
| **YAML 路径** | `cmd_vel_udp_bridge.ros__parameters.min_effective_wz` |
| **当前值** | `0.4` |
| **单位** | rad/s |
| **作用** | 触发死区补偿时 wz 提升到的目标值 |

---

### 12.4 `arm_control_server`

**YAML 路径**: `arm_control_server.ros__parameters`
**节点**: `arm_control_server`（[源码](src/robot_functionality/legged_bringup/nodes/arm_control_server.py)）
**功能**: 机械臂控制 Action Server（可选，`enable_arm_control=true` 时启用）

| 参数 | 当前值 | 作用 |
|------|--------|------|
| `arm_timeout` | `30.0` | 机械臂单次动作超时时间（秒） |
| `enable_serial_publish` | `true` | 是否通过串口发布机械臂命令 |
| `arm_command_topic` | `"/arm_command"` | 机械臂命令发布话题 |

---

### 12.5 `arm_mission_trigger`

**YAML 路径**: `arm_mission_trigger.ros__parameters`
**节点**: `arm_mission_trigger`（[源码](src/robot_functionality/legged_bringup/nodes/arm_mission_trigger.py)）
**功能**: 机械臂抓取使命自动触发器（可选，`enable_waypoint_mission=true` 时启用）

| 参数 | 当前值 | 作用 |
|------|--------|------|
| `startup_delay` | `0.0` | 启动后额外等待时间（秒）。`TimerAction` 已做延迟，此处为 0 |
| `action_timeout` | `30.0` | 机械臂抓取动作超时（秒） |

---

### 12.6 `stand_up_sender`

**YAML 路径**: `stand_up_sender.ros__parameters`
**节点**: `stand_up_sender`（[源码](src/robot_functionality/legged_bringup/nodes/stand_up_sender.py)）
**功能**: 在导航开始前通过 UDP 向 deploy_cpp 发送起立命令

| 参数 | 当前值 | 作用 |
|------|--------|------|
| `reloc_delay` | `0.0` | 重定位完成后额外等待时间（秒）。0 = 重定位完成后立即起立 |

> **注意**: `udp_ip` 和 `udp_port` 由 launch arg 动态覆盖，不在 YAML 中固定。

---

### 12.7 `bringup_timing`

**YAML 路径**: `bringup_timing.ros__parameters`
**功能**: 启动时序参数汇总。这些值对应 `bringup_in_real.launch.py` 中各 `TimerAction` 的 `period` 参数。

| 参数 | 当前值 | 对应 Launch Arg | 作用 |
|------|--------|----------------|------|
| `start_delay` | `5.0` | `start_delay` | Livox 启动后等待多久启动 bringup（秒） |
| `stand_up_delay` | `3.0` | `stand_up_delay` | bringup 启动后等待多久发送起立命令（秒） |
| `waypoint_start_delay` | `25.0` | `waypoint_start_delay` | bringup 启动后等待多久触发机械臂使命（秒） |
| `arm_control_delay` | `12.0` | `arm_control_delay` | bringup 启动后等待多久启动机械臂控制（秒） |

> **时序链**: Livox → 5s → bringup → 3s → stand_up → 12s → arm_control → 25s → arm_mission

---

*文档基于 [nav2_params.yaml](src/robot_functionality/legged_bringup/params/nav2_params.yaml) 完整解析。*
*如有参数变更，请同步更新此文档。*
