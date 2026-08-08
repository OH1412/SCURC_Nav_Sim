### DWB 区域策略切换（边缘区/中间区）

当前代码默认使用纯中间策略（所有区域 yaw 锁 0°）。以下是从默认配置切换到「根据 X 坐标自动切换区域」的操作步骤。

#### 区域定义

| 区域   | X 坐标范围           | 行为                                   |
| ------ | -------------------- | -------------------------------------- |
| 边缘区 | x < 0.9m 或 x > 4.9m | 允许旋转，精确朝向对齐（3°）          |
| 中间区 | 0.9m ≤ x ≤ 4.9m    | 禁止旋转，yaw 锁 0°（朝向容差 360°） |

#### 切换步骤

**1. `params/nav2_params.yaml`** — 5 个参数从中间区值改为边缘区值：

| 参数                                              | 当前（中间区） | 改为（边缘区） |
| ------------------------------------------------- | :------------: | :------------: |
| `RotateToGoal.scale`                            |      0.0      |      32.0      |
| `GoalAlign.scale`                               |      0.0      |      24.0      |
| `PathAlign.scale`                               |      0.0      |      32.0      |
| `"dwb_yaw_constraint::MaintainYawCritic.scale"` |     5000.0     |      0.0      |
| `yaw_goal_tolerance`                            |      6.28      |    0.05236    |

**2. `launch/navigation.launch.py`** — 取消 `position_switcher_node` 的注释（约 L367-L385）：

```python
position_switcher_node = Node(
    package='legged_bringup',
    executable='position_based_param_switcher.py',
    name='position_based_param_switcher',
    output='screen',
    parameters=[{
        'lower_boundary': 0.9,
        'upper_boundary': 4.9,
        'hysteresis_margin': 0.1,
        'odom_topic': 'state_estimation',
        'target_node': 'controller_server',
    }],
    arguments=['--ros-args', '--log-level', 'info'],
)
ld.add_action(TimerAction(period=5.0, actions=[position_switcher_node]))
```

**3.** 重启 navigation launch 即可生效，需编译。
