#!/usr/bin/env python3
"""
KFS + weapon 3D grasp node: subscribes to 2D detections and depth, computes 3D poses.
Uses TF to transform camera points into base frame.
"""
import numpy as np
import cv2
from typing import cast, Optional

import rclpy
from rclpy.node import Node
from rclpy.duration import Duration

from sensor_msgs.msg import Image, CameraInfo
from geometry_msgs.msg import PoseArray, Pose, PointStamped
from yolov8_ros2_msgs.msg import BoundingBoxes

from cv_bridge import CvBridge
import tf2_ros
from tf2_ros import TransformException  # type: ignore[attr-defined]
from message_filters import Subscriber, ApproximateTimeSynchronizer
# 注册 PointStamped 等类型到 TF2
from tf2_geometry_msgs import do_transform_point  # noqa: F401


class KFSWeapon3DGraspNode(Node):
    def __init__(self):
        super().__init__("kfs_weapon_3d_grasp")

        # ===== 参数 =====
        self.declare_parameter("boxes_topic", "/yolov8/BoundingBoxes")
        self.declare_parameter("depth_topic", "/camera/camera/aligned_depth_to_color/image_raw")
        self.declare_parameter("camera_info_topic", "/camera/camera/aligned_depth_to_color/camera_info")
        self.declare_parameter("base_frame", "base_link")

        self.declare_parameter("kfs_top_offset", 5)        # 从 bbox 顶部往内偏多少像素
        self.declare_parameter("kfs_roi_half_size", 3)     # ROI 半径
        self.declare_parameter("kfs_z_offset", 0.0)        # 抓取点再往上抬一点，可选
        self.declare_parameter("weapon_roi_half_size", 3)  # 武器头 ROI 半径
        self.declare_parameter("weapon_z_offset", 0.0)     # 武器头 Z 偏移
        self.declare_parameter("max_depth", 3.0)

        self.boxes_topic = self.get_parameter("boxes_topic").get_parameter_value().string_value
        self.depth_topic = self.get_parameter("depth_topic").get_parameter_value().string_value
        self.camera_info_topic = self.get_parameter("camera_info_topic").get_parameter_value().string_value
        self.base_frame = self.get_parameter("base_frame").get_parameter_value().string_value

        self.kfs_top_offset = self.get_parameter("kfs_top_offset").get_parameter_value().integer_value
        self.kfs_roi_half_size = self.get_parameter("kfs_roi_half_size").get_parameter_value().integer_value
        self.kfs_z_offset = self.get_parameter("kfs_z_offset").get_parameter_value().double_value
        self.weapon_roi_half_size = self.get_parameter("weapon_roi_half_size").get_parameter_value().integer_value
        self.weapon_z_offset = self.get_parameter("weapon_z_offset").get_parameter_value().double_value
        self.max_depth = self.get_parameter("max_depth").get_parameter_value().double_value

        # ===== 内参缓存 =====
        self.fx: Optional[float] = None
        self.fy: Optional[float] = None
        self.cx: Optional[float] = None
        self.cy: Optional[float] = None
        self.camera_info_received = False

        # 工具
        self.bridge = CvBridge()
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        # ===== 订阅 CameraInfo =====
        self.create_subscription(
            CameraInfo,
            self.camera_info_topic,
            self.camera_info_callback,
            10
        )

        # ===== message_filters 同步：BoundingBoxes + Depth =====
        self.boxes_sub = Subscriber(self, BoundingBoxes, self.boxes_topic)
        self.depth_sub = Subscriber(self, Image, self.depth_topic)
        self.sync = ApproximateTimeSynchronizer(
            [self.boxes_sub, self.depth_sub],
            queue_size=10,
            slop=0.03  # 30ms
        )
        self.sync.registerCallback(self.sync_callback)

        # ===== 发布 =====
        self.kfs_poses_pub = self.create_publisher(PoseArray, "/kfs_target_poses", 10)
        self.weapon_poses_pub = self.create_publisher(PoseArray, "/weapon_target_poses", 10)
        self.viz_pub = self.create_publisher(Image, "/kfs_weapon/grasp_viz", 1)

        self.get_logger().info("KFSWeapon3DGraspNode initialized.")

    # ---------- CameraInfo 回调 ----------
    def camera_info_callback(self, msg: CameraInfo):
        if not self.camera_info_received:
            self.fx = msg.k[0]
            self.fy = msg.k[4]
            self.cx = msg.k[2]
            self.cy = msg.k[5]
            self.camera_info_received = True
            self.get_logger().info(
                f"Camera intrinsics: fx={self.fx:.2f}, fy={self.fy:.2f}, cx={self.cx:.2f}, cy={self.cy:.2f}"
            )

    # ---------- 同步回调：bboxes + depth ----------
    def sync_callback(self, boxes_msg: BoundingBoxes, depth_msg: Image):
        if not self.camera_info_received:
            self.get_logger().warning("CameraInfo not received yet.")
            return

        # 深度转 numpy (m)
        try:
            depth = self.bridge.imgmsg_to_cv2(depth_msg, desired_encoding="passthrough")
        except Exception as e:
            self.get_logger().error(f"Depth convert failed: {e}")
            return

        depth_m = self.convert_depth_to_meters(depth, depth_msg.encoding)

        # 准备 PoseArray
        kfs_array = PoseArray()
        kfs_array.header.stamp = boxes_msg.header.stamp
        kfs_array.header.frame_id = self.base_frame

        weapon_array = PoseArray()
        weapon_array.header.stamp = boxes_msg.header.stamp
        weapon_array.header.frame_id = self.base_frame

        for box in boxes_msg.bounding_boxes:
            cls = box.class_name

            # 根据 class_name 区分 KFS / 武器头
            if cls.startswith("weapon"):
                pose = self.compute_weapon_grasp(box, depth_m, depth_msg)
                if pose is not None:
                    cast(list, weapon_array.poses).append(pose)
            else:
                pose = self.compute_kfs_grasp(box, depth_m, depth_msg)
                if pose is not None:
                    cast(list, kfs_array.poses).append(pose)

        if len(kfs_array.poses) > 0:
            self.kfs_poses_pub.publish(kfs_array)

        if len(weapon_array.poses) > 0:
            self.weapon_poses_pub.publish(weapon_array)

        # 可视化 2D 抓取点，便于在 rviz 中检查
        self.publish_grasp_viz(depth_m, depth_msg.header, boxes_msg.bounding_boxes, kfs_array, weapon_array)

    # ---------- KFS 3D 抓取方案 ----------
    def compute_kfs_grasp(self, box, depth_m: np.ndarray, depth_msg: Image) -> Optional[Pose]:
        # 1. 取上边中心点
        u_center = int((box.xmin + box.xmax) / 2.0)
        v_top = int(box.ymin + self.kfs_top_offset)

        # 2. 在附近 ROI 求中位数深度
        Z = self.median_depth_in_roi(
            depth_m,
            u_center,
            v_top,
            roi_half_size=self.kfs_roi_half_size
        )
        if Z is None or Z <= 0.0 or Z > self.max_depth:
            return None

        # 3. 反投影到相机坐标
        assert self.fx is not None and self.fy is not None
        assert self.cx is not None and self.cy is not None
        X_cam = (u_center - self.cx) * Z / self.fx
        Y_cam = (v_top - self.cy) * Z / self.fy
        Z_cam = Z

        # 4. TF 变换到 base_link
        p_cam = PointStamped()
        p_cam.header = depth_msg.header
        p_cam.point.x = float(X_cam)
        p_cam.point.y = float(Y_cam)
        p_cam.point.z = float(Z_cam)

        try:
            p_base = self.tf_buffer.transform(
                p_cam,
                self.base_frame,
                timeout=Duration(nanoseconds=50_000_000)  # 0.05s = 50ms
            )
        except TransformException as ex:
            self.get_logger().warning(f"TF transform failed (KFS): {ex}")
            return None

        # 5. 构造 Pose（位置 + 简单姿态）
        pose = Pose()
        p_base = cast(PointStamped, p_base)  # Help Pylance understand the return type
        pose.position.x = p_base.point.x
        pose.position.y = p_base.point.y
        pose.position.z = p_base.point.z + self.kfs_z_offset

        # 简单姿态：朝向留给机械臂/吸盘再处理
        pose.orientation.x = 0.0
        pose.orientation.y = 0.0
        pose.orientation.z = 0.0
        pose.orientation.w = 1.0
        return pose

    # ---------- 武器头 3D 抓取方案 ----------
    def compute_weapon_grasp(self, box, depth_m: np.ndarray, depth_msg: Image) -> Optional[Pose]:
        # 1. 武器用 bbox 中心点
        u_center = int((box.xmin + box.xmax) / 2.0)
        v_center = int((box.ymin + box.ymax) / 2.0)

        # 2. ROI 中位数深度
        Z = self.median_depth_in_roi(
            depth_m,
            u_center,
            v_center,
            roi_half_size=self.weapon_roi_half_size
        )
        if Z is None or Z <= 0.0 or Z > self.max_depth:
            return None

        # 3. 反投影
        assert self.fx is not None and self.fy is not None
        assert self.cx is not None and self.cy is not None
        X_cam = (u_center - self.cx) * Z / self.fx
        Y_cam = (v_center - self.cy) * Z / self.fy
        Z_cam = Z

        p_cam = PointStamped()
        p_cam.header = depth_msg.header
        p_cam.point.x = float(X_cam)
        p_cam.point.y = float(Y_cam)
        p_cam.point.z = float(Z_cam)

        try:
            p_base = self.tf_buffer.transform(
                p_cam,
                self.base_frame,
                timeout=Duration(nanoseconds=50_000_000)  # 0.05s = 50ms
            )
        except TransformException as ex:
            self.get_logger().warning(f"TF transform failed (weapon): {ex}")
            return None

        pose = Pose()
        p_base = cast(PointStamped, p_base)  # Help Pylance understand the return type
        pose.position.x = p_base.point.x
        pose.position.y = p_base.point.y
        pose.position.z = p_base.point.z + self.weapon_z_offset

        pose.orientation.x = 0.0
        pose.orientation.y = 0.0
        pose.orientation.z = 0.0
        pose.orientation.w = 1.0
        return pose

    # ---------- 工具函数 ----------
    def convert_depth_to_meters(self, depth_raw: np.ndarray, encoding: str) -> np.ndarray:
        if encoding in ["16UC1", "mono16"]:
            return depth_raw.astype(np.float32) * 0.001
        elif encoding in ["32FC1"]:
            return depth_raw.astype(np.float32)
        else:
            self.get_logger().warning(f"Unknown depth encoding {encoding}, assume 16UC1.")
            return depth_raw.astype(np.float32) * 0.001

    def median_depth_in_roi(self, depth_m: np.ndarray, u: int, v: int, roi_half_size: int) -> Optional[float]:
        h, w = depth_m.shape
        us = max(0, u - roi_half_size)
        ue = min(w - 1, u + roi_half_size)
        vs = max(0, v - roi_half_size)
        ve = min(h - 1, v + roi_half_size)

        roi = depth_m[vs:ve + 1, us:ue + 1]
        valid = roi[(roi > 0.0) & (roi < self.max_depth)]
        if valid.size == 0:
            return None
        return float(np.median(valid))

    # ---------- 可视化抓取点并发布 ----------
    def publish_grasp_viz(self, depth_m: np.ndarray, header, boxes, kfs_array: PoseArray, weapon_array: PoseArray):
        if depth_m is None or depth_m.size == 0:
            return

        try:
            # 把深度归一化为灰度图，再转 BGR 方便着色
            depth_norm = np.clip(depth_m / float(self.max_depth), 0.0, 1.0)
            depth_img = (depth_norm * 255.0).astype(np.uint8)
            viz = cv2.cvtColor(depth_img, cv2.COLOR_GRAY2BGR)

            # 绘制检测框
            for box in boxes:
                x1, y1, x2, y2 = int(box.xmin), int(box.ymin), int(box.xmax), int(box.ymax)
                cv2.rectangle(viz, (x1, y1), (x2, y2), (0, 255, 255), 1)
                cv2.putText(viz, box.class_name, (x1, max(0, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)

            # 绘制抓取点（使用 2D 像素位置，KFS 用绿色，weapon 用洋红）
            for box in boxes:
                if box.class_name.startswith("weapon"):
                    u = int((box.xmin + box.xmax) / 2.0)
                    v = int((box.ymin + box.ymax) / 2.0)
                    cv2.circle(viz, (u, v), 4, (255, 0, 255), -1)
                else:
                    u = int((box.xmin + box.xmax) / 2.0)
                    v = int(box.ymin + self.kfs_top_offset)
                    cv2.circle(viz, (u, v), 4, (0, 255, 0), -1)

            img_msg = self.bridge.cv2_to_imgmsg(viz, encoding="bgr8")
            img_msg.header = header
            self.viz_pub.publish(img_msg)
        except Exception as e:
            self.get_logger().debug(f"Publish viz failed: {e}")


def main(args=None):
    rclpy.init(args=args)
    node = KFSWeapon3DGraspNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
