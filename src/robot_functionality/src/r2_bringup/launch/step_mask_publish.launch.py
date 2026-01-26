from launch import LaunchDescription
from launch_ros.actions import ComposableNodeContainer
from launch_ros.descriptions import ComposableNode
import os
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    pkg_dir = get_package_share_directory('r2_bringup')
    mask_yaml = os.path.join(pkg_dir, 'maps', 'step_mask.yaml')

    container = ComposableNodeContainer(
        name='step_mask_container',
        namespace='',
        package='rclcpp_components',
        executable='component_container_mt',
        composable_node_descriptions=[
            ComposableNode(
                package='step_mask_publisher',
                plugin='step_mask_publisher::StepMaskPublisher',
                name='step_mask_publisher',
                parameters=[{
                    "mask_yaml": mask_yaml
                }]
            )
        ],
        output='screen',
    )

    return LaunchDescription([container])
