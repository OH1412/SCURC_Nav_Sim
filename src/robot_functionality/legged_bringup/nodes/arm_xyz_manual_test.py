#!/usr/bin/env python3
"""交互输入 xyz，发 /arm_command，在同终端打印 /arm_status ACK。"""

from __future__ import annotations

import threading

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray, UInt8MultiArray

STATE_CN = {0x01: 'PICK完成', 0x02: 'PLACE完成'}
RESULT_CN = {0x00: '成功', 0x01: '失败'}


class ArmXyzManualTest(Node):
    def __init__(self) -> None:
        super().__init__('arm_xyz_manual_test')
        self.pub = self.create_publisher(Float64MultiArray, '/arm_command', 10)
        self.create_subscription(UInt8MultiArray, '/arm_status', self._on_ack, 10)
        self._ack_event = threading.Event()
        self._last_ack: tuple[int, int] | None = None

    def _on_ack(self, msg: UInt8MultiArray) -> None:
        if len(msg.data) < 2:
            return
        state, result = int(msg.data[0]), int(msg.data[1])
        self._last_ack = (state, result)
        print(
            f'  << ACK: state=0x{state:02X} ({STATE_CN.get(state, "未知")}) '
            f'result=0x{result:02X} ({RESULT_CN.get(result, "未知")})',
            flush=True,
        )
        self._ack_event.set()

    def send(self, x: float, y: float, z: float, action: int = 1) -> None:
        self._ack_event.clear()
        self._last_ack = None
        msg = Float64MultiArray()
        msg.data = [float(x), float(y), float(z), 0.0, float(action)]
        self.pub.publish(msg)
        act = 'PICK' if action == 1 else 'PLACE'
        print(
            f'  >> 已发送 /arm_command: x={x} y={y} z={z} mm, '
            f'action={action}({act})',
            flush=True,
        )


def main() -> None:
    rclpy.init()
    node = ArmXyzManualTest()
    spin_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    spin_thread.start()

    print('=' * 60, flush=True)
    print('  机械臂串口联调 — 输入格式: x y z [action]', flush=True)
    print('  action: 1=Pick(默认)  2=Place', flush=True)
    print('  示例: 0 -550 -100', flush=True)
    print('  示例: 0 -500 -50 2', flush=True)
    print('  退出: q', flush=True)
    print('=' * 60, flush=True)

    try:
        while rclpy.ok():
            line = input('xyz> ').strip()
            if not line:
                continue
            if line.lower() in ('q', 'quit', 'exit'):
                break
            parts = line.split()
            if len(parts) < 3:
                print('  需要至少 3 个数: x y z', flush=True)
                continue
            try:
                x, y, z = (float(parts[0]), float(parts[1]), float(parts[2]))
                action = int(parts[3]) if len(parts) >= 4 else 1
            except ValueError:
                print('  输入格式错误，请用数字', flush=True)
                continue

            node.send(x, y, z, action)
            if node._ack_event.wait(timeout=30.0):
                _, result = node._last_ack or (0, 1)
                if result == 0x00:
                    print('  => 动作完成\n', flush=True)
                else:
                    print('  => 下位机报告失败\n', flush=True)
            else:
                print('  => 30s 内未收到 ACK（检查串口/下位机）\n', flush=True)
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
