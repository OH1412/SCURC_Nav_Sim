#!/usr/bin/env python3
# ============================================================================
# arm_points 可视化 — 在 RViz 中以 Marker 显示抓取/放置点位
#
# 抓取 (pick, 0~7):  绿色球
# 放置 (place, 8~15): 红色球
# 附带文字标签
# ============================================================================

from __future__ import annotations

import math
import os
from typing import Any

import rclpy
import yaml
from geometry_msgs.msg import Point, Quaternion
from rclpy.node import Node
from std_msgs.msg import ColorRGBA
from visualization_msgs.msg import Marker, MarkerArray


def make_color(r: float, g: float, b: float, a: float = 1.0) -> ColorRGBA:
    c = ColorRGBA()
    c.r = r
    c.g = g
    c.b = b
    c.a = a
    return c


PICK_COLOR = make_color(0.0, 0.8, 0.0, 0.8)    # 绿
PLACE_COLOR = make_color(0.9, 0.2, 0.2, 0.8)   # 红


class ArmPointsVisualizer(Node):
    def __init__(self) -> None:
        super().__init__('arm_points_visualizer')

        bringup_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        default_points = os.path.join(bringup_dir, 'params', 'arm_points.yaml')

        self.declare_parameter('arm_points_file', default_points)
        self.declare_parameter('frame_id', 'map')
        self.declare_parameter('publish_rate', 1.0)
        self.declare_parameter('marker_scale', 0.08)

        points_path = self.get_parameter('arm_points_file').value
        self._frame_id = self.get_parameter('frame_id').value
        rate = self.get_parameter('publish_rate').value
        scale = self.get_parameter('marker_scale').value

        self._points = self._load_points(points_path)
        self._markers = self._build_markers(scale)
        self._pub = self.create_publisher(MarkerArray, '/arm_points_viz', 10)
        self._timer = self.create_timer(1.0 / rate, self._publish)

        self.get_logger().info(
            f'Loaded {len(self._points)} arm points, '
            f'publishing to /arm_points_viz in frame [{self._frame_id}]')

    def _load_points(self, path: str) -> dict[str, dict[str, Any]]:
        if not os.path.isfile(path):
            self.get_logger().warn(f'Arm points file not found: {path}')
            return {}
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        return data.get('arm_points', {})

    def _build_markers(self, scale: float) -> MarkerArray:
        markers = MarkerArray()

        for key, entry in self._points.items():
            mt = entry.get('map_target')
            if mt is None:
                continue
            role = entry.get('role', '')
            label = entry.get('label', key)
            color = PICK_COLOR if role == 'pick' else PLACE_COLOR

            # ---- 球 ----
            sphere = Marker()
            sphere.header.frame_id = self._frame_id
            sphere.ns = f'arm_point_sphere'
            sphere.id = int(key)
            sphere.type = Marker.SPHERE
            sphere.action = Marker.ADD
            sphere.pose.position = Point(x=float(mt['x']), y=float(mt['y']), z=float(mt.get('z', 0.0)))
            sphere.pose.orientation = Quaternion(w=1.0)
            sphere.scale.x = scale
            sphere.scale.y = scale
            sphere.scale.z = scale
            sphere.color = color
            markers.markers.append(sphere)

            # ---- 文字标签 ----
            text = Marker()
            text.header.frame_id = self._frame_id
            text.ns = f'arm_point_label'
            text.id = int(key) + 100
            text.type = Marker.TEXT_VIEW_FACING
            text.action = Marker.ADD
            text.pose.position = Point(
                x=float(mt['x']),
                y=float(mt['y']),
                z=float(mt.get('z', 0.0)) + scale * 1.5,
            )
            text.pose.orientation = Quaternion(w=1.0)
            text.scale.z = scale * 1.2
            text.color = make_color(1.0, 1.0, 1.0, 0.9)
            text.text = f'{key}: {label}'
            markers.markers.append(text)

            # ---- 竖直杆 (从地面到点) ----
            rod = Marker()
            rod.header.frame_id = self._frame_id
            rod.ns = f'arm_point_rod'
            rod.id = int(key) + 200
            rod.type = Marker.CYLINDER
            rod.action = Marker.ADD
            z_val = float(mt.get('z', 0.0))
            rod.pose.position = Point(
                x=float(mt['x']),
                y=float(mt['y']),
                z=z_val / 2.0,
            )
            rod.pose.orientation = Quaternion(w=1.0)
            rod.scale.x = scale * 0.3
            rod.scale.y = scale * 0.3
            rod.scale.z = max(z_val, 0.01)
            rod.color = color
            rod.color.a = 0.4
            markers.markers.append(rod)

        return markers

    def _publish(self) -> None:
        self._pub.publish(self._markers)


def main() -> None:
    rclpy.init()
    node = ArmPointsVisualizer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
