# 🤖 KFS 决策接口文档 (KFS Decision Interface)

### 🎯 用途
`KfsManager` 节点处理来自 YOLO 检测器的原始数据，并发布**高级决策信息** `/kfs_decision`。
行为树订阅此话题来：
- 确定是否有可抓取的真 KFS
- 可抓取的真 KFS 信息
- 周围是否有假 KFS
- 假的 KFS 信息

## 话题信息

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

# 终端 3: 查看决策消息
ros2 topic echo /kfs_decision
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


**版本历史**：
- v1.0 (2026-01-20): 初始文档，包含完整的字段解释和使用指南