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

---

## 实际消息输出示例

### 场景 1：有 2 个真 KFS，1 个假 KFS（最近的真 KFS 距离 1.5 m）

**日志输出**：
```
[INFO] [1768899527.602480409] [kfs_manager]: Published KFS : Real KFS=Yes, Count=2, Fake KFS Count=1, Closest Fake Distance=2.50 m
```

**话题消息** (`ros2 topic echo /kfs_decision`):
```yaml
real_kfs_available: true
real_kfs_count: 2
primary_target_index: 0

real_kfs_class_names:
- r1
- r1

real_kfs_distances:
- 1.5
- 2.5

real_kfs_confidences:
- 0.95
- 0.92

real_kfs_colors:
- red
- red

real_kfs_bbox_xmin:
- 50.0
- 120.0

real_kfs_bbox_ymin:
- 30.0
- 80.0

real_kfs_bbox_xmax:
- 150.0
- 220.0

real_kfs_bbox_ymax:
- 130.0
- 180.0

fake_kfs_count: 1
fake_kfs_distances:
- 2.5
fake_kfs_confidences:
- 0.88
fake_kfs_colors:
- blue
closest_fake_kfs_distance: 2.5
safety_status: SAFE
priority_level: HIGH
timestamp:
  sec: 1768899527
  nanosec: 602480409
frame_id: camera
decision_confidence: 0.8
```

**行为树应该做什么**：
```
✅ real_kfs_available = true    → 有目标
✅ real_kfs_count = 2            → 有 2 个选择
✅ primary_target_index = 0      → 首选第 1 个（最近）
✅ safety_status = SAFE          → 环境安全
✅ priority_level = HIGH         → 立即执行
→ 导航到 距离 1.5 m 的 r1，进行抓取
→ 如果失败，可以尝试 距离 2.5 m 的第 2 个 r1
```

---

### 场景 2：有 1 个真 KFS，无假 KFS（安全环境）

**日志输出**：
```
[INFO] [1768899528.602580412] [kfs_manager]: Published KFS : Real KFS=Yes, Count=1, Fake KFS Count=0, Closest Fake Distance=-1.00 m
```

**话题消息**:
```yaml
real_kfs_available: true
real_kfs_count: 1
primary_target_index: 0

real_kfs_class_names:
- r2

real_kfs_distances:
- 1.8

real_kfs_confidences:
- 0.90

real_kfs_colors:
- red

real_kfs_bbox_xmin:
- 75.0

real_kfs_bbox_ymin:
- 50.0

real_kfs_bbox_xmax:
- 175.0

real_kfs_bbox_ymax:
- 150.0

fake_kfs_count: 0
fake_kfs_distances: []
fake_kfs_confidences: []
fake_kfs_colors: []
closest_fake_kfs_distance: -1.0
safety_status: SAFE
priority_level: HIGH
timestamp:
  sec: 1768899528
  nanosec: 602580412
frame_id: camera
decision_confidence: 1.0
```

**行为树应该做什么**：
```
✅ real_kfs_available = true    → 有唯一目标
✅ safety_status = SAFE          → 完全安全
✅ priority_level = HIGH         → 最高优先级
✅ decision_confidence = 1.0     → 100% 可信
→ 立即导航到 r2，执行抓取（无需避障）
```

---

### 场景 3：无真 KFS，有 2 个假 KFS（需要避开）

**日志输出**：
```
[INFO] [1768899529.602650415] [kfs_manager]: Published KFS : Real KFS=No, Count=0, Fake KFS Count=2, Closest Fake Distance=1.80 m
```

**话题消息**:
```yaml
real_kfs_available: false
real_kfs_count: 0
primary_target_index: 0

real_kfs_class_names: []
real_kfs_distances: []
real_kfs_confidences: []
real_kfs_colors: []
real_kfs_bbox_xmin: []
real_kfs_bbox_ymin: []
real_kfs_bbox_xmax: []
real_kfs_bbox_ymax: []

fake_kfs_count: 2
fake_kfs_distances:
- 1.8
- 3.2
fake_kfs_confidences:
- 0.85
- 0.78
fake_kfs_colors:
- blue
- blue
closest_fake_kfs_distance: 1.8
safety_status: WARNING
priority_level: WAIT
timestamp:
  sec: 1768899529
  nanosec: 602650415
frame_id: camera
decision_confidence: 0.4
```

