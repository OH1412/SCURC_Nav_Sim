# legged_mission_bt

独立行为树任务执行器（fly_step 架构）：在 XML 中自由组合导航、吸取、放置。

## 节点

| BT 节点 | 说明 |
|---------|------|
| `Nav2PoseNode` | 调用 `navigate_to_pose`，到达即 SUCCESS |
| `ArmPickNode` | 发布 `/arm_command` (action=1)，等 ACK state=0x01 result=0x00 |
| `ArmPlaceNode` | 发布 `/arm_command` (action=2)，等 ACK state=0x02 result=0x00 |
| `WaitSecondsNode` | 等待若干秒 |

机械臂坐标单位为 **arm_base 毫米**，与手动测试命令一致。

## 构建

```bash
colcon build --packages-select legged_mission_bt --symlink-install
source install/setup.bash
```

## 启动（实机全套）

```bash
ros2 launch legged_bringup bringup_arm_mission.launch.py
```

自定义 BT：

```bash
ros2 launch legged_bringup bringup_arm_mission.launch.py \
  bt_xml_file:=$(ros2 pkg prefix legged_mission_bt)/share/legged_mission_bt/behavior_trees/mission_template.xml
```

仅 BT（Nav2 已运行）：

```bash
ros2 launch legged_mission_bt mission_bt_only.launch.py
```

**纯机械臂测试（只需串口，不需要 Nav2）**：

```bash
ros2 launch legged_mission_bt arm_only_test.launch.py
ros2 launch legged_mission_bt arm_only_test.launch.py port:=/dev/ttyUSB0
```

默认 BT：`behavior_trees/arm_only_demo.xml`（仅 Pick + Wait + Place）。编辑该 XML 或指定 `bt_xml_file:=` 即可。

## 编辑任务

复制 `behavior_trees/mission_template.xml`，在 `<Sequence>` 内增删节点即可改变顺序。

ACK 协议见仓库根目录 `arm_control_serial_protocol_ACK.md`。
