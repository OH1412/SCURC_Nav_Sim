from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    # 你的功能包名
    your_package = "r2_bringup"
    # Nav2包路径（用于引入默认导航节点）
    nav2_package = "r2_bringup"

    # 路径计算
    your_package_share = get_package_share_directory(your_package)
    nav2_share = get_package_share_directory(nav2_package)
    # 你的复合任务树路径（test_control_height_bt.xml）

    behavior_ext_share_dir = get_package_share_directory("behavior_ext_plugins")

# 插件库所在的lib目录（共享目录的上级目录的lib子目录）
# 例如：share目录是install/behavior_ext_plugins/share/behavior_ext_plugins/
# 则lib目录是install/behavior_ext_plugins/lib/
    behavior_ext_lib_dir = os.path.join(
    os.path.dirname(behavior_ext_share_dir),  # 上一级目录：install/behavior_ext_plugins/share/
    os.pardir,                                # 再上一级：install/behavior_ext_plugins/
    "lib"                                     # 拼接lib目录：install/behavior_ext_plugins/lib/
    )

    test_bt_path = os.path.join(your_package_share, "behavior_tree", "test_height_only_bt.xml")
    # Nav2参数文件路径
    nav2_params_path = os.path.join(your_package_share, "params", "nav2_params.yaml")

    return LaunchDescription([
        # 1. 引入Nav2默认导航节点（规划器、控制器、代价图等）
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(nav2_share, "launch", "navigation.launch.py")),
            launch_arguments={
                "params_file": nav2_params_path  # 传递你的参数文件
            }.items()
        )
    ]
)
