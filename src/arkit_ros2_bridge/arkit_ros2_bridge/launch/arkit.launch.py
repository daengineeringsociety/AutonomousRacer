import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    package_dir = get_package_share_directory('arkit_ros2_bridge')
    
    return LaunchDescription([
        Node(
            package='arkit_ros2_bridge',
            executable='iphoneInput',  # e.g., 'my_script' from setup.py console_scripts
            name='iphoneInput',
            output='screen'
        ),
    ])
