#!/usr/bin/env python3
"""订阅 /interactive_arm/coord_report，在独立终端打印每次抓取/放置的发送坐标。"""

from __future__ import annotations

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class ArmCoordMonitor(Node):
    def __init__(self) -> None:
        super().__init__('arm_coord_monitor')
        self.declare_parameter('coord_report_topic', '/interactive_arm/coord_report')
        topic = str(self.get_parameter('coord_report_topic').value)
        self.create_subscription(String, topic, self._on_report, 10)
        print('=' * 68, flush=True)
        print('  机械臂坐标监视 — 每次 X 键抓取/放置后在此输出发送坐标', flush=True)
        print(f'  话题: {topic}', flush=True)
        print('=' * 68 + '\n', flush=True)

    def _on_report(self, msg: String) -> None:
        print(msg.data, flush=True)


def main() -> None:
    rclpy.init()
    node = ArmCoordMonitor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()


if __name__ == '__main__':
    main()
