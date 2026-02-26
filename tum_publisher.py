import os
import sys
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
import cv2
import numpy as np

class TUMPublisher(Node):
    def __init__(self, dataset_path):
        super().__init__('tum_publisher')
        
        self.rgb_pub = self.create_publisher(Image, '/camera/rgb/image_color', 10)
        self.depth_pub = self.create_publisher(Image, '/camera/depth/image', 10)
        self.cam_info_pub = self.create_publisher(CameraInfo, '/camera/rgb/camera_info', 10)
        
        self.dataset_path = dataset_path
        self.idx = 0
        
        self.pairs = self.sync_dataset()
        self.get_logger().info(f"Found {len(self.pairs)} synchronized frames. Publishing at 30 Hz...")
        self.timer = self.create_timer(0.033, self.publish_frames)

    def sync_dataset(self):
        rgb_lines = [l.strip().split() for l in open(os.path.join(self.dataset_path, 'rgb.txt')) if not l.startswith('#')]
        depth_lines = [l.strip().split() for l in open(os.path.join(self.dataset_path, 'depth.txt')) if not l.startswith('#')]
        
        pairs = []
        depth_times = [float(l[0]) for l in depth_lines]
        
        for r_time, r_path in rgb_lines:
            r_t = float(r_time)
            diffs = [abs(r_t - d_t) for d_t in depth_times]
            min_idx = diffs.index(min(diffs))
            if diffs[min_idx] < 0.02: 
                pairs.append((r_path, depth_lines[min_idx][1]))
        return pairs

    def cv2_to_imgmsg(self, cv_image, encoding):
        msg = Image()
        msg.height = cv_image.shape[0]
        msg.width = cv_image.shape[1]
        msg.encoding = encoding
        msg.is_bigendian = 0
        if encoding == "bgr8":
            msg.step = msg.width * 3
        elif encoding == "16UC1":
            msg.step = msg.width * 2
        msg.data = cv_image.tobytes()
        return msg

    def publish_frames(self):
        if self.idx >= len(self.pairs):
            self.get_logger().info("Dataset playback complete.")
            self.timer.cancel()
            return
            
        rgb_file, depth_file = self.pairs[self.idx]
        
        rgb_img = cv2.imread(os.path.join(self.dataset_path, rgb_file), cv2.IMREAD_COLOR)
        depth_img = cv2.imread(os.path.join(self.dataset_path, depth_file), cv2.IMREAD_UNCHANGED)
        
        # --- THE FIX: Convert TUM depth (5000=1m) to ROS depth (1000=1m) ---
        depth_img = (depth_img / 5.0).astype(np.uint16)
        
        now = self.get_clock().now().to_msg()
        
        rgb_msg = self.cv2_to_imgmsg(rgb_img, "bgr8")
        rgb_msg.header.stamp = now
        rgb_msg.header.frame_id = "camera_optical_link"
        self.rgb_pub.publish(rgb_msg)
        
        depth_msg = self.cv2_to_imgmsg(depth_img, "16UC1")
        depth_msg.header.stamp = now
        depth_msg.header.frame_id = "camera_optical_link"
        self.depth_pub.publish(depth_msg)
        
        cam_info = CameraInfo()
        cam_info.header.stamp = now
        cam_info.header.frame_id = "camera_optical_link"
        cam_info.width = 640
        cam_info.height = 480
        cam_info.k = [520.9, 0.0, 325.1, 0.0, 521.0, 249.7, 0.0, 0.0, 1.0]
        cam_info.p = [520.9, 0.0, 325.1, 0.0, 0.0, 521.0, 249.7, 0.0, 0.0, 0.0, 1.0, 0.0]
        self.cam_info_pub.publish(cam_info)
        
        self.idx += 1

def main():
    rclpy.init()
    dataset_folder = "rgbd_dataset_freiburg2_pioneer_360" 
    
    if not os.path.exists(dataset_folder):
        print(f"Error: Could not find '{dataset_folder}'.")
        sys.exit(1)
        
    node = TUMPublisher(dataset_folder)
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
        
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()