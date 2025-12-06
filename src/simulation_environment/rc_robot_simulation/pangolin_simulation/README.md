# Pangolin Simulation - 2026 RoboCon武林探秘仿真环境

[![ROS 2 Humble](https://img.shields.io/badge/ROS2-Humble-22314E.svg)](https://docs.ros.org/en/humble/)
[![Gazebo 11](https://img.shields.io/badge/Gazebo-11-orange.svg)](https://gazebosim.org/)
[![RoboCon 2026](https://img.shields.io/badge/RoboCon-2026-9C27B0.svg)]()

## 📖 项目简介

Pangolin Simulation 是专为 2026 RoboCon 武林探秘比赛设计的机器人仿真环境包。该包基于 ROS 2 Humble 和 Gazebo 11，提供完整的机器人仿真生态系统，包括全向轮机器人模型、专业比赛场地和可视化配置。

### 🎯 核心特性

- **🏁 武林探秘专用场地**: 包含完整的 RoboCon2026 武林探秘比赛场地仿真
- **🤖 全向轮机器人**: 支持全方位移动的机器人模型
- **🌍 双场地模式**: 带墙赛道和无墙赛道两种配置
- **👁️ RViz集成**: 完整的可视化配置和调试工具
- **⚡ ROS 2集成**: 完全兼容ROS 2 Humble的通信机制

---

## 🏗️ 系统架构

### 包结构概览

```
pangolin_simulation/
├── launch/                     # 🚀 启动配置文件
│   ├── pangolin_simulation.launch.py  # 主仿真启动文件
│   ├── control.launch.py              # 控制节点启动
│   └── rm_real.launch.py              # 真实机器人启动
├── urdf/                       # 🤖 机器人模型
│   ├── simulation_waking_robot.xacro # 仿真用机器人模型
│   └── real_waking_robot.xacro       # 真实机器人模型
├── world/                      # 🏁 比赛场地
│   ├── robocon_map/                   # 地图资源文件
│   └── xzx_gazebo/                    # Gazebo世界文件
├── meshes/                     # 📐 网格模型
│   └── mid360.stl                     # Livox Mid-360激光雷达模型
├── rviz/                       # 👁️ 可视化配置
│   ├── rviz2.rviz                     # RViz主配置
│   └── vehicle_simulator.rviz         # 车辆仿真配置
└── CMakeLists.txt/package.xml         # 🛠️ 构建配置
```

### 技术栈

| 组件 | 版本 | 说明 |
|------|------|------|
| **ROS 2** | Humble Hawksbill | 机器人操作系统框架 |
| **Gazebo** | 11.x | 物理仿真引擎 |
| **编译工具** | Colcon + CMake | ROS 2 标准构建工具 |
| **机器人模型** | URDF/Xacro | 统一机器人描述格式 |
| **可视化** | RViz2 | ROS 2 可视化工具 |

---

## 📋 系统要求

### 硬件要求
- **CPU**: Intel i5 / AMD Ryzen 5 以上
- **内存**: 8GB RAM 以上 (推荐16GB)
- **GPU**: 支持OpenGL 3.3+的显卡
- **存储**: 10GB 可用空间

### 软件依赖
- **操作系统**: Ubuntu 22.04 LTS
- **ROS 2**: Humble Hawksbill
- **Gazebo**: 11.x (随ROS 2自动安装)
- **Python**: 3.10 (用于launch文件)

---

## 🛠️ 安装指南

### 1. 系统依赖安装

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装ROS 2 Humble（如果尚未安装）
sudo apt install ros-humble-desktop

# 安装Gazebo相关依赖
sudo apt install ros-humble-gazebo-ros-pkgs

# 安装编译工具
sudo apt install python3-colcon-common-extensions
```

### 2. 工作空间编译

```bash
# 进入工作空间
cd ~/SCURC_Nav_Sim

# 编译pangolin_simulation包
colcon build --packages-select pangolin_simulation

# 或者编译整个工作空间
colcon build --symlink-install

# 加载环境
source install/setup.bash
```

---

## 🎯 使用指南

### 1. 启动仿真环境

#### 带墙赛道启动（默认）

```bash
# 启动完整的仿真环境（带墙赛道 + RViz）
ros2 launch pangolin_simulation pangolin_simulation.launch.py \
  world:=RoboconWithWall \
  use_rviz:=true
```

#### 无墙赛道启动

```bash
# 启动无墙赛道仿真环境
ros2 launch pangolin_simulation pangolin_simulation.launch.py \
  world:=RoboconWithoutWall \
  use_rviz:=true
```

#### 仅启动Gazebo（不启动RViz）

```bash
# 只启动Gazebo仿真，不启动RViz
ros2 launch pangolin_simulation pangolin_simulation.launch.py \
  rviz:=false
```

### 2. 启动参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `world` | `RoboconWithWall` | 选择世界类型：`RoboconWithWall` 或 `RoboconWithoutWall` |
| `use_sim_time` | `True` | 是否使用仿真时间 |
| `rviz` | `true` | 是否启动RViz可视化 |
| `use_joint_state_publisher` | `false` | 是否启动关节状态发布器 |

### 3. 控制机器人

```bash
# 发布速度控制命令
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.5, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.5}}"

# 查看里程计数据
ros2 topic echo /odom

# 查看关节状态
ros2 topic echo /joint_states
```

---

## 🏁 比赛场地说明

### 场地类型

#### 1. RoboconWithWall（带墙赛道）
- **特点**: 包含完整的比赛场地边界墙壁
- **适用场景**: 标准比赛环境，测试路径规划算法
- **初始位置**: x=4.7, y=-2.5, z=0.0
- **朝向**: yaw=0.0 (面向正前方)

#### 2. RoboconWithoutWall（无墙赛道）
- **特点**: 开放式场地，无边界限制
- **适用场景**: 自由探索、算法调试
- **初始位置**: 同上
- **朝向**: 同上

### 场地资源

```
world/
├── xzx_gazebo/                 # Gazebo世界文件
│   ├── robocon2026_map_foreset.world        # 带墙完整场地
│   ├── robocon2026_map_foreset_wall.world   # 带墙版本
│   └── *.dae                                # 3D模型文件
└── robocon_map/               # 地图纹理资源
    └── *.png                                 # 场地纹理贴图
```

---

## 🤖 机器人模型

### 仿真机器人 (simulation_waking_robot.xacro)

#### 基本规格
- **尺寸**: 长0.3m × 宽0.2m × 高0.1m
- **质量**: 8.2kg (base_link)
- **轮子**: 4个全向轮 (半径0.06m)
- **关节**: 连续关节，支持全方位旋转

#### 坐标系
- **base_link**: 机器人基座坐标系
- **yaw_link**: 偏航旋转关节
- **odom**: 里程计坐标系
- **map**: 地图坐标系

#### 传感器配置
- **Livox Mid-360**: 激光雷达模型 (mid360.stl)
- **IMU**: 惯性测量单元 (模拟)
- **关节状态**: 轮子转速反馈

### 真实机器人 (real_waking_robot.xacro)

与仿真版本对应，用于真实机器人控制时的URDF描述。

---

## 👁️ 可视化配置

### RViz配置

#### 主配置 (rviz2.rviz)
- **机器人模型显示**: 显示完整的机器人几何模型
- **TF变换**: 显示所有坐标系变换关系
- **激光雷达数据**: Livox点云可视化
- **路径规划**: 导航路径和代价地图显示

#### 车辆仿真配置 (vehicle_simulator.rviz)
- **专门用于车辆运动学仿真**
- **轮子转速可视化**
- **速度向量显示**

### 启动可视化

```bash
# 方法1: 通过launch文件启动
ros2 launch pangolin_simulation pangolin_simulation.launch.py

# 方法2: 手动启动RViz
rviz2 -d $(ros2 pkg prefix pangolin_simulation)/share/pangolin_simulation/rviz/rviz2.rviz

# 方法3: 启动车辆专用视图
rviz2 -d $(ros2 pkg prefix pangolin_simulation)/share/pangolin_simulation/rviz/vehicle_simulator.rviz
```

---

## 🔧 高级配置

### 自定义机器人初始位置

在launch文件中修改spawn参数：

```python
spawn_entity_node = Node(
    package='gazebo_ros',
    executable='spawn_entity.py',
    arguments=[
        '-entity', 'robot',
        '-topic', 'robot_description',
        '-x', '4.7',    # 修改X坐标
        '-y', '-2.5',   # 修改Y坐标
        '-z', '0.0',    # 修改Z坐标
        '-Y', '0.0',    # 修改朝向 (弧度)
    ],
    output='screen'
)
```

### 添加新的比赛场地

1. **创建世界文件**
   ```bash
   # 在world/xzx_gazebo/目录下创建新的.world文件
   cp robocon2026_map_foreset.world my_custom_world.world
   ```

2. **编辑世界配置**
   ```xml
   <!-- 在.world文件中添加你的自定义元素 -->
   <model name="my_obstacle">
     <static>true</static>
     <!-- 添加几何形状和位置 -->
   </model>
   ```

3. **更新launch文件**
   ```python
   # 在launch文件中添加新的世界类型
   WorldType.MyCustomWorld = 'MyCustomWorld'
   
   # 添加对应的配置
   'MyCustomWorld': {
       'x': '0.0', 'y': '0.0', 'z': '0.0',
       'world_path': 'xzx_gazebo/my_custom_world.world'
   }
   ```

### 修改机器人模型

1. **编辑Xacro文件**
   ```xml
   <!-- 在urdf/目录下的.xacro文件中修改参数 -->
   <xacro:property name="robot_length" value="0.4" />
   <xacro:property name="robot_width" value="0.25" />
   ```

2. **添加新的传感器**
   ```xml
   <!-- 添加摄像头 -->
   <link name="camera_link">
     <visual>
       <geometry><box size="0.02 0.02 0.02"/></geometry>
     </visual>
   </link>
   ```

---

## 🔧 调试与故障排除

### 常见问题

#### 1. Gazebo启动失败
```
错误: Could not load world file
```
**解决**:
- 检查世界文件路径是否正确
- 确认Gazebo模型路径设置正确
- 检查文件权限

#### 2. 机器人生成失败
```
错误: Spawn service timeout
```
**解决**:
- 增加spawn_entity的timeout参数
- 检查URDF文件语法正确性
- 确认robot_description话题正常发布

#### 3. RViz无数据显示
```
现象: RViz界面空白
```
**解决**:
- 检查use_sim_time参数设置
- 确认所有坐标变换都正确发布
- 检查RViz配置文件路径

#### 4. 速度控制无效
```
现象: 发布/cmd_vel后机器人不动
```
**解决**:
- 检查机器人模型是否包含速度控制器插件
- 确认关节名称与控制器匹配
- 验证Gazebo物理引擎是否启动

### 调试技巧

#### 查看节点状态
```bash
# 检查仿真相关节点
ros2 node list | grep -E "gazebo|robot|joint"

# 查看话题列表
ros2 topic list | grep -E "cmd_vel|odom|joint"

# 检查服务
ros2 service list | grep gazebo
```

#### 监控系统状态
```bash
# 查看TF树
ros2 run tf2_tools view_frames.py

# 检查时钟同步
ros2 topic echo /clock

# 监控关节状态
ros2 topic hz /joint_states
```

---

## 📊 性能优化

### Gazebo性能调优

1. **减少渲染质量**
   ```bash
   # 启动时使用简化渲染
   export GAZEBO_GRAPHICS=0
   ```

2. **调整物理引擎参数**
   ```xml
   <!-- 在.world文件中调整 -->
   <physics type="ode">
     <max_step_size>0.01</max_step_size>
     <real_time_factor>1.0</real_time_factor>
   </physics>
   ```

### ROS 2通信优化

1. **调整话题QoS**
   ```cpp
   // 在代码中设置QoS策略
   rclcpp::QoS qos(10);
   qos.reliability(RMW_QOS_POLICY_RELIABILITY_BEST_EFFORT);
   ```

2. **使用组件化启动**
   ```python
   # 在launch文件中使用ComposableNode
   ComposableNode(
       package='your_package',
       plugin='your_plugin',
       name='node_name'
   )
   ```

---

## 📝 开发指南

### 扩展仿真功能

#### 添加新的传感器

1. **在URDF中定义传感器**
   ```xml
   <link name="lidar_link">
     <visual>
       <geometry><cylinder radius="0.05" length="0.1"/></geometry>
     </visual>
   </link>
   
   <joint name="lidar_joint" type="fixed">
     <parent link="base_link"/>
     <child link="lidar_link"/>
     <origin xyz="0.1 0 0.15"/>
   </joint>
   
   <gazebo reference="lidar_link">
     <sensor name="lidar" type="ray">
       <!-- 传感器配置 -->
     </sensor>
   </gazebo>
   ```

2. **配置传感器插件**
   ```xml
   <plugin name="gazebo_ros_ray_sensor" filename="libgazebo_ros_ray_sensor.so">
     <ros>
       <namespace>/robot</namespace>
       <remapping>~/scan:=scan</remapping>
     </ros>
     <output_type>sensor_msgs/LaserScan</output_type>
   </plugin>
   ```

#### 创建新的世界环境

1. **使用Gazebo编辑器**
   ```bash
   gazebo --verbose  # 启动Gazebo世界编辑器
   ```

2. **添加模型和对象**
   - 从模型库中拖拽对象
   - 设置位置、姿态和物理属性
   - 保存为.world文件

3. **集成到launch文件**
   ```python
   # 在launch文件中添加新的世界选项
   declare_world_cmd = DeclareLaunchArgument(
       'world',
       default_value='MyCustomWorld',
       description='Choose world: MyCustomWorld, RoboconWithWall, RoboconWithoutWall'
   )
   ```

---

## 📄 许可证

本项目采用 Apache 2.0 许可证开源。

---

## 📞 联系与支持

- **项目主页**: [SCURC Navigation Simulation](https://github.com/OH1412/SCURC_Nav_Sim)
- **技术支持**: [GitHub Issues](https://github.com/OH1412/SCURC_Nav_Sim/issues)
- **维护者**: Lihan Chen (lihan.chen@smbu.edu.cn)
- **贡献者**: Pangolin战队

---

*最后更新: 2025年12月6日*
