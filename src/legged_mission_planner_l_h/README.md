# legged_mission_planner

ROBOCON 2026 仿生足式机器人**任务赛逻辑路径规划**独立包。负责赛前标注、策略规划、路径/航点顺序与每步状态导出；**不包含** map 坐标解析、Nav2 执行、机械臂动作、串口 ack（由 `legged_bringup` 负责）。

## 设计原则

| 本包负责 | 本包不负责 |
|----------|------------|
| 场地逻辑模型（路径 / 航点 / 箱位 / 归位区） | Nav2 `NavigateToPose` |
| 取放顺序与路径切换策略 | map 坐标 / 吸放站位标定 |
| 逻辑任务序列导出（path, wp, state） | 行为树执行节点 |
| 操作手 UI 标注 + 路径示意图 | 机械臂 ack 与重试 |

---

## 目录结构

```
legged_mission_planner/
├── assets/                 # 场地图、箱子/放置区图标
├── config/
│   ├── field_layout.yaml   # 仅 UI 路径示意图几何（非 Nav2 坐标）
│   ├── mission_params.yaml # 默认策略与规划参数
│   ├── export_format.yaml  # 导出格式 v2 约定
│   └── scenarios/
├── launch/
│   └── ui_standalone.launch.py
├── legged_mission_planner/
│   ├── field_model.py      # 场地逻辑
│   ├── path_planner.py     # 路径规划核心
│   ├── plan_exporter.py    # 逻辑序列 YAML/JSON 导出
│   ├── path_enumerator.py  # 批量场景穷举
│   ├── state_definitions.py
│   ├── path_viz.py         # UI 路径示意图
│   ├── ui_labeling.py      # 操作手 UI
│   ├── quiz_listener.py    # 智力题 ROS 话题订阅
│   └── pose_resolver.py     # deprecated，供 bringup 迁移参考
└── tmp/                    # 默认导出目录
```

---

## 命令行接口

```bash
colcon build --packages-select legged_mission_planner --symlink-install
source install/setup.bash
```

| 命令 | 说明 |
|------|------|
| `ros2 run legged_mission_planner mission_ui` | 标注 + 规划 + 导出 |
| `ros2 run legged_mission_planner export_scenarios` | 批量导出逻辑场景 |
| `ros2 launch legged_mission_planner ui_standalone.launch.py` | Launch 启动 UI |

UI 示例（`field_layout` 仅用于路径示意图）：

```bash
ros2 run legged_mission_planner mission_ui \
  --field-layout src/legged_mission_planner/config/field_layout.yaml \
  --mission-params src/legged_mission_planner/config/mission_params.yaml
```

批量导出（无需 field_layout）：

```bash
ros2 run legged_mission_planner export_scenarios --limit 1
```

---

## Python API

```python
from legged_mission_planner.path_planner import MissionPathPlanner
from legged_mission_planner.plan_exporter import PlanExporter

planner = MissionPathPlanner()
sequence = planner.plan(
    box_types=[0, 1, 2, 3, 0, 1, 2, 3],
    zone_types=[0, 1, 2, 3],
    strategy='safe_edges',
    switch_mode='wp4_only',
)

scenario = {
    'box_types': [0, 1, 2, 3, 0, 1, 2, 3],
    'zone_types': [0, 1, 2, 3],
    'include_quiz_state': False,
}
exporter = PlanExporter()
plan = exporter.export(sequence, scenario, 'safe_edges', 'wp4_only', 'tmp/mission_plan')

# 智力题二次规划（仅重排取放顺序，不改变路径集合）
quiz_sequence = planner.plan(
    box_types=[0, 1, 2, 3, 0, 1, 2, 3],
    zone_types=[0, 1, 2, 3],
    strategy='safe_edges',
    switch_mode='wp4_only',
    quiz_type=2,
)
```

---

## 智力题二次规划

比赛开始后识别智力题，在**基础规划导出之后**可选启用：

