# RC Interfaces (RC 接口定义)

[![ROS 2 Humble](https://img.shields.io/badge/ROS2-Humble-22314E.svg)](https://docs.ros.org/en/humble/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

## 📖 项目简介

RC Interfaces 是 SCURC 机器人导航仿真系统中的接口定义包集合。该包为整个系统提供标准化的消息和服务接口定义，确保各模块间的无缝通信和数据交换。

### 🎯 主要功能

- **🔧 服务接口定义**: 提供机器人任务规划和执行的服务接口
- **📦 消息格式标准化**: 统一YOLOv8目标检测和KFS决策的消息格式
- **🔗 模块间通信**: 确保导航、感知、决策模块间的可靠数据交换

---

## 🏗️ 包结构

```
rc_interfaces/
├── fly_step_msgs/           # 飞行步进消息包
│   └── srv/
│       └── SetMainWps.srv   # 设置主要航点服务
└── yolov8_ros2_msgs/        # YOLOv8 ROS2消息包
    └── msg/
        ├── BoundingBox.msg      # 单个边界框消息
        ├── BoundingBoxes.msg    # 边界框数组消息
        └── KFSDecision.msg      # KFS决策消息
```

---

## 📋 系统要求

- **操作系统**: Ubuntu 22.04 LTS
- **ROS版本**: ROS 2 Humble Hawksbill
- **依赖包**: `rosidl_default_generators`, `std_msgs`, `builtin_interfaces`

---

## 🚀 消息与服务详解

### 1. fly_step_msgs

#### SetMainWps 服务 (`fly_step_msgs/srv/SetMainWps`)

用于设置机器人导航的主要航点序列。

**请求字段**:
- `wps` (int32[]): 航点ID数组，表示要访问的航点序列

**响应字段**:
- `success` (bool): 操作是否成功
- `message` (string): 状态消息或错误描述

**使用示例**:
```bash
# 设置航点序列 [1, 3, 5, 2]
ros2 service call /set_main_wps fly_step_msgs/srv/SetMainWps "{wps: [1, 3, 5, 2]}"
```

---

### 2. yolov8_ros2_msgs

#### BoundingBox 消息 (`yolov8_ros2_msgs/msg/BoundingBox`)

描述单个检测到的目标边界框信息。

**字段说明**:

| 字段 | 类型 | 描述 |
|------|------|------|
| `xmin` | float64 | 边界框左上角X坐标 (像素) |
| `ymin` | float64 | 边界框左上角Y坐标 (像素) |
| `xmax` | float64 | 边界框右下角X坐标 (像素) |
| `ymax` | float64 | 边界框右下角Y坐标 (像素) |
| `class_name` | string | 目标类别名称 (如 "r1", "r2") |
| `color` | string | 目标颜色 ("red", "blue", "unknown") |
| `probability` | float64 | 检测置信度 (0.0-1.0) |
| `distance` | float64 | 目标距离 (米) |

#### BoundingBoxes 消息 (`yolov8_ros2_msgs/msg/BoundingBoxes`)

包含多个边界框的检测结果集合。

**字段说明**:

| 字段 | 类型 | 描述 |
|------|------|------|
| `bounding_boxes` | BoundingBox[] | 检测到的所有目标边界框数组 |
| `header` | std_msgs/Header | ROS标准消息头 |
| `image_header` | std_msgs/Header | 原始图像消息头 |

#### KFSDecision 消息 (`yolov8_ros2_msgs/msg/KFSDecision`)

KFS (目标物) 决策信息，描述12个台阶的状态快照。

**常量定义**:
```cpp
OBJECT_NONE = 0    // 台阶为空
OBJECT_R1 = 1      // 台阶上有r1
OBJECT_R2 = 2      // 台阶上有r2
OBJECT_FAKE = 3    // 台阶上有假KFS
OBJECT_UNK = 4     // 台阶上未知物体
```

**字段说明**:

| 字段 | 类型 | 描述 |
|------|------|------|
| `total_stairs` | int32 | 总台阶数 (固定=12) |
| `stair_object_type` | int32[] | 每个台阶的物体类型 (长度=12) |
| `stair_confidences` | float64[] | 每个台阶物体的置信度 (长度=12) |
| `stair_names` | string[] | 台阶名称数组 (长度=12) |
| `total_r1_count` | int32 | 全场景r1总数 |
| `total_r2_count` | int32 | 全场景r2总数 |
| `total_fake_count` | int32 | 全场景假KFS总数 (0或1) |
| `total_empty_count` | int32 | 空台阶数量 |
| `timestamp` | builtin_interfaces/Time | 时间戳 |
| `frame_id` | string | 坐标系ID |

**使用示例**:
```python
# 订阅KFS决策消息
def kfs_callback(msg):
    print(f"总台阶数: {msg.total_stairs}")
    print(f"R1数量: {msg.total_r1_count}")
    print(f"R2数量: {msg.total_r2_count}")
    print(f"假KFS数量: {msg.total_fake_count}")

    # 检查每个台阶的状态
    for i, obj_type in enumerate(msg.stair_object_type):
        stair_name = msg.stair_names[i]
        confidence = msg.stair_confidences[i]
        print(f"台阶 {stair_name}: 类型={obj_type}, 置信度={confidence}")
```

---

## 🛠️ 安装与编译

### 1. 添加到工作空间

```bash
# 克隆或复制到ROS2工作空间
cp -r rc_interfaces ~/ros2_ws/src/
```

### 2. 编译包

```bash
# 加载ROS2环境
source /opt/ros/humble/setup.bash

# 编译工作空间
cd ~/ros2_ws
colcon build --packages-select fly_step_msgs yolov8_ros2_msgs

# 加载编译结果
source install/setup.bash
```

### 3. 验证安装

```bash
# 检查消息和服务是否正确生成
ros2 interface list | grep -E "(fly_step_msgs|yolov8_ros2_msgs)"
```

---

## 🔍 接口使用指南

### 1. 在C++中使用

```cpp
#include "yolov8_ros2_msgs/msg/bounding_boxes.hpp"
#include "fly_step_msgs/srv/set_main_wps.hpp"

// 使用消息
auto bbox_msg = yolov8_ros2_msgs::msg::BoundingBox();
bbox_msg.class_name = "r1";
bbox_msg.probability = 0.95;

// 调用服务
auto request = std::make_shared<fly_step_msgs::srv::SetMainWps::Request>();
request->wps = {1, 2, 3, 4};
```

### 2. 在Python中使用

```python
from yolov8_ros2_msgs.msg import BoundingBoxes, KFSDecision
from fly_step_msgs.srv import SetMainWps

# 创建消息
bbox = BoundingBoxes()
# ... 填充消息字段

# 创建服务请求
req = SetMainWps.Request()
req.wps = [1, 2, 3, 4]
```

### 3. 话题监控

```bash
# 监控边界框检测结果
ros2 topic echo /yolo_detections

# 监控KFS决策信息
ros2 topic echo /kfs_decision

# 查看可用的服务
ros2 service list | grep set_main_wps
```

---

## 📚 相关模块

- **kfs_detection_nav**: 使用 `KFSDecision` 消息进行目标决策
- **yolo_simulator**: 发布 `BoundingBoxes` 消息
- **r2_bringup**: 调用 `SetMainWps` 服务设置导航航点

---

## 📄 许可证

本项目采用 [Apache 2.0 许可证](LICENSE)。

---

## 📞 联系与支持

- **项目主页**: [SCURC Navigation Simulation](https://github.com/OH1412/SCURC_Nav_Sim)
- **技术支持**: [GitHub Issues](https://github.com/OH1412/SCURC_Nav_Sim/issues)
- **维护者**: [Pangolin战队](https://github.com/mose1s/RC_vision_2026)

---

*最后更新: 2026年1月23日*
