#!/usr/bin/env python3
"""Aggregate /bringup/mission_log_event into a single timestamped session log file."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from std_msgs.msg import String

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mission_log_labels import event_label, level_label, source_label

# Dynamic planning events are excluded from mission hardcoded logs.
_EXCLUDED_SOURCES = {'mission_quintuple_loader'}
_EXCLUDED_EVENT_PREFIXES = ('PLAN_', 'BT_CONFIG_', 'QUINTUPLE_')


def _format_event_time(sec: int, nanosec: int) -> str:
    whole = datetime.fromtimestamp(sec)
    return f'{whole.strftime("%Y-%m-%d %H:%M:%S")}.{nanosec:09d}'


class MissionSessionLogger(Node):
    def __init__(self) -> None:
        super().__init__('mission_session_logger')

        default_log_dir = (
            Path(__file__).resolve().parents[1] / 'logs'
        )
        self.declare_parameter('log_dir', str(default_log_dir))
        self.declare_parameter('session_name', 'mission_hardcoded')
        self.declare_parameter('session_detail', '')

        log_dir = Path(self.get_parameter('log_dir').value)
        session_name = str(self.get_parameter('session_name').value)
        session_detail = str(self.get_parameter('session_detail').value).strip()
        log_dir.mkdir(parents=True, exist_ok=True)

        started_at = datetime.now()
        self._log_path = log_dir / f'{session_name}_{started_at.strftime("%Y%m%d_%H%M%S")}.log'
        self._file = self._log_path.open('a', encoding='utf-8')

        qos = QoSProfile(depth=512, reliability=ReliabilityPolicy.RELIABLE)
        self.create_subscription(String, '/bringup/mission_log_event', self._on_event, qos)

        launch_detail = f'日志文件={self._log_path}'
        if session_detail:
            launch_detail = f'{session_detail} | {launch_detail}'
        self._write_line(
            sec=int(started_at.timestamp()),
            nanosec=started_at.microsecond * 1000,
            level='INFO',
            source='mission_session_logger',
            event_id='LAUNCH_SESSION_START',
            detail=launch_detail,
        )
        self.get_logger().info(f'任务会话日志: {self._log_path}')

    def _write_line(
        self,
        *,
        sec: int,
        nanosec: int,
        level: str,
        source: str,
        event_id: str,
        detail: str,
    ) -> None:
        ts = _format_event_time(sec, nanosec)
        line = (
            f'[{ts}] [{level_label(level)}] [{source_label(source)}] '
            f'{event_label(event_id)} | {detail}\n'
        )
        self._file.write(line)
        self._file.flush()

    def _on_event(self, msg: String) -> None:
        try:
            payload = json.loads(msg.data)
        except json.JSONDecodeError:
            return

        level = str(payload.get('level', 'INFO'))
        if level not in ('INFO', 'ERROR'):
            return

        source = str(payload.get('source', 'unknown'))
        event_id = str(payload.get('event_id', 'UNKNOWN'))

        if source in _EXCLUDED_SOURCES:
            return
        if any(event_id.startswith(prefix) for prefix in _EXCLUDED_EVENT_PREFIXES):
            return

        self._write_line(
            sec=int(payload.get('sec', 0)),
            nanosec=int(payload.get('nanosec', 0)),
            level=level,
            source=source,
            event_id=event_id,
            detail=str(payload.get('detail', '')),
        )

    def destroy_node(self) -> bool:
        if self._file and not self._file.closed:
            now = datetime.now()
            self._write_line(
                sec=int(now.timestamp()),
                nanosec=now.microsecond * 1000,
                level='INFO',
                source='mission_session_logger',
                event_id='LAUNCH_SESSION_END',
                detail=f'日志文件={self._log_path}',
            )
            self._file.close()
        return super().destroy_node()


def main() -> None:
    rclpy.init()
    node = MissionSessionLogger()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
