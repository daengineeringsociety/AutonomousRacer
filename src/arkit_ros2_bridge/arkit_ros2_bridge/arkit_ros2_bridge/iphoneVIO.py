#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster
import socket
import struct
import numpy as np
from scipy.spatial.transform import Rotation as R

class DirectARKitSync(Node):
    def __init__(self):
        super().__init__('direct_arkit_sync')
        
        # 🚀 ONLY PUBLISH ODOMETRY & TF
        self.pub_odom = self.create_publisher(Odometry, '/synced/odom', 10)
        self.tf_broadcaster = TransformBroadcaster(self)
        
        # 🚀 HIGH-SPEED UDP SOCKET
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8 * 1024 * 1024)
        self.sock.bind(('0.0.0.0', 8765)) 
        self.sock.setblocking(False)
        
        # Polling insanely fast to catch the 60Hz stream instantly
        self.timer = self.create_timer(0.001, self.poll_socket)
        
        self.udp_chunks = {}
        self.get_logger().info("🔥 VIO Telemetry Active! Streaming 60Hz Odometry...")

    def poll_socket(self):
        try:
            while True:
                data, _ = self.sock.recvfrom(65000)
                if len(data) < 14: continue
                
                topic_id, _, sec, nano, total_chunks, chunk_idx = struct.unpack('>BBIIHH', data[:14])
                
                # We only care about Topic 2 (Odometry) now
                if topic_id != 2: continue 
                
                frame_key = f"{sec}_{nano}"
                
                if frame_key not in self.udp_chunks:
                    self.udp_chunks[frame_key] = {
                        'chunks': [None] * total_chunks, 'received': 0
                    }
                
                buffer = self.udp_chunks[frame_key]
                if buffer['chunks'][chunk_idx] is None:
                    buffer['chunks'][chunk_idx] = data[14:]
                    buffer['received'] += 1
                
                if buffer['received'] == total_chunks:
                    raw_data = b''.join(buffer['chunks'])
                    self.publish_odometry(raw_data)
                    del self.udp_chunks[frame_key]
        except BlockingIOError:
            pass

    def publish_odometry(self, odom_data):
        now = self.get_clock().now().to_msg()

        # ==========================================
        # 1. DECODE THE ARKIT MATRIX
        # ==========================================
        mat_flat = struct.unpack('<16f', odom_data)
        ar_mat = np.array(mat_flat).reshape(4, 4).T 

        # Keep original translation mapping
        ros_tx, ros_ty, ros_tz = -ar_mat[2, 3], -ar_mat[0, 3], ar_mat[1, 3]
        
        # Get base rotation matrix from ARKit
        swift_rotation_map = np.array([[0,0,1,0], [1,0,0,0], [0,1,0,0], [0,0,0,1]])
        ros_rot_mat = ar_mat @ swift_rotation_map
        base_rot = R.from_matrix(ros_rot_mat[0:3, 0:3])

        # Extract Euler Angles (Roll, Pitch, Yaw)
        roll, pitch, yaw = base_rot.as_euler('xyz', degrees=True)

        # APPLY CUSTOM CORRECTIONS
        new_roll = -yaw + 90.0
        new_pitch = pitch
        new_yaw = roll - 90.0

        # Pack back into the quaternion for ROS
        quat = R.from_euler('xyz', [new_roll, new_pitch, new_yaw], degrees=True).as_quat()

        # ==========================================
        # 2. BROADCAST THE TF TREE
        # ==========================================
        
        # A. Main Transform (odom -> camera_link)
        t = TransformStamped()
        t.header.stamp, t.header.frame_id = now, 'odom'
        t.child_frame_id = 'camera_link'
        t.transform.translation.x, t.transform.translation.y, t.transform.translation.z = float(ros_tx), float(ros_ty), float(ros_tz)
        t.transform.rotation.x, t.transform.rotation.y, t.transform.rotation.z, t.transform.rotation.w = quat[0], quat[1], quat[2], quat[3]
        self.tf_broadcaster.sendTransform(t)

        # B. Chassis Bridge (camera_link -> base_link)
        t_base = TransformStamped()
        t_base.header.stamp = now
        t_base.header.frame_id = 'camera_link'
        t_base.child_frame_id = 'base_link'
        t_base.transform.rotation.w = 1.0 
        self.tf_broadcaster.sendTransform(t_base)

        # C. God Mode Bypass (map -> odom)
        t_map = TransformStamped()
        t_map.header.stamp = now
        t_map.header.frame_id = 'map'
        t_map.child_frame_id = 'odom'
        t_map.transform.rotation.w = 1.0 
        self.tf_broadcaster.sendTransform(t_map)

        # ==========================================
        # 3. PUBLISH ODOMETRY TOPIC
        # ==========================================
        odom = Odometry()
        odom.header.stamp, odom.header.frame_id = now, 'odom'
        odom.child_frame_id = 'camera_link'
        odom.pose.pose.position.x, odom.pose.pose.position.y, odom.pose.pose.position.z = float(ros_tx), float(ros_ty), float(ros_tz)
        odom.pose.pose.orientation.x, odom.pose.pose.orientation.y, odom.pose.pose.orientation.z, odom.pose.pose.orientation.w = quat[0], quat[1], quat[2], quat[3]
        
        cov = [0.0] * 36
        cov[0] = cov[7] = cov[14] = cov[21] = cov[28] = cov[35] = 0.001
        odom.pose.covariance = cov
        self.pub_odom.publish(odom)

def main():
    rclpy.init()
    rclpy.spin(DirectARKitSync())

if __name__ == '__main__':
    main()