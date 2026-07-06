from __future__ import annotations


class PlanReadyPublisher:
    """Publish a ROS signal when mission plan export completes."""

    def __init__(self, topic: str) -> None:
        self.topic = topic
        self._node = None
        self._publisher = None
        self._ros_available: bool | None = None
        self._error: str | None = None

    @property
    def ros_available(self) -> bool:
        return bool(self._ros_available)

    @property
    def error(self) -> str | None:
        return self._error

    def publish(self, *, plan_source: str = 'base') -> bool:
        if not self._ensure_publisher():
            return False
        from std_msgs.msg import Bool

        msg = Bool()
        msg.data = True
        self._publisher.publish(msg)
        self._node.get_logger().info(
            f'Published plan ready on {self.topic} (plan_source={plan_source})'
        )
        return True

    def _ensure_publisher(self) -> bool:
        if self._ros_available is True:
            return True
        if self._ros_available is False:
            return False
        try:
            import rclpy
            from rclpy.node import Node
            from std_msgs.msg import Bool
        except ImportError:
            self._error = 'rclpy not available'
            self._ros_available = False
            return False

        try:
            if not rclpy.ok():
                rclpy.init()
            topic = self.topic

            class _PlanReadyNode(Node):
                def __init__(self) -> None:
                    super().__init__('legged_mission_planner_lh_plan_ready')
                    self._pub = self.create_publisher(Bool, topic, 10)

            self._node = _PlanReadyNode()
            self._publisher = self._node._pub
            self._ros_available = True
            return True
        except Exception as exc:
            self._error = str(exc)
            self._ros_available = False
            return False

    def shutdown(self) -> None:
        if self._node is not None:
            try:
                self._node.destroy_node()
            except Exception:
                pass
            self._node = None
        self._publisher = None
        self._ros_available = None
