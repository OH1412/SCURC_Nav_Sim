# `critic_dynamic_scale.hpp` 参数回调名字匹配 Bug 详细分析

## 概述

`critic_dynamic_scale.hpp` 中的 `registerScaleDynamicCallback` 函数注册了一个 ROS2 参数回调，用于在运行时动态更新 DWB critic 的 `scale_` 值。然而由于参数名比较逻辑的缺陷，回调**自 2026-07-09 引入以来从未正确执行过** —— `setScale()` 从未被调用，critic 内部的 `scale_` 成员变量始终停留在 `onInit()` 时读取的初始值。

---

## 背景：为什么需要动态更新 critic scale

Nav2 DWB 控制器通过多个 critic（评分器）对轨迹采样打分，选择最优轨迹。每个 critic 有一个 `scale_` 权重。对于不同导航模式，同一个 critic 需要不同的权重：

| Zone | 场景 | RotateToPathCritic.scale | 行为 |
|------|------|:---:|------|
| `edge` | MP1/MP2 远距离 | **96.0** | 强制旋转对齐路径切线 |
| `middle` | MP0 / 近目标 | **0.0** | 禁用旋转约束，直线前进 |
| `straight` | MP3 | **0.0** | 仅 X 方向 |

`position_based_param_switcher.py` 通过调用 `/{controller_server}/set_parameters` 服务来切换这些参数。参数 store（ROS2 内置 key-value 存储）被正确更新，但 critic 对象内部的 C++ 成员变量 `scale_` 需要通过回调机制同步更新。

---

## 架构：参数更新的完整链路

```
position_based_param_switcher.py
  │
  │  req = SetParameters.Request(parameters=[
  │    Parameter(name="FollowPath.dwb_yaw_constraint::RotateToPathCritic.scale",
  │              value=ParameterValue(type=3, double_value=0.0))
  │  ])
  │
  ▼
rclcpp Service: /controller_server/set_parameters
  │
  │  服务处理器:
  │    1. 将 rcl_interfaces::msg::Parameter → rclcpp::Parameter
  │    2. 解析参数名为绝对路径（加节点前缀）
  │    3. 存入参数 store（成功 → ros2 param get 可见）
  │    4. 调用 on_set_parameters_callback 回调链
  │
  ├──▶ 参数 store 更新 ✅（param get 能看到）
  │
  └──▶ on_set_parameters_callback 链
         │
         ├─ callback_1: RotateToPathCritic 的回调
         │     param.get_name() == scale_param_name ?
         │       YES → setScale(param.as_double()) → scale_ 更新
         │       NO  → 跳过（什么都不做）              ← BUG：永远走这里
         │
         ├─ callback_2: RotateToGoalXYCritic 的回调
         │     （同上逻辑，同样被 bug 影响）
         │
         └─ callback_3: MaintainYawCritic 的回调
               （同上逻辑，同样被 bug 影响）
```

---

## Bug 分析

### 问题代码

文件：`src/navigation_plugins/nav2_ext_plugins/dwb_yaw_constraint/include/dwb_yaw_constraint/critic_dynamic_scale.hpp`

**修复前（原始代码）：**

```cpp
inline void registerScaleDynamicCallback(
  const nav2_util::LifecycleNode::SharedPtr & node,
  const std::string & scale_param_name,      // ← 相对路径
  const std::function<void(double)> & set_scale,
  rclcpp::node_interfaces::OnSetParametersCallbackHandle::SharedPtr & handle)
{
  handle = node->add_on_set_parameters_callback(
    [scale_param_name, set_scale](const std::vector<rclcpp::Parameter> & parameters) {
      rcl_interfaces::msg::SetParametersResult result;
      result.successful = true;
      for (const auto & param : parameters) {
        if (param.get_name() == scale_param_name &&          // ← BUG
          param.get_type() == rclcpp::ParameterType::PARAMETER_DOUBLE)
        {
          set_scale(param.as_double());
        }
      }
      return result;
    });
}
```

### 为什么比较失败

