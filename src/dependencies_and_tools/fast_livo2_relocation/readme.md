# FAST-LIVO2 ROS2 HUMBLE

**注意事项**:此仓库安装方式与(FAST_LIVO2_ROS2)[https://github.com/mose1s/RC_vision_2026/tree/main/Slam/]相同，唯一不同之处在于：本仓库安装时需要先将`/src/icp_relocalization`移出目录，在`src/livox_ros_driver2`目录下执行命令`./build.sh humble`进行安装后再移回来，然后在\[workspace\]下执行命令`colcon build`进行安装。

*暂时先这样解决，后面会（也许）更改`build.sh`进行修复。*

参考链接：
https://github.com/SuperLDG/FASTLIVO2_ROS2
https://github.com/PolarisXQ/Fast-LIO2-Localization

## 1. Introduction
FAST-LIVO2 is a LiDAR-Inertial Odometry and Mapping system. It is based on FAST-LIO2, and adapted to work with ROS2 Humble.

## 2. Prerequisites

### 2.1 Ubuntu and ROS

Ubuntu 22.04.  [ROS Installation](http://wiki.ros.org/ROS/Installation).

### 2.2 PCL && Eigen && OpenCV

PCL>=1.6, Follow [PCL Installation](https://pointclouds.org/). 

Eigen>=3.3.4, Follow [Eigen Installation](https://eigen.tuxfamily.org/index.php?title=Main_Page).

OpenCV>=3.2, Follow [Opencv Installation](http://opencv.org/).

### 2.3 Sophus

Binary installation

```bash
sudo apt install ros-$ROS_DISTRO-sophus
```

or build from source

```bash
git clone https://github.com/strasdat/Sophus.git #
cd Sophus
git checkout a621ff
mkdir build && cd build && cmake ..
make
sudo make install
```

if build fails due to `so2.cpp:32:26: error: lvalue required as left operand of assignment`, modify the code as follows:

**so2.cpp**
```diff
namespace Sophus
{

SO2::SO2()
{
-  unit_complex_.real() = 1.;
-  unit_complex_.imag() = 0.;
+  unit_complex_.real(1.);
+  unit_complex_.imag(0.);
}
```

### 2.4 Vikit

直接用本仓库下的就可



### 2.5 **livox_ros_driver2**

Follow [livox_ros_driver2 Installation](https://github.com/Livox-SDK/livox_ros_driver2).

why not use `livox_ros_driver`? Because it is not compatible with ROS2 directly. actually i am not think there s any difference between [livox ros driver](https://github.com/Livox-SDK/livox_ros_driver.git) and [livox ros driver2](https://github.com/Livox-SDK/livox_ros_driver2.git) 's `CustomMsg`, the latter 's ros2 version is sufficient.

## 3. Build
将这个仓库下的三个文件夹放入你的ROS2工作空间的src下，然后进入livox_ros_driver2文件夹，输入命令
```bash
./build.sh humble
```

## 4.Run

```bash
ros2 launch livox_ros_driver2 msg_MID360_launch.py
ros2 launch fast_livo mapping_avia.launch.py use_rviz:=True
```

## 报错解决
1. **系统找不到 `liblivox_lidar_sdk_shared.so` 这个共享库文件**

**检查系统是否存在该库文件**：

```bash
# 在系统库目录中搜索
find /usr/lib /usr/local/lib ~/humble -name "liblivox_lidar_sdk_shared.so"
```
如果找得到，如：
getting@GT:~/humble/FAST-LIVO2-ROS2$ find /usr/lib /usr/local/lib ~/humble -name "liblivox_lidar_sdk_shared.so" /usr/local/lib/liblivox_lidar_sdk_shared.so /home/getting/humble/Livox-SDK2/build/sdk_core/liblivox_lidar_sdk_shared.so
则：
```bash
# 将系统库路径加入动态库搜索列表
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib
```
并且永久配置路径，避免每次终端重复操作

```bash
# 将路径写入用户环境变量文件（~/.bashrc）
echo 'export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib' >> ~/.bashrc
# 让配置立即生效（无需重启终端）
source ~/.bashrc
```
若找不到，则重新安装livox-SDK

2. 解决「image_transport/compressed_sub 插件缺失」问题

`republish` 节点需要压缩图像传输插件，系统默认未安装，需手动安装对应的功能包：+  unit_complex_.real(1.);
s

```bash
# 安装 image_transport 压缩插件（支持 compressed 格式图像）
sudo apt install -y ros-humble-image-transport-plugins
```
