from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    # 仅配置control_height专属路径和参数
    pkg_r2_bringup = get_package_share_directory("r2_bringup")
    pkg_behavior_ext = get_package_share_directory("height_control_plugins")

    # control_height专属行为树文件（仅包含control_height逻辑的BT文件）
    control_height_bt_path = os.path.join(
        pkg_r2_bringup, "behavior_tree", "test_control_height_bt.xml"
    )
    # control_height专属参数文件（若有单独配置，无则复用但仅加载control_height相关项）
    nav2_params_path = os.path.join(pkg_r2_bringup, "params", "nav2_params.yaml")

    # 插件库路径（仅为control_height插件服务）
    behavior_ext_lib_dir = os.path.join(
        os.path.dirname(pkg_behavior_ext),
        os.pardir,
        "lib"
    )

    return LaunchDescription([
        # 仅启动control_height所需的bt_navigator节点，无其他冗余节点
        Node(
            package="nav2_bt_navigator",
            executable="bt_navigator",
            name="bt_navigator",
            output="screen",
            additional_env={
                "LD_LIBRARY_PATH": f"{os.environ.get('LD_LIBRARY_PATH', '')}:{behavior_ext_lib_dir}"
            },
            # 仅订阅/publish control_height相关话题，屏蔽无关通信（可选，进一步隔离）
            remappings=[
                ("/bt_navigator/goal", "/control_height_goal"),
                ("/bt_navigator/status", "/control_height_status")
            ]
        )
    ])
