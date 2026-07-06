#!/usr/bin/env python3
# ============================================================================
# 机器狗站起指令发送器
# ============================================================================
# 通过 UDP 向 deploy_cpp 发送 mode=1 (STAND_UP) 指令。
# deploy_cpp 收到后自动插值到站立姿态 (standup_duration=2s)。
#
# 支持等待重定位完成后再发送: 监听 /LIVO2/pose_offset 话题，
# 收到第一条消息后延迟 reloc_delay 秒再发送站立指令。
#
# 协议 (17 bytes, little-endian):
#   int32_t mode   // 0=IDLE, 1=STAND_UP, 2=RL, 3=JOINT_DAMPING, 4=RETURN_DEFAULT
#   float   vx, vy, yaw
#   uint8_t e_stop
#
# 用法:
#   ros2 run legged_bringup stand_up_sender.py
#   ros2 run legged_bringup stand_up_sender.py --ros-args -p reloc_delay:=5.0
# ============================================================================

import socket
import struct
import time
import sys

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import Bool


class StandUpSender(Node):
    """等待重定位完成 → 发送单次 STAND_UP UDP 指令到 deploy_cpp"""

    def __init__(self):
        super().__init__('stand_up_sender')

        self.declare_parameter('udp_ip', '127.0.0.1')
        self.declare_parameter('udp_port', 9870)
        self.declare_parameter('standup_wait', 3.0)
        self.declare_parameter('wait_for_reloc', True)
        self.declare_parameter('reloc_delay', 4.0)
        self.declare_parameter('reloc_timeout', 60.0)
        self.declare_parameter('reloc_topic', '/LIVO2/pose_offset')
        self.declare_parameter('stand_up_done_topic', '/bringup/stand_up_done')

        udp_ip = self.get_parameter('udp_ip').value
        udp_port = self.get_parameter('udp_port').value
        standup_wait = self.get_parameter('standup_wait').value
        wait_for_reloc = self.get_parameter('wait_for_reloc').value
        reloc_delay = self.get_parameter('reloc_delay').value
        reloc_timeout = self.get_parameter('reloc_timeout').value
        reloc_topic = self.get_parameter('reloc_topic').value
        stand_up_done_topic = self.get_parameter('stand_up_done_topic').value

        self.udp_ip = udp_ip
        self.udp_port = udp_port
        self.standup_wait = standup_wait
        self.reloc_delay = reloc_delay
        self.reloc_timeout = reloc_timeout
        self._reloc_received = False
        self._reloc_arrival_time = None
        self._start_time = self.get_clock().now()
        self._stand_up_done_topic = stand_up_done_topic
        self._done_pub = self.create_publisher(Bool, stand_up_done_topic, 10)

        if wait_for_reloc:
            self.get_logger().info(
                f'Waiting for relocalization signal on {reloc_topic} '
                f'(delay={reloc_delay:.0f}s, timeout={reloc_timeout:.0f}s)')
            self._sub = self.create_subscription(
                PoseStamped, reloc_topic, self._reloc_callback, 10)
            self._check_timer = self.create_timer(0.5, self._check_reloc)
        else:
            self.get_logger().info('Skipping reloc wait, sending immediately...')
            self._send_stand_up()

    def _reloc_callback(self, msg):
        if not self._reloc_received:
            self._reloc_received = True
            self._reloc_arrival_time = self.get_clock().now()
            elapsed = (self._reloc_arrival_time - self._start_time).nanoseconds * 1e-9
            self.get_logger().info(
                f'Relocalization signal received (t+{elapsed:.1f}s). '
                f'Delay={self.reloc_delay:.1f}s')
            # reloc_delay=0 时立刻发送，不等 timer 轮询
            if self.reloc_delay <= 0.0:
                self._check_timer.cancel()
                self.destroy_subscription(self._sub)
                self._send_stand_up()

    def _check_reloc(self):
        now = self.get_clock().now()
        elapsed = (now - self._start_time).nanoseconds * 1e-9

        if elapsed > self.reloc_timeout:
            self.get_logger().warn(
                f'Reloc wait timeout ({self.reloc_timeout:.0f}s). Sending stand_up anyway...')
            self._check_timer.cancel()
            self.destroy_subscription(self._sub)
            self._send_stand_up()
            return

        if self._reloc_received and self._reloc_arrival_time is not None:
            since_reloc = (now - self._reloc_arrival_time).nanoseconds * 1e-9
            if since_reloc >= self.reloc_delay:
                self._check_timer.cancel()
                self.destroy_subscription(self._sub)
                self._send_stand_up()

    def _send_stand_up(self):
        self.get_logger().info(f'Sending STAND_UP to {self.udp_ip}:{self.udp_port}')

        packet = struct.pack('<i f f f B', 1, 0.0, 0.0, 0.0, 0)

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(packet, (self.udp_ip, self.udp_port))
            sock.close()
            self.get_logger().info('STAND_UP command sent successfully.')
        except Exception as e:
            self.get_logger().fatal(f'Failed to send STAND_UP: {e}')
            sys.exit(1)

        self.get_logger().info(
            f'Waiting {self.standup_wait:.1f}s for standup to complete...'
        )
        self.timer = self.create_timer(self.standup_wait, self._done)

    def _done(self):
        self.get_logger().info('Standup should be complete. Exiting.')
        done_msg = Bool()
        done_msg.data = True
        self._done_pub.publish(done_msg)
        self.get_logger().info(f'Published stand-up done on {self._stand_up_done_topic}')
        rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)
    node = StandUpSender()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except SystemExit:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
