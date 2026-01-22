# 🤖 KFS 决策接口文档 (KFS Decision Interface)

### 🎯 用途
`KfsManager` 节点处理来自 YOLO 检测器的原始数据，并发布**高级决策信息** 。


## 话题1:识别到的KFS信息

### 基础信息
| 属性 | 值 |
|------|-----|
| **话题名称** | `/kfs_decision` |
| **消息类型** | `yolov8_ros2_msgs/msg/KFSDecision` |
| **发布频率** | 1 Hz (每秒一次) |
| **发布者** | `kfs_detection_nav` 包中的 `KfsManager` 节点 |

### 启动节点的命令
```bash
# 终端 1: 启动 YOLO 模拟器
ros2 run yolo_simulator yolo_simulator_node

# 终端 2: 启动 KFS 管理器
ros2 run kfs_detection_nav kfs_detection_node

# 终端 3: 查看决策消息（决策结果）
ros2 topic echo /kfs_decision

# 终端 4: 查看台阶匹配结果（详细信息）
ros2 topic echo /stair_match_result
```

### 日志输出示例

当 KfsManager 发布决策信息时，会输出类似的日志：
```
[INFO] [1768899527.602480409] [kfs_manager]: Published KFS : Real KFS=Yes, Count=2, Fake KFS Count=1, Closest Fake Distance=2.50 m

```

**日志字段说明**：
- `Real KFS=Yes/No` - 是否有可抓取的真 KFS
- `Count=N` - 可抓取的真 KFS 数量
- `Fake KFS Count=M` - 检测到的假 KFS 数量
- `Closest Fake Distance=X.XX m` - 最近的假 KFS 距离（-1.0 表示无假 KFS）

## 消息字段详解

### 🎯 【目标相关字段】- 所有可抓取的真 KFS（按距离排序）

#### `real_kfs_available` (bool)
- **含义**：是否存在可抓取的真 KFS（置信度 ≥ 80%）
- **值范围**：`true` / `false`



#### `real_kfs_count` (uint32)
- **含义**：检测到的可抓取真 KFS 总数
- **值范围**：0, 1, 2, 3, ...


#### `real_kfs_class_names` (string[])
- **含义**：所有真 KFS 的类型列表（按距离从近到远排序）
- **值范围**：`"r1"` / `"r2"`
- **数组长度**：等于 `real_kfs_count`
- **用途**：区分不同的 KFS 类型
- **示例**：
  ```yaml
  real_kfs_class_names:
  - r1        # 排序 1 (最近)
  - r1        # 排序 2
  - r2        # 排序 3 (最远)
  ```

#### `real_kfs_distances` (float64[])
- **含义**：所有真 KFS 的距离列表（按距离从近到远排序）
- **单位**：米 (m)
- **数组长度**：等于 `real_kfs_count`
- **用途**：规划导航路径，选择最优目标
- **示例**：
  ```yaml
  real_kfs_distances:
  - 1.5       # 排序 1 (最近)
  - 2.5       # 排序 2
  - 3.0       # 排序 3 (最远)
  ```

#### `real_kfs_confidences` (float64[])
- **含义**：所有真 KFS 的置信度列表
- **值范围**：0.0 ~ 1.0 (所有值 ≥ 0.80)
- **数组长度**：等于 `real_kfs_count`
- **用途**：评估每个目标的可靠性
- **示例**：
  ```yaml
  real_kfs_confidences:
  - 0.95      # 第 1 个置信度 95%（非常可信）
  - 0.92      # 第 2 个置信度 92%
  - 0.80      # 第 3 个置信度 80%（刚好满足最低要求）
  ```

#### `real_kfs_colors` (string[])
- **含义**：所有真 KFS 的颜色列表
- **值范围**：`"red"` / `"blue"` / `"unknown"`
- **数组长度**：等于 `real_kfs_count`
- **用途**：视觉识别和调试
- **示例**：
  ```yaml
  real_kfs_colors:
  - red       # 第 1 个是红色
  - red       # 第 2 个是红色
  - red       # 第 3 个是红色
  ```

#### `real_kfs_bbox_xmin`, `real_kfs_bbox_ymin`, `real_kfs_bbox_xmax`, `real_kfs_bbox_ymax` (float64[])
- **含义**：所有真 KFS 在摄像头图像中的边界框坐标数组
- **单位**：像素
- **数组长度**：等于 `real_kfs_count`
- **用途**：精准定位、可视化、机械臂视觉伺服
- **示例**：
  ```yaml
  real_kfs_bbox_xmin:
  - 50.0      # 第 1 个 KFS 左上角 X
  - 120.0     # 第 2 个 KFS 左上角 X
  - 200.0     # 第 3 个 KFS 左上角 X
  
  real_kfs_bbox_ymin:
  - 30.0      # 第 1 个 KFS 左上角 Y
  - 80.0      # 第 2 个 KFS 左上角 Y
  - 150.0     # 第 3 个 KFS 左上角 Y
  
  real_kfs_bbox_xmax:
  - 150.0     # 第 1 个 KFS 右下角 X
  - 220.0     # 第 2 个 KFS 右下角 X
  - 300.0     # 第 3 个 KFS 右下角 X
  
  real_kfs_bbox_ymax:
  - 130.0     # 第 1 个 KFS 右下角 Y
  - 180.0     # 第 2 个 KFS 右下角 Y
  - 250.0     # 第 3 个 KFS 右下角 Y
  ```

