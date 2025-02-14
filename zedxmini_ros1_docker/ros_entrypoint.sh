#!/bin/bash
set -e

# setup ros environment
source "/root/ros_catkin_ws/install_isolated/setup.bash"
source "/ros_ws/devel/setup.bash"

exec "$@"