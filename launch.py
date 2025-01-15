import os

from ament_index_python.packages import get_package_share_directory
from launch_ros.actions import Node

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    # Get the path to the ZED wrapper launch file
    zed_wrapper_dir = get_package_share_directory('zed_wrapper')
    zed_launch_path = os.path.join(zed_wrapper_dir, 'launch', 'zed_camera.launch.py')

    # Include the ZED camera launch file with specified parameters
    zed_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(zed_launch_path),
        launch_arguments={'camera_model': 'zedxm'}.items()
    )

    # Create the Foxglove Bridge node
    foxglove_bridge = Node(
        package='foxglove_bridge',  # Updated package name
        executable='foxglove_bridge',
        name='foxglove_bridge',
        parameters=[{
            'port': 8765,  # Default WebSocket port
            'address': '0.0.0.0',  # Listen on all network interfaces
            'send_buffer_limit': 1_000_000_000,
            'use_compression': True
        }]
    )

    # Create and return launch description
    return LaunchDescription([
        zed_launch,
        foxglove_bridge
    ])
