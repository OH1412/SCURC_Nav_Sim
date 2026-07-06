from __future__ import annotations

from typing import List, Optional, Sequence, Set

from .field_model import FALLBACK_BOX_ID, FieldModel, MAX_WAYPOINT
from .state_definitions import MissionState, MissionStep
from .validation import validate_box_types, validate_sequence, validate_zone_types
from .waypoint_config import WaypointConfig


class MissionPathPlanner:
    """Generate logical (path, waypoint, state) sequences for front/back suction plans."""

    def __init__(
        self,
        field: Optional[FieldModel] = None,
        waypoint_config: Optional[WaypointConfig] = None,
    ) -> None:
        self.field = field or FieldModel()
        self.waypoint_config = waypoint_config

    def plan(
        self,
        box_types: Sequence[int],
        zone_types: Sequence[int] = (0, 1, 2, 3),
        switch_mode: str = 'safe_mode',
        include_quiz_state: bool = False,
        quiz_type: int | None = None,
        *,
        strategy: str | None = None,
        waypoint_config: WaypointConfig | None = None,
    ) -> List[MissionStep]:
        del strategy  # kept for API compatibility with shared UI helpers
        validate_box_types(box_types)
        validate_zone_types(zone_types)
        if switch_mode not in self.field.switch_modes():
            raise ValueError(f'Unknown switch_mode {switch_mode!r}')
        if quiz_type is not None and quiz_type not in range(4):
            raise ValueError(f'quiz_type must be 0~3, got {quiz_type!r}')

        wp_config = waypoint_config or self.waypoint_config
        if switch_mode == 'fast_mode' and wp_config is None:
            wp_config = WaypointConfig.for_mode('fast_mode')
        if switch_mode == 'fast_mode' and wp_config is None:
            raise FileNotFoundError(
                'fast_mode 需要 ui_points_fast_mode.yaml，但未在 package share/config 中找到。'
                '请确认已 colcon build 且 config/ui_points_fast_mode.yaml 已安装。'
            )

        sequence: List[MissionStep] = []
        navigator = _SequenceBuilder(sequence, switch_mode, wp_config)

        start_state = MissionState.QUIZ_RECOGNITION if include_quiz_state else MissionState.TRANSIT
        navigator.append(0, 0, start_state, note='start')

        fallback_zone = self.field.zone_for_type(int(box_types[FALLBACK_BOX_ID]), zone_types)
        fallback_place_path = self.field.place_path_for_zone(fallback_zone)

        fallback_box_type = int(box_types[FALLBACK_BOX_ID])
        navigator.build_fallback_pick(fallback_box_type)
        navigator.build_fallback_place(
            fallback_place_path,
            fallback_box_type,
            fallback_zone,
            int(zone_types[fallback_zone]),
        )

        tasks = self.field.main_tasks(box_types, zone_types, wp_config)
        ordered = self._order_main_tasks(
            tasks,
            navigator.current_path,
            quiz_type,
            switch_mode=switch_mode,
            placed_types={fallback_box_type},
        )
        navigator.build_main_tasks(ordered)

        validate_sequence(sequence, wp_config)
        return sequence

    def _order_main_tasks(
        self,
        tasks: Sequence[dict],
        start_path: int,
        quiz_type: int | None,
        *,
        switch_mode: str,
        placed_types: Set[int],
    ) -> List[dict]:
        upper = [t for t in tasks if t['row'] == 'upper']
        lower = [t for t in tasks if t['row'] == 'lower']
        ordered: List[dict] = []
        current_path = start_path
        placed = set(placed_types)
        rank_fn = self._task_rank_fast if switch_mode == 'fast_mode' else self._task_rank_safe
        for group in (upper, lower):
            remaining = list(group)
            while remaining:
                best = min(
                    remaining,
                    key=lambda t: rank_fn(t, current_path, quiz_type, placed),
                )
                ordered.append(best)
                remaining.remove(best)
                current_path = best['place_path']
                placed.add(best['box_type'])
        return ordered

    @staticmethod
    def _task_rank_safe(task: dict, current_path: int, quiz_type: int | None, _placed: Set[int]) -> tuple:
        quiz_rank = 0 if quiz_type is not None and task['box_type'] == quiz_type else 1
        direct_rank = 0 if task['direct'] else 1
        distance = FieldModel.path_distance(current_path, task['pick_path'])
        return (quiz_rank, direct_rank, distance, task['box_id'])

    @staticmethod
    def _task_rank_fast(task: dict, current_path: int, quiz_type: int | None, placed_types: Set[int]) -> tuple:
        quiz_rank = 0 if quiz_type is not None and task['box_type'] == quiz_type else 1
        unplaced_rank = 0 if task['box_type'] not in placed_types else 1
        distance = FieldModel.path_distance(current_path, task['pick_path'])
        return (quiz_rank, unplaced_rank, distance, task['box_id'])


class _SequenceBuilder:
    def __init__(
        self,
        sequence: List[MissionStep],
        switch_mode: str,
        waypoint_config: WaypointConfig | None = None,
    ) -> None:
        self.sequence = sequence
        self.switch_mode = switch_mode
        self.waypoint_config = waypoint_config
        self.current_path = 0
        self.current_wp = 0

    def _path_max_wp(self, path: int) -> int:
        if self.waypoint_config is not None:
            return self.waypoint_config.max_wp(path)
        return MAX_WAYPOINT

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
            if self.switch_mode == 'fast_mode':
                self._append_task_step(path, target_wp, final_state, task, note)
                return
            self.move_within_path(path, target_wp, final_state, task=task, note=note)
            return

        if self.switch_mode == 'fast_mode':
            self._append_task_step(path, target_wp, final_state, task, note)
            return

        # safe_mode cross-path
        if target_wp == MAX_WAYPOINT:
            if self.current_wp != MAX_WAYPOINT:
                self.move_within_path(self.current_path, MAX_WAYPOINT)
            self._append_task_step(path, MAX_WAYPOINT, final_state, task, note)
            return

        if self.current_wp != MAX_WAYPOINT:
            self.move_within_path(self.current_path, MAX_WAYPOINT)
        self.append(path, MAX_WAYPOINT, MissionState.TRANSIT, note=f'switch to path {path}')
        self.move_within_path(path, target_wp, final_state, task=task, note=note)

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

    def build_fallback_pick(self, box_type: int) -> None:
        task = {
            'box_id': FALLBACK_BOX_ID,
            'box_type': box_type,
            'zone_id': None,
            'zone_type': None,
        }
        self.move_to(1, 1, MissionState.PICK, task=task, note=f'fallback pick box {FALLBACK_BOX_ID}')
        self.move_within_path(1, self._path_max_wp(1), MissionState.TRANSIT, note='fallback transit')

    def build_fallback_place(
        self,
        place_path: int,
        box_type: int,
        zone_id: int,
        zone_type: int,
    ) -> None:
        task = {
            'box_id': FALLBACK_BOX_ID,
            'box_type': box_type,
            'zone_id': zone_id,
            'zone_type': zone_type,
        }
        if self.waypoint_config is not None:
            place_wp = self.waypoint_config.place_for_zone(zone_id).wp
        else:
            place_wp = MAX_WAYPOINT

        if self.switch_mode == 'safe_mode' and place_path != self.current_path:
            self.move_to(place_path, 3, MissionState.TRANSIT, note='fallback place align')
        self.move_to(
            place_path,
            place_wp,
            MissionState.PLACE,
            task=task,
            note=f'fallback place box {FALLBACK_BOX_ID} to zone {zone_id}',
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
