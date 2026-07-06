"""Helpers for event-driven bringup launch chains."""

from __future__ import annotations

from launch.actions import ExecuteProcess, RegisterEventHandler
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.substitutions import LaunchConfiguration


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
        event_handler=OnProcessExit(target_action=action),
        actions=[follow_up],
    )


def on_process_exit_if(action, follow_up, condition) -> RegisterEventHandler:
    return RegisterEventHandler(
        event_handler=OnProcessExit(target_action=action),
        actions=[follow_up],
        condition=condition,
    )
