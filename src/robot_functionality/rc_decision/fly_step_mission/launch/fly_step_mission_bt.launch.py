import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    pkg_share = get_package_share_directory('fly_step_mission')
    bt_xml = os.path.join(pkg_share, 'behavior_trees', 'fly_step_mission.xml')

    fly_step_bt_node = Node(
        package='fly_step_mission',
        executable='fly_step_bt_node',
        name='fly_step_bt_node',
        output='screen',
        parameters=[{
            'bt_xml_file': bt_xml
        }]
    )

    ld = LaunchDescription()
    ld.add_action(fly_step_bt_node)
    return ld
