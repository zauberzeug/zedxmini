# https://github.com/dusty-nv/jetson-containers/tree/master/packages#user-content-containers
# https://github.com/stereolabs/zed-ros2-wrapper/tree/master/docker

ARG L4T_VERSION=l4t-r35.4.1
ARG IMAGE_NAME=dustynv/ros:humble-ros-base-${L4T_VERSION}

FROM ${IMAGE_NAME}

ARG ZED_SDK_MAJOR=4
ARG ZED_SDK_MINOR=2
ARG ZED_SDK_PATCH=3
ARG JETPACK_MAJOR=5
ARG JETPACK_MINOR=1
ARG L4T_MAJOR=35
ARG L4T_MINOR=4

ARG ROS2_DIST=humble
ENV DEBIAN_FRONTEND noninteractive

# ZED SDK link
ENV ZED_SDK_URL="https://stereolabs.sfo2.cdn.digitaloceanspaces.com/zedsdk/${ZED_SDK_MAJOR}.${ZED_SDK_MINOR}/ZED_SDK_Tegra_L4T${L4T_MAJOR}.${L4T_MINOR}_v${ZED_SDK_MAJOR}.${ZED_SDK_MINOR}.${ZED_SDK_PATCH}.zstd.run"

# Check that this SDK exists
RUN if [ "$(curl -I "${ZED_SDK_URL}" -o /dev/null -s -w '%{http_code}\n' | head -n 1)" = "200" ]; then \
        echo "The URL points to something."; \
    else \
        echo "The URL does not point to a .run file or the file does not exist."; \
        exit 1; \
    fi

# Disable apt-get warnings
RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 42D5A192B819C5DA || true && \
  apt-get update || true && apt-get install -y --no-install-recommends apt-utils dialog && \
  rm -rf /var/lib/apt/lists/*

ENV TZ=Europe/Berlin

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone && \ 
  apt-get update && \
  apt-get install --yes lsb-release wget less udev sudo build-essential cmake python3 python3-dev python3-pip python3-wheel git jq libpq-dev zstd usbutils && \    
  rm -rf /var/lib/apt/lists/*

RUN echo "# R${L4T_MAJOR} (release), REVISION: ${L4T_MINOR}" > /etc/nv_tegra_release && \
  apt-get update -y || true && \
  apt-get install -y --no-install-recommends zstd wget less cmake curl gnupg2 \
  build-essential python3 python3-pip python3-dev python3-setuptools libusb-1.0-0-dev -y && \
  pip install protobuf && \
  wget -q --no-check-certificate -O ZED_SDK_Linux_JP.run \
  ${ZED_SDK_URL} && \
  chmod +x ZED_SDK_Linux_JP.run ; ./ZED_SDK_Linux_JP.run silent skip_tools && \
  rm -rf /usr/local/zed/resources/* && \
  rm -rf ZED_SDK_Linux_JP.run && \
  rm -rf /var/lib/apt/lists/*

# Install the ZED ROS2 Wrapper
ENV ROS_DISTRO ${ROS2_DIST}

RUN apt-get update && apt-get install --yes zlib1g-dev libwebsocketpp-dev rapidjson-dev && rm -rf /var/lib/apt/lists/*

RUN wget https://raw.githubusercontent.com/dusty-nv/jetson-containers/refs/heads/master/packages/ros/ros2_install.sh -O /ros2_install.sh && chmod 755 /ros2_install.sh
RUN /ros2_install.sh robot_localization
RUN /ros2_install.sh geographic_info
RUN /ros2_install.sh nmea_msgs
RUN /ros2_install.sh "https://github.com/ros2/rcpputils.git -b humble"
RUN /ros2_install.sh "https://github.com/ros2/message_filters.git -b humble"
RUN /ros2_install.sh "https://github.com/ros-perception/point_cloud_transport.git -b humble"
RUN /ros2_install.sh zed_msgs
RUN /ros2_install.sh "https://github.com/stereolabs/zed-ros2-wrapper.git --recursive"
RUN /ros2_install.sh "https://github.com/ros2-gbp/xacro-release.git -b release/humble/xacro"
RUN /ros2_install.sh "https://github.com/ros/resource_retriever.git -b humble"
RUN /ros2_install.sh "https://github.com/facontidavide/rosx_introspection.git"
RUN /ros2_install.sh "https://github.com/nlohmann/json.git"
RUN /ros2_install.sh https://github.com/foxglove/ros-foxglove-bridge.git

# Copy your custom files
COPY ros_entrypoint.sh /sbin/ros_entrypoint.sh
COPY launch.py /sbin/launch.py

# Set correct permissions
RUN sudo chmod 755 /sbin/ros_entrypoint.sh

ENTRYPOINT ["source \"/opt/ros/$ROS_DISTRO/install/setup.bash\" && ros2 launch /sbin/launch.py"]
CMD ["bash"]