**以下为构建过程中可能出现的问题**
## fast_livo2_relocation部分
#### 构建前先阅读dependencies_and_tools/fast_livo2_relocation/readme.md
### 1.缺少Sophus
- 方法1
```bash
sudo apt install ros-$ROS_DISTRO-sophus
```
- 方法2
```bash
git clone https://github.com/strasdat/Sophus.git #
cd Sophus
git checkout a621ff
mkdir build && cd build && cmake ..
make
sudo make install
```
### 2.缺失pcl_ros 包依赖的 PCL
- 安装 PCL 1.12 开发包（ROS 2 Humble 对应版本）
```bash
sudo apt install libpcl-dev=1.12.1+dfsg-3build1
```

###  3.Boost 库配置异常
- 安装 Boost 序列化库（PCL 依赖）
```bash
sudo apt install libboost-serialization-dev
```
## simukation_evironment部分

### 1.缺少xacro
```bash
sudo apt install ros-humble-xacro
```
### 2.缺少joint_state_publisher包

```bash
sudo apt install ros-humble-joint-state-publisher
```




