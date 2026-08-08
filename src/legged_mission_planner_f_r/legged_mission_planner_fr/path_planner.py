from __future__ import annotations

from typing import List, Optional, Sequence

from .field_model import PATH4_FIRST_BOX_ID, PATH4_LAST_BOX_ID, FieldModel
from .state_definitions import MissionState, MissionStep
from .validation import validate_box_types, validate_sequence, validate_zone_types
from .waypoint_config import WaypointConfig

SWITCH_MODE = 'fast_mode'


class MissionPathPlanner:
    """Generate logical (path, waypoint, state) sequences for front/back suction plans."""

    def __init__(
        self,
        field: Optional[FieldModel] = None,
        waypoint_config: Optional[WaypointConfig] = None,
    ) -> None:
        self.field = field or FieldModel()
        self.waypoint_config = waypoint_config or WaypointConfig.load_default()
        if self.waypoint_config is None:
            raise FileNotFoundError(
                '规划需要 ui_points_fast_mode.yaml，但未在 package share/config 中找到。'
                '请确认已 colcon build 且 config/ui_points_fast_mode.yaml 已安装。'
            )

    def plan(
        self,
        box_types: Sequence[int],
        zone_types: Sequence[int] = (0, 1, 2, 3),
        include_quiz_state: bool = False,
        quiz_type: int | None = None,
        *,
        strategy: str | None = None,
        waypoint_config: WaypointConfig | None = None,
    ) -> List[MissionStep]:
        del strategy  # kept for API compatibility with shared UI helpers
        validate_box_types(box_types)
        validate_zone_types(zone_types)
        if quiz_type is not None and quiz_type not in range(4):
            raise ValueError(f'quiz_type must be 0~3, got {quiz_type!r}')

        wp_config = waypoint_config or self.waypoint_config
        if wp_config is None:
            wp_config = WaypointConfig.load_default()
        if wp_config is None:
            raise FileNotFoundError(
                '规划需要 ui_points_fast_mode.yaml，但未在 package share/config 中找到。'
                '请确认已 colcon build 且 config/ui_points_fast_mode.yaml 已安装。'
            )

        sequence: List[MissionStep] = []
        navigator = _SequenceBuilder(sequence, wp_config)

        start_state = MissionState.QUIZ_RECOGNITION if include_quiz_state else MissionState.TRANSIT
        navigator.append(0, 0, start_state, note='start')

        box2_task = self.field.build_path4_task(PATH4_FIRST_BOX_ID, box_types, zone_types, wp_config)
        navigator.build_path4_task(box2_task)

        tasks = self.field.main_tasks(box_types, zone_types, wp_config)
        ordered = self._order_main_tasks(tasks, navigator.current_path, quiz_type)
        navigator.build_main_tasks(ordered)

        box6_task = self.field.build_path4_task(PATH4_LAST_BOX_ID, box_types, zone_types, wp_config)
        navigator.build_path4_task(box6_task)

        validate_sequence(sequence, wp_config)
        return sequence

    def _order_main_tasks(
        self,
        tasks: Sequence[dict],
        start_path: int,
        quiz_type: int | None,
    ) -> List[dict]:
        upper = [t for t in tasks if t['row'] == 'upper']
        lower = [t for t in tasks if t['row'] == 'lower']
        ordered: List[dict] = []
        current_path = start_path
        for group in (upper, lower):
            remaining = list(group)
            while remaining:
                best = min(
                    remaining,
                    key=lambda t: self._task_rank(t, current_path, quiz_type),
                )
                ordered.append(best)
                remaining.remove(best)
                current_path = best['place_path']
        return ordered

    @staticmethod
    def _task_rank(task: dict, current_path: int, quiz_type: int | None) -> tuple:
        quiz_rank = 0 if quiz_type is not None and task['box_type'] == quiz_type else 1
        distance = FieldModel.path_distance(current_path, task['pick_path'])
        return (quiz_rank, distance, task['box_id'])


