# 机械臂坐标抓取/放置控制串口协议 v2.0

## 概述

本协议用于通过串口与机械臂下位机进行双向通信，实现坐标抓取（Pick）和放置（Place）功能。

协议包含两个方向的帧：

- **命令帧** (上位机 → 下位机): 发送目标坐标和控制指令
- **ACK 帧** (下位机 → 上位机): 回报动作执行结果

---

## 命令帧格式

| 字节索引 | 字段名   | 大小 | 说明                             |
| -------- | -------- | ---- | -------------------------------- |
| 0        | 帧头 1   | 1    | `0xFD`                           |
| 1        | 帧头 2   | 1    | `0xFD`                           |
| 2        | 长度     | 1    | `0x07`（数据区固定 7 字节）      |
| 3        | 控制位   | 1    | `0x01`=Pick / `0x02`=Place       |
| 4-5      | X 坐标   | 2    | int16 小端序，单位 mm            |
| 6-7      | Y 坐标   | 2    | int16 小端序，单位 mm            |
| 8-9      | Z 坐标   | 2    | int16 小端序，单位 mm            |
| 10       | checksum | 1    | 前 10 字节累加和取低 8 位        |

**帧总长: 11 字节**

### 校验和计算

```
checksum = (0xFD + 0xFD + 0x07 + ctrl + X_L + X_H + Y_L + Y_H + Z_L + Z_H) & 0xFF
```

### 命令帧示例

```
吸取坐标 (x=0, y=350, z=50) mm, checksum_offset=0:
  FD FD 07 01 00 00 5E 01 32 00 9E
```

---

## ACK 帧格式

| 字节索引 | 字段名   | 大小 | 说明                          |
| -------- | -------- | ---- | ----------------------------- |
| 0        | 帧头 1   | 1    | `0xFE`                        |
| 1        | 帧头 2   | 1    | `0xFE`                        |
| 2        | 长度     | 1    | `0x03`（数据区固定 3 字节）   |
| 3        | state    | 1    | `0x01`=Pick完成 / `0x02`=Place完成 |
| 4        | result   | 1    | `0x00`=成功 / `0x01`=失败     |
| 5        | checksum | 1    | 前 5 字节累加和取低 8 位      |

**帧总长: 6 字节**

### 校验和计算

```
checksum = (0xFE + 0xFE + 0x03 + state + result) & 0xFF
```

### 状态码定义

| state | 含义          |
| ----- | ------------- |
| 0x01  | Pick 动作完成 |
| 0x02  | Place 动作完成 |

### 结果码定义

| result | 含义 |
| ------ | ---- |
| 0x00   | 成功 |
| 0x01   | 失败 |

### ACK 帧示例

```
Pick 完成、成功:  FE FE 03 01 00 02
Place 完成、失败: FE FE 03 02 01 04
```

---

## 控制位定义

| 控制位 | 含义                    |
| ------ | ----------------------- |
| 0x01   | 吸取（Pick）            |
| 0x02   | 放置（Place）           |

---

## 坐标系定义

### arm_base 坐标系

机械臂基座坐标系，原点位于机械臂 Base 基座中心：

| 坐标轴 | 方向 | 说明         |
| ------ | ---- | ------------ |
| X      | 向前 | 机械臂正前方 |
| Y      | 向左 | 机械臂左侧   |
| Z      | 向上 | 垂直向上     |

### arm_base 与 base_link 的关系

机械臂基座与机器人底盘 base_link 之间存在绕 Z 轴 180° 的安装偏差：

```
arm_x = -base_link_x
arm_y = -base_link_y
arm_z =  base_link_z
```

此变换在 `arm_control_server.py` 中完成。

---

## 坐标范围

| 坐标轴 | 范围               | 说明         |
| ------ | ------------------ | ------------ |
| X,Y    | X² + Y² < 570      | 工作空间约束 |
| Y      | \|Y\| > 280        | Y 轴限制     |
| Z      | -150 ~ 150         | Z 轴范围     |

