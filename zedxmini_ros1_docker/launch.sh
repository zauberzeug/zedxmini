#!/bin/bash

# Source ROS1 environment
source /opt/ros/noetic/setup.bash
#source /root/catkin_ws/devel/setup.bash
source /ros_ws/devel/setup.bash

# Start roscore and wait for it to be ready
roscore &
sleep 5

# Start Foxglove Bridge in the background
roslaunch foxglove_bridge foxglove_bridge.launch &

#  Start ZED wrapper node
roslaunch zed_wrapper zedxm.launch

# Keep container running
wait
