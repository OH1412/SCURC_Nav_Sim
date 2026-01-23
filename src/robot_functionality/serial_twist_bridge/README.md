# Serial Twist Bridge

[![ROS 2 Humble](https://img.shields.io/badge/ROS2-Humble-22314E.svg)](https://docs.ros.org/en/humble/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

## 📖 概述

Serial Twist Bridge 是 SCURC 机器人导航仿真系统中的串口通信桥接包，专门用于接收 `teleop_twist_keyboard` 或其他节点的 Twist 消息，并通过串口将控制指令转发给 MCU（微控制器）。该包实现了 ROS 2 环境与嵌入式系统的无缝通信。

### 🎯 主要功能

- **🔄 Twist消息桥接**: 订阅 `/cmd_vel` 话题的 Twist 消息
- **📡 串口通信**: 支持多种波特率和串口设备的通信
- **🎮 键盘控制支持**: 完美配合 `teleop_twist_keyboard` 使用
- **🔧 MCU集成**: 提供标准化的串口协议格式
- **📊 调试支持**: 实时输出调试信息和通信状态

---

## 🏗️ 系统架构

### 数据流

```
teleop_twist_keyboard ── Twist消息 ── Serial Bridge ── 串口协议 ── MCU
        │                        │                        │
        └─ 键盘输入              └─ ROS2节点              └─ 硬件控制
```

### 数据格式详细说明

#### 1. ROS输入数据格式 (geometry_msgs/Twist)

串口桥接节点订阅的标准ROS Twist消息：

```yaml
# geometry_msgs/Twist 消息结构
linear:
  x: float64  # 前进/后退线速度 (m/s)，正值前进，负值后退
  y: float64  # 左右平移线速度 (m/s)，正值右移，负值左移
  z: float64  # 上下移动线速度 (m/s)，通常为0

angular:
  x: float64  # 绕X轴角速度 (rad/s)，通常为0
  y: float64  # 绕Y轴角速度 (rad/s)，通常为0
  z: float64  # 绕Z轴角速度 (rad/s)，正值逆时针，负值顺时针

# teleop_twist_keyboard 默认参数：
# - 最大线速度: 0.5 m/s
# - 最大角速度: 1.0 rad/s
# - 发布频率: 10 Hz
```

**Twist消息示例**:
- 前进: `linear.x = 0.5, angular.z = 0.0`
- 左转: `linear.x = 0.0, angular.z = 1.0`
- 右转: `linear.x = 0.0, angular.z = -1.0`
- 停止: `linear.x = 0.0, angular.z = 0.0`

#### 2. 串口输出数据格式

发送给MCU的ASCII字符串格式：
```
格式: Vx,Vy,Vz,Wx,Wy,Wz\r\n
```

**字段说明**:
- `Vx`: 线速度X分量，范围通常 -0.5 ~ +0.5 m/s
- `Vy`: 线速度Y分量，范围通常 -0.5 ~ +0.5 m/s
- `Vz`: 线速度Z分量，通常为0.0
- `Wx`: 角速度X分量，通常为0.0
- `Wy`: 角速度Y分量，通常为0.0
- `Wz`: 角速度Z分量，范围通常 -1.0 ~ +1.0 rad/s

**实际示例**:
```
0.500,0.000,0.000,0.000,0.000,0.000\r\n  # 前进
0.000,0.000,0.000,0.000,0.000,1.000\r\n  # 原地左转
-0.200,0.000,0.000,0.000,0.000,-0.500\r\n # 后退右转
0.000,0.000,0.000,0.000,0.000,0.000\r\n  # 停止
```

**格式特点**:
- 使用逗号分隔的6个浮点数
- 3位小数精度 (%.3f)
- 以 `\r\n` (CRLF) 结尾，便于MCU解析
- ASCII编码，无需考虑字节序问题

---

## 📋 系统要求

- **操作系统**: Ubuntu 22.04 LTS
- **ROS版本**: ROS 2 Humble Hawksbill
- **依赖包**: `rclcpp`, `geometry_msgs`, `std_msgs`
- **串口设备**: 支持标准POSIX串口设备

---

## ⚡ 快速开始 (3分钟上手)

### 场景1: 使用Arduino测试

```bash
# 1. 编译包
colcon build --packages-select serial_twist_bridge --symlink-install
source install/setup.bash

# 2. 启动串口桥接 (Arduino通常是ttyACM0, 9600波特率)
ros2 launch serial_twist_bridge serial_bridge.launch.py \
  serial_device:=/dev/ttyACM0 \
  baud_rate:=9600

# 3. 新终端启动键盘控制
ros2 run teleop_twist_keyboard teleop_twist_keyboard

# 4. 开始控制: 按 'i' 前进, 'j' 左转, 'l' 右转, 'k' 停止
```

### 场景2: 使用ESP32/STM32

```bash
# 启动串口桥接 (ESP32通常是ttyUSB0, 115200波特率)
ros2 launch serial_twist_bridge serial_bridge.launch.py \
  serial_device:=/dev/ttyUSB0 \
  baud_rate:=115200

# 然后启动键盘控制...
```

### 场景3: 与导航系统集成

```bash
# 启动完整导航系统
ros2 launch r2_bringup dynamic_waypoint_mission.launch.py

# 串口桥接会自动接收导航产生的速度指令
ros2 launch serial_twist_bridge serial_bridge.launch.py
```

### 验证成功

启动后，你应该看到：
1. 串口桥接节点正常启动，无错误信息
2. 键盘控制启动后显示操作说明
3. 按键时在串口桥接终端看到"Sent: 0.500,0.000,..."格式的调试信息

---

## 🚀 使用指南

### 1. 编译安装

```bash
# 编译整个工作空间
colcon build --packages-select serial_twist_bridge --symlink-install

# 加载环境
source install/setup.bash
```

### 2. 串口设备准备

在使用前，请确保串口设备正确连接并设置权限：

```bash
# 检查串口设备
ls /dev/tty*

# 添加用户到dialout组（一次性设置）
sudo usermod -a -G dialout $USER

# 临时设置串口权限（如果需要）
sudo chmod 666 /dev/ttyUSB0

# 重新登录终端使组权限生效
```

### 3. teleop_twist_keyboard 键盘控制使用说明

#### 3.1 安装 teleop_twist_keyboard

如果系统中没有安装 `teleop_twist_keyboard`：

```bash
# Ubuntu/Debian
sudo apt install ros-humble-teleop-twist-keyboard

# 或从源码编译
sudo apt install ros-humble-teleop-tools
```

#### 3.2 teleop_twist_keyboard 控制说明

启动键盘控制后，使用以下按键控制机器人：

```
移动控制:
   u    i    o
   j    k    l
   m    ,    .

前进/后退:
   i: 前进
   ,: 后退
   j: 左转
   l: 右转

速度控制:
   q/z : 增加/减少最大速度 (m/s)
   w/x : 增加/减少最大角速度 (rad/s)

特殊按键:
   k: 强制停止
   space: 强制停止
   CTRL-C: 退出
```

#### 3.3 默认参数说明

- **线速度**: 默认最大 0.5 m/s
- **角速度**: 默认最大 1.0 rad/s
- **发布频率**: 10 Hz
- **发布话题**: `/cmd_vel` (geometry_msgs/Twist)

### 4. 启动串口桥接

#### 基本启动（推荐用于测试）
```bash
# 使用默认参数启动
ros2 launch serial_twist_bridge serial_bridge.launch.py
```

#### 自定义参数启动
```bash
# 指定串口设备和波特率
ros2 launch serial_twist_bridge serial_bridge.launch.py \
  serial_device:=/dev/ttyACM0 \
  baud_rate:=9600 \
  twist_topic:=/cmd_vel
```

#### 不同MCU设备的配置示例

```bash
# Arduino Uno (通常使用 /dev/ttyACM0, 9600波特率)
ros2 launch serial_twist_bridge serial_bridge.launch.py \
  serial_device:=/dev/ttyACM0 \
  baud_rate:=9600

# ESP32/STM32 (通常使用 /dev/ttyUSB0, 115200波特率)
ros2 launch serial_twist_bridge serial_bridge.launch.py \
  serial_device:=/dev/ttyUSB0 \
  baud_rate:=115200

# Teensy (通常使用 /dev/ttyACM0, 高波特率)
ros2 launch serial_twist_bridge serial_bridge.launch.py \
  serial_device:=/dev/ttyACM0 \
  baud_rate:=2000000
```

### 5. 完整使用流程

#### 步骤1: 硬件连接
- 将MCU通过USB连接到电脑
- 确认串口设备路径（`/dev/ttyUSB0` 或 `/dev/ttyACM0`）

#### 步骤2: 启动串口桥接
```bash
# 终端1: 启动串口桥接
ros2 launch serial_twist_bridge serial_bridge.launch.py
```

#### 步骤3: 启动键盘控制
```bash
# 终端2: 启动键盘控制
ros2 run teleop_twist_keyboard teleop_twist_keyboard

# 或者使用自定义参数
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args \
  -p speed:=1.0 \
  -p turn:=2.0 \
  -p repeat_rate:=20.0
```

#### 步骤4: 开始控制
- 在键盘控制终端按 `i` 开始前进
- 观察串口桥接终端的调试输出
- MCU应该接收到格式化的速度指令

### 6. 直接运行节点（高级用法）

```bash
# 直接运行可执行文件
ros2 run serial_twist_bridge serial_bridge_node --ros-args \
  -p serial_device:=/dev/ttyUSB0 \
  -p baud_rate:=115200 \
  -p twist_topic:=/cmd_vel
```

### 7. 与其他控制节点配合

串口桥接不仅可以与 `teleop_twist_keyboard` 配合，还可以与其他发布 Twist 消息的节点一起使用：

```bash
# 与导航系统配合
ros2 launch r2_bringup navigation.launch.py  # 启动Nav2导航

# 串口桥接会自动接收导航产生的 /cmd_vel 消息
ros2 launch serial_twist_bridge serial_bridge.launch.py
```

```bash
# 与自定义控制节点配合
ros2 run my_control_package my_controller_node  # 发布到 /cmd_vel

ros2 launch serial_twist_bridge serial_bridge.launch.py \
  twist_topic:=/cmd_vel  # 指定订阅话题
```

---

## ⚙️ 参数配置

### 核心参数

| 参数 | 默认值 | 说明 | 推荐值 |
|------|--------|------|--------|
| `serial_device` | `/dev/ttyUSB0` | 串口设备路径 | `/dev/ttyACM0` (Arduino), `/dev/ttyUSB0` (USB串口) |
| `baud_rate` | `115200` | 串口波特率 | 9600-2000000，根据MCU能力选择 |
| `twist_topic` | `/cmd_vel` | 订阅的Twist话题 | `/cmd_vel` (标准), `/teleop/cmd_vel` (自定义) |
| `publish_rate` | `50.0` | 发布频率 (Hz) | 10-100，根据控制需求调整 |

### 支持的波特率

#### 标准波特率（推荐）
- **9600**: Arduino基础通信，稳定可靠
- **19200**: 一般嵌入式系统
- **38400**: 中等速度通信
- **57600**: 高速嵌入式通信
- **115200**: 默认值，平衡速度和稳定性

#### 高速波特率（高级应用）
- **230400**: 高速数据传输
- **460800**: 非常高速
- **500000**: USB原生高速率
- **921600**: 极高速率
- **1000000-4000000**: 专业高速串口设备

### MCU兼容性配置

#### Arduino Uno/Nano
```bash
ros2 launch serial_twist_bridge serial_bridge.launch.py \
  serial_device:=/dev/ttyACM0 \
  baud_rate:=9600
```

#### ESP32/STM32
```bash
ros2 launch serial_twist_bridge serial_bridge.launch.py \
  serial_device:=/dev/ttyUSB0 \
  baud_rate:=115200
```

#### Teensy/Raspberry Pi Pico
```bash
ros2 launch serial_twist_bridge serial_bridge.launch.py \
  serial_device:=/dev/ttyACM0 \
  baud_rate:=2000000
```

---

## 🔧 开发与调试

### 调试信息

节点会发布调试信息到 `/serial_bridge/debug` 话题：

```bash
# 监控调试信息
ros2 topic echo /serial_bridge/debug
```

### 串口权限设置

```bash
# 添加用户到dialout组
sudo usermod -a -G dialout $USER

# 重新登录或重启终端
# 检查串口权限
ls -la /dev/ttyUSB0
```

### MCU串口读取和解析指南

#### 串口配置要求

**必须与ROS节点保持一致**:
```cpp
// Arduino 示例
#define BAUD_RATE 115200  // 必须与ROS launch文件中的baud_rate参数一致
#define SERIAL_PORT Serial // 对于Arduino Uno/Nano
// #define SERIAL_PORT Serial1 // 对于Arduino Mega (多个串口)

void setup() {
  SERIAL_PORT.begin(BAUD_RATE);
  while (!SERIAL_PORT) {
    ; // 等待串口连接 (Arduino Leonardo/Micro等)
  }
}
```

**ESP32串口配置**:
```cpp
// ESP32 Arduino Framework
HardwareSerial SerialPort(2); // 使用UART2

void setup() {
  Serial.begin(115200);     // USB调试串口
  SerialPort.begin(115200, SERIAL_8N1, 16, 17); // GPIO16=RX, GPIO17=TX
}
```

#### 数据接收策略

**方法1: 按行读取 (推荐)**

```cpp
// Arduino 按行读取示例
String receivedData = "";

void loop() {
  while (SERIAL_PORT.available()) {
    char incomingChar = SERIAL_PORT.read();

    if (incomingChar == '\n') {
      // 收到完整行，处理数据
      processTwistData(receivedData);
      receivedData = ""; // 清空缓冲区
    } else if (incomingChar != '\r') { // 忽略回车符
      receivedData += incomingChar;
    }
  }
}
```

**方法2: 超时读取**

```cpp
// 带超时的读取示例
#define READ_TIMEOUT 100  // 100ms超时

String readLineWithTimeout() {
  String data = "";
  unsigned long startTime = millis();

  while (millis() - startTime < READ_TIMEOUT) {
    if (SERIAL_PORT.available()) {
      char c = SERIAL_PORT.read();
      if (c == '\n') {
        return data; // 返回不含换行符的数据
      } else if (c != '\r') {
        data += c;
      }
      startTime = millis(); // 重置超时计时器
    }
  }
  return ""; // 超时返回空字符串
}
```

#### 数据解析和验证

**标准解析函数**:

```cpp
// 安全的Twist数据解析函数
struct TwistData {
  float vx, vy, vz;    // 线速度 (m/s)
  float wx, wy, wz;    // 角速度 (rad/s)
  bool valid;          // 数据是否有效
};

TwistData parseTwistString(String data) {
  TwistData result = {0, 0, 0, 0, 0, 0, false};

  // 验证数据格式 (应该有5个逗号，分割成6个数字)
  int commaCount = 0;
  for (char c : data) {
    if (c == ',') commaCount++;
  }

  if (commaCount != 5) {
    SERIAL_PORT.println("ERROR: Invalid comma count: " + String(commaCount));
    return result;
  }

  // 解析6个浮点数
  int parsed = sscanf(data.c_str(), "%f,%f,%f,%f,%f,%f",
                      &result.vx, &result.vy, &result.vz,
                      &result.wx, &result.wy, &result.wz);

  if (parsed == 6) {
    // 验证数据范围 (可选)
    if (abs(result.vx) > 2.0 || abs(result.vy) > 2.0 || abs(result.wz) > 5.0) {
      SERIAL_PORT.println("WARNING: Values out of expected range");
      // 可以选择不标记为无效，继续使用
    }

    result.valid = true;
    return result;
  } else {
    SERIAL_PORT.println("ERROR: Failed to parse 6 floats from: " + data);
    return result;
  }
}
```

**完整使用示例**:

```cpp
// 全局变量
TwistData currentTwist = {0, 0, 0, 0, 0, 0, false};
unsigned long lastReceiveTime = 0;
const unsigned long TIMEOUT_MS = 500; // 500ms超时

void loop() {
  // 读取串口数据
  if (SERIAL_PORT.available()) {
    String line = SERIAL_PORT.readStringUntil('\n');
    line.trim(); // 移除空白字符

    if (line.length() > 0) {
      currentTwist = parseTwistString(line);
      lastReceiveTime = millis();

      if (currentTwist.valid) {
        // 数据有效，控制电机
        controlMotors(currentTwist.vx, currentTwist.vy, currentTwist.wz);

        // 可选: 发送确认信息
        // SERIAL_PORT.println("OK");
      }
    }
  }

  // 超时检测
  if (millis() - lastReceiveTime > TIMEOUT_MS) {
    // 超过500ms没有收到数据，停止机器人
    stopMotors();
    currentTwist.valid = false;
  }

  // 其他任务...
  delay(10); // 小延迟避免CPU占用过高
}
```

#### 错误处理和调试

**调试输出建议**:

```cpp
#define DEBUG_MODE true

void processTwistData(String data) {
  if (DEBUG_MODE) {
    SERIAL_PORT.print("Received: ");
    SERIAL_PORT.println(data);
  }

  TwistData twist = parseTwistString(data);

  if (DEBUG_MODE) {
    if (twist.valid) {
      SERIAL_PORT.printf("Parsed: vx=%.3f, vy=%.3f, wz=%.3f\n",
                        twist.vx, twist.vy, twist.wz);
    } else {
      SERIAL_PORT.println("Parse failed!");
    }
  }

  if (twist.valid) {
    controlMotors(twist.vx, twist.vy, twist.wz);
  }
}
```

#### 性能优化建议

1. **缓冲区大小**: 根据你的MCU内存调整接收缓冲区
2. **解析频率**: 避免在每个循环中都进行复杂的字符串操作
3. **数据验证**: 添加合理的数据范围检查
4. **超时处理**: 实现适当的通信超时机制
5. **确认机制**: 可选实现数据接收确认

### MCU端协议解析示例

#### Arduino完整示例

```cpp
// Arduino Serial Twist Bridge - 完整示例
// 兼容 Arduino Uno, Nano, Mega 等

// 引脚定义 (根据你的硬件修改)
#define LED_PIN 13
#define MOTOR_ENA 5   // PWM引脚
#define MOTOR_ENB 6   // PWM引脚
#define MOTOR_IN1 7   // 方向引脚
#define MOTOR_IN2 8   // 方向引脚
#define MOTOR_IN3 9   // 方向引脚
#define MOTOR_IN4 10  // 方向引脚

// 串口配置
#define BAUD_RATE 115200  // 必须与ROS节点一致
#define SERIAL_TIMEOUT 500 // 500ms超时

// 全局变量
struct TwistData {
  float vx, vy, vz;    // 线速度 (m/s)
  float wx, wy, wz;    // 角速度 (rad/s)
} currentTwist = {0};

unsigned long lastReceiveTime = 0;
bool dataValid = false;

void setup() {
  // 初始化串口
  Serial.begin(BAUD_RATE);
  while (!Serial) {
    ; // 等待串口就绪 (Leonardo/Micro)
  }

  // 初始化LED
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  // 初始化电机引脚
  pinMode(MOTOR_ENA, OUTPUT);
  pinMode(MOTOR_ENB, OUTPUT);
  pinMode(MOTOR_IN1, OUTPUT);
  pinMode(MOTOR_IN2, OUTPUT);
  pinMode(MOTOR_IN3, OUTPUT);
  pinMode(MOTOR_IN4, OUTPUT);

  // 停止所有电机
  stopMotors();

  Serial.println("Serial Twist Bridge Ready");
}

void loop() {
  // 读取串口数据
  readSerialData();

  // 超时检测
  checkTimeout();

  // 控制电机
  if (dataValid) {
    controlMotors(currentTwist.vx, currentTwist.vy, currentTwist.wz);
    digitalWrite(LED_PIN, HIGH); // 数据有效指示
  } else {
    stopMotors();
    digitalWrite(LED_PIN, LOW); // 无数据指示
  }

  delay(10); // 控制循环频率
}

void readSerialData() {
  static String buffer = "";

  while (Serial.available()) {
    char c = Serial.read();

    if (c == '\n') {
      // 收到完整行
      buffer.trim();

      if (parseTwistData(buffer)) {
        lastReceiveTime = millis();
        dataValid = true;

        // 调试输出 (可选)
        Serial.print("Parsed: vx=");
        Serial.print(currentTwist.vx, 3);
        Serial.print(", vy=");
        Serial.print(currentTwist.vy, 3);
        Serial.print(", wz=");
        Serial.println(currentTwist.wz, 3);
      } else {
        Serial.println("Parse error: " + buffer);
        dataValid = false;
      }

      buffer = ""; // 清空缓冲区
    } else if (c != '\r') { // 忽略回车符
      buffer += c;

      // 防止缓冲区溢出
      if (buffer.length() > 64) {
        buffer = "";
        Serial.println("Buffer overflow");
      }
    }
  }
}

bool parseTwistData(String data) {
  // 验证格式：应该有5个逗号
  int commaCount = 0;
  for (char c : data) {
    if (c == ',') commaCount++;
  }

  if (commaCount != 5) {
    return false;
  }

  // 解析6个浮点数
  int parsed = sscanf(data.c_str(), "%f,%f,%f,%f,%f,%f",
                      &currentTwist.vx, &currentTwist.vy, &currentTwist.vz,
                      &currentTwist.wx, &currentTwist.wy, &currentTwist.wz);

  return (parsed == 6);
}

void checkTimeout() {
  if (millis() - lastReceiveTime > SERIAL_TIMEOUT) {
    dataValid = false;
  }
}

void controlMotors(float vx, float vy, float wz) {
  // 简单的差分驱动控制示例
  // vx: 前进/后退速度 (-1.0 ~ 1.0)
  // vy: 左右平移速度 (暂时忽略，差分驱动不支持)
  // wz: 旋转角速度 (-1.0 ~ 1.0)

  // 计算左右轮速度
  float leftSpeed = vx - wz;   // 左轮
  float rightSpeed = vx + wz;  // 右轮

  // 限制速度范围
  leftSpeed = constrain(leftSpeed, -1.0, 1.0);
  rightSpeed = constrain(rightSpeed, -1.0, 1.0);

  // 转换为PWM值 (0-255)
  int leftPWM = abs(leftSpeed) * 255;
  int rightPWM = abs(rightSpeed) * 255;

  // 控制左轮
  if (leftSpeed > 0.01) {
    // 前进
    digitalWrite(MOTOR_IN1, HIGH);
    digitalWrite(MOTOR_IN2, LOW);
    analogWrite(MOTOR_ENA, leftPWM);
  } else if (leftSpeed < -0.01) {
    // 后退
    digitalWrite(MOTOR_IN1, LOW);
    digitalWrite(MOTOR_IN2, HIGH);
    analogWrite(MOTOR_ENA, leftPWM);
  } else {
    // 停止
    digitalWrite(MOTOR_IN1, LOW);
    digitalWrite(MOTOR_IN2, LOW);
    analogWrite(MOTOR_ENA, 0);
  }

  // 控制右轮
  if (rightSpeed > 0.01) {
    // 前进
    digitalWrite(MOTOR_IN3, HIGH);
    digitalWrite(MOTOR_IN4, LOW);
    analogWrite(MOTOR_ENB, rightPWM);
  } else if (rightSpeed < -0.01) {
    // 后退
    digitalWrite(MOTOR_IN3, LOW);
    digitalWrite(MOTOR_IN4, HIGH);
    analogWrite(MOTOR_ENB, rightPWM);
  } else {
    // 停止
    digitalWrite(MOTOR_IN3, LOW);
    digitalWrite(MOTOR_IN4, LOW);
    analogWrite(MOTOR_ENB, 0);
  }
}

void stopMotors() {
  // 停止所有电机
  digitalWrite(MOTOR_IN1, LOW);
  digitalWrite(MOTOR_IN2, LOW);
  digitalWrite(MOTOR_IN3, LOW);
  digitalWrite(MOTOR_IN4, LOW);
  analogWrite(MOTOR_ENA, 0);
  analogWrite(MOTOR_ENB, 0);
}
```

#### ESP32 Arduino Framework

```cpp
// ESP32 Serial Twist Bridge - 完整示例
// 支持WiFi调试、多核处理、高精度控制

#include <HardwareSerial.h>

// ESP32串口配置
HardwareSerial SerialPort(2); // UART2 (UART0被USB占用)
#define RX_PIN 16             // GPIO16
#define TX_PIN 17             // GPIO17
#define BAUD_RATE 115200

// 任务句柄 (用于双核处理)
TaskHandle_t serialTaskHandle;
TaskHandle_t motorTaskHandle;

// 共享数据 (需要互斥锁保护)
struct TwistData {
  float vx, vy, vz;
  float wx, wy, wz;
  bool updated;
} sharedTwist;

SemaphoreHandle_t twistMutex;

// LED引脚
#define LED_PIN 2

void setup() {
  // 初始化USB串口 (用于调试)
  Serial.begin(115200);
  delay(1000); // 等待串口稳定

  // 初始化硬件串口
  SerialPort.begin(BAUD_RATE, SERIAL_8N1, RX_PIN, TX_PIN);
  Serial.println("ESP32 Serial Twist Bridge Starting...");

  // 初始化LED
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  // 初始化互斥锁
  twistMutex = xSemaphoreCreateMutex();

  // 初始化共享数据
  sharedTwist = {0, 0, 0, 0, 0, 0, false};

  // 创建FreeRTOS任务
  xTaskCreatePinnedToCore(
    serialTask,      // 任务函数
    "SerialTask",    // 任务名称
    4096,            // 栈大小
    NULL,            // 参数
    1,               // 优先级
    &serialTaskHandle, // 任务句柄
    0                // 在核心0上运行
  );

  xTaskCreatePinnedToCore(
    motorTask,       // 任务函数
    "MotorTask",     // 任务名称
    4096,            // 栈大小
    NULL,            // 参数
    2,               // 更高优先级
    &motorTaskHandle, // 任务句柄
    1                // 在核心1上运行
  );

  Serial.println("ESP32 Serial Twist Bridge Ready!");
}

// 串口接收任务 (核心0)
void serialTask(void *pvParameters) {
  static String buffer = "";

  while (true) {
    while (SerialPort.available()) {
      char c = SerialPort.read();

      if (c == '\n') {
        buffer.trim();

        // 获取互斥锁
        if (xSemaphoreTake(twistMutex, portMAX_DELAY) == pdTRUE) {
          if (parseTwistData(buffer, sharedTwist)) {
            sharedTwist.updated = true;
            Serial.printf("[SERIAL] Parsed: vx=%.3f, vy=%.3f, wz=%.3f\n",
                         sharedTwist.vx, sharedTwist.vy, sharedTwist.wz);
          } else {
            Serial.println("[SERIAL] Parse error: " + buffer);
          }
          xSemaphoreGive(twistMutex);
        }

        buffer = "";
      } else if (c != '\r') {
        buffer += c;
        if (buffer.length() > 64) {
          buffer = "";
        }
      }
    }

    vTaskDelay(pdMS_TO_TICKS(10)); // 10ms延迟
  }
}

// 电机控制任务 (核心1)
void motorTask(void *pvParameters) {
  static unsigned long lastUpdate = 0;

  while (true) {
    // 检查是否有新数据
    if (xSemaphoreTake(twistMutex, portMAX_DELAY) == pdTRUE) {
      if (sharedTwist.updated) {
        controlMotorsESP32(sharedTwist.vx, sharedTwist.vy, sharedTwist.wz);
        sharedTwist.updated = false;
        lastUpdate = millis();
        digitalWrite(LED_PIN, HIGH); // 数据更新指示
      }
      xSemaphoreGive(twistMutex);
    }

    // 超时检测
    if (millis() - lastUpdate > 500) {
      stopMotorsESP32();
      digitalWrite(LED_PIN, LOW); // 超时指示
    }

    vTaskDelay(pdMS_TO_TICKS(20)); // 50Hz控制频率
  }
}

bool parseTwistData(String data, TwistData& twist) {
  int commaCount = 0;
  for (char c : data) {
    if (c == ',') commaCount++;
  }

  if (commaCount != 5) return false;

  int parsed = sscanf(data.c_str(), "%f,%f,%f,%f,%f,%f",
                      &twist.vx, &twist.vy, &twist.vz,
                      &twist.wx, &twist.wy, &twist.wz);

  return (parsed == 6);
}

void controlMotorsESP32(float vx, float vy, float wz) {
  // ESP32的高级电机控制实现
  // 这里可以集成更复杂的控制算法
  // vx: 线速度 (m/s)
  // vy: 横向速度 (m/s) - 全向轮支持
  // wz: 角速度 (rad/s)

  // 示例：简单的PWM输出
  // 你需要根据你的硬件添加具体的电机控制代码

  Serial.printf("[MOTOR] Control: vx=%.3f, vy=%.3f, wz=%.3f\n", vx, vy, wz);
}

void stopMotorsESP32() {
  // 停止所有电机
  Serial.println("[MOTOR] Emergency stop - timeout");
}
```

void loop() {
  // ESP32的主循环可以处理其他任务
  // 实际的串口和电机控制都在FreeRTOS任务中处理

  static unsigned long lastPrint = 0;
  if (millis() - lastPrint > 5000) { // 每5秒打印状态
    Serial.println("[MAIN] ESP32 Serial Twist Bridge running...");
    lastPrint = millis();
  }

  delay(1000);
}
```

#### STM32 HAL Library

```c
// STM32 Serial Twist Bridge 示例
#include "usart.h"

// UART接收缓冲区
uint8_t rx_buffer[64];
uint8_t rx_index = 0;

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart) {
    if (huart->Instance == USART1) {
        if (rx_buffer[rx_index] == '\n') {
            // 处理完整消息
            rx_buffer[rx_index] = '\0'; // 替换换行符

            float vx, vy, vz, wx, wy, wz;
            int parsed = sscanf((char*)rx_buffer, "%f,%f,%f,%f,%f,%f",
                               &vx, &vy, &vz, &wx, &wy, &wz);

            if (parsed == 6) {
                // STM32电机控制
                MotorControl_SetSpeed(vx, vy, wz);
                HAL_GPIO_WritePin(LED_GPIO_Port, LED_Pin, GPIO_PIN_SET);
            }

            rx_index = 0; // 重置缓冲区
        } else {
            rx_index++;
            if (rx_index >= sizeof(rx_buffer)) {
                rx_index = 0; // 缓冲区溢出重置
            }
        }

        // 继续接收
        HAL_UART_Receive_IT(huart, &rx_buffer[rx_index], 1);
    }
}

void MotorControl_SetSpeed(float vx, float vy, float wz) {
    // STM32电机控制实现
    // vx: 线速度 (m/s)
    // vy: 横向速度 (m/s)
    // wz: 角速度 (rad/s)
}
```

#### Infineon TC264 (AURIX)

```c
// Infineon TC264 Serial Twist Bridge - 使用iLLD驱动库
// 基于FreeRTOS操作系统，支持实时任务调度

#include "Ifx_Types.h"
#include "IfxCpu.h"
#include "IfxScuWdt.h"
#include "IfxAsclin_Asc.h"
#include "IfxPort.h"
#include "IfxGtm_Tom_Pwm.h"
#include "IfxGtm_Cmu.h"
#include "FreeRTOS.h"
#include "task.h"
#include "semphr.h"

// UART配置 (ASCLIN0 - P14.0 RX, P14.1 TX)
#define UART_BAUDRATE     115200
#define UART_RX_BUFFER_SIZE 128
#define UART_TX_BUFFER_SIZE 128

// 电机PWM配置 (GTM_TOM)
// 左轮: P02.0 (TOM0_CH0), P02.1 (TOM0_CH1) - 方向控制
// 右轮: P02.2 (TOM0_CH2), P02.3 (TOM0_CH3) - 方向控制
#define PWM_FREQUENCY     20000  // 20kHz PWM

// 全局变量
typedef struct {
    float vx, vy, vz;    // 线速度 (m/s)
    float wx, wy, wz;    // 角速度 (rad/s)
    boolean updated;     // 数据更新标志
} TwistData;

TwistData g_TwistData = {0};
SemaphoreHandle_t g_TwistMutex;
TaskHandle_t g_SerialTaskHandle;
TaskHandle_t g_MotorTaskHandle;

// UART句柄和缓冲区
IfxAsclin_Asc g_UartHandle;
uint8 g_RxBuffer[UART_RX_BUFFER_SIZE];
uint8 g_TxBuffer[UART_TX_BUFFER_SIZE];
uint32 g_RxIndex = 0;

// PWM句柄
IfxGtm_Tom_Pwm_Driver g_LeftPwmDriver;
IfxGtm_Tom_Pwm_Driver g_RightPwmDriver;

// 函数声明
void initHardware(void);
void initUART(void);
void initPWM(void);
void initRTOS(void);
void serialTask(void* pvParameters);
void motorTask(void* pvParameters);
boolean parseTwistData(const char* data, TwistData* twist);
void controlMotors(float vx, float vy, float wz);
void stopMotors(void);
void setMotorPWM(IfxGtm_Tom_Pwm_Driver* driver, float duty, boolean direction);

// UART接收中断回调
IFX_INTERRUPT(uartRxISR, 0, ISR_PRIORITY_UART_RX) {
    uint8 data = IfxAsclin_Asc_read(&g_UartHandle);

    if (data == '\n') {
        // 收到完整行
        g_RxBuffer[g_RxIndex] = '\0'; // 添加字符串结束符

        // 获取互斥锁
        if (xSemaphoreTake(g_TwistMutex, portMAX_DELAY) == pdPASS) {
            if (parseTwistData((const char*)g_RxBuffer, &g_TwistData)) {
                g_TwistData.updated = TRUE;

                // 可选: 通过UART发送确认
                // IfxAsclin_Asc_write(&g_UartHandle, (uint8*)"OK\r\n", 4, TIME_INFINITE);
            } else {
                // 解析失败，通过UART发送错误信息
                IfxAsclin_Asc_write(&g_UartHandle, (uint8*)"PARSE_ERROR\r\n", 13, TIME_INFINITE);
            }
            xSemaphoreGive(g_TwistMutex);
        }

        g_RxIndex = 0; // 重置缓冲区索引
    } else if (data != '\r') {
        // 存储数据（排除回车符）
        if (g_RxIndex < UART_RX_BUFFER_SIZE - 1) {
            g_RxBuffer[g_RxIndex++] = data;
        } else {
            // 缓冲区溢出，重置
            g_RxIndex = 0;
            IfxAsclin_Asc_write(&g_UartHandle, (uint8*)"BUFFER_OVERFLOW\r\n", 16, TIME_INFINITE);
        }
    }
}

void initHardware(void) {
    // 初始化SCU时钟
    IfxScuWdt_disableCpuWatchdog(IfxScuWdt_getCpuWatchdogPassword());
    IfxScuWdt_disableSafetyWatchdog(IfxScuWdt_getSafetyWatchdogPassword());

    // 初始化时钟
    IfxScuCcu_init(&IfxScuCcu_defaultClockConfig);

    // 初始化GPIO
    IfxPort_setPinMode(&MODULE_P14, 0, IfxPort_Mode_inputPullUp);    // UART RX
    IfxPort_setPinMode(&MODULE_P14, 1, IfxPort_Mode_outputPushPull); // UART TX

    // 初始化电机方向引脚
    IfxPort_setPinMode(&MODULE_P02, 0, IfxPort_Mode_outputPushPull); // 左轮PWM
    IfxPort_setPinMode(&MODULE_P02, 1, IfxPort_Mode_outputPushPull); // 左轮方向1
    IfxPort_setPinMode(&MODULE_P02, 2, IfxPort_Mode_outputPushPull); // 右轮PWM
    IfxPort_setPinMode(&MODULE_P02, 3, IfxPort_Mode_outputPushPull); // 右轮方向1
}

void initUART(void) {
    // UART配置
    IfxAsclin_Asc_Config uartConfig;
    IfxAsclin_Asc_initModuleConfig(&uartConfig, &MODULE_ASCLIN0);

    // FIFO配置
    uartConfig.rxBufferSize = UART_RX_BUFFER_SIZE;
    uartConfig.txBufferSize = UART_TX_BUFFER_SIZE;

    // 引脚配置
    const IfxAsclin_Asc_Pins pins = {
        &IfxAsclin0_RX_P14_1_IN,   // RX引脚
        &IfxAsclin0_TX_P14_0_OUT,  // TX引脚
        IfxPort_PadDriver_cmosAutomotiveSpeed1
    };
    uartConfig.pins = &pins;

    // 波特率配置
    uartConfig.baudrate.prescaler = 1;
    uartConfig.baudrate.baudrate = UART_BAUDRATE;
    uartConfig.baudrate.oversampling = IfxAsclin_OversamplingFactor_16;

    // 帧格式
    uartConfig.frame.dataLength = IfxAsclin_DataLength_8;
    uartConfig.frame.parityBit = FALSE;
    uartConfig.frame.stopBit = IfxAsclin_StopBit_1;

    // 中断配置
    uartConfig.interrupt.rxPriority = ISR_PRIORITY_UART_RX;
    uartConfig.interrupt.typeOfService = IfxSrc_Tos_cpu0;

    // 初始化UART
    IfxAsclin_Asc_initModule(&g_UartHandle, &uartConfig);

    // 配置接收中断
    IfxAsclin_Asc_enableRxFifoFillLevelFlag(&g_UartHandle, TRUE);
}

void initPWM(void) {
    // GTM时钟配置
    IfxGtm_enable(&MODULE_GTM);
    IfxGtm_Cmu_setGclkFrequency(&MODULE_GTM, IfxGtm_Cmu_Clk_0, 100000000); // 100MHz

    // 左轮PWM配置 (TOM0_CH0)
    IfxGtm_Tom_Pwm_Config leftPwmConfig;
    IfxGtm_Tom_Pwm_initConfig(&leftPwmConfig, &MODULE_GTM);

    leftPwmConfig.tom = IfxGtm_Tom_0;
    leftPwmConfig.tomChannel = IfxGtm_Tom_Ch_0;
    leftPwmConfig.period = 100000000 / PWM_FREQUENCY; // 计算周期值
    leftPwmConfig.dutyCycle = 0;
    leftPwmConfig.pin.outputPin = &IfxGtm_TOM0_0_TOUT0_P02_0_OUT;
    leftPwmConfig.synchronousUpdateEnabled = TRUE;

    IfxGtm_Tom_Pwm_init(&g_LeftPwmDriver, &leftPwmConfig);

    // 右轮PWM配置 (TOM0_CH2)
    IfxGtm_Tom_Pwm_Config rightPwmConfig;
    IfxGtm_Tom_Pwm_initConfig(&rightPwmConfig, &MODULE_GTM);

    rightPwmConfig.tom = IfxGtm_Tom_0;
    rightPwmConfig.tomChannel = IfxGtm_Tom_Ch_2;
    rightPwmConfig.period = 100000000 / PWM_FREQUENCY;
    rightPwmConfig.dutyCycle = 0;
    rightPwmConfig.pin.outputPin = &IfxGtm_TOM0_2_TOUT2_P02_2_OUT;
    rightPwmConfig.synchronousUpdateEnabled = TRUE;

    IfxGtm_Tom_Pwm_init(&g_RightPwmDriver, &rightPwmConfig);

    // 启动PWM
    IfxGtm_Tom_Pwm_start(&g_LeftPwmDriver, TRUE);
    IfxGtm_Tom_Pwm_start(&g_RightPwmDriver, TRUE);
}

void initRTOS(void) {
    // 创建互斥锁
    g_TwistMutex = xSemaphoreCreateMutex();

    // 创建串口任务
    xTaskCreate(serialTask, "SerialTask", 1024, NULL, 1, &g_SerialTaskHandle);

    // 创建电机控制任务
    xTaskCreate(motorTask, "MotorTask", 1024, NULL, 2, &g_MotorTaskHandle);

    // 启动调度器
    vTaskStartScheduler();
}

void serialTask(void* pvParameters) {
    TickType_t xLastWakeTime = xTaskGetTickCount();
    const TickType_t xFrequency = pdMS_TO_TICKS(10); // 100Hz

    while (1) {
        // 串口处理主要在中断中完成
        // 这里可以添加额外的串口监控逻辑

        vTaskDelayUntil(&xLastWakeTime, xFrequency);
    }
}

void motorTask(void* pvParameters) {
    TickType_t xLastWakeTime = xTaskGetTickCount();
    const TickType_t xFrequency = pdMS_TO_TICKS(20); // 50Hz控制频率
    static uint32 lastUpdateTime = 0;

    while (1) {
        // 检查是否有新数据
        if (xSemaphoreTake(g_TwistMutex, portMAX_DELAY) == pdPASS) {
            if (g_TwistData.updated) {
                controlMotors(g_TwistData.vx, g_TwistData.vy, g_TwistData.wz);
                g_TwistData.updated = FALSE;
                lastUpdateTime = xTaskGetTickCount();
            }
            xSemaphoreGive(g_TwistMutex);
        }

        // 超时检测 (500ms)
        if ((xTaskGetTickCount() - lastUpdateTime) > pdMS_TO_TICKS(500)) {
            stopMotors();
        }

        vTaskDelayUntil(&xLastWakeTime, xFrequency);
    }
}

boolean parseTwistData(const char* data, TwistData* twist) {
    int commaCount = 0;

    // 统计逗号数量
    for (const char* p = data; *p != '\0'; p++) {
        if (*p == ',') commaCount++;
    }

    if (commaCount != 5) {
        return FALSE;
    }

    // 解析6个浮点数
    int parsed = sscanf(data, "%f,%f,%f,%f,%f,%f",
                       &twist->vx, &twist->vy, &twist->vz,
                       &twist->wx, &twist->wy, &twist->wz);

    return (parsed == 6) ? TRUE : FALSE;
}

void controlMotors(float vx, float vy, float wz) {
    // 差分驱动计算
    float leftSpeed = vx - wz;   // 左轮速度
    float rightSpeed = vx + wz;  // 右轮速度

    // 限制速度范围 (-1.0 到 1.0)
    leftSpeed = (leftSpeed > 1.0f) ? 1.0f : (leftSpeed < -1.0f) ? -1.0f : leftSpeed;
    rightSpeed = (rightSpeed > 1.0f) ? 1.0f : (rightSpeed < -1.0f) ? -1.0f : rightSpeed;

    // 控制左轮
    setMotorPWM(&g_LeftPwmDriver, fabsf(leftSpeed), leftSpeed >= 0);

    // 控制右轮
    setMotorPWM(&g_RightPwmDriver, fabsf(rightSpeed), rightSpeed >= 0);
}

void setMotorPWM(IfxGtm_Tom_Pwm_Driver* driver, float duty, boolean direction) {
    // duty范围: 0.0-1.0
    uint32 pwmDuty = (uint32)(duty * 1000); // 转换为0-1000范围
    pwmDuty = (pwmDuty > 1000) ? 1000 : pwmDuty;

    // 设置PWM占空比
    IfxGtm_Tom_Pwm_setDutyCycle(driver, pwmDuty, 1000);

    // 设置方向 (这里需要根据你的硬件连接修改)
    // 例如: 设置方向引脚的高低电平
    // if (driver == &g_LeftPwmDriver) {
    //     IfxPort_setPinState(&MODULE_P02, 1, direction ? IfxPort_State_high : IfxPort_State_low);
    // } else {
    //     IfxPort_setPinState(&MODULE_P02, 3, direction ? IfxPort_State_high : IfxPort_State_low);
    // }
}

void stopMotors(void) {
    // 停止所有电机
    setMotorPWM(&g_LeftPwmDriver, 0.0f, TRUE);
    setMotorPWM(&g_RightPwmDriver, 0.0f, TRUE);
}

int core0_main(void) {
    initHardware();
    initUART();
    initPWM();
    initRTOS();

    // 不应该到达这里
    while (1) {
        // 错误处理
    }

    return 0;
}
```

**TC264配置要点**:
- **编译环境**: 使用Infineon编译器或GCC for TriCore
- **库依赖**: iLLD (Infineon Low Level Drivers) + FreeRTOS
- **时钟配置**: 需要正确配置GTM和ASCLIN时钟
- **中断优先级**: UART中断优先级应设置得足够高
- **内存分配**: FreeRTOS任务需要足够的堆栈空间
- **引脚复用**: 确保引脚没有冲突，支持多个功能复用
# Raspberry Pi Pico Serial Twist Bridge - 完整MicroPython示例
import machine
import utime
import _thread

# 硬件配置
UART_ID = 0
BAUD_RATE = 115200
TX_PIN = machine.Pin(0)  # GPIO0
RX_PIN = machine.Pin(1)  # GPIO1

# LED指示灯
LED_PIN = machine.Pin(25)  # 板载LED
led = machine.Pin(25, machine.Pin.OUT)

# 电机控制引脚 (根据你的硬件修改)
MOTOR_PINS = {
    'left_dir1': machine.Pin(2, machine.Pin.OUT),
    'left_dir2': machine.Pin(3, machine.Pin.OUT),
    'left_pwm': machine.PWM(machine.Pin(4), freq=1000),
    'right_dir1': machine.Pin(6, machine.Pin.OUT),
    'right_dir2': machine.Pin(7, machine.Pin.OUT),
    'right_pwm': machine.PWM(machine.Pin(8), freq=1000),
}

# 全局变量
current_twist = {'vx': 0.0, 'vy': 0.0, 'vz': 0.0,
                 'wx': 0.0, 'wy': 0.0, 'wz': 0.0}
data_valid = False
last_receive_time = utime.ticks_ms()

# 线程间通信锁
import _thread
lock = _thread.allocate_lock()

def init_motors():
    """初始化电机控制"""
    for pin in MOTOR_PINS.values():
        if hasattr(pin, 'duty_u16'):
            pin.duty_u16(0)  # PWM初始化为0
        else:
            pin.value(0)    # GPIO初始化为低电平

def parse_twist_data(data_str):
    """解析串口数据"""
    global current_twist, data_valid

    try:
        # 移除空白字符
        data_str = data_str.strip()

        # 检查逗号数量
        if data_str.count(',') != 5:
            return False

        # 分割并转换为浮点数
        values = data_str.split(',')
        if len(values) != 6:
            return False

        # 更新全局变量
        with lock:
            current_twist['vx'] = float(values[0])
            current_twist['vy'] = float(values[1])
            current_twist['vz'] = float(values[2])
            current_twist['wx'] = float(values[3])
            current_twist['wy'] = float(values[4])
            current_twist['wz'] = float(values[5])
            data_valid = True

        return True

    except (ValueError, IndexError) as e:
        print(f"Parse error: {e}")
        data_valid = False
        return False

def control_motors(vx, vy, wz):
    """电机控制函数"""
    # 差分驱动计算
    left_speed = vx - wz   # 左轮速度
    right_speed = vx + wz  # 右轮速度

    # 限制速度范围 (-1.0 到 1.0)
    left_speed = max(-1.0, min(1.0, left_speed))
    right_speed = max(-1.0, min(1.0, right_speed))

    # 转换为PWM值 (0-65535)
    def speed_to_pwm(speed):
        # 死区处理
        if abs(speed) < 0.01:
            return 0
        # 线性映射到PWM范围
        pwm_value = int(abs(speed) * 65535)
        return max(8000, min(65535, pwm_value))  # 最小占空比约12%

    left_pwm = speed_to_pwm(left_speed)
    right_pwm = speed_to_pwm(right_speed)

    # 控制左轮
    if left_speed > 0.01:
        # 前进
        MOTOR_PINS['left_dir1'].value(1)
        MOTOR_PINS['left_dir2'].value(0)
        MOTOR_PINS['left_pwm'].duty_u16(left_pwm)
    elif left_speed < -0.01:
        # 后退
        MOTOR_PINS['left_dir1'].value(0)
        MOTOR_PINS['left_dir2'].value(1)
        MOTOR_PINS['left_pwm'].duty_u16(left_pwm)
    else:
        # 停止
        MOTOR_PINS['left_dir1'].value(0)
        MOTOR_PINS['left_dir2'].value(0)
        MOTOR_PINS['left_pwm'].duty_u16(0)

    # 控制右轮
    if right_speed > 0.01:
        # 前进
        MOTOR_PINS['right_dir1'].value(1)
        MOTOR_PINS['right_dir2'].value(0)
        MOTOR_PINS['right_pwm'].duty_u16(right_pwm)
    elif right_speed < -0.01:
        # 后退
        MOTOR_PINS['right_dir1'].value(0)
        MOTOR_PINS['right_dir2'].value(1)
        MOTOR_PINS['right_pwm'].duty_u16(right_pwm)
    else:
        # 停止
        MOTOR_PINS['right_dir1'].value(0)
        MOTOR_PINS['right_dir2'].value(0)
        MOTOR_PINS['right_pwm'].duty_u16(0)

def stop_all_motors():
    """紧急停止所有电机"""
    for pin in MOTOR_PINS.values():
        if hasattr(pin, 'duty_u16'):
            pin.duty_u16(0)
        else:
            pin.value(0)

def serial_reader():
    """串口读取线程"""
    global last_receive_time

    uart = machine.UART(UART_ID, baudrate=BAUD_RATE, tx=TX_PIN, rx=RX_PIN)
    buffer = b""

    print("Serial reader thread started")

    while True:
        if uart.any():
            # 读取一个字节
            byte = uart.read(1)
            if byte:
                buffer += byte

                # 检查是否收到换行符
                if buffer.endswith(b'\n'):
                    try:
                        # 解码为字符串
                        line = buffer.decode('utf-8').strip()

                        if parse_twist_data(line):
                            last_receive_time = utime.ticks_ms()
                            led.value(1)  # 成功指示
                            print(f"Parsed: vx={current_twist['vx']:.3f}, wz={current_twist['wz']:.3f}")
                        else:
                            print(f"Parse failed: {line}")

                    except UnicodeDecodeError:
                        print("Decode error")

                    buffer = b""  # 清空缓冲区

        # 检查超时
        with lock:
            if data_valid and utime.ticks_diff(utime.ticks_ms(), last_receive_time) > 500:
                data_valid = False
                led.value(0)  # 超时指示

        utime.sleep(0.01)

# 主程序
def main():
    print("Raspberry Pi Pico Serial Twist Bridge")
    print(f"UART{UART_ID}: TX={TX_PIN}, RX={RX_PIN}, Baud={BAUD_RATE}")

    # 初始化
    init_motors()
    led.value(0)

    # 启动串口读取线程
    _thread.start_new_thread(serial_reader, ())

    # 主循环
    while True:
        with lock:
            if data_valid:
                # 使用最新的twist数据控制电机
                control_motors(
                    current_twist['vx'],
                    current_twist['vy'],
                    current_twist['wz']
                )
            else:
                # 超时停止
                stop_all_motors()

        utime.sleep(0.02)  # 50Hz控制频率

# 程序入口
if __name__ == "__main__":
    main()
```

---

## 🐛 故障排除

### 1. 串口无法打开

#### 问题: `Failed to open serial port: Permission denied`

**原因**: 用户没有串口设备的访问权限

**解决方法**:
```bash
# 方法1: 临时设置权限
sudo chmod 666 /dev/ttyUSB0

# 方法2: 添加用户到dialout组（推荐，永久生效）
sudo usermod -a -G dialout $USER
# 重新登录终端或重启系统

# 方法3: 检查设备所有者
ls -la /dev/ttyUSB0
# 如果是root所有，添加到udev规则
echo 'KERNEL=="ttyUSB*", MODE="0666"' | sudo tee /etc/udev/rules.d/99-ttyusb.rules
sudo udevadm control --reload-rules
```

### 2. 串口设备不存在

#### 问题: `Failed to open serial port: No such file or directory`

**原因**: 串口设备未正确连接或设备名错误

**诊断步骤**:
```bash
# 1. 列出所有串口设备
ls /dev/tty* | grep -E "(USB|ACM|S0|S1)"

# 2. 检查USB设备连接
lsusb
# 查看详细USB信息
lsusb -v | grep -A 10 -B 10 "Serial"

# 3. 检查内核消息
dmesg | grep tty | tail -10
dmesg | grep usb | tail -10

# 4. 如果是Arduino，重启Arduino IDE或拔插USB线
# 5. 检查设备是否被其他程序占用
lsof /dev/ttyUSB0 2>/dev/null || echo "设备未被占用"
```

### 3. Twist消息无响应

#### 问题: 串口桥接节点启动正常，但没有收到键盘控制指令

**诊断步骤**:
```bash
# 1. 检查话题是否存在
ros2 topic list | grep cmd_vel

# 2. 检查消息发布频率
ros2 topic hz /cmd_vel

# 3. 查看消息内容
ros2 topic echo /cmd_vel --once

# 4. 检查teleop_twist_keyboard是否正确启动
ros2 node list | grep teleop

# 5. 查看串口桥接的调试信息
ros2 topic echo /serial_bridge/debug
```

**常见原因**:
- teleop_twist_keyboard 未启动或配置错误
- 话题名称不匹配（/cmd_vel vs 其他名称）
- 消息发布频率过低
- 串口桥接节点订阅了错误的topic

### 4. MCU接收不到数据

#### 问题: 串口桥接显示发送成功，但MCU没有响应

**检查步骤**:
```bash
# 1. 验证串口连接
# 使用minicom或screen测试串口
sudo apt install minicom
minicom -D /dev/ttyUSB0 -b 115200

# 2. 检查波特率设置
# 确保MCU和ROS节点的波特率一致

# 3. 验证协议格式
# MCU应能解析格式: Vx,Vy,Vz,Wx,Wy,Wz\r\n
# 示例: 0.500,0.000,0.000,0.000,0.000,1.200\r\n

# 4. 测试串口回环
# 短接TX和RX引脚，检查数据是否回环
```

### 5. 数据格式错误

#### 问题: MCU收到数据但解析失败

**原因**: 浮点数精度或格式问题

**解决方法**:
```cpp
// MCU端正确的解析代码
char buffer[64];
float vx, vy, vz, wx, wy, wz;

if (Serial.available()) {
  String data = Serial.readStringUntil('\n');
  data.trim(); // 移除\r

  // 解析CSV格式
  int parsed = sscanf(data.c_str(), "%f,%f,%f,%f,%f,%f",
                      &vx, &vy, &vz, &wx, &wy, &wz);

  if (parsed == 6) {
    // 成功解析6个浮点数
    controlMotors(vx, vy, wz);
  } else {
    // 解析失败，输出调试信息
    Serial.print("Parse failed: ");
    Serial.println(data);
  }
}
```

### 6. 性能问题

#### 问题: 控制延迟大或丢包

**优化方法**:
```bash
# 1. 调整发布频率
ros2 launch serial_twist_bridge serial_bridge.launch.py publish_rate:=100.0

# 2. 使用更高波特率
ros2 launch serial_twist_bridge serial_bridge.launch.py baud_rate:=2000000

# 3. 检查系统负载
top -p $(pgrep -f serial_bridge_node)

# 4. 监控串口缓冲区
cat /proc/tty/driver/usbserial 2>/dev/null || echo "检查串口驱动"
```

### 7. 与其他节点的冲突

#### 问题: 多个节点发布到/cmd_vel导致冲突

**解决方法**:
```bash
# 1. 使用不同的topic名称
ros2 launch serial_twist_bridge serial_bridge.launch.py twist_topic:=/serial_cmd_vel

# 2. 检查topic发布者
ros2 topic info /cmd_vel

# 3. 使用topic remapping
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args \
  --remap cmd_vel:=/teleop_cmd_vel
```

---

## 📄 许可证

本项目采用 [Apache 2.0 许可证](LICENSE)。

---

## 📞 联系与支持

- **项目主页**: [SCURC Navigation Simulation](https://github.com/OH1412/SCURC_Nav_Sim)
- **技术支持**: [GitHub Issues](https://github.com/OH1412/SCURC_Nav_Sim/issues)
- **维护者**: Pangolin战队

---

*最后更新: 2026年1月24日*
