#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster
import socket
import struct
import zlib
import numpy as np
import cv2
from scipy.spatial.transform import Rotation as R

class DirectARKitSync(Node):
    def __init__(self):
        super().__init__('direct_arkit_sync')
        
        # 🚀 THE SYNCHRONIZED PUBLISHERS
        self.pub_rgb = self.create_publisher(Image, '/synced/rgb/image_raw', 10)
        self.pub_depth = self.create_publisher(Image, '/synced/depth/image_raw', 10)
        self.pub_info = self.create_publisher(CameraInfo, '/synced/camera_info', 10)
        self.pub_odom = self.create_publisher(Odometry, '/synced/odom', 10)
        self.tf_broadcaster = TransformBroadcaster(self)
        
        # 🚀 HIGH-SPEED UDP SOCKET
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8 * 1024 * 1024)
        self.sock.bind(('0.0.0.0', 8765)) # Ensure this matches your iOS app port!
        self.sock.setblocking(False)
        
        self.timer = self.create_timer(0.001, self.poll_socket)
        
        # Buffers
        self.udp_chunks = {}
        self.sync_buffer = {} # Pairs RGB and Depth by iOS timestamp
        self.latest_odom_data = None
        self.latest_info_data = None

        self.get_logger().info("🔥 Direct ARKit Sync Active! Listening on UDP 8765...")

    def poll_socket(self):
        try:
            while True:
                data, _ = self.sock.recvfrom(65000)
                if len(data) < 14: continue
                
                topic_id, _, sec, nano, total_chunks, chunk_idx = struct.unpack('>BBIIHH', data[:14])
                frame_key = f"{topic_id}_{sec}_{nano}"
                
                if frame_key not in self.udp_chunks:
                    self.udp_chunks[frame_key] = {
                        'topic': topic_id, 'sec': sec, 'nano': nano,
                        'chunks': [None] * total_chunks, 'received': 0
                    }
                
                buffer = self.udp_chunks[frame_key]
                if buffer['chunks'][chunk_idx] is None:
                    buffer['chunks'][chunk_idx] = data[14:]
                    buffer['received'] += 1
                
                if buffer['received'] == total_chunks:
                    self.route_payload(buffer)
                    del self.udp_chunks[frame_key]
        except BlockingIOError:
            pass

    def route_payload(self, buffer):
        raw_data = b''.join(buffer['chunks'])
        stamp_key = f"{buffer['sec']}_{buffer['nano']}"
        topic = buffer['topic']

        # Update latest persistent data
        if topic == 2:
            self.latest_odom_data = raw_data
            return
        elif topic == 3:
            self.latest_info_data = raw_data
            return

        # Buffer RGB and Depth for perfect synchronization
        if stamp_key not in self.sync_buffer:
            self.sync_buffer[stamp_key] = {'rgb': None, 'depth': None}
            
            # Memory safety: Keep only the last 5 frames in buffer
            if len(self.sync_buffer) > 5:
                oldest_key = list(self.sync_buffer.keys())[0]
                del self.sync_buffer[oldest_key]

        if topic == 0:
            self.sync_buffer[stamp_key]['rgb'] = raw_data
        elif topic == 1:
            self.sync_buffer[stamp_key]['depth'] = raw_data

        # 🚀 TRIGGER: If we have both RGB and Depth for this exact microsecond, publish!
        if self.sync_buffer[stamp_key]['rgb'] and self.sync_buffer[stamp_key]['depth']:
            self.publish_unified_frame(self.sync_buffer[stamp_key]['rgb'], self.sync_buffer[stamp_key]['depth'])
            del self.sync_buffer[stamp_key]

    def publish_unified_frame(self, rgb_data, depth_data):
        if not self.latest_odom_data or not self.latest_info_data:
            return # Wait until we have at least one Odom and Info packet

        # 1. THE UNIFIED TIMESTAMP
        now = self.get_clock().now().to_msg()
        TARGET_W, TARGET_H = 480, 360

        # ==========================================
        # 2. DECOMPRESS & PUBLISH RGB
        # ==========================================
        np_arr = np.frombuffer(rgb_data, np.uint8)
        cv_rgb = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if cv_rgb is None: return

        rgb_msg = Image()
        rgb_msg.header.stamp, rgb_msg.header.frame_id = now, "camera_optical_link"
        rgb_msg.height, rgb_msg.width = TARGET_H, TARGET_W
        rgb_msg.encoding, rgb_msg.is_bigendian = "bgr8", 0
        rgb_msg.step = TARGET_W * 3
        rgb_msg.data = cv_rgb.tobytes()
        self.pub_rgb.publish(rgb_msg)

        # ==========================================
        # 3. DECOMPRESS & PUBLISH DEPTH
        # ==========================================
        try:
            try:
                decomp_depth = zlib.decompress(depth_data, 15 + 32)
            except zlib.error:
                decomp_depth = zlib.decompress(depth_data, -15)
        except Exception:
            return

        depth_msg = Image()
        depth_msg.header.stamp, depth_msg.header.frame_id = now, "camera_optical_link"
        depth_msg.height, depth_msg.width = TARGET_H, TARGET_W
        depth_msg.encoding, depth_msg.is_bigendian = "32FC1", 0
        depth_msg.step = TARGET_W * 4
        depth_msg.data = decomp_depth
        self.pub_depth.publish(depth_msg)

        # ==========================================
        # 4. PUBLISH CAMERA INFO
        # ==========================================
        intrinsics = struct.unpack('<9f', self.latest_info_data)
        
        # ARKit sends Column-Major: fx, 0, 0, 0, fy, 0, cx, cy, 1
        # Extract the specific values using their column-major indices
        fx = intrinsics[0]
        fy = intrinsics[4]
        cx = intrinsics[6]
        cy = intrinsics[7]

        info_msg = CameraInfo()
        info_msg.header.stamp, info_msg.header.frame_id = now, "camera_optical_link"
        info_msg.width, info_msg.height = TARGET_W, TARGET_H
        
        # 🚀 MANDATORY FOR RTAB-MAP: Declare the distortion model so it passes calibration checks
        info_msg.distortion_model = "plumb_bob"
        info_msg.d = [0.0, 0.0, 0.0, 0.0, 0.0]
        
        # Pack them back into Row-Major format for ROS
        info_msg.k = [
            fx,  0.0, cx,
            0.0, fy,  cy,
            0.0, 0.0, 1.0
        ]
        info_msg.p = [
            fx,  0.0, cx,  0.0,
            0.0, fy,  cy,  0.0,
            0.0, 0.0, 1.0, 0.0
        ]
        self.pub_info.publish(info_msg)
        # ==========================================
        # 5. ODOMETRY & ALL TRANSFORMS
        # ==========================================
        mat_flat = struct.unpack('<16f', self.latest_odom_data)
        ar_mat = np.array(mat_flat).reshape(4, 4).T 

        # Keep original translation mapping
        ros_tx, ros_ty, ros_tz = -ar_mat[2, 3], -ar_mat[0, 3], ar_mat[1, 3]
        
        # Get base rotation matrix from ARKit
        swift_rotation_map = np.array([[0,0,1,0], [1,0,0,0], [0,1,0,0], [0,0,0,1]])
        ros_rot_mat = ar_mat @ swift_rotation_map
        base_rot = R.from_matrix(ros_rot_mat[0:3, 0:3])

        # 🚀 EXTRACT EULER ANGLES (Roll, Pitch, Yaw)
        roll, pitch, yaw = base_rot.as_euler('xyz', degrees=True)

        # 🚀 APPLY YOUR CUSTOM CORRECTIONS
        # 1. Swap Roll and Yaw
        new_roll = -yaw
        new_pitch = pitch
        new_yaw = roll
        
        # 2. Rotate Yaw 90 degrees clockwise 
        # (In ROS right-hand rule, Z-up means CCW is positive, so Clockwise is -90)
        # Note: If it rotates the wrong way in RViz, change this to += 90.0
        new_yaw -= 90.0
        new_roll += 90.0

        # Pack back into the quaternion for ROS
        quat = R.from_euler('xyz', [new_roll, new_pitch, new_yaw], degrees=True).as_quat()

        # A. Main Transform (odom -> camera_link)
        t = TransformStamped()
        t.header.stamp, t.header.frame_id = now, 'odom'
        t.child_frame_id = 'camera_link'
        t.transform.translation.x, t.transform.translation.y, t.transform.translation.z = float(ros_tx), float(ros_ty), float(ros_tz)
        t.transform.rotation.x, t.transform.rotation.y, t.transform.rotation.z, t.transform.rotation.w = quat[0], quat[1], quat[2], quat[3]
        self.tf_broadcaster.sendTransform(t)

        # 🚀 B. THE CHASSIS BRIDGE (camera_link -> base_link)
        t_base = TransformStamped()
        t_base.header.stamp = now
        t_base.header.frame_id = 'camera_link'
        t_base.child_frame_id = 'base_link'
        t_base.transform.translation.x = 0.0
        t_base.transform.translation.y = 0.0
        t_base.transform.translation.z = 0.0
        t_base.transform.rotation.x = 0.0
        t_base.transform.rotation.y = 0.0
        t_base.transform.rotation.z = 0.0
        t_base.transform.rotation.w = 1.0  # Identity rotation (0 offset)
        self.tf_broadcaster.sendTransform(t_base)

        # 🚀 C. THE GOD MODE BYPASS (map -> odom)
        t_map = TransformStamped()
        t_map.header.stamp = now
        t_map.header.frame_id = 'map'
        t_map.child_frame_id = 'odom'
        t_map.transform.translation.x = 0.0
        t_map.transform.translation.y = 0.0
        t_map.transform.translation.z = 0.0
        t_map.transform.rotation.x = 0.0
        t_map.transform.rotation.y = 0.0
        t_map.transform.rotation.z = 0.0
        t_map.transform.rotation.w = 1.0  # Identity rotation (0 offset)
        self.tf_broadcaster.sendTransform(t_map)

        # B. Static Optical Transform (camera_link -> camera_optical_link)
        t_opt = TransformStamped()
        t_opt.header.stamp, t_opt.header.frame_id = now, 'camera_link'
        t_opt.child_frame_id = 'camera_optical_link'
        q_opt = R.from_euler('xyz', [-90, 0, -90], degrees=True).as_quat()
        t_opt.transform.rotation.x, t_opt.transform.rotation.y, t_opt.transform.rotation.z, t_opt.transform.rotation.w = q_opt[0], q_opt[1], q_opt[2], q_opt[3]
        self.tf_broadcaster.sendTransform(t_opt)

        # C. Odometry Message
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