在 ROS2 Humble 的 rclcpp 中，`set_parameters` 服务处理器在处理参数时，会调用内部函数将参数名**解析为绝对路径**（Fully Qualified Name），然后才传递给回调链。

**绝对路径的构建规则：**

```
FQN = "/" + node_namespace + "/" + node_name + "/" + relative_param_name
```

对于 `controller_server` 节点（无 namespace）：

```
relative_param_name = "FollowPath.dwb_yaw_constraint::RotateToPathCritic.scale"
fqn                 = "/controller_server/FollowPath.dwb_yaw_constraint::RotateToPathCritic.scale"
```

### 具体不匹配示例

以 `RotateToPathCritic` 为例，该 critic 在 `onInit()` 中注册回调：

```cpp
// rotate_to_path_critic.cpp:59-61
const std::string scale_param = prefix + name_ + ".scale";
// scale_param = "FollowPath.dwb_yaw_constraint::RotateToPathCritic.scale"

registerScaleDynamicCallback(
  node, scale_param,                                      // ← 传入的是相对路径
  [this](double s) { setScale(s); }, dyn_params_handler_);
```

当 switcher 调用 `set_parameters` 后，回调被触发：

| 变量 | 值 | 来源 |
|------|-----|------|
| `param.get_name()` | `"/controller_server/FollowPath.dwb_yaw_constraint::RotateToPathCritic.scale"` | rclcpp 内部解析 |
| `scale_param_name` | `"FollowPath.dwb_yaw_constraint::RotateToPathCritic.scale"` | critic onInit() 构造 |

```
strcmp: "/controller_server/FollowPath..." == "FollowPath..."
                                          ↑ 开头多出 "/controller_server/"
结果：FALSE → setScale() 不执行 → scale_ 保持原值
```

### 受影响的 Critic

所有使用 `registerScaleDynamicCallback` 的 critic 都受影响：

| Critic | 注册位置 | 初始 scale_ | 切换到 middle 期望 | 实际 scale_（永远不变） |
|--------|---------|:---:|:---:|:---:|
| `RotateToPathCritic` | rotate_to_path_critic.cpp:61 | **96.0** | 0.0 | **96.0** |
| `RotateToGoalXYCritic` | rotate_to_goal_xy_critic.cpp | **32.0** | 0.0 | **32.0** |
| `MaintainYawCritic` | maintain_yaw_critic.cpp | **0.0** | 5000.0 | **0.0** |
| `DecouplingCritic` | decoupling_critic.cpp | **5.0** | 0.0 | **5.0** |

### 后果链

```
switcher 发送 set_parameters("RotateToPathCritic.scale" = 0.0)
  │
  ├──▶ param store 更新 ✅   ros2 param get 返回 0.0
  │
  └──▶ 回调: param.get_name() != scale_param_name
         setScale(0.0) 未被调用 ❌
           │
           ▼
         critic.scale_ 仍为 96.0
           │
           ▼
         scoreTrajectory():
           if (scale_ > 0.0 && yaw_error > 30°)  ← scale_=96 > 0 条件满足！
               if (linear_speed > 0.05)
                   throw IllegalTrajectoryException  ← 所有前向轨迹被踢
           │
           ▼
         DWB 只能选择纯旋转轨迹
           │
           ▼
         /cmd_vel: linear.x=0, angular.z=0.189
```

---

## 为什么 2026-07-12 下午能工作，07-13 早上不能

这个问题并非 07-13 才引入，而是自 07-09 `critic_dynamic_scale.hpp` 引入就存在。只是在此前被另一个 bug 的副作用所掩盖。

### 时间线

| 日期 | 事件 | 影响 |
|------|------|------|
| 07-09 | `2755486` 引入 `critic_dynamic_scale.hpp` | Bug 诞生，但尚未暴露 |
| 07-12 下午 | 工作正常 | 掩蔽因子生效中（见下文） |
| 07-12 22:18 | `5c1273b "前后抽搐"` 修改 maintain_yaw_critic | 调整了 critic 参数 |
| 07-13 早上 | `colcon build` 全量编译 | 所有包重编 |
| 07-13 14:15 | `f712dcc "mp0回退"` | **掩蔽因子被移除，Bug 暴露** |

