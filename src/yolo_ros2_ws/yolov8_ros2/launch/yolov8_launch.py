from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration
from launch.actions import DeclareLaunchArgument
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    """生成启动描述"""
    
    # 获取包的共享目录
    pkg_share = get_package_share_directory('yolov8_ros2')
    # 计算 model 的绝对路径（安装后位于 share/yolov8_ros2/config/best.pt）
    model_path = os.path.join(pkg_share, 'config', 'best.pt')
    
    # 声明启动参数
    config_file = LaunchConfiguration('config_file')
    log_level = LaunchConfiguration('log_level')
    node_output = LaunchConfiguration('node_output')
    image_topic = LaunchConfiguration('image_topic')
    weapon_enabled = LaunchConfiguration('weapon_enabled')
    weapon_weight_path = LaunchConfiguration('weapon_weight_path')
    weapon_conf = LaunchConfiguration('weapon_conf')
    depth_topic = LaunchConfiguration('depth_topic')
    camera_info_topic = LaunchConfiguration('camera_info_topic')
    base_frame = LaunchConfiguration('base_frame')
    
    declare_config_file_arg = DeclareLaunchArgument(
        'config_file',
        default_value=os.path.join(pkg_share, 'config', 'yolov8_config.yaml'),
        description='Path to the configuration file'
    )

    declare_log_level_arg = DeclareLaunchArgument(
        'log_level',
        default_value='info',
        description='ROS log level for YOLO and related nodes (debug/info/warn/error/fatal)'
    )
    declare_node_output_arg = DeclareLaunchArgument(
        'node_output',
        default_value='screen',
        description='Node output destination: screen or log'
    )
    
    declare_image_topic_arg = DeclareLaunchArgument(
        'image_topic',
        default_value='/camera/camera/color/image_raw',
        description='Input image topic name'
    )

    declare_weapon_enabled_arg = DeclareLaunchArgument(
        'weapon_enabled',
        default_value='false',
        description='Enable weapon detection model'
    )

    declare_weapon_weight_arg = DeclareLaunchArgument(
        'weapon_weight_path',
        default_value='',
        description='Path to weapon detection weights'
    )

    declare_weapon_conf_arg = DeclareLaunchArgument(
        'weapon_conf',
        default_value='0.6',
        description='Confidence threshold for weapon model'
    )

    declare_depth_topic_arg = DeclareLaunchArgument(
        'depth_topic',
        default_value='/camera/camera/aligned_depth_to_color/image_raw',
        description='Depth image topic'
    )

    declare_camera_info_arg = DeclareLaunchArgument(
        'camera_info_topic',
        default_value='/camera/camera/aligned_depth_to_color/camera_info',
        description='Camera info topic'
    )

    declare_base_frame_arg = DeclareLaunchArgument(
        'base_frame',
        default_value='base_link',
        description='Base frame for TF transform'
    )
    
    # 创建YOLOv8节点
    yolov8_node = Node(
        package='yolov8_ros2',
        executable='yolov8_node',
        name='yolov8_ros2_node',
        output=node_output,
        parameters=[
            config_file,
            {
                'image_topic': image_topic,
                # 覆盖 YAML 中的 weight_path，确保使用绝对路径加载模型
                'weight_path': model_path,
                'weapon_enabled': weapon_enabled,
                'weapon_weight_path': weapon_weight_path,
                'weapon_conf': weapon_conf,
            },
        ],
        # pass ros-args to set node log level
        arguments=['--ros-args', '--log-level', log_level],
    )

    # 3D 位姿节点
    kfs_weapon_3d_node = Node(
        package='yolov8_ros2',
        executable='kfs_weapon_3d_grasp_node',
        name='kfs_weapon_3d_grasp',
        output=node_output,
        parameters=[
            config_file,
            {
                'boxes_topic': '/yolov8/BoundingBoxes',
                'depth_topic': depth_topic,
                'camera_info_topic': camera_info_topic,
                'base_frame': base_frame,
            },
        ],
        arguments=['--ros-args', '--log-level', log_level],
    )
    
    # 创建启动描述
    return LaunchDescription([
        declare_config_file_arg,
        declare_log_level_arg,
        declare_node_output_arg,
        declare_image_topic_arg,
        declare_weapon_enabled_arg,
        declare_weapon_weight_arg,
        declare_weapon_conf_arg,
        declare_depth_topic_arg,
        declare_camera_info_arg,
        declare_base_frame_arg,
        yolov8_node,
        kfs_weapon_3d_node
    ])
