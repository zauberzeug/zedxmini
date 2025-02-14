# https://github.com/stereolabs/zed-ros2-wrapper/tree/master/docker
# https://github.dev/husarion/zed-docker/blob/ros2/Dockerfile.jetson

# Avalible dustynv ros humble images:
# 36.3.0 for Jetpack 6, 35.4.1 for Jetpack 5, 32.7.1 for Jetpack 4

# Based on https://hub.docker.com/r/stereolabs/zed/
# needed ubuntu 20.04 for ros noetic
ARG L4T_MAJOR=35
ARG L4T_MINOR=2
ARG ZED_SDK_MAJOR=4
ARG ZED_SDK_MINOR=2
#ARG ZED_SDK_PATCH=0
ARG ROS_DISTRO=noetic

### BUILD IMAGE ###
FROM stereolabs/zed:${ZED_SDK_MAJOR}.${ZED_SDK_MINOR}-devel-l4t-r${L4T_MAJOR}.${L4T_MINOR} AS build

# scope to build 
ARG L4T_MAJOR
ARG L4T_MINOR
ARG ZED_SDK_MAJOR
ARG ZED_SDK_MINOR
ARG ROS_DISTRO

SHELL ["/bin/bash", "-c"]

ENV NVIDIA_DRIVER_CAPABILITIES \
 ${NVIDIA_DRIVER_CAPABILITIES:+$NVIDIA_DRIVER_CAPABILITIES,}compute,video,utility

# ROS install
ENV ROS_DISTRO=${ROS_DISTRO}
RUN echo "deb http://packages.ros.org/ros/ubuntu $(lsb_release -sc) main" > /etc/apt/sources.list.d/ros1-latest.list && \
    apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C1CF6E31E6BADE8868B172B4F42ED6FBAB17C654 && \
    apt-get update && \ 
    apt-get install -y --no-install-recommends \
        ros-${ROS_DISTRO}-ros-core && \    
    rm -rf /var/lib/apt/lists/*

# Install & initialize ws
WORKDIR /ros_ws
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        git \
        python3-pip && \
        pip3 install \
        rosdep && \    
    rm -rf /var/lib/apt/lists/*

# Workspace & dependencies
RUN apt-get update && \
    git clone --recursive https://github.com/stereolabs/zed-ros-wrapper src/zed-ros-wrapper && \
    git clone --recursive https://github.com/foxglove/ros-foxglove-bridge src/ros-foxglove-bridge && \
    source /opt/ros/$ROS_DISTRO/setup.bash && \
    rosdep init && \
    rosdep update --rosdistro $ROS_DISTRO && \
    rosdep install --from-paths src -y -i && \    
    rm -rf /var/lib/apt/lists/*

# Build
RUN source /opt/ros/$ROS_DISTRO/setup.bash && \
    catkin_make -DCMAKE_BUILD_TYPE=Release


### RUN IMAGE ###
FROM stereolabs/zed:${ZED_SDK_MAJOR}.${ZED_SDK_MINOR}-runtime-l4t-r${L4T_MAJOR}.${L4T_MINOR} AS run

# scope to run
ARG L4T_MAJOR
ARG L4T_MINOR
ARG ZED_SDK_MAJOR
ARG ZED_SDK_MINOR
ARG ROS_DISTRO
SHELL ["/bin/bash", "-c"]

ENV NVIDIA_DRIVER_CAPABILITIES \
    ${NVIDIA_DRIVER_CAPABILITIES:+$NVIDIA_DRIVER_CAPABILITIES,}compute,video,utility

# ROS install
ENV ROS_DISTRO=${ROS_DISTRO}
RUN echo "deb http://packages.ros.org/ros/ubuntu $(lsb_release -sc) main" > /etc/apt/sources.list.d/ros1-latest.list && \
    apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C1CF6E31E6BADE8868B172B4F42ED6FBAB17C654 && \
    apt-get update && \ 
    apt-get install -y --no-install-recommends \
        ros-${ROS_DISTRO}-ros-core && \    
    rm -rf /var/lib/apt/lists/*

# Install & initialize ws
WORKDIR /ros_ws
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        git \
        python3-pip && \
        pip3 install \
        rosdep && \    
    rm -rf /var/lib/apt/lists/*

# Workspace & dependencies
COPY --from=build /ros_ws /ros_ws
RUN apt-get update && \
    source /opt/ros/$ROS_DISTRO/setup.bash && \
    rosdep init && \
    rosdep update --rosdistro $ROS_DISTRO && \
    rosdep install --from-paths src -y -i && \    
    rm -rf /var/lib/apt/lists/*

COPY ros_entrypoint_jetson.sh /ros_entrypoint.sh
COPY launch.sh /launch.sh
RUN sudo chmod 755 /ros_entrypoint.sh && \
    sudo chmod 755 /launch.sh

ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["/launch.sh"]