### 掩蔽因子分析

`f712dcc "mp0回退"` 在 `position_based_param_switcher.py` 中做了一个关键改动：

```diff
 MIDDLE_PARAMS = {
     ...
     'FollowPath.dwb_yaw_constraint::MaintainYawCritic.scale': 5000.0,
-    'FollowPath.dwb_yaw_constraint::MaintainYawCritic.desired_yaw': 3.1416,   // 180° (车尾)
+    'FollowPath.dwb_yaw_constraint::MaintainYawCritic.desired_yaw': 0.0,      // 0° (车头)
     ...
 }
```

#### 07-12 之前（desired_yaw = 3.1416 = 180°）

- 启动后默认 zone 是 `edge`，`RotateToPathCritic.scale_` = 96.0（初始化值）
- 但 `MaintainYawCritic.scale` = 5000，`desired_yaw` = 3.1416
- MaintainYawCritic 的 scale 为 5000（是 RotateToPathCritic 96 的 **52 倍**）
- 两个 critic 的目标 yaw 互相矛盾（一个锁 180°，一个跟路径切线），但由于 MaintainYawCritic 的绝对优势权重，**实质上是 MaintainYawCritic 在主导**
- MaintainYawCritic 的 `prepare()` 中计算 `target_yaw_`，并在 `scoreTrajectory()` 返回 `scale_ * |yaw_error|` = **纯线性惩罚**，不像 RotateToPathCritic 那样抛 `IllegalTrajectoryException`
- **结果**：虽然 edge→middle 切换失败（callback bug），但 MaintainYawCritic 的巨大 scale 压倒了 RotateToPathCritic 的 IllegalTrajectoryException 效应，机器人实际能走

#### 07-13 mp0回退后（desired_yaw = 0.0）

- `desired_yaw` 改为 0.0，MaintainYawCritic 不再与 RotateToPathCritic 形成"对抗"
- RotateToPathCritic 的 IllegalTrajectoryException（`scale_` = 96）成为**唯一主导力量**
- 所有前向轨迹被踢 → 机器人只旋转不前进
- **Bug 完全暴露**

---

## 修复

### 修复后代码

文件：`src/navigation_plugins/nav2_ext_plugins/dwb_yaw_constraint/include/dwb_yaw_constraint/critic_dynamic_scale.hpp`

```cpp
inline void registerScaleDynamicCallback(
  const nav2_util::LifecycleNode::SharedPtr & node,
  const std::string & scale_param_name,
  const std::function<void(double)> & set_scale,
  rclcpp::node_interfaces::OnSetParametersCallbackHandle::SharedPtr & handle)
{
  // 构建节点前缀：如 "/controller_server/"
  const std::string node_prefix = "/" + std::string(node->get_name()) + "/";

  handle = node->add_on_set_parameters_callback(
    [scale_param_name, node_prefix, set_scale](
        const std::vector<rclcpp::Parameter> & parameters) {
      rcl_interfaces::msg::SetParametersResult result;
      result.successful = true;
      for (const auto & param : parameters) {
        const auto & pname = param.get_name();
        // 同时匹配相对路径和绝对路径
        // 相对路径: "FollowPath.dwb_yaw_constraint::RotateToPathCritic.scale"
        // 绝对路径: "/controller_server/FollowPath.dwb_yaw_constraint::RotateToPathCritic.scale"
        if ((pname == scale_param_name ||                          // 相对路径
             pname == node_prefix + scale_param_name) &&           // 绝对路径
          param.get_type() == rclcpp::ParameterType::PARAMETER_DOUBLE)
        {
          set_scale(param.as_double());
        }
      }
      return result;
    });
}
```

### 改动要点

