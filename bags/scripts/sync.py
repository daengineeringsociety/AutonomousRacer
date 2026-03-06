import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage, Image, CameraInfo
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster
import numpy as np
from scipy.spatial.transform import Rotation as R
from rclpy.qos import qos_profile_sensor_data
import cv2

class ARKitSync(Node):
    def __init__(self):
        super().__init__('arkit_sync')

        # --- Constants ---
        self.TARGET_W = 480
        self.TARGET_H = 360

        # --- Publishers (Synced Output) ---
        self.rgb_pub = self.create_publisher(Image, '/synced/rgb/image_raw', 10)
        self.depth_pub = self.create_publisher(Image, '/synced/depth/image_raw', 10)
        self.info_pub = self.create_publisher(CameraInfo, '/synced/camera_info', 10)
        self.odom_pub = self.create_publisher(Odometry, '/synced/odom', 10)
        self.tf_broadcaster = TransformBroadcaster(self)

        # --- Subscribers (Raw Bag Data) ---
        self.sub_rgb = self.create_subscription(
            CompressedImage, 
            '/camera/rgb/compressed', 
            self.rgb_cb, 
            qos_profile_sensor_data
        )
        self.sub_odom = self.create_subscription(
            Odometry, 
            '/odom', 
            self.odom_cb, 
            qos_profile_sensor_data
        )
        self.sub_depth = self.create_subscription(
            Image, 
            '/camera/depth/image_raw', 
            self.depth_cb, 
            qos_profile_sensor_data
        )

        self.latest_rgb = None
        self.latest_odom = None

        self.get_logger().info("ARKit Sync Started! Play your bag file...")

    def rgb_cb(self, msg):
        self.latest_rgb = msg

    def odom_cb(self, msg):
        self.latest_odom = msg

    def depth_cb(self, depth_msg):
        """
        The depth callback acts as the trigger for the sync process.
        """
        if self.latest_rgb is None or self.latest_odom is None:
            return

        now = self.get_clock().now().to_msg()

        # --- 1. Process & Resize RGB ---
        np_arr = np.frombuffer(self.latest_rgb.data, np.uint8)
        cv_rgb = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        cv_rgb_resized = cv2.resize(
            cv_rgb, (self.TARGET_W, self.TARGET_H), interpolation=cv2.INTER_LINEAR
        )

        rgb_raw_msg = Image()
        rgb_raw_msg.header.stamp = now
        rgb_raw_msg.header.frame_id = "camera_optical_link"
        rgb_raw_msg.height = self.TARGET_H
        rgb_raw_msg.width = self.TARGET_W
        rgb_raw_msg.encoding = "bgr8"
        rgb_raw_msg.step = self.TARGET_W * 3
        rgb_raw_msg.data = cv_rgb_resized.tobytes()
        self.rgb_pub.publish(rgb_raw_msg)

        # --- 2. Process & Resize DEPTH ---
        # Handle different depth encodings safely
        if depth_msg.encoding == '32FC1':
            dtype = np.float32
            bytes_per_pixel = 4
        elif depth_msg.encoding == '16UC1':
            dtype = np.uint16
            bytes_per_pixel = 2
        else:
            self.get_logger().warn(f"Unsupported depth encoding: {depth_msg.encoding}")
            return

        depth_img = np.frombuffer(depth_msg.data, dtype=dtype).reshape(
            (depth_msg.height, depth_msg.width)
        )

        # INTER_NEAREST is crucial for depth to avoid ghosting/interpolation artifacts
        depth_resized = cv2.resize(
            depth_img, (self.TARGET_W, self.TARGET_H), interpolation=cv2.INTER_NEAREST
        )

        depth_raw_msg = Image()
        depth_raw_msg.header.stamp = now
        depth_raw_msg.header.frame_id = "camera_optical_link"
        depth_raw_msg.height = self.TARGET_H
        depth_raw_msg.width = self.TARGET_W
        depth_raw_msg.encoding = depth_msg.encoding
        depth_raw_msg.is_bigendian = depth_msg.is_bigendian
        depth_raw_msg.step = self.TARGET_W * bytes_per_pixel
        depth_raw_msg.data = depth_resized.tobytes()
        self.depth_pub.publish(depth_raw_msg)

        # --- 3. Publish Camera Info ---
        info_msg = CameraInfo()
        info_msg.header.stamp = now
        info_msg.header.frame_id = "camera_optical_link"
        info_msg.width = self.TARGET_W
        info_msg.height = self.TARGET_H
        # Update intrinsics based on 480x360 scale
        info_msg.k = [360.93, 0.0, 238.43, 0.0, 360.93, 182.25, 0.0, 0.0, 1.0]
        info_msg.p = [360.93, 0.0, 238.43, 0.0, 0.0, 360.93, 182.25, 0.0, 0.0, 0.0, 1.0, 0.0]
        self.info_pub.publish(info_msg)

        # --- 4. Process Odometry and TF ---
        self.process_odom(self.latest_odom, now)

    def process_odom(self, odom_msg, now):
        # Extract Position
        pos = odom_msg.pose.pose.position
        
        # Correct Rotation (Coordinate Frame Alignment)
        q = odom_msg.pose.pose.orientation
        raw_rotation = R.from_quat([q.x, q.y, q.z, q.w])
        correction = R.from_euler('xyz', [180.0, -90.0, 90.0], degrees=True)
        final_rot = (raw_rotation * correction).as_quat()

        # Broadcast TF
        t = TransformStamped()
        t.header.stamp = now
        t.header.frame_id = 'odom'
        t.child_frame_id = 'camera_link'
        t.transform.translation.x = float(pos.x)
        t.transform.translation.y = float(pos.y)
        t.transform.translation.z = float(pos.z)
        t.transform.rotation.x = final_rot[0]
        t.transform.rotation.y = final_rot[1]
        t.transform.rotation.z = final_rot[2]
        t.transform.rotation.w = final_rot[3]
        self.tf_broadcaster.sendTransform(t)

        # Publish Fixed Odometry
        fixed_odom = Odometry()
        fixed_odom.header.stamp = now
        fixed_odom.header.frame_id = 'odom'
        fixed_odom.child_frame_id = 'camera_link'
        fixed_odom.pose.pose.position = pos
        fixed_odom.pose.pose.orientation.x = final_rot[0]
        fixed_odom.pose.pose.orientation.y = final_rot[1]
        fixed_odom.pose.pose.orientation.z = final_rot[2]
        fixed_odom.pose.pose.orientation.w = final_rot[3]

        # Add reasonable covariance for SLAM systems
        cov = [0.0] * 36
        for i in range(0, 36, 7):
            cov[i] = 0.001
        fixed_odom.pose.covariance = cov

        self.odom_pub.publish(fixed_odom)

def main(args=None):
    rclpy.init(args=args)
    node = ARKitSync()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()