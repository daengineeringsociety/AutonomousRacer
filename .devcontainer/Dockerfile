FROM ros:humble-ros-base

# Add a non-root user (match UID/GID 1000 for standard Mac/Linux)
ARG USERNAME=ros_user
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && apt-get update \
    && apt-get install -y sudo \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

# Install basic dev tools
RUN apt-get update && apt-get install -y \
    python3-colcon-common-extensions \
    python3-rosdep \
    git \
    && rm -rf /var/lib/apt/lists/*

# Initialize rosdep
RUN rosdep update

# Set up the workspace
USER $USERNAME
WORKDIR /home/$USERNAME/ros2_ws

# Automatically source ROS2 in every new terminal
RUN echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc