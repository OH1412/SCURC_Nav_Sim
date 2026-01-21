
import cv2
import torch
import rclpy
import numpy as np
from ultralytics import YOLO
from time import time
from rclpy.node import Node
from typing import Any, cast

# 线程/队列/调试支持
import threading
import queue
import signal
import faulthandler

# 注册 faulthandler：向进程发送 SIGUSR1 会输出所有 Python 线程堆栈到 stderr
faulthandler.register(signal.SIGUSR1, all_threads=True)

# ROS2消息类型导入
from std_msgs.msg import Header
from sensor_msgs.msg import Image
from yolov8_ros2_msgs.msg import BoundingBox, BoundingBoxes


class YoloDectNode(Node):
    def __init__(self):
        super().__init__('yolov8_ros2_node')

        # 参数声明
        self.declare_parameter('weight_path', 'best.pt')
        self.declare_parameter('image_topic','/camera/camera/color/image_raw')
        # self.declare_parameter('image_topic', '/camera/camera/image_raw')    
        self.declare_parameter('pub_topic', '/yolov8/BoundingBoxes')
        self.declare_parameter('camera_frame', '')
        self.declare_parameter('conf', 0.7)
        self.declare_parameter('visualize', False)
        self.declare_parameter('use_cpu', True)
        self.declare_parameter('color_ratio_threshold', 0.15)  # 颜色判定占比阈值

        # 武器检测相关参数
        self.declare_parameter('weapon_weight_path', 'best.pt') 
        self.declare_parameter('weapon_conf', 0.6)
        self.declare_parameter('weapon_enabled', False)

        # 获取参数
        weight_path = self.get_parameter('weight_path').get_parameter_value().string_value
        image_topic = self.get_parameter('image_topic').get_parameter_value().string_value
        pub_topic = self.get_parameter('pub_topic').get_parameter_value().string_value
        self.camera_frame = self.get_parameter('camera_frame').get_parameter_value().string_value
        conf = self.get_parameter('conf').get_parameter_value().double_value
        self.visualize = self.get_parameter('visualize').get_parameter_value().bool_value
        use_cpu = self.get_parameter('use_cpu').get_parameter_value().bool_value
        self.color_ratio_threshold = self.get_parameter('color_ratio_threshold').get_parameter_value().double_value

        self.weapon_weight_path = self.get_parameter('weapon_weight_path').get_parameter_value().string_value
        self.weapon_conf = self.get_parameter('weapon_conf').get_parameter_value().double_value
        self.weapon_enabled = self.get_parameter('weapon_enabled').get_parameter_value().bool_value
        # 默认关闭武器模型，按需加载，避免属性不存在
        self.weapon_model = None

        # 设备选择
        if use_cpu:
            self.device = 'cpu'
        else:
            if torch.cuda.is_available():
                self.device = 'cuda'
            else:
                self.device = 'cpu'
                self.get_logger().warning('CUDA not available, using CPU instead')

        # 加载模型
        self.get_logger().info(f'Loading YOLOv8 model from {weight_path}')
        self.model = YOLO(weight_path)
        try:
            self.model.to(self.device)
            self.model.fuse()
        except Exception as e:
            self.get_logger().warning(f'Model to/fuse error: {e}')

        model_any: Any = self.model
        model_any.conf = float(conf)
        self.color_image = None
        self.getImageStatus = False
        self.classes_colors = {}

        if self.weapon_enabled and self.weapon_weight_path:
            self.get_logger().info(f'Loading weapon detection model from {self.weapon_weight_path}')
            self.weapon_model = YOLO(self.weapon_weight_path)
            try:
                self.weapon_model.to(self.device)
                self.weapon_model.fuse()
            except Exception as e:
                self.get_logger().warning(f'Weapon model to/fuse error: {e}')
            weapon_model_any: Any = self.weapon_model
            weapon_model_any.conf = float(self.weapon_conf)
        else:
            self.get_logger().info("Weapon detection disabled")
        
                        
        # 推理队列与后台线程，避免在回调中阻塞
        self._frame_queue = queue.Queue(maxsize=2)
        self._worker_stop = threading.Event()
        self._worker_thread = threading.Thread(target=self._inference_worker, daemon=True)
        self._worker_thread.start()

        # 订阅与发布
        self.color_sub = self.create_subscription(
            Image,
            image_topic,
            self.image_callback,
            1)
        self.color_sub

        self.position_pub = self.create_publisher(
            BoundingBoxes,
            pub_topic,
            1)

        self.image_pub = self.create_publisher(
            Image,
            '/yolov8/detection_image',
            1)

        self.timer = self.create_timer(2.0, self.check_image_status)

        self.get_logger().info('YOLOv8 ROS2 node initialized successfully')

    def check_image_status(self):
        if not self.getImageStatus:
            self.get_logger().info("Waiting for image...")

    def _inference_worker(self):
        """后台线程：从队列取帧做模型推理与发布"""
        while not self._worker_stop.is_set():
            try:
                item = self._frame_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            frame_rgb, frame_bgr, header, height, width = item
           
            try:
                # 1) KFS 检测
                kfs_results = self.model(frame_rgb, show=False, conf=self.model.conf)

                # 2) 可选：武器头检测
                weapon_results = None
                if self.weapon_model is not None:
                    weapon_results = self.weapon_model(frame_rgb, show=False, conf=self.weapon_model.conf)

                # 3) 统一调用 dectshow
                self.dectshow(
                    kfs_results=kfs_results,
                    weapon_results=weapon_results,
                    height=height,
                    width=width,
                    header=header,
                    color_frame=frame_bgr
                )
            except Exception as e:
                self.get_logger().error(f'Inference worker exception: {e}')
            finally:
                try:
                    self._frame_queue.task_done()
                except Exception:
                    pass

    def image_callback(self, image):
        """接收图像，快速转换并入队，避免阻塞 rclpy 回调"""
        self.getImageStatus = True

        try:
            # 原始字节转成 H×W×3
            raw = np.frombuffer(image.data, dtype=np.uint8).reshape(
                image.height, image.width, -1
            ).copy()

            # 按 ROS Image 的 encoding 判断是 rgb8 还是 bgr8
            encoding = getattr(image, "encoding", "rgb8")  # 没有的话默认按 rgb8 处理

            if encoding.lower() == "rgb8":
                # RealSense 默认情况：raw 本来就是 RGB
                frame_rgb = raw
                frame_bgr = cv2.cvtColor(raw, cv2.COLOR_RGB2BGR)
            elif encoding.lower() == "bgr8":
                # 如果你的相机就是 bgr8
                frame_bgr = raw
                frame_rgb = cv2.cvtColor(raw, cv2.COLOR_BGR2RGB)
            else:
                # 其它编码就先按 rgb8 处理（可以再细化）
                frame_rgb = raw
                frame_bgr = cv2.cvtColor(raw, cv2.COLOR_RGB2BGR)

        except Exception as e:
            self.get_logger().error(f'image_callback conversion error: {e}')
            return

        try:
            # 约定：队列里第一个是给 YOLO 的 RGB，第二个是可视化和颜色判断用的 BGR
            self._frame_queue.put_nowait(
                (frame_rgb, frame_bgr, image.header, image.height, image.width)
            )
        except queue.Full:
            # 替换最旧帧以保持最新性
            try:
                _ = self._frame_queue.get_nowait()
                self._frame_queue.put_nowait(
                    (frame_rgb, frame_bgr, image.header, image.height, image.width)
                )
                self.get_logger().debug('Frame queue full: replaced oldest frame')
            except Exception:
                pass
        return

    def dectshow(self, kfs_results=None, weapon_results=None, height=0, width=0, header=None, color_frame=None):
        """处理检测结果并发布/可视化，支持 KFS + 武器模型联合输出"""
        if color_frame is not None:
            frame = color_frame.copy()
        else:
            frame = np.zeros((height, width, 3), dtype=np.uint8)

        bboxes_msg = BoundingBoxes()
        if header is not None:
            bboxes_msg.header = header
            bboxes_msg.image_header = header

        detections = []
        if kfs_results is not None and len(kfs_results) > 0:
            detections.append(("kfs", kfs_results[0]))
        if weapon_results is not None and len(weapon_results) > 0:
            detections.append(("weapon", weapon_results[0]))

        color_map = {
            "red": (0, 0, 255),
            "blue": (255, 0, 0),
            "unknown": (0, 255, 255),
        }
        color_en_map = {
            "red": "RED",
            "blue": "BLUE",
            "unknown": "UNKNOWN",
        }
        weapon_box_color = (255, 0, 255)  # 洋红色区分武器

        for source_tag, res in detections:
            for result in res.boxes:
                try:
                    boundingBox = BoundingBox()
                    x1 = int(result.xyxy[0][0].item())
                    y1 = int(result.xyxy[0][1].item())
                    x2 = int(result.xyxy[0][2].item())
                    y2 = int(result.xyxy[0][3].item())
                    x1 = max(0, min(x1, width - 1))
                    y1 = max(0, min(y1, height - 1))
                    x2 = max(0, min(x2, width))
                    y2 = max(0, min(y2, height))

                    cls_name = res.names[result.cls.item()]
                    if source_tag == "weapon":
                        boundingBox.class_name = f"weapon:{cls_name}"
                        boundingBox.color = "unknown"
                        box_color = weapon_box_color
                        label_text = f"[WEAPON] {cls_name} {result.conf.item():.2f}"
                    else:
                        boundingBox.class_name = cls_name
                        color_label = "unknown"
                        if color_frame is not None and x2 > x1 and y2 > y1:
                            roi = color_frame[y1:y2, x1:x2]
                            color_label = self.detect_color(roi)
                        boundingBox.color = color_label
                        box_color = color_map.get(color_label, (0, 255, 255))
                        label_text = f"{cls_name} {color_en_map.get(color_label, 'UNKNOWN')} {result.conf.item():.2f}"

                    boundingBox.xmin = float(x1)
                    boundingBox.ymin = float(y1)
                    boundingBox.xmax = float(x2)
                    boundingBox.ymax = float(y2)
                    boundingBox.probability = result.conf.item()
                    # Some generated ROS message stubs annotate the field as an
                    # abstract/immutable collection which makes Pylance think
                    # "append" doesn't exist. Cast to `list` for the static
                    # checker while keeping runtime behavior the same.
                    cast(list, bboxes_msg.bounding_boxes).append(boundingBox)

                    cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 3)
                    (tw, th), baseline = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
                    text_x = x1
                    text_y = max(0, y1 - 5)
                    cv2.rectangle(frame, (text_x, text_y - th - baseline), (text_x + tw, text_y + baseline), (0, 0, 0), -1)
                    cv2.putText(frame, label_text, (text_x, text_y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.7, box_color, 2, cv2.LINE_AA)
                except Exception as e:
                    self.get_logger().warning(f'box parse error: {e}')

        try:
            self.position_pub.publish(bboxes_msg)
            self.publish_image(frame, height, width)
        except Exception as e:
            self.get_logger().error(f'Publish error: {e}')

        if self.visualize:
            try:
                cv2.imshow('YOLOv8', frame)
                cv2.waitKey(1)
            except Exception as e:
                self.get_logger().warning(f'cv2.imshow failed: {e}')

    def detect_color(self, roi_bgr):
        """
        基于整个检测框的像素占比，判断主颜色，只区分 red / blue（无其它颜色标签）。
        """
        if roi_bgr is None or roi_bgr.size == 0:
            return "unknown"

        try:
            h, w = roi_bgr.shape[:2]
            if h < 2 or w < 2:
                return "unknown"

            # 1) 整个框做轻微平滑，降低噪声
            blur = cv2.GaussianBlur(roi_bgr, (5, 5), 0)
            hsv = cv2.cvtColor(blur, cv2.COLOR_BGR2HSV)

            H, S, V = cv2.split(hsv)

            # 2) 定义“有效像素”：饱和度 + 亮度要足够高，过滤掉灰、黑、暗区
            sat_thresh = 60
            val_thresh = 50
            valid_mask = (S > sat_thresh) & (V > val_thresh)
            valid_pixels = int(np.count_nonzero(valid_mask))
            if valid_pixels == 0:
                return "unknown"

            valid_mask_u8 = valid_mask.astype(np.uint8) * 255

            # 3) 红色和蓝色掩膜（整个框）
            #   红色两段：0-10 和 160-180
            # 使用明确的 numpy 数组并指定 dtype 来避免 Pylance/pyright 关于 overload 的类型警告
            low_red1 = np.array((0, 80, 80), dtype=np.uint8)
            high_red1 = np.array((10, 255, 255), dtype=np.uint8)
            low_red2 = np.array((160, 80, 80), dtype=np.uint8)
            high_red2 = np.array((180, 255, 255), dtype=np.uint8)
            red_mask1 = cv2.inRange(hsv, low_red1, high_red1)
            red_mask2 = cv2.inRange(hsv, low_red2, high_red2)
            red_mask = cv2.bitwise_or(red_mask1, red_mask2)

            #   蓝色大致：100-130（同样使用 numpy 数组明确类型）
            low_blue = np.array((100, 80, 80), dtype=np.uint8)
            high_blue = np.array((130, 255, 255), dtype=np.uint8)
            blue_mask = cv2.inRange(hsv, low_blue, high_blue)

            # 只在有效像素里统计红/蓝
            red_mask = cv2.bitwise_and(red_mask, red_mask, mask=valid_mask_u8)
            blue_mask = cv2.bitwise_and(blue_mask, blue_mask, mask=valid_mask_u8)

            # 4) 形态学开闭运算，去掉零碎的小块
            kernel = np.ones((3, 3), np.uint8)
            red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel, iterations=1)
            red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel, iterations=1)

            blue_mask = cv2.morphologyEx(blue_mask, cv2.MORPH_OPEN, kernel, iterations=1)
            blue_mask = cv2.morphologyEx(blue_mask, cv2.MORPH_CLOSE, kernel, iterations=1)

            red_pixels = cv2.countNonZero(red_mask)
            blue_pixels = cv2.countNonZero(blue_mask)

            if red_pixels == 0 and blue_pixels == 0:
                return "unknown"

            red_ratio = red_pixels / float(valid_pixels)
            blue_ratio = blue_pixels / float(valid_pixels)

            # debug：你可以先打开这一行看数值
            # self.get_logger().info(f"color debug: red_ratio={red_ratio:.3f}, blue_ratio={blue_ratio:.3f}")

            # 5) 判定逻辑：谁占比大是谁，但要满足占比和差距这两个条件
            min_ratio = self.color_ratio_threshold  # 比如 0.15
            diff_thresh = 0.05                      # 红蓝占比差至少 5%

            # 只输出红或蓝（如两者都为0，仍返回 unknown）
            if red_pixels == 0 and blue_pixels == 0:
                return "unknown"

            return "red" if red_ratio >= blue_ratio else "blue"

        except Exception as e:
            self.get_logger().debug(f'Color detect failed: {e}')
            return "unknown"
    

    def publish_image(self, imgdata, height, width):
        image_temp = Image()
        header = Header()
        header.stamp = self.get_clock().now().to_msg()
        header.frame_id = self.camera_frame

        image_temp.height = height
        image_temp.width = width
        image_temp.encoding = 'bgr8'
        # 确保 imgdata 为 numpy array
        try:
            arr = np.array(imgdata)
            image_temp.data = arr.tobytes()
            image_temp.header = header
            image_temp.step = width * 3
            self.image_pub.publish(image_temp)
        except Exception as e:
            self.get_logger().error(f'publish_image error: {e}')

    def destroy_node(self):
        # 优雅停止 worker
        self._worker_stop.set()
        try:
            if hasattr(self, '_worker_thread') and self._worker_thread.is_alive():
                self._worker_thread.join(timeout=2.0)
        except Exception:
            pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    from rclpy.executors import MultiThreadedExecutor
    executor = MultiThreadedExecutor()

    yolo_dect_node = YoloDectNode()
    executor.add_node(yolo_dect_node)

    try:
        executor.spin()
    except KeyboardInterrupt:
        yolo_dect_node.get_logger().info('Node interrupted by user')
    finally:
        executor.shutdown()
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
        yolo_dect_node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    print("PyTorch version:", getattr(torch, "__version__", "unknown"))
    print("CUDA available:", torch.cuda.is_available() if hasattr(torch, "cuda") else False)
    main()
