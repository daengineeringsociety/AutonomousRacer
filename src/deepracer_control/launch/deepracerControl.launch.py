import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    config_dir = os.path.join(get_package_share_directory('deepracer_control'), 'hardware_params.yaml')
    return LaunchDescription([
        Node(
            package='deepracer_control',
            executable='cmdVelNode',   # This must match your setup.py entry point!
            name='cmd_vel_node',
            output='screen',
            parameters=[config_dir]  # <-- Loads the YAML here!
        )
    ])