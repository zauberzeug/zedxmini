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
    # web_bridge = Node(
    #     package='rosbridge_server',
    #     executable='rosbridge_websocket',
    #     name='rosbridge_websocket',
    #     parameters=[{
    #         'port': 9090,
    #         'address': '0.0.0.0',
    #         # 'retry_startup_delay': 5.0,
    #         # 'fragment_timeout': 600,
    #         # 'delay_between_messages': 0,
    #         # 'max_message_size': 10_000_000,
    #         # 'unregister_timeout': 10.0,
    #         # # 'use_compression': False,
    #         # 'topics_glob': [],
    #         # 'services_glob': [],
    #         # 'params_glob': []
    #     }],
    #     output='screen'
    # )

    # rosapi = Node(
    #     package='rosapi',
    #     executable='rosapi_node',
    #     name='rosapi',
    #     # parameters=[{
    #     #     'topics_glob': [],
    #     #     'services_glob': [],
    #     #     'params_glob': []
    #     # }]
    # )

    # Create and return launch description
    return LaunchDescription([
        zed_launch,
        foxglove_bridge
        # web_bridge,
        # rosapi
    ])
