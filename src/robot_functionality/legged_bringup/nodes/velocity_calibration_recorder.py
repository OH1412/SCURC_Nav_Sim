#!/usr/bin/env python3
"""
实时记录 指令速度 vs 实际速度 (odom 位姿微分)

指令来源:  /robot_cmd (Float32MultiArray [vx, vy, yaw])
实际来源:  /aft_mapped_to_init (Odometry) — 对 pose 微分得机体系 vx, vy, yaw_rate

输出 CSV (~/vel_logs/vel_calib_YYYYMMDD_HHMMSS.csv):
  time_s, cmd_vx, cmd_vy, cmd_yaw, actual_vx, actual_vy, actual_yaw,
  odom_twist_vx, odom_twist_vy, odom_twist_yaw, pose_x, pose_y, pose_yaw
"""

from __future__ import annotations

import csv
import math
from datetime import datetime
from pathlib import Path

import numpy as np
import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from std_msgs.msg import Float32MultiArray
from tf2_ros import Buffer, TransformListener


def quat_to_yaw(q) -> float:
    """四元数 → yaw (绕 Z 轴旋转角)"""
    siny = 2.0 * (q.w * q.z + q.x * q.y)
    cosy = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return float(np.arctan2(siny, cosy))


class VelocityCalibrationRecorder(Node):
    def __init__(self) -> None:
        super().__init__('velocity_calibration_recorder')

        self.declare_parameter('log_dir', str(Path.home() / 'vel_logs'))
        self.declare_parameter('cmd_topic', '/robot_cmd')
        self.declare_parameter('odom_topic', '/aft_mapped_to_init')
        self.declare_parameter('odom_frame', 'map')
        self.declare_parameter('base_frame', 'base_link')
        self.declare_parameter('record_hz', 50.0)

        log_dir = Path(str(self.get_parameter('log_dir').value))
        self.cmd_topic = str(self.get_parameter('cmd_topic').value)
        self.odom_topic = str(self.get_parameter('odom_topic').value)
        self.odom_frame = str(self.get_parameter('odom_frame').value)
        self.base_frame = str(self.get_parameter('base_frame').value)
        self.record_hz = float(self.get_parameter('record_hz').value)

        log_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.csv_path = log_dir / f'vel_calib_{stamp}.csv'

        self.latest_cmd = None
        self.latest_odom = None
        self.prev_pose = None  # (x, y, yaw, t)

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        fieldnames = [
            'time_s', 'cmd_vx', 'cmd_vy', 'cmd_yaw',
            'actual_vx', 'actual_vy', 'actual_yaw',
            'odom_twist_vx', 'odom_twist_vy', 'odom_twist_yaw',
            'pose_x', 'pose_y', 'pose_yaw',
        ]
        self.csv_file = open(self.csv_path, 'w', newline='', encoding='utf-8')
        self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=fieldnames)
        self.csv_writer.writeheader()
        self.csv_file.flush()

        # deploy_node 用 BestEffort 发 /robot_cmd
        self.cmd_sub = self.create_subscription(
            Float32MultiArray, self.cmd_topic, self._on_cmd, qos_profile_sensor_data)
        self.odom_sub = self.create_subscription(
            Odometry, self.odom_topic, self._on_odom, 10)

        period = 1.0 / max(self.record_hz, 1.0)
        self.create_timer(period, self._write_row)
        self.row_count = 0

        self.get_logger().info(
            '============================================================\n'
            f'  VelocityCalibrationRecorder started\n'
            f'  CMD  topic : {self.cmd_topic}\n'
            f'  ODOM topic : {self.odom_topic}\n'
            f'  Rate       : {self.record_hz} Hz\n'
            f'  CSV        : {self.csv_path}\n'
            '============================================================')

    def _on_cmd(self, msg: Float32MultiArray) -> None:
        data = msg.data
        if len(data) >= 3:
            self.latest_cmd = (float(data[0]), float(data[1]), float(data[2]))

    def _on_odom(self, msg: Odometry) -> None:
        self.latest_odom = msg

    def _get_pose_in_map(self, stamp):
        """
        通过 TF 获取 base_link 在 map 系下的位姿。
        如果 TF 不可用，回退到 odom 自身的 pose。
        """
        try:
            if self.tf_buffer.can_transform(
                self.odom_frame, self.base_frame, rclpy.time.Time()
            ):
                tf = self.tf_buffer.lookup_transform(
                    self.odom_frame, self.base_frame, rclpy.time.Time())
                x = tf.transform.translation.x
                y = tf.transform.translation.y
                q = tf.transform.rotation
                yaw = quat_to_yaw(q)
                return (x, y, yaw)
        except Exception:
            pass

        if self.latest_odom is None:
            return None
        p = self.latest_odom.pose.pose
        return (p.position.x, p.position.y, quat_to_yaw(p.orientation))

    def _write_row(self) -> None:
        now = self.get_clock().now()
        time_s = now.nanoseconds * 1e-9

        cmd_vx = cmd_vy = cmd_yaw = 0.0
        if self.latest_cmd is not None:
            cmd_vx, cmd_vy, cmd_yaw = self.latest_cmd

        actual_vx = actual_vy = actual_yaw = 0.0
        odom_twist_vx = odom_twist_vy = odom_twist_yaw = 0.0
        pose_x = pose_y = pose_yaw = 0.0

        pose_now = self._get_pose_in_map(now)
        if pose_now is not None:
            px, py, pyaw = pose_now
            pose_x, pose_y, pose_yaw = px, py, pyaw

            if self.prev_pose is not None:
                prev_x, prev_y, prev_yaw, prev_t = self.prev_pose
                dt = time_s - prev_t
                if dt > 1e-6:
                    # 世界系速度 → 当前机体系，便于与 /robot_cmd 对比
                    dx_w = (px - prev_x) / dt
                    dy_w = (py - prev_y) / dt
                    c = math.cos(pyaw)
                    s = math.sin(pyaw)
                    actual_vx = c * dx_w + s * dy_w
                    actual_vy = -s * dx_w + c * dy_w

                    dyaw = pyaw - prev_yaw
                    dyaw = float(np.arctan2(np.sin(dyaw), np.cos(dyaw)))
                    actual_yaw = dyaw / dt

        if self.latest_odom is not None:
            t = self.latest_odom.twist.twist
            odom_twist_vx = t.linear.x
            odom_twist_vy = t.linear.y
            odom_twist_yaw = t.angular.z

        if pose_now is not None:
            self.prev_pose = (pose_x, pose_y, pose_yaw, time_s)

        self.csv_writer.writerow({
            'time_s': f'{time_s:.6f}',
            'cmd_vx': f'{cmd_vx:.4f}',
            'cmd_vy': f'{cmd_vy:.4f}',
            'cmd_yaw': f'{cmd_yaw:.4f}',
            'actual_vx': f'{actual_vx:.4f}',
            'actual_vy': f'{actual_vy:.4f}',
            'actual_yaw': f'{actual_yaw:.4f}',
            'odom_twist_vx': f'{odom_twist_vx:.4f}',
            'odom_twist_vy': f'{odom_twist_vy:.4f}',
            'odom_twist_yaw': f'{odom_twist_yaw:.4f}',
            'pose_x': f'{pose_x:.4f}',
            'pose_y': f'{pose_y:.4f}',
            'pose_yaw': f'{pose_yaw:.4f}',
        })
        self.row_count += 1
        if self.row_count % 50 == 0:
            self.csv_file.flush()
            self.get_logger().info(
                f'[{self.row_count}] cmd=({cmd_vx:+.3f},{cmd_vy:+.3f},{cmd_yaw:+.3f}) '
                f'act=({actual_vx:+.3f},{actual_vy:+.3f},{actual_yaw:+.3f})')

    def destroy_node(self) -> bool:
        try:
            self.csv_file.close()
            self.get_logger().info(f'CSV saved: {self.csv_path}')
        except Exception:
            pass
        return super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = VelocityCalibrationRecorder()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
