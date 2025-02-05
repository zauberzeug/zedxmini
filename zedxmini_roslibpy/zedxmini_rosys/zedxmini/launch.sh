#!/bin/bash

# Source ROS2 environment
source /opt/ros/humble/setup.bash

# Start ZED wrapper node in the background
ros2 launch zed_wrapper zed_camera.launch.py camera_model:=zedxm &

# Start the ROS bridge server
ros2 launch rosbridge_server rosbridge_websocket_launch.xml 