**行为树应该做什么**：
```
❌ real_kfs_available = false    → 无目标
⚠️ safety_status = WARNING        → 有假 KFS 在 1.8 m
⚠️ priority_level = WAIT          → 暂停任务
→ 停止当前操作，等待真 KFS 出现
→ 或者主动避开假 KFS 的位置，继续搜索
```

---

### 场景 4：有 3 个真 KFS 在不同阶梯，1 个假 KFS

**日志输出**：
```
[INFO] [1768899530.602750418] [kfs_manager]: Published KFS : Real KFS=Yes, Count=3, Fake KFS Count=1, Closest Fake Distance=2.80 m
```

**话题消息** (阶梯场景示例):
```yaml
real_kfs_available: true
real_kfs_count: 3
primary_target_index: 0

real_kfs_class_names:
- r1        # 低阶梯
- r2        # 中阶梯
- r1        # 高阶梯

real_kfs_distances:
- 1.2
- 2.0
- 3.5

real_kfs_confidences:
- 0.96
- 0.91
- 0.85

real_kfs_colors:
- red
- red
- red

real_kfs_bbox_xmin:
- 40.0
- 100.0
- 160.0

real_kfs_bbox_ymin:
- 80.0
- 60.0
- 40.0

real_kfs_bbox_xmax:
- 140.0
- 200.0
- 260.0

real_kfs_bbox_ymax:
- 180.0
- 160.0
- 140.0

fake_kfs_count: 1
fake_kfs_distances:
- 2.8
fake_kfs_confidences:
- 0.82
fake_kfs_colors:
- blue
closest_fake_kfs_distance: 2.8
safety_status: SAFE
priority_level: HIGH
timestamp:
  sec: 1768899530
  nanosec: 602750418
frame_id: camera
decision_confidence: 0.8
```

**行为树应该做什么**：
```
✅ 有 3 个真 KFS 在不同高度（阶梯）
→ 策略 1：尝试最近的（1.2 m 的 r1 在低阶梯）
  - 若成功抓取：任务完成
  - 若失败（无法上到该阶梯）：尝试策略 2
  
→ 策略 2：尝试第 2 个（2.0 m 的 r2 在中阶梯）
  - 若成功抓取：任务完成
  - 若失败：尝试策略 3
  
→ 策略 3：尝试第 3 个（3.5 m 的 r1 在高阶梯）
  - 若成功抓取：任务完成
  - 若仍失败：报告失败
```

---

#### `fake_kfs_count` (uint32)
- **含义**：检测到的假 KFS 数量
- **值范围**：0, 1, 2, 3, ...
- **用途**：判断周围是否有危险，触发避障逻辑
- **示例**：
  ```
  fake_kfs_count: 0  (环境安全，没有假 KFS)
  fake_kfs_count: 1  (有 1 个假 KFS 需要避开)

  ```

#### `fake_kfs_distances` (float64[])
- **含义**：每个假 KFS 的距离列表
- **单位**：米 (m)
- **数组长度**：等于 `fake_kfs_count`
- **用途**：评估假 KFS 的威胁程度，规划避开路径
- **示例**：
  ```
  fake_kfs_distances:
  - 2.5  (第 1 个假 KFS 距离 2.5 米)
  - 3.8  (第 2 个假 KFS 距离 3.8 米)
  ```

#### `fake_kfs_confidences` (float64[])
- **含义**：每个假 KFS 的检测置信度列表
- **值范围**：0.0 ~ 1.0
- **数组长度**：等于 `fake_kfs_count`
- **用途**：评估假 KFS 识别的可靠性
- **示例**：
  ```
  fake_kfs_confidences:
  - 0.88  (第 1 个假 KFS 置信度 88%)
  - 0.76  (第 2 个假 KFS 置信度 76%)
  ```

