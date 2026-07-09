# Front/back suction mission path planner (legged_mission_planner_f_r)

Discrete logical path planner for ROBOCON 2026 task event with front/back arm suction.

## Build

```bash
colcon build --packages-select legged_mission_planner_f_r --symlink-install
source install/setup.bash
```

## Usage

两阶段规划（须按顺序执行）：

```bash
# 1. 基础规划：标注箱子/归还区，导出规划并保存 base_scenario.yaml
ros2 launch legged_mission_planner_f_r base_plan.launch.py

# 2. 智力题二次规划：加载基础场景，自动等待 20s 话题，收到则覆盖导出
ros2 launch legged_mission_planner_f_r quiz_plan.launch.py

# 兼容旧命令（等同 base_plan）
ros2 launch legged_mission_planner_f_r ui_standalone.launch.py
```

```bash
# 航点标定（路径规划 ↔ BT 命名）
ros2 launch legged_mission_planner_f_r waypoint_editor.launch.py

# 批量导出场景
ros2 run legged_mission_planner_f_r export_scenarios_fr --limit 10

# 模拟智力题结果（在 quiz_plan 等待期间发布）
ros2 topic pub --once /mission/quiz_type std_msgs/msg/Int32 "{data: 2}"
```

输出目录默认 `src/legged_mission_planner_f_r/tmp/`：
- `base_scenario.yaml` — 基础规划保存的箱子/归还区配置
- `mission_plan.yaml` / `.json` / `.csv` / `.png`
- `mission_quintuple.yaml` — 行为树五元组序列

## Tests

```bash
cd src/legged_mission_planner_f_r && PYTHONPATH=. python3 -m pytest test/ -q
```

See [路径规划要求和限制.md](路径规划要求和限制.md) for design details.
