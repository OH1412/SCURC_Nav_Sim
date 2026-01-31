#!/usr/bin/env python3
"""
临时测试发布器：发布一条 KFSDecision（只发一次），使用 ROS 时钟打时间戳。
设计目标：在行为树启动后（延迟一段时间）自动运行，避免时间戳与 /clock 不一致导致的 MessageFilter 丢弃。
"""
import time
import argparse
import socket
import re
import rclpy
from rclpy.node import Node
from yolov8_ros2_msgs.msg import KFSDecision


class ContinuousKfsPub(Node):
    def __init__(self):
        super().__init__('kfs_test_pub')
        self.pub = self.create_publisher(KFSDecision, '/kfs_decision', 10)

    def wait_for_ros_time(self, timeout: float = 10.0) -> bool:
        """Wait until the ROS clock starts (useful when using /use_sim_time).
        Returns True if clock is non-zero before timeout, False otherwise.
        """
        start = time.time()
        while rclpy.ok():
            now = self.get_clock().now()
            if getattr(now, 'nanoseconds', 0) and now.nanoseconds != 0:
                return True
            if timeout > 0 and (time.time() - start) > timeout:
                return False
            time.sleep(0.05)

    def _publish_message(self, stair_values: list):
        # Map incoming values to KFSDecision enum values
        # Incoming mapping (from wifi device): 1->R2, 2->R1, 3->FAKE, 0->EMPTY
        # KFSDecision constants: OBJECT_NONE=0, OBJECT_R1=1, OBJECT_R2=2, OBJECT_FAKE=3
        mapping = {1: 2, 2: 1, 3: 3, 0: 0}
        msg = KFSDecision()
        msg.total_stairs = 12
        mapped = []
        for i in range(12):
            val = 0
            try:
                inv = int(stair_values[i])
            except Exception:
                inv = 0
            val = mapping.get(inv, 0)
            mapped.append(val)
        msg.stair_object_type = mapped
        # confidences default to 0.0 except when we see R1/R2/FAKE we set 0.8
        confidences = []
        for v in mapped:
            if v == 0:
                confidences.append(0.0)
            else:
                confidences.append(0.8)
        msg.stair_confidences = confidences
        msg.stair_names = [f's{i+1}' for i in range(12)]
        msg.timestamp = self.get_clock().now().to_msg()
        msg.frame_id = 'wifi'
        try:
            self.pub.publish(msg)
            self.get_logger().info(f'Published KFSDecision from UDP data: {mapped}')
        except Exception as e:
            self.get_logger().error(f'Publish failed: {e}')

    def udp_listen_and_publish(self, ip: str = '0.0.0.0', port: int = 8888, timeout: float = 0.0):
        """Listen on a UDP socket and publish incoming data converted to KFSDecision.
        Expected incoming payload: 12 integers (comma/space separated). Mapping: 1->R2,2->R1,3->FAKE,0->EMPTY
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1.0)
        try:
            sock.bind((ip, port))
        except Exception as e:
            self.get_logger().error(f'Failed to bind UDP socket {ip}:{port}: {e}')
            return

        self.get_logger().info(f'UDP server listening on {ip}:{port}')

        # Wait for ROS time if using sim time
        self.get_logger().info('Waiting for ROS time to become available (if using sim_time)')
        ok_time = self.wait_for_ros_time(timeout=5.0)
        if not ok_time:
            self.get_logger().warning('ROS time did not become available; timestamps will be zero')

        start = time.time()
        while rclpy.ok():
            # optional timeout to exit
            if timeout > 0 and (time.time() - start) > timeout:
                self.get_logger().info('UDP listen timeout reached; exiting')
                break
            try:
                data, addr = sock.recvfrom(2048)
            except socket.timeout:
                continue
            except Exception as e:
                self.get_logger().error(f'UDP recv error: {e}')
                break

            try:
                text = data.decode('utf-8').strip()
            except Exception:
                # try latin1 fallback
                try:
                    text = data.decode('latin1').strip()
                except Exception:
                    text = ''

            if not text:
                self.get_logger().warning(f'Received empty UDP payload from {addr}')
                continue

            # Extract integers from payload (allow separators , space ; | )
            parts = re.findall(r'-?\d+', text)
            if len(parts) < 12:
                self.get_logger().warning(f'UDP payload has {len(parts)} integers (expected 12): {text}')
                # if too short, pad with zeros
                parts += ['0'] * (12 - len(parts))
            # Take first 12
            parts = parts[:12]

            self.get_logger().info(f'Received UDP from {addr}: {parts}')
            self._publish_message(parts)

        sock.close()

    def publish_loop(self, timeout_sec: float = 30.0, interval: float = 1.0):
        """持续发布，直到发现订阅者或超时。

        - timeout_sec: 最大持续时间（秒），0 表示无限期
        - interval: 每次发布间隔（秒）
        """
        self.get_logger().info('Waiting for at least 1 matching subscription(s)...')
        start = time.time()
        published_count = 0

        while rclpy.ok():
            now = time.time()
            elapsed = now - start
            if timeout_sec > 0 and elapsed >= timeout_sec:
                self.get_logger().warn(f'timeout ({timeout_sec}s) reached, stopping publisher')
                break

            # 构造消息并使用 ROS 时钟打点
            m = KFSDecision()
            m.total_stairs = 12
            m.stair_object_type = [1,4,2,0,3,0,1,0,2,0,0,0]
            m.stair_confidences = [0.9,0.0,0.85,0.0,0.6,0.0,0.95,0.0,0.8,0.0,0.0,0.0]
            m.stair_names = ['s1','s2','s3','s4','s5','s6','s7','s8','s9','s10','s11','s12']
            m.timestamp = self.get_clock().now().to_msg()
            m.frame_id = 'camera'

            try:
                self.pub.publish(m)
                published_count += 1
                self.get_logger().info(f'publishing #{published_count}: KFSDecision timestamp={m.timestamp.sec}')
            except Exception as e:
                self.get_logger().error('Publish failed: %s' % str(e))

            # 为了确保kfs_planner_node能接收到消息，持续发布一段时间
            if published_count >= 20:  # 发布20条消息后停止
                self.get_logger().info('Published 20 messages; stopping')
                break

            # 睡一段时间再试
            time.sleep(interval)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--timeout', type=float, default=30.0, help='最大发布超时（秒），0 表示无限期')
    parser.add_argument('--interval', type=float, default=1.0, help='发布间隔（秒）')
    parser.add_argument('--udp', action='store_true', help='启用 UDP 接收模式（WiFi）')
    parser.add_argument('--udp-ip', type=str, default='0.0.0.0', help='UDP 监听 IP')
    parser.add_argument('--udp-port', type=int, default=8888, help='UDP 监听端口')
    args = parser.parse_args()

    rclpy.init()
    node = ContinuousKfsPub()
    try:
        # 等待 rclpy 初始化
        time.sleep(0.1)
        if args.udp:
            # UDP mode: listen and publish whenever a WiFi message arrives
            node.udp_listen_and_publish(ip=args.udp_ip, port=args.udp_port, timeout=args.timeout)
        else:
            node.publish_loop(timeout_sec=args.timeout, interval=args.interval)
            # 再等待一下，确保消息发送
            time.sleep(0.2)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
