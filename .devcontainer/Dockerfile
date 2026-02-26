FROM ros:foxy-ros-core


# Add universe repo for nav2, turtlebot3, rosbridge etc.
RUN apt-get update && apt-get install -y \
    software-properties-common \
    && add-apt-repository universe \
    && apt-get update \
    && rm -rf /var/lib/apt/lists/*

# Install system and ROS packages
RUN apt-get update && apt-get install -y \
    sudo \
    git \
    bash-completion \
    curl \
    kmod \
    ufw \
    vim \
    iputils-ping \
    ros-foxy-rmw-cyclonedds-cpp \
    ros-foxy-teleop-twist-keyboard \
    ros-foxy-nav2-bringup \
    ros-foxy-rosbridge-suite \
    python3-rosdep \
    python3-pip \
    python3-colcon-common-extensions \
    ros-foxy-rtabmap* \
    ros-foxy-xacro \
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