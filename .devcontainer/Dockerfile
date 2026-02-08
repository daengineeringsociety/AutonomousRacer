FROM ros:foxy-ros-core

RUN apt-get update && apt-get install -y \
    sudo \
    git \               
    bash-completion \
    ros-foxy-rmw-cyclonedds-cpp \
    python3-rosdep \
    kmod \
    && rm -rf /var/lib/apt/lists/*

# Create the 'daes' user
ARG USERNAME=daes
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

RUN curl https://install.husarnet.com/install.sh | bash

RUN ARCH=$(uname -m | sed 's/x86_64/amd64/' | sed 's/aarch64/arm64/') && \
    curl -L "https://github.com/husarnet/husarnet-dds/releases/download/v1.3.6/husarnet-dds-linux-$ARCH" -o /usr/bin/husarnet-dds && \
    chmod +x /usr/bin/husarnet-dds

# Set up the ROS environment for the 'daes' user
RUN echo "source /opt/ros/foxy/setup.bash" >> /home/$USERNAME/.bashrc

USER $USERNAME