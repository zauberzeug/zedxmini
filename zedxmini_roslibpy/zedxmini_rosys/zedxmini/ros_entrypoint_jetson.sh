#!/bin/bash
set -e

# Add ROS2 setup to .bashrc for all shells
echo "source /opt/ros/$ROS_DISTRO/setup.bash" >> /root/.bashrc
echo "source /root/ros2_ws/install/local_setup.bash" >> /root/.bashrc

# setup ros2 environment for this session
source "/opt/ros/$ROS_DISTRO/install/setup.bash"
source "/root/ros2_ws/install/local_setup.bash"

# Source ROS2 setup files again to ensure all packages are found
source /opt/ros/$ROS_DISTRO/setup.bash

export ROS_DOMAIN_ID=0

# Welcome information
echo "ZED ROS2 Docker Image"
echo "---------------------"
echo 'ROS distro: ' $ROS_DISTRO
echo 'DDS middleware: ' $RMW_IMPLEMENTATION
echo 'ROS 2 Workspaces:' $COLCON_PREFIX_PATH
echo 'ROS 2 Domain ID:' $ROS_DOMAIN_ID
echo ' * Note: Host and Docker image Domain ID must match to allow communication'
echo 'Local IPs:' $(hostname -I)
echo "---"  
echo 'Available ZED packages:'
ros2 pkg list | grep zed
echo "---------------------"
echo "Commands you might want to run:"
echo "1. Start rosbridge: ros2 launch rosbridge_server rosbridge_websocket_launch.xml"
echo "2. Start ZED camera: ros2 launch zed_wrapper zed_camera.launch.py camera_model:=zedxm"
echo "---------------------"

# Execute the command passed to the entrypoint or fall back to bash
exec "${@:-bash}"