1. 操作手标注 → 点击 **规划并导出** → 立即导出基础 `mission_plan.*`
2. 可选点击 **等待智力题** → 开始 10s 倒计时并订阅 ROS 话题
3. 时限内收到结果 → 按智力题种类重排取放顺序 → 覆盖导出（`plan_source: quiz`），**启动区首步 state=0**（智力题识别）
4. 超时或未点击等待按钮 → 保持基础规划（`plan_source: base`），启动区首步 **state=1**（纯走点）

配置见 `config/mission_params.yaml`：

```yaml
quiz_result_topic: /mission/quiz_type   # 可自行修改
quiz_wait_timeout_s: 10.0
```

模拟发布智力题结果：

```bash
ros2 topic pub --once /mission/quiz_type std_msgs/msg/Int32 "{data: 2}"
```

---

## 导出格式 v2（`mission_plan.yaml` / `.json`）

**不含 `pose` / `frame_id`**。bringup 侧根据 `(path, wp, state, target_*)` 解析 map 坐标。

顶层：

- `format_version: 2`
- `strategy`, `switch_mode`, `scenario`
- `quiz_type`, `quiz_received`, `quiz_wait_started`, `plan_source`
- `sequence`

每步 `sequence[i]`：

| 字段 | 含义 |
|------|------|
| `step` | 1-based 步骤序号 |
| `path` | 路径 1~5（0=启动） |
| `wp` | 航点 1~5 |
| `state` | 航点状态 0~5 |
| `state_label` | 可读标签 |
| `target_box` / `target_zone` | 取放目标 |
| `box_type` / `zone_type` | 物资种类 |
| `note` | 备注 |

### 航点状态

| state | 含义 | bringup 行为 |
|-------|------|--------------|
| 0 | 智力题（预留） | 识别节点 |
| 1 | 纯走点 | Nav2 导航 |
| 2 | 左吸 | 导航 + 左臂取箱 |
| 3 | 右吸 | 导航 + 右臂取箱 |
| 4 | 左放 | 导航 + 左臂放箱 |
| 5 | 右放 | 导航 + 右臂放箱 |

---

## bringup 对接契约（Phase 2，本包不实现）

`legged_bringup` 应：

1. 加载 `mission_plan.yaml` v2 的 `sequence`
2. 维护 `task_field.yaml`（map 原点、路径 y、航点 x、pick/place 偏移、箱位坐标）
3. 实现 `MissionPoseResolver`：`(path, wp, state, target_box, target_zone)` → `PoseStamped`
4. 行为树按 `state` 分支：Nav2 → 机械臂 → WaitAck

```
For each step in sequence:
  resolve_pose(step)  # bringup 内部
  ├─ state 1  → NavigateToPose
  ├─ state 2  → NavigateToPose → ArmPickLeft → WaitAck
  ├─ state 3  → NavigateToPose → ArmPickRight → WaitAck
  ├─ state 4  → NavigateToPose → ArmPlaceLeft → WaitAck
  └─ state 5  → NavigateToPose → ArmPlaceRight → WaitAck
```

---

## 场地编号约定

**8 个箱位**（上排 0~3，下排 4~7，从右往左）：

```
上排:  3  2  1  0
下排:  7  6  5  4
```

**4 个归位区**（从右往左 0~3）：食品 / 工具 / 仪器 / 药品

**规划策略**：`safe_edges`（1–5，边界扫掠）或 `middle_paths`（2,3,4）

**路径切换**：`wp4_only` 或 `wp4_or_wp5`

---

## 输出文件

| 文件 | 内容 |
|------|------|
| `mission_plan.yaml` / `.json` | 逻辑任务序列（供 bringup） |
| `mission_plan.csv` | 步骤摘要（无坐标） |
| `mission_plan.png` | 场地图 + 标注 + 逻辑路径示意 |

---

## 依赖

- Python 3 + PyYAML + Pillow（UI 与可视化）
- ROS 2 ament_python + rclpy + std_msgs（智力题话题订阅）

---

## 相关文档

- [路径规划要求和限制.md](../../docs/路径规划要求和限制.md)
