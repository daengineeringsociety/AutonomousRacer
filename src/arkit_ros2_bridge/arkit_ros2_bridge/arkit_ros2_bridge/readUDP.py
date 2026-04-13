#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage, Image, CameraInfo
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster
import socket
import struct
import zlib
import numpy as np
from builtin_interfaces.msg import Time
from scipy.spatial.transform import Rotation as R

class MultiplexedUDPReceiver(Node):
    def __init__(self):
        super().__init__('ios_vslam_bridge')
        
        # Publishers
        self.pub_rgb = self.create_publisher(CompressedImage, '/camera/rgb/compressed', 10)
        self.pub_depth = self.create_publisher(Image, '/camera/depth/image_raw', 10)
        self.pub_odom = self.create_publisher(Odometry, '/odom', 10)
        self.pub_info = self.create_publisher(CameraInfo, '/camera/rgb/camera_info', 10)
        self.tf_broadcaster = TransformBroadcaster(self)
        
        # Networking - 8MB Buffer for High-Speed LiDAR
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8 * 1024 * 1024)
        self.sock.bind(('0.0.0.0', 8765))
        self.sock.setblocking(False)
        
        self.timer = self.create_timer(0.001, self.poll_socket)
        self.frame_buffers = {}

    def poll_socket(self):
        try:
            while True:
                data, _ = self.sock.recvfrom(65000)
                if len(data) < 14: continue
                
                topic_id, _, sec, nano, total_chunks, chunk_idx = struct.unpack('>BBIIHH', data[:14])
                frame_key = f"{topic_id}_{sec}_{nano}"
                
                if frame_key not in self.frame_buffers:
                    self.frame_buffers[frame_key] = {
                        'topic': topic_id, 'chunks': [None] * total_chunks, 'received': 0
                    }
                
                buffer = self.frame_buffers[frame_key]
                if buffer['chunks'][chunk_idx] is None:
                    buffer['chunks'][chunk_idx] = data[14:]
                    buffer['received'] += 1
                
                if buffer['received'] == total_chunks:
                    stamp = Time(sec=sec, nanosec=nano)
                    self.process_assembled_payload(buffer, stamp)
                    del self.frame_buffers[frame_key]
        except BlockingIOError:
            pass

    def process_assembled_payload(self, buffer, stamp):
        raw_data = b''.join(buffer['chunks'])
        if buffer['topic'] == 0:    # RGB
            self.publish_rgb(raw_data, stamp)
        elif buffer['topic'] == 1:  # DEPTH
            self.publish_depth(raw_data, stamp)
        elif buffer['topic'] == 2:  # ODOM / TF
            self.publish_tf_odom(raw_data, stamp)
        elif buffer['topic'] == 3:  # CAMERA INFO
            self.publish_camera_info(raw_data, stamp)

    def publish_rgb(self, data, stamp):
        msg = CompressedImage()
        msg.header.stamp = stamp
        msg.header.frame_id = "camera_optical_frame"
        msg.format = "jpeg"
        msg.data = np.frombuffer(data, dtype=np.uint8).tobytes()
        self.pub_rgb.publish(msg)

    def publish_depth(self, data, stamp):
        try:
            # Multi-mode decompression for Apple Zlib headers
            try:
                decompressed = zlib.decompress(data, 15 + 32)
            except zlib.error:
                decompressed = zlib.decompress(data, -15)
            
            msg = Image()
            msg.header.stamp = stamp
            msg.header.frame_id = "camera_optical_frame"
            msg.height, msg.width = 192, 256
            msg.encoding, msg.step = "32FC1", 256 * 4
            msg.data = np.frombuffer(decompressed, dtype=np.uint8).tobytes()
            self.pub_depth.publish(msg)
        except Exception:
            pass

    def publish_tf_odom(self, data, stamp):
        # 16 floats from ARKit (Column-Major)
        mat_flat = struct.unpack('<16f', data)
        ar_mat = np.array(mat_flat).reshape(4, 4).T 

        # Your verified Swift Coordinate Mapping
        ros_tx, ros_ty, ros_tz = -ar_mat[2, 3], -ar_mat[0, 3], ar_mat[1, 3]

        # Rotation remapping matrix
        swift_rotation_map = np.array([[0,0,1,0], [1,0,0,0], [0,1,0,0], [0,0,0,1]])
        ros_rot_mat = ar_mat @ swift_rotation_map
        quat = R.from_matrix(ros_rot_mat[0:3, 0:3]).as_quat()

        # TF Broadcast
        t = TransformStamped()
        t.header.stamp, t.header.frame_id = stamp, 'odom'
        t.child_frame_id = 'camera_optical_frame'
        t.transform.translation.x, t.transform.translation.y, t.transform.translation.z = float(ros_tx), float(ros_ty), float(ros_tz)
        t.transform.rotation.x, t.transform.rotation.y, t.transform.rotation.z, t.transform.rotation.w = quat[0], quat[1], quat[2], quat[3]
        self.tf_broadcaster.sendTransform(t)

        # Odom Publish
        odom = Odometry()
        odom.header, odom.child_frame_id = t.header, t.child_frame_id
        odom.pose.pose.position.x, odom.pose.pose.position.y, odom.pose.pose.position.z = float(ros_tx), float(ros_ty), float(ros_tz)
        odom.pose.pose.orientation = t.transform.rotation
        self.pub_odom.publish(odom)

    def publish_camera_info(self, data, stamp):
        intrinsics = struct.unpack('<9f', data)
        msg = CameraInfo()
        msg.header.stamp, msg.header.frame_id = stamp, "camera_optical_frame"
        msg.width, msg.height = 640, 480
        msg.k = [float(x) for x in intrinsics]
        self.pub_info.publish(msg)

def main():
    rclpy.init()
    node = MultiplexedUDPReceiver()
    rclpy.spin(node)

if __name__ == '__main__':
    main()