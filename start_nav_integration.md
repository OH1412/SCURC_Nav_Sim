# start_nav 手柄触发 — 导航侧对齐说明

本文档描述 `deploy_cpp` 通过手柄 X 键发布 `/start_nav` 的契约，供 SCURC_Nav_Sim / 导航脚本订阅对接。

## 1. 话题契约

| 项目     | 值                                                          |
| -------- | ----------------------------------------------------------- |
| 话题名   | `/start_nav`（可在 yaml 中改 `start_nav_topic`）        |
| 消息类型 | `std_msgs/msg/Bool`                                       |
| QoS      | Reliable, depth=10（与`/suction_action` 相同）            |
| 发布者   | `deploy_node`（仅 `teleop_master=true` 的 master 节点） |

### payload

每条消息均为 **`data: true`**。

## 2. 触发语义

- **按键**：Xbox/通用手柄 **X 键** → `buttons[3]`（yaml: `joy_button_start_nav: 3`）
- **边沿**：仅在按键 **rising edge**（从未按下→按下）时启动周期发布
- **周期**：点击 X 后立即发 1 条，之后每 **500 ms** 持续发布 `Bool(true)`（yaml: `start_nav_publish_interval_ms: 500`）
- **停止**：周期发布一旦启动会持续运行（再次按 X 不会重复创建定时器，但会立即再发 1 条）

时序示意：

```
按下 X 键
  t=0ms     → /start_nav  data: true
  t=500ms   → /start_nav  data: true
  t=1000ms  → /start_nav  data: true
  ...
  deploy 日志: "Started start_nav periodic publish every 500ms on /start_nav"
```

## 3. deploy 侧配置（mybot_arm.yaml）

```yaml
joy_button_start_nav: 3
start_nav_topic: /start_nav
start_nav_publish_interval_ms: 500
```

设为 `-1` 可禁用该功能：

```yaml
joy_button_start_nav: -1
```

## 4. 当前有效手柄映射（mybot_arm）

| 物理键 | buttons 索引 | yaml 配置                     | 功能                   |
| ------ | ------------ | ----------------------------- | ---------------------- |
| A      | 0            | `joy_button_stand_up`       | 站起                   |
| B      | 1            | `joy_button_return_default` | 回默认姿态             |
| X      | 3            | `joy_button_start_nav`      | **触发导航启动** |
| Y      | 4            | `joy_button_rl`             | 进入 RL 策略控制       |

摇杆：`axes[1]`=vx，`axes[0]`=vy，`axes[2]`=yaw。

## 5. 导航侧订阅建议

### 5.1 推荐逻辑

收到 **任意 1 条** `data=true` 即启动导航（需做幂等保护，避免重复启动）。

```python
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool

class StartNavListener(Node):
    def __init__(self):
        super().__init__('start_nav_listener')
        self._nav_launched = False
        self.create_subscription(Bool, '/start_nav', self._cb, 10)
        self.get_logger().info('Listening on /start_nav (launch on first data=true)')

    def _cb(self, msg):
        if not msg.data or self._nav_launched:
            return
        self._nav_launched = True
        self.get_logger().info('start_nav received — launching navigation...')
        self._launch_navigation()
```

### 5.2 启动导航示例（gnome-terminal）

按你现有工程结构替换 launch 命令：

```python
import subprocess

NAV_CMD = (
    'source /opt/ros/humble/setup.bash && '
    'source /home/dog12/SCURC_Nav_Sim/install/setup.bash && '
    'ros2 launch legged_bringup navigation.launch.py'
)

subprocess.Popen([
    'gnome-terminal', '--title=navigation', '--',
    'bash', '-lc', f'{NAV_CMD}; exec bash'
])
```

若导航已在运行，订阅方应做 **幂等保护**（例如 `_nav_launched` 标志或检查 Nav2 lifecycle）。

### 5.3 与 bringup 集成参考

现有导航入口：

- Launch: `legged_bringup/launch/navigation.launch.py`
- 全栈: `legged_bringup/launch/bringup_all_in_one.launch.py`（内含 delayed navigation）

可参考 `stand_up_sender.py` 的模式：订阅触发 → 执行动作 → 可选发布完成话题。
