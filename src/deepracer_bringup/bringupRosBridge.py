import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, SetEnvironmentVariable, ExecuteProcess
from launch.launch_description_sources import AnyLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():

    # Path to the ROSBRIDGE XML launch file
    rosbridge_launch_path = os.path.join(
        get_package_share_directory('rosbridge_server'),
        'launch',
        'rosbridge_websocket_launch.xml'
    )

    # Use AnyLaunchDescriptionSource so it knows how to parse XML
    included_launch = IncludeLaunchDescription(
        AnyLaunchDescriptionSource(rosbridge_launch_path)
    )

    run_setup_script = ExecuteProcess(
        cmd=['./setupFoxglove.sh'],
        cwd='/workspaces/deepracer_project/scripts/inContainer/', # Sets the working directory
        output='screen'
    )

    return LaunchDescription([
        run_setup_script,
        included_launch
    ])