---

## 通信参数

| 参数   | 值               |
| ------ | ---------------- |
| 串口   | `/dev/arm_port` (udev 绑定) |
| 波特率 | `115200`         |
| 数据位 | 8                |
| 停止位 | 1                |
| 校验位 | 无               |

### udev 串口绑定

为防止插拔后设备名变化，通过 udev 规则将物理 USB 端口绑定为固定名称：

```bash
# /etc/udev/rules.d/99-arm-port.rules
SUBSYSTEM=="tty", ENV{ID_PATH}=="pci-0000:00:14.0-usb-0:1.2:1.0", SYMLINK+="arm_port"
```

---

## ROS2 系统架构

```
map_goal (PoseStamped)
    │
    ▼
arm_control_server.py          ← Action Server, tf2 坐标变换
    │  map → base_link → arm_base
    │  /arm_command (Float64MultiArray [x,y,z,yaw,action], mm)
    ▼
serial_cmd_sender (C++)        ← 串口驱动节点
    │  FD FD 07 ctrl X Y Z CHK  ──►  下位机
    │  ◄──  FE FE 03 state result CHK
    │  /arm_status (UInt8MultiArray [state, result])
    ▼
arm_control_server.py          ← 等待 ACK，判断成功/失败
```

### ROS2 话题

| 话题          | 类型                  | 方向            | 说明                            |
| ------------- | --------------------- | --------------- | ------------------------------- |
| `/arm_command`| `Float64MultiArray`   | → 下位机         | [x,y,z,yaw,action], xyz 单位 mm |
| `/arm_status` | `UInt8MultiArray`     | ← 下位机         | [state, result] ACK 状态回报     |

### `/arm_command` 数据格式

| 索引 | 字段   | 单位 | 说明                  |
| ---- | ------ | ---- | --------------------- |
| 0    | x      | mm   | arm_base 坐标系 X     |
| 1    | y      | mm   | arm_base 坐标系 Y     |
| 2    | z      | mm   | arm_base 坐标系 Z     |
| 3    | yaw    | rad  | 偏航角（备用）        |
| 4    | action | -    | 1=Pick(吸取), 2=Place(放置) |

---

## 节点信息

| 项           | 值                   |
| ------------ | -------------------- |
| C++ 节点     | `serial_cmd_sender`  |
| Python 节点  | `arm_control_server` |
| 串口库       | `serial_driver`      |

---

## ROS2 使用示例

### 发送吸取命令 (Float64MultiArray, mm)

```bash
ros2 topic pub --once /arm_command std_msgs/msg/Float64MultiArray "{data: [0.0, 350.0, 50.0, 0.0, 1.0]}"
```

### 发送放置命令 (Float64MultiArray, mm)

```bash
ros2 topic pub --once /arm_command std_msgs/msg/Float64MultiArray "{data: [0.0, 350.0, 50.0, 0.0, 2.0]}"
```

### 查看 ACK 状态

```bash
ros2 topic echo /arm_status
```

---

## 启动方式

```bash
# 使用 udev 绑定端口
ros2 run serial_driver serial_cmd_sender --ros-args -p port:=/dev/arm_port

# 或直接指定物理端口
ros2 run serial_driver serial_cmd_sender --ros-args -p port:=/dev/ttyUSB5
```

---

## 设计说明

- **ACK 握手**: 下位机完成动作后发送 ACK 帧，上位机 `arm_control_server` 等待 ACK 确认成功/失败
- **防重复 ACK**: 每次发送命令前自动清空串口接收缓冲区，防止上一次残留 ACK 干扰
- **ACK 轮询**: `serial_cmd_sender` 以 10Hz 非阻塞轮询串口，解析到有效 ACK 后发布到 `/arm_status`
- **坐标系**: 上位机完成 map → base_link → arm_base 两级变换，下位机接收的坐标已在 arm_base 系