class _SequenceBuilder:
    def __init__(
        self,
        sequence: List[MissionStep],
        waypoint_config: WaypointConfig,
    ) -> None:
        self.sequence = sequence
        self.waypoint_config = waypoint_config
        self.current_path = 0
        self.current_wp = 0

    def _path_max_wp(self, path: int) -> int:
        return self.waypoint_config.max_wp(path)

    def append(
        self,
        path: int,
        wp: int,
        state: MissionState,
        *,
        target_box: int | None = None,
        target_zone: int | None = None,
        box_type: int | None = None,
        zone_type: int | None = None,
        note: str = '',
    ) -> None:
        step = MissionStep(
            path=path,
            wp=wp,
            state=state,
            target_box=target_box,
            target_zone=target_zone,
            box_type=box_type,
            zone_type=zone_type,
            note=note,
        )
        if self.sequence:
            prev = self.sequence[-1]
            if (
                prev.path == step.path
                and prev.wp == step.wp
                and prev.state == step.state
                and prev.target_box == step.target_box
                and prev.target_zone == step.target_zone
            ):
                return
        self.sequence.append(step)
        self.current_path = path
        self.current_wp = wp

    def move_within_path(
        self,
        path: int,
        target_wp: int,
        final_state: MissionState = MissionState.TRANSIT,
        *,
        task: dict | None = None,
        note: str = '',
    ) -> None:
        if self.current_path != path:
            raise RuntimeError('move_within_path called across paths')
        if self.current_wp == target_wp:
            self._append_task_step(path, target_wp, final_state, task, note)
            return
        step_dir = 1 if target_wp > self.current_wp else -1
        for wp in range(self.current_wp + step_dir, target_wp + step_dir, step_dir):
            is_final = wp == target_wp
            self._append_task_step(
                path,
                wp,
                final_state if is_final else MissionState.TRANSIT,
                task if is_final else None,
                note if is_final else 'transit',
            )

    def move_to(
        self,
        path: int,
        target_wp: int,
        final_state: MissionState = MissionState.TRANSIT,
        *,
        task: dict | None = None,
        note: str = '',
    ) -> None:
        if self.current_path == 0:
            if target_wp == 1 and final_state != MissionState.TRANSIT:
                self._append_task_step(path, 1, final_state, task, note or f'enter path {path}')
                return
            self.append(path, 1, MissionState.TRANSIT, note=f'enter path {path}')
            if target_wp == 1:
                return
            if target_wp > 1:
                self.move_within_path(path, target_wp, final_state, task=task, note=note)
            return

        if self.current_path == path:
            self._append_task_step(path, target_wp, final_state, task, note)
            return

        self._append_task_step(path, target_wp, final_state, task, note)

    def _append_task_step(
        self,
        path: int,
        wp: int,
        state: MissionState,
        task: dict | None,
        note: str,
    ) -> None:
        if task is not None and state in (MissionState.PICK, MissionState.PLACE):
            self.append(
                path,
                wp,
                state,
                target_box=task['box_id'],
                target_zone=task['zone_id'],
                box_type=task['box_type'],
                zone_type=task['zone_type'],
                note=note,
            )
        else:
            self.append(path, wp, state, note=note)

    def build_path4_task(self, task: dict) -> None:
        self.move_to(
            task['pick_path'],
            task['pick_wp'],
            task['pick_state'],
            task=task,
            note=f"path4 pick box {task['box_id']}",
        )
        self.move_to(
            task['place_path'],
            task['place_wp'],
            task['place_state'],
            task=task,
            note=f"path4 place box {task['box_id']} to zone {task['zone_id']}",
        )

    def build_main_tasks(self, tasks: Sequence[dict]) -> None:
        for task in tasks:
            self.move_to(
                task['pick_path'],
                task['pick_wp'],
                task['pick_state'],
                task=task,
                note=f"pick box {task['box_id']}",
            )
            self.move_to(
                task['place_path'],
                task['place_wp'],
                task['place_state'],
                task=task,
                note=f"place box {task['box_id']} to zone {task['zone_id']}",
            )