#### `primary_target_index` (uint32)
- **含义**：行为树优先选择的目标在数组中的索引
- **值范围**：0 ~ (real_kfs_count - 1)
- **用途**：指定首选目标（通常是最近的）
- **示例**：
  ```yaml
  primary_target_index: 0  # 选择第 1 个（最近的）作为首选
  ```
- **行为树使用方式**：
  ```cpp
  // 首先尝试首选目标
  int idx = msg.primary_target_index;  // = 0
  target.distance = msg.real_kfs_distances[idx];
  target.class_name = msg.real_kfs_class_names[idx];
  
  // 如果首选失败，可以尝试次选
  if (grasp_failed && msg.real_kfs_count > 1) {
    idx = 1;  // 尝试第 2 个
    target.distance = msg.real_kfs_distances[idx];
  }
  ```
---

## 话题2：台阶匹配结果详情 (`/stair_match_result`)

该话题用于描述**当前场景中 12 个台阶上分别放置了什么物体**，是系统对环境状态的整体感知结果快照，供后续决策、调度或调试使用。

### 基础信息
| 属性 | 值 |
|------|-----|
| **话题名称** | `/stair_match_result` |
| **消息类型** | `yolov8_ros2_msgs/msg/StairMatchResult` |
| **发布频率** | 1 Hz (每秒一次，与 `/kfs_decision` 同步) |
| **发布者** | `kfs_detection_nav` 包中的 `KfsManager` 节点 |
| **目的** | 发布每个检测到的 KFS 的**详细台阶匹配信息** |

### 用途说明

- 每个 KFS 匹配到的**具体台阶 ID 和名称**
- 每个 KFS 在**全局地图坐标系中的 3D 位置**
- 机器人与每个 KFS 的**实际距离和类别**

### 消息字段详解


---

### 🔢 常量定义（Object Type）

| 常量名 | 数值 | 含义 |
|------|------|------|
| `OBJECT_NONE` | 0 | 该台阶为空 |
| `OBJECT_R1` | 1 | 该台阶上存在 R1 |
| `OBJECT_R2` | 2 | 该台阶上存在 R2 |
| `OBJECT_FAKE` | 3 | 该台阶上存在假 KFS |
| `OBJECT_UNKNOWN` | 4 | 该台阶上状态未知 |

---

### 🧱 基本信息字段

| 字段名 | 类型 | 说明 |
|------|------|------|
| `total_stairs` | `int32` | 台阶总数，固定为 **12** |

---

### 📦 每个台阶的内容描述（数组字段）

以下数组字段长度均为 **12**，数组索引 `i` 对应 **第 `i+1` 个台阶**。

| 字段名 | 类型 | 说明 |
|------|------|------|
| `stair_object_type` | `int32[]` | 每个台阶上的物体类型，取值为上述 **Object Type 常量** |
| `stair_confidences` | `float64[]` | 对应台阶物体的识别置信度；当 `stair_object_type[i] == OBJECT_NONE` 时，该值为 **0.0** |
| `stair_names` | `string[]` | 台阶名称，用于调试和日志输出（如 `"Stair_Deep_Green_1"`） |

---

### 📊 场景统计信息字段

这些字段对整个 12 台阶场景进行统计汇总，便于快速判断当前状态。

| 字段名 | 类型 | 说明 |
|------|------|------|
| `total_r1_count` | `int32` | 当前场景中 R1 的总数量 |
| `total_r2_count` | `int32` | 当前场景中 R2 的总数量 |
| `total_fake_count` | `int32` | 当前场景中假 KFS 的总数量（通常为 0 或 1） |
| `total_empty_count` | `int32` | 当前为空的台阶数量 |

---

### ⏱️ 时序与坐标信息

| 字段名 | 类型 | 说明 |
|------|------|------|
| `timestamp` | `builtin_interfaces/Time` | 该快照生成时的时间戳 |
| `frame_id` | `string` | 所属坐标系标识（如 `"map"` 或 `"world"`） |

---


---

**版本历史**：
- v1.0 (2026-01-20): 初始文档，包含完整的字段解释和使用指南
- v2.0 (2026-01-21): 新增 `/stair_match_result` 话题文档，完善两个话题的对比说明