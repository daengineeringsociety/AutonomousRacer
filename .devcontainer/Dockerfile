FROM ros:foxy-ros-core

RUN apt-get update && apt-get install -y \
    sudo \
    git \               
    bash-completion \
    ros-foxy-rmw-cyclonedds-cpp \
    python3-rosdep \
    && rm -rf /var/lib/apt/lists/*

# Create the 'daes' user
ARG USERNAME=daes
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

# Set up the ROS environment for the 'daes' user
RUN echo "source /opt/ros/foxy/setup.bash" >> /home/$USERNAME/.bashrc

USER $USERNAME