1. **新增 `node_prefix`**：在注册回调前计算节点的绝对路径前缀（`"/" + node_name + "/"`）
2. **双轨匹配**：同时检查相对路径和绝对路径两种形式
3. **兼容性**：覆盖不同 ROS2 版本可能返回不同格式的情况

### 为什么这样修复是安全的

- `node->get_name()` 返回节点的本地名称（不含 namespace），如 `"controller_server"`
- 拼接后的 `node_prefix` = `"/controller_server/"`
- 无论 rclcpp 返回相对路径还是绝对路径，都能正确匹配
- 如果未来 ROS2 版本改变行为（比如回调传相对路径），代码无需再次修改

---

## 验证方法

### 1. 参数 store 更新验证

```bash
# 发布 edge zone
ros2 topic pub /mission_bt/nav_zone std_msgs/msg/String "data: edge" --once

# 检查参数（应为 edge 值: 96.0, 32.0, 0.0）
ros2 param get /controller_server "FollowPath.dwb_yaw_constraint::RotateToPathCritic.scale"
ros2 param get /controller_server "FollowPath.dwb_yaw_constraint::RotateToGoalXYCritic.scale"
ros2 param get /controller_server "FollowPath.dwb_yaw_constraint::MaintainYawCritic.scale"

# 发布 middle zone
ros2 topic pub /mission_bt/nav_zone std_msgs/msg/String "data: middle" --once

# 再次检查参数（应为 middle 值: 0.0, 0.0, 5000.0）
ros2 param get /controller_server "FollowPath.dwb_yaw_constraint::RotateToPathCritic.scale"
ros2 param get /controller_server "FollowPath.dwb_yaw_constraint::RotateToGoalXYCritic.scale"
ros2 param get /controller_server "FollowPath.dwb_yaw_constraint::MaintainYawCritic.scale"
```

### 2. 机器人行为验证

- 使用 MP1 或 MP2 航点启动导航
- 观察机器人是否在距离目标 > 1m 时正确走 edge 模式（允许旋转）
- 观察机器人是否在距离目标 < 1m 时切换到 middle 模式（yaw 锁定，直线前进）
- 使用 `ros2 topic echo /cmd_vel` 验证线速度是否正常

---

## 相关文件

| 文件 | 角色 |
|------|------|
| `src/navigation_plugins/nav2_ext_plugins/dwb_yaw_constraint/include/dwb_yaw_constraint/critic_dynamic_scale.hpp` | 回调注册函数（**Bug 所在**） |
| `src/navigation_plugins/nav2_ext_plugins/dwb_yaw_constraint/plugins/rotate_to_path_critic.cpp` | 调用 registerScaleDynamicCallback，含 IllegalTrajectoryException 逻辑 |
| `src/navigation_plugins/nav2_ext_plugins/dwb_yaw_constraint/plugins/rotate_to_goal_xy_critic.cpp` | 调用 registerScaleDynamicCallback |
| `src/navigation_plugins/nav2_ext_plugins/dwb_yaw_constraint/plugins/maintain_yaw_critic.cpp` | 调用 registerScaleDynamicCallback |
| `src/robot_functionality/legged_bringup/nodes/position_based_param_switcher.py` | 发布 zone → set_parameters 的发起方 |
| `src/robot_functionality/legged_mission_bt/src/nav2_pose_node.cpp` | Nav2PoseNode，onRunning() 中距离检查触发 edge→middle 切换 |
| `src/robot_functionality/legged_bringup/params/nav2_params.yaml` | 初始参数配置 |

---

## 总结

```
Bug:     critic_dynamic_scale.hpp 回调中 param.get_name() 比较失败
原因:    回调收到的是绝对路径名，比较的是相对路径名
影响:    setScale() 从未调用 → critic 内部 scale_ 永远不变
结果:    RotateToPathCritic.scale_ 恒为 96 → IllegalTrajectoryException 踢掉所有前向轨迹
修复:    同时匹配相对和绝对路径两种格式
引入:    2026-07-09 (2755486)
暴露:    2026-07-13 (f712dcc "mp0回退" 移除掩蔽因子)
修复日:  2026-07-15
```
