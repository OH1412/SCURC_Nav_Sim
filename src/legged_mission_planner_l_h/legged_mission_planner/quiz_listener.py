from __future__ import annotations

import threading
from typing import Callable, Optional

VALID_QUIZ_TYPES = frozenset(range(4))


class QuizResultListener:
    """Subscribe to a ROS topic for quiz box type (0~3). Starts only when start() is called."""

    def __init__(self, topic: str, on_result: Callable[[int], None]) -> None:
        self.topic = topic
        self.on_result = on_result
        self._result: int | None = None
        self._lock = threading.Lock()
        self._running = False
        self._thread: threading.Thread | None = None
        self._node = None
        self._ros_available = False
        self._error: str | None = None

    @property
    def result(self) -> int | None:
        with self._lock:
            return self._result

    @property
    def ros_available(self) -> bool:
        return self._ros_available

    @property
    def error(self) -> str | None:
        return self._error

    def start(self) -> bool:
        if self._running:
            return self._ros_available
        self._running = True
        self._thread = threading.Thread(target=self._spin_loop, daemon=True, name='quiz-listener')
        self._thread.start()
        self._thread.join(timeout=0.5)
        return self._ros_available

    def stop(self) -> None:
        self._running = False
        if self._node is not None:
            try:
                self._node.destroy_node()
            except Exception:
                pass
            self._node = None

    def _spin_loop(self) -> None:
        try:
            import rclpy
            from rclpy.node import Node
            from std_msgs.msg import Int32
        except ImportError:
            self._error = 'rclpy not available'
            self._ros_available = False
            return

        try:
            if not rclpy.ok():
                rclpy.init()
            listener = self

            class _QuizNode(Node):
                def __init__(self) -> None:
                    super().__init__('legged_mission_planner_quiz_listener')
                    self.create_subscription(Int32, listener.topic, listener._handle_msg, 10)

            self._node = _QuizNode()
            self._ros_available = True
            while self._running and rclpy.ok():
                rclpy.spin_once(self._node, timeout_sec=0.05)
        except Exception as exc:
            self._error = str(exc)
            self._ros_available = False
        finally:
            if self._node is not None:
                try:
                    self._node.destroy_node()
                except Exception:
                    pass
                self._node = None

    def _handle_msg(self, msg) -> None:
        value = int(msg.data)
        if value not in VALID_QUIZ_TYPES:
            return
        with self._lock:
            if self._result is not None:
                return
            self._result = value
        self.on_result(value)
