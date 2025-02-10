#!/bin/bash

# Source ROS2 environment
source /opt/ros/humble/setup.bash

# Start ZED wrapper node in the background
ros2 launch zed_wrapper zed_camera.launch.py camera_model:=zedxm &

# Start the Foxglove Bridge server
ros2 launch foxglove_bridge foxglove_bridge_launch.xml 