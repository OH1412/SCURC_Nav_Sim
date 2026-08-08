# 适用于机器人上/下位机串口通信的驱动（上位机部分）
> NOTE:此仓库基于Ubuntu22.04-ros-humble实现\
> 通信协议本身使用纯CPP实现，不局限于ROS等系统\
> 本仓库[主函数](src/serial_main.cpp)提供ROS2可用的[测试样例](#demo)，若使用ROS1或外部调用等场景需要自行修改launch文件或对应编译配置，使用ROS1可以参照[ros1版本仓库](https://github.com/CGC12123/serial_driver_ros1.git)

## Requirement
需要先安装 `serial` 库，在ubuntu22中无法直接使用apt安装，故需要从源码安装

```bash
git clone https://github.com/RoverRobotics-forks/serial-ros2.git
cd serial-ros2
mkdir build && cd build
cmake ..
make -j$(nproc)
sudo make install
```

## 通信协议
### 协议帧格式
| 字节索引 | 字段名     | 大小（字节） | 示例值          | 描述说明                                           |
|----------|------------|---------------|-----------------|----------------------------------------------------|
| 0        | 帧头1      | 1             | `0x0F`          | 固定帧头起始标志                                  |
| 1        | 帧头2      | 1             | `0xF0` / `0xFF` | `0xF0` 表示**发送帧**，`0xFF` 表示**接收帧**     |
| 2        | 数据长度   | 1             | `0x04`          | 后续数据字段长度（不包括帧头和校验和）            |
| 3～N     | 数据       | N（可变）     | `0x03, 0xE8 ...`| 以 2 字节为单位的 int16（缩放后 float 数据）    |
| N + 1    | 校验和     | 1             | `0x??`          | 对前面所有字节求和的低 8 位，用于验证完整性       |

### 数据说明
- 每 2 字节表示一个 `int16_t`，是浮点数 ×1000 后的整数形式。
- 数据数量 = 数据长度 ÷ 2。

### 数据demo
发送发送 float 数组 `{1.0f, -2.0f}`

| 字段名   | 十六进制示例                     | 说明                              |
|----------|----------------------------------|-----------------------------------|
| 帧头1    | `0x0F`                           | 固定值                            |
| 帧头2    | `0xF0`                           | 发送帧                            |
| 长度     | `0x04`                           | 两个 float，共 4 字节（2 x int16） |
| 数据     | `0x03, 0xE8, 0xF8, 0x30`         | `1000` → 1.0，`-2000` → -2.0      |
| 校验和   | `0x16`                           | 对前面所有字节求和取低 8 位       |

## Usage
### 串口及波特率设置
在[config/serial_config.yaml](config/serial_config.yaml)中设置
```
serial_cmd_sender:
  ros__parameters:
    port: "/dev/ttyS1"
    baudrate: 115200
```

### 函数调用
参照[include/serial_driver/serial_comm.hpp](include/serial_driver/serial_comm.hpp)
```
// init
SerialComm(const std::string& port, unsigned long baudrate);

// send
// 例如：命令 ID 0 表示速度命令
bool success = serial_comm_ptr->sendFloatArrayCommand(speeds, 0);

// receive
std::vector<float> readFloatArrayResponse();
```

### demo
一个基于ros的示例如[src/serial_main.cpp](src/serial_main.cpp)，为订阅/LIVO2/pose_offset话题并通过串口发送数据
```
ros2 launch serial_driver serial_driver.launch.py
```
同时有一个模拟导航模块发送数据的python脚本用于测试
```
python script/send_demo.py
```
