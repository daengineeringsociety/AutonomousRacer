# arkit_ros2_bridge
ROS2 Package to interface with https://github.com/ion206/ARKit-to-ROS-Bridge-V2


Mac users:
brew install socat
socat udp-listen:8000,reuseaddr,fork udp:127.0.0.1:8765
 Maps the recieinvg port 8000 to localhost 8765 to be accessed in the docker container