"""Publish structured mission log events to /bringup/mission_log_event."""

from __future__ import annotations

import json
import os

from rclpy.node import Node
from std_msgs.msg import String

TOPIC = '/bringup/mission_log_event'

_publisher = None

# 环境变量 MISSION_LOG_ENABLED=0 可临时关闭所有日志
_ENABLED = os.environ.get('MISSION_LOG_ENABLED', '1') != '0'


def _get_publisher(node: Node):
    global _publisher
    if _publisher is None:
        _publisher = node.create_publisher(String, TOPIC, 100)
    return _publisher


def log_event(
    node: Node,
    source: str,
    event_id: str,
    detail: str,
    *,
    level: str = 'INFO',
) -> None:
    if not _ENABLED:
        return
    if level not in ('INFO', 'ERROR'):
        return
    stamp = node.get_clock().now()
    payload = {
        'sec': int(stamp.nanoseconds // 1_000_000_000),
        'nanosec': int(stamp.nanoseconds % 1_000_000_000),
        'source': source,
        'event_id': event_id,
        'level': level,
        'detail': detail,
    }
    msg = String()
    msg.data = json.dumps(payload, ensure_ascii=False)
    _get_publisher(node).publish(msg)
