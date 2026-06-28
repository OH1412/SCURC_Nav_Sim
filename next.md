# 待修改问题

> 最后更新: 2026-06-28

---

## 1. 行为树航点导航问题

**描述**: 行为树 `navigate_waypoints_with_task.xml` 中第二个航点没有走过去。

**当前状态**:

- `waypoint_pause_duration` 已从 8s 改为 0（不等待直接进入下一个）
- 恢复行为（BackUp、Spin）在 `navigate_to_pose_w_replanning_and_recovery.xml` 中被注释
- 需确认问题是否已解决

**建议**: 在实机上测试 waypoint_follower 模式，观察航点切换是否正常。

---

## 2. waypoints.yaml 与 BT XML 坐标不一致

**描述**:

- `waypoints.yaml` 中 waypoint 的 y 值为 0.0
- `navigate_with_arm_grasp.xml` 中 arm_grasp 目标 y 值为 -0.425
- 两个文件定义的是不同场景（waypoint_sender 模式 vs 自包含 BT 模式），但容易混淆

**建议**: 在文件中添加注释说明各坐标系的含义和使用场景。

---

## 3. arm_control_server 缺少机械臂完成反馈机制

**描述**: [arm_control_server.py](src/robot_functionality/legged_bringup/nodes/arm_control_server.py) 中有 TODO 标注（第 1183-1185 行），当前发送指令后直接返回成功，未等待机械臂实际完成的反馈信号。

```python
# TODO: 订阅机械臂状态反馈 topic 并等待完成信号
# 当前版本直接返回成功（后续可扩展为订阅 /arm_status 等待完成）
```

**建议**:

- 订阅机械臂状态反馈 topic（如 `/arm_status`）
- 增加超时机制，超过 `arm_timeout` 后返回失败
- 或在串口协议中增加应答帧

---

## 4. 中间区 vy=0 卡住问题

**发现日期**: 2026-06-28

**现象**: 机器人进入中间区后，因为 footprint 踩到了障碍物红色代价区域，全局规划器规划了有 Y 方向偏移的避障路径。中间区 `min_vel_y=0, max_vel_y=0` 从 DWB 采样器层面彻底禁止了 Y 速度，导致无法跟随路径 → 卡住。手动将机器人移到正中间后直行正常。

**根因分析**:

1. [waypoints.yaml](src/robot_functionality/legged_bringup/params/waypoints.yaml#L21) waypoint 1 的 `x=1.35` 恰好等于 `lower_boundary`
2. 迟滞逻辑（[position_based_param_switcher.py:117-125](src/robot_functionality/legged_bringup/nodes/position_based_param_switcher.py#L117-L125)）：从边缘区进入中间区需要 `x ≥ lower_boundary + hysteresis = 1.35 + 0.1 = 1.45`
3. 但 `xy_goal_tolerance=0.10`（[nav2_params.yaml:152](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L152)）允许机器人在偏离中心 ±0.1m 的位置就算"到达" waypoint 1
4. 到达后 waypoint_follower 立即下发 waypoint 2（x=1.925），planner 从偏离位置规划到 (1.925, 0.0) 的路径 → 路径有 Y 分量
5. 机器人向 waypoint 2 移动，x 跨过 1.45 时触发中间区切换 → vy 锁死为 0 → **卡住**

**时序图**:

```
x=1.0    x=1.35 (waypoint1)  x=1.45 (实际切换)   x=1.925 (waypoint2)
  |           |                   |                    |
  |─ 边缘区 ─|                   |── 中间区(vy=0) ───→|
  可旋转,Y移  ↑到达(可能偏±0.1m)  切换点              直行目标
              planner: 从(x=1.28,y=0.07)→(1.925,0.0) 路径有Y分量
              → 进入中间区后无法修正Y → 卡住
```

**为什么 Y 方向不能做小幅度修正**:

- [nav2_params.yaml:599](src/robot_functionality/legged_bringup/params/nav2_params.yaml#L599) `deadzone_vy=0.3`，`min_effective_vy=0.7`
- 如果开放 vy ±0.3，DWB 输出 vy=0.25 → UDP bridge 检测到 0<0.25<0.3 → 触发死区补偿 → 提升到 0.7 m/s → 机器人突然以 0.7 m/s 横移（四足 Y 行走差，不可接受）
- 物理死区 vy≈0.8 m/s，小 vy 指令底盘根本不响应

**涉及的全部参数**（共 41 个，详见对话记录）:

| 参数组       | 关键参数                                                                                       | 作用                              |
| ------------ | ---------------------------------------------------------------------------------------------- | --------------------------------- |
| 区域边界     | `lower_boundary`(1.35), `hysteresis_margin`(0.1)                                           | 控制何时切换中间区                |
| waypoint     | waypoint 1`x=1.35`                                                                           | 入口位姿，恰好等于 lower_boundary |
| goal checker | `xy_goal_tolerance`(0.10)                                                                    | 到达 waypoint 的精度              |
| DWB 速度     | `min_vel_y`(0.0), `max_vel_y`(0.0)                                                         | 中间区 Y 速度锁                   |
| DWB critics  | `MaintainYawCritic.scale`(5000), `PathDist.scale`(32.0), `ObstacleFootprint.scale`(50.0) | yaw 锁 + 路径跟随 + 避障          |
| 障碍物检测   | `min_obstacle_intensity`(0.2), `obstacle_max_range`(4.5)                                   | 决定红色代价区域                  |
| planner      | `w_traversal_cost`(2.0), `inflation_radius`(0.3)                                           | 路径是否走中间                    |
| 死区         | `deadzone_vy`(0.3), `min_effective_vy`(0.7)                                                | 禁止小 vy 的存在                  |

**修复方向**（待实施）:

- **方案 A（推荐）**: 将 waypoint 1 的 x 前移到 `lower_boundary - hysteresis - 余量`（如 x=1.0 或 x=1.2），确保机器人进入中间区前已在边缘区完成 Y 对齐
- **方案 B**: 增加 `lower_boundary` 值，给边缘区更多对齐空间
- **方案 C**: 降低进入中间区前的 xy_goal_tolerance（更精确到达入口点）
- **不考虑**: 开放中间区 vy（死区导致不可行）、开放中间区旋转（破坏设计目的）