#### `fake_kfs_colors` (string[])
- **含义**：每个假 KFS 的颜色列表
- **值范围**：`"red"` / `"blue"` / `"unknown"`
- **数组长度**：等于 `fake_kfs_count`
- **示例**：
  ```
  fake_kfs_colors:
  - blue      (第 1 个假 KFS 是蓝色)
  - red       (第 2 个假 KFS 是红色)
  ```

#### `closest_fake_kfs_distance` (float64)
- **含义**：最近的假 KFS 的距离
- **单位**：米 (m)
- **特殊值**：`-1.0` 表示没有检测到假 KFS（此时 `fake_kfs_count == 0`）
- **用途**：快速判断是否有紧急危险
- **示例**：
  ```
  closest_fake_kfs_distance: 0.8   (危险！假 KFS 只有 0.8 米)
  closest_fake_kfs_distance: 2.5   (安全距离，不紧急)
  closest_fake_kfs_distance: -1.0  (没有假 KFS)
  ```

---

### 🛡️ 【安全状态字段】

#### `safety_status` (string)
- **含义**：系统当前的安全状态评级
- **值范围**：`"SAFE"` / `"WARNING"` / `"DANGER"`
- **用途**：行为树的安全决策门槛

**详细说明**：

| 状态 | 含义 | 危险距离 | 行为树应该怎么做 |
|------|------|---------|------------------|
| **SAFE** | 周围完全安全，可以正常操作 | 无假 KFS 或假 KFS > 1.0 m | ✅ 可以继续执行抓取动作 |
| **WARNING** | 有假 KFS 在警告区，需要谨慎 | 0.5 ~ 1.0 m | ⚠️ 可以操作但要规划避开路径 |
| **DANGER** | 有假 KFS 在危险区，不安全 | < 0.3 m | 🚫 避免碰撞 |

**示例**：
```yaml
# 安全的情况
safety_status: SAFE
fake_kfs_count: 0
closest_fake_kfs_distance: -1.0

# 警告的情况
safety_status: WARNING
fake_kfs_count: 1
closest_fake_kfs_distance: 0.8

# 危险的情况
safety_status: DANGER
fake_kfs_count: 1
closest_fake_kfs_distance: 0.3
```

---

### 🎯 【优先级字段】

#### `priority_level` (string)
- **含义**：系统对操作的优先级建议
- **值范围**：`"HIGH"` / `"MEDIUM"` / `"LOW"` / `"WAIT"`
- **用途**：行为树的任务调度和决策优先级

**详细说明**：

| 优先级 | 含义 | 何时触发 | 行为树应该做什么 |
|--------|------|---------|------------------|
| **HIGH** | 有高置信度目标且环境安全 | `real_kfs_available == true && safety_status == "SAFE"` | ✅ 立即执行抓取任务 |
| **MEDIUM** | 有目标但周围有假 KFS 需要避开 | `real_kfs_available == true && safety_status == "WARNING"` | 🔄 规划避开路径，小心操作 |
| **LOW** | 有目标但不紧急，或置信度低 | `real_kfs_available == true && safety_status == "DANGER"` | ⏳ 等待危险消除，再执行 |
| **WAIT** | 没有可用目标，需要等待 | `real_kfs_available == false` | ⏸️ 暂停，继续观察或主动搜索 |

### 阈值参考值 (kfs_manager.hpp)
```cpp
PROBABILITY_THRESHOLD = 0.80       // 置信度门槛 (可改 0.70-0.90)
DANGER_ZONE_RADIUS = 1.0          // 警告区 (1 米内)
CRITICAL_DANGER_RADIUS = 0.3      // 危险区 (0.3 米内)
```

**版本历史**：
- v1.0 (2026-01-20): 初始文档，包含完整的字段解释和使用指南