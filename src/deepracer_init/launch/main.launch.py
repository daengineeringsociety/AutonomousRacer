import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, ExecuteProcess, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource

def generate_launch_description():
    # 1. Find the exact installation directories for both packages
    control_pkg_dir = get_package_share_directory('deepracer_control')
    init_pkg_dir = get_package_share_directory('deepracer_init')

    # 2. Build the exact file paths to the child launch files
    cmd_vel_launch_path = os.path.join(control_pkg_dir, 'deepracerControl.launch.py')
    ros_bridge_launch_path = os.path.join(init_pkg_dir, 'bringupRosBridge.launch.py')

    # 3. Create the include actions
    include_cmd_vel = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(cmd_vel_launch_path)
    )

    include_ros_bridge = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(ros_bridge_launch_path)
    )

    # 4. The raw Python script execution
    iphone_input_process = ExecuteProcess(
        cmd=['python3', 'src/arkit_ros2_bridge/arkit_ros2_bridge/arkit_ros2_bridge/iphoneVIO.py'],
        output='screen'
    )

    # 5. Force it to execute LAST by delaying it for 3 seconds
    delayed_iphone_input = TimerAction(
        period=3.0,
        actions=[iphone_input_process]
    )

    # 6. Launch them together!
    return LaunchDescription([
        include_cmd_vel,
        include_ros_bridge,
        delayed_iphone_input
    ])