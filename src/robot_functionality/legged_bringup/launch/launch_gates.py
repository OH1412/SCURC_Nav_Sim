"""Helpers for event-driven bringup launch chains."""

from __future__ import annotations

from launch.actions import ExecuteProcess, RegisterEventHandler
from launch.condition import Condition
from launch.conditions import IfCondition, UnlessCondition
from launch.event_handlers import OnProcessExit
from launch.launch_context import LaunchContext
from launch.substitutions import LaunchConfiguration


class AllConditions(Condition):
    """Logical AND for multiple launch conditions (Humble has no AndCondition)."""

    def __init__(self, conditions: list[Condition]) -> None:
        self._conditions = list(conditions)
        super().__init__(predicate=self._predicate)

    def _predicate(self, context: LaunchContext) -> bool:
        return all(c.evaluate(context) for c in self._conditions)


def wait_for_ros_condition(
    *,
    name: str,
    timeout: LaunchConfiguration | str,
    extra_args: list | None = None,
) -> ExecuteProcess:
    cmd = [
        'ros2', 'run', 'legged_bringup', 'wait_for_ros_condition.py',
        '--timeout', timeout,
    ]
    if extra_args:
        cmd.extend(extra_args)
    return ExecuteProcess(cmd=cmd, name=name, output='screen')


def on_process_exit(action, follow_up) -> RegisterEventHandler:
    return RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=action,
            on_exit=follow_up,
        ),
    )


def on_process_exit_if(action, follow_up, condition) -> RegisterEventHandler:
    return RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=action,
            on_exit=follow_up,
        ),
        condition=condition,
    )
