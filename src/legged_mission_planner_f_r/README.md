# Front/back suction mission path planner (legged_mission_planner_f_r)

Discrete logical path planner for ROBOCON 2026 task event with front/back arm suction.

## Build

```bash
colcon build --packages-select legged_mission_planner_f_r --symlink-install
source install/setup.bash
```

## Usage

统一路径规划（标注 + 可选智力题 + 一次导出）：

```bash
ros2 launch legged_mission_planner_f_r mission_plan.launch.py
```

侧栏「智力题种类」默认 **未识别 (-1)** → 基础规划；选择 0~3 后点击「规划并导出」→ 智力题规划。均直接输出最终 `mission_plan.yaml` 等到 `tmp/`。

```bash
# 航点标定（路径规划 ↔ BT 命名）
ros2 launch legged_mission_planner_f_r waypoint_editor.launch.py

# 箱子/归还区点击区域标定
ros2 launch legged_mission_planner_f_r hotspot_editor.launch.py

# 批量导出场景
ros2 run legged_mission_planner_f_r export_scenarios_fr --limit 10
```

输出目录默认 `src/legged_mission_planner_f_r/tmp/`：
- `mission_plan.yaml` / `.json` / `.csv` / `.png` — 最终路径规划
- `mission_quintuple.yaml` — 行为树五元组序列
- `base_scenario.yaml` — 本次标注的箱子/归还区配置

## Tests

```bash
cd src/legged_mission_planner_f_r && PYTHONPATH=. python3 -m pytest test/ -q
```

See [路径规划要求和限制.md](路径规划要求和限制.md) for design details.
