# Front/back suction mission path planner (legged_mission_planner_f_r)

Discrete logical path planner for ROBOCON 2026 task event with front/back arm suction.

## Build

```bash
colcon build --packages-select legged_mission_planner_f_r --symlink-install
source install/setup.bash
```

## Usage

```bash
# UI labeling and planning
ros2 launch legged_mission_planner_f_r ui_standalone.launch.py

# Waypoint calibration (path planner ↔ BT naming)
ros2 launch legged_mission_planner_f_r waypoint_editor.launch.py

# Export scenario batch
ros2 run legged_mission_planner_f_r export_scenarios_fr --limit 10

# Simulate quiz result
ros2 topic pub --once /mission/quiz_type std_msgs/msg/Int32 "{data: 2}"
```

## Tests

```bash
pytest src/legged_mission_planner_f_r/test/test_fr_planner.py -q
pytest src/legged_mission_planner_f_r/test/test_waypoint_yaml_exporter.py -q
```

See [路径规划要求和限制.md](路径规划要求和限制.md) for design details.
