# https://github.com/stereolabs/zed-ros2-wrapper/tree/master/docker

# Avalible dustynv ros humble images:
# 36.3.0 for Jetpack 6, 35.4.1 for Jetpack 5, 32.7.1 for Jetpack 4

# Base image with ROS Noetic
ARG IMAGE_NAME=dustynv/ros:noetic-ros-core-l4t-r35.2.1

FROM ${IMAGE_NAME}

ARG ZED_SDK_MAJOR=4
ARG ZED_SDK_MINOR=2
ARG ZED_SDK_PATCH=3
ARG L4T_MAJOR=35
ARG L4T_MINOR=2

# ROS distribution
ARG ROS_DIST=noetic

ENV DEBIAN_FRONTEND=noninteractive

# Add ROS repository
RUN sh -c 'echo "deb http://packages.ros.org/ros/ubuntu $(lsb_release -sc) main" > /etc/apt/sources.list.d/ros-latest.list' && \
    curl -s https://raw.githubusercontent.com/ros/rosdistro/master/ros.asc | apt-key add -

# Install basic system dependencies first
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3-pip \
    wget \
    zstd \
    build-essential \
    cmake \
    curl \
    usbutils \
    python3-dev \
    python3-setuptools \
    libusb-1.0-0-dev \
    libgeographic-dev \
    zlib1g-dev \
    net-tools \
    python3-tornado \
    git \
    lsb-release \
    gnupg2 \
    libwebsocketpp-dev \
    libboost-all-dev \
    libasio-dev \
    libssl-dev \
    nlohmann-json3-dev \
    openssl && \
    rm -rf /var/lib/apt/lists/*

# Create dpkg preferences to prevent OpenCV installation
RUN echo 'Package: libopencv*\nPin: release *\nPin-Priority: -1\n' > /etc/apt/preferences.d/opencv && \
    echo 'Package: python3-opencv\nPin: release *\nPin-Priority: -1\n' >> /etc/apt/preferences.d/opencv

# Install ROS packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ros-${ROS_DIST}-catkin \
    ros-${ROS_DIST}-tf2-ros \
    ros-${ROS_DIST}-tf2-msgs \
    ros-${ROS_DIST}-tf2-geometry-msgs \
    ros-${ROS_DIST}-diagnostic-updater \
    ros-${ROS_DIST}-robot-state-publisher \
    ros-${ROS_DIST}-xacro \
    ros-${ROS_DIST}-image-transport \
    ros-${ROS_DIST}-nodelet \
    ros-${ROS_DIST}-nodelet-core \
    ros-${ROS_DIST}-pluginlib \
    ros-${ROS_DIST}-resource-retriever \
    ros-${ROS_DIST}-ros-environment \
    ros-${ROS_DIST}-rosbridge-suite \
    ros-${ROS_DIST}-rosbridge-server \
    ros-${ROS_DIST}-rosapi \
    ros-${ROS_DIST}-common-msgs \
    ros-${ROS_DIST}-roscpp-tutorials && \
    rm -rf /var/lib/apt/lists/*

# ZED SDK link
ENV ZED_SDK_URL="https://stereolabs.sfo2.cdn.digitaloceanspaces.com/zedsdk/${ZED_SDK_MAJOR}.${ZED_SDK_MINOR}/ZED_SDK_Tegra_L4T${L4T_MAJOR}.${L4T_MINOR}_v${ZED_SDK_MAJOR}.${ZED_SDK_MINOR}.${ZED_SDK_PATCH}.zstd.run"

# Check that this SDK exists
RUN if [ "$(curl -I "${ZED_SDK_URL}" -o /dev/null -s -w '%{http_code}\n' | head -n 1)" = "200" ]; then \
        echo "The URL points to something."; \
    else \
        echo "The URL does not point to a .run file or the file does not exist."; \
        exit 1; \
    fi

# Install ZED SDK
RUN echo "# R${L4T_MAJOR} (release), REVISION: ${L4T_MINOR}" > /etc/nv_tegra_release && \
    apt-get update -y || true && \
    apt-get install -y --no-install-recommends zstd wget less cmake curl gnupg2 \
    build-essential python3 python3-pip python3-dev python3-setuptools libusb-1.0-0-dev \ 
    libgeographic-dev zlib1g-dev -y && \
    pip install protobuf && \
    wget -q --no-check-certificate -O ZED_SDK_Linux_JP.run \
    ${ZED_SDK_URL} && \
    chmod +x ZED_SDK_Linux_JP.run ; ./ZED_SDK_Linux_JP.run silent skip_tools && \
    mkdir -p /usr/local/zed/resources && \
    rm -rf ZED_SDK_Linux_JP.run && \
    rm -rf /var/lib/apt/lists/*

# Create catkin workspace and clone ZED ROS wrapper and Foxglove Bridge
WORKDIR /root/catkin_ws/src
RUN git clone --recursive https://github.com/stereolabs/zed-ros-wrapper.git && \
    git clone --recursive https://github.com/foxglove/ros-foxglove-bridge.git && \
    git clone --recursive https://github.com/StefanFabian/ros_babel_fish.git

# Build the workspace
WORKDIR /root/catkin_ws
RUN /bin/bash -c "source /opt/ros/$ROS_DISTRO/setup.bash && \
    catkin_make -DCMAKE_BUILD_TYPE=Release"

# Setup environment variables 
COPY ros_entrypoint_jetson.sh /sbin/ros_entrypoint.sh
COPY launch.sh /sbin/launch.sh
RUN sudo chmod 755 /sbin/ros_entrypoint.sh && \
    sudo chmod 755 /sbin/launch.sh

ENTRYPOINT ["/sbin/ros_entrypoint.sh"]
CMD ["/sbin/launch.sh"]