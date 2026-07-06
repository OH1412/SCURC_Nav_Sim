# arm_pose_broadcaster：物体位置 → 机械臂指令

## 结论

当前**不是**直接读取 base_link 下的物体位姿，而是：

1. **标定**：物体/抓取点在 **map/init 固定坐标系** 下写入 `params/arm_points.yaml` 的 `map_target`（米）
2. **运行时**：用当前定位把 `map_target` **变换到此刻的 base_link**（毫米）
3. **执行**：BT 的 `ArmPickNode` / `ArmPlaceNode` 收到 `arm_waypoint` 后发布 `/arm_command` → `serial_cmd_sender`

可选 `base_link_target` 仅作**无定位时的固定回退**（同 `arm_only_demo` 内联坐标），不参与 map 补偿。

## 端到端数据流

```
ArmPickNode
  → /mission_bt/arm_pose_request (arm_point_id)
arm_pose_broadcaster
  ← /aft_mapped_to_init (定位)
  → /mission_bt/arm_waypoint (base_link mm)
WaypointRegistry (mission_bt_node 内)
  → ArmPickNode resolveCoords()
  → /arm_command (x, y, z, yaw, action)
serial_cmd_sender → 串口
```

| 环节 | 文件 |
|------|------|
| 标定数据 | `params/arm_points.yaml` |
| 坐标变换 | `nodes/arm_pose_broadcaster.py` |
| BT 请求/等待 | `legged_mission_bt/src/arm_action_node.cpp` |
| 航点注册 | `legged_mission_bt/src/waypoint_ros_bridge.cpp` |
| 静态 TF | `params/static_tf_params.yaml` t1 (aft_mapped → base_link) |

## 标定：arm_points.yaml

```yaml
"0":
  role: pick
  map_target: {x: 2.0078, y: -1.2503, z: -0.1000, yaw: 0.0000}  # map/init，米
  base_link_target: {x: 550.0, y: 0.0, z: -50.0, yaw: 0.0}      # 可选回退，毫米
```

- `map_target`：物体在地图中的绝对位置（标定后不变）
- `base_link_target`：固定机械臂坐标，不随机器人位移补偿

编号：0~7 抓取，8~15 放置。

## broadcaster 输入/输出

**订阅**

- `/mission_bt/arm_pose_request` — `ArmPoseRequest.arm_point_id` (0~15)
- `/aft_mapped_to_init` — FAST-LIVO 定位（aft_mapped 在 init 系）

**发布**

- `/mission_bt/arm_waypoint` — `ArmWaypoint(id, x, y, z, yaw)`，单位 mm / rad，**已是 base_link 坐标**

**处理步骤** (`_try_publish_for_request`)

1. 按 `arm_point_id` 查 yaml，校验 role
2. 有定位 → `map_target` 变换；无定位 → `base_link_target` 回退
3. 发布 `arm_waypoint`

## 坐标变换

### 当前 base_link 在 init 系

```
/aft_mapped_to_init  →  aft (x, y, z, yaw)
  + 静态 aft→base_link  (-0.21368, 0, -0.12978, yaw=0.05)
  = base_in_init
```

函数：`compose_aft_to_base_in_init()`

### map 固定点 → 当前 base_link

函数：`map_target_to_baselink()`

- XY：`se2_to_base()` 逆变换，米 → ×1000 毫米
- Z：`(map_z - cur_z) * 1000` mm
- Yaw：`map_yaw - cur_yaw`（归一化）

物体在地图上不动，机器人移动后，同一物体在 base_link 下的坐标会变化。

### 吸盘 XY 优化（默认开启）

标定点 `(tx, ty)` 为 **12.5cm 容差圆** 的圆心；吸盘为 **半径 3.5cm** 圆盘；机械臂 XY 工作空间为 base_link 下 **半径 570mm** 圆。

下发给机械臂的是 **吸盘中心**，需满足：

- 整盘在容差圆内：`|p - target| + 35 ≤ 125` → 中心距目标 ≤ **90mm**
- 吸盘中心在工作空间内：`|p| ≤ 570mm`（中心最远 570mm，不含吸盘半径扣减）

在可行域内取 **距目标圆心最近** 的吸盘中心。

两圆盘无交集条件：目标距 base_link > 570 + 90 = **660mm** 时不发布。

ROS 参数（`arm_pose_broadcaster`）：

| 参数 | 默认 |
|------|------|
| `enable_suction_cup_xy_adjust` | true |
| `arm_workspace_radius_mm` | 570 |
| `suction_cup_radius_mm` | 35 |
| `goal_tolerance_radius_mm` | 125 |

不可行时不发布 `arm_waypoint` 并打 ERROR 日志。

### 发布模式

| 条件 | 模式 |
|------|------|
| 有 `/aft_mapped_to_init` + `map_target` | `map_target → base_link`（真机常用） |
| 无定位 + `base_link_target` | `base_link_target (no odom)` |
| 无定位 + 无回退 | 等待，日志 `Waiting for /aft_mapped_to_init` |

## BT 下发机械臂

`ArmPickNode`（`arm_point_id` 模式）：

1. `publishArmPoseRequest()` → `arm_pose_request`
2. `clearArm(wp_id)` 清缓存，每次重新算
3. 等待 `arm_waypoint` 进入 `WaypointRegistry`
4. `publishCommand()` → `/arm_command` = `[x, y, z, yaw, action]`（1=Pick, 2=Place）

对比 `arm_only_demo.xml`：内联 x/y/z，跳过 broadcaster。

## 真机日志示例

```
ManualConfirmNode: confirmed arm_slot='0'
ArmPickNode: published arm_pose_request arm_point=0
arm_pose_broadcaster: Published arm_waypoint ... [map_target → base_link] (509.0, -28.5, 69.4)
ArmPickNode: sent Pick to /arm_command: (509.0, -28.5, 69.4, ...)
```

## 旧格式兼容

`legacy_to_map_target()`：`reference_aft` + `arm_target`(base_link mm) → 反推 `map_target`。新标定应直接写 `map_target`。

## 扩展（当前未实现）

若要从感知/TF 直接读 base_link 下物体位姿驱动机械臂，需新增节点或改 broadcaster，跳过 map 变换直接发 `arm_waypoint`。
