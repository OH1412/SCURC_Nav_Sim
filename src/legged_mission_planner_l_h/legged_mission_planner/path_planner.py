from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence

from .field_model import FieldModel, PickupOption, PlaceOption
from .state_definitions import MissionState, MissionStep
from .validation import validate_box_types, validate_sequence, validate_zone_types


@dataclass(frozen=True)
class BoxTask:
    box_id: int
    box_type: int
    zone_id: int
    zone_type: int
    pickup: PickupOption
    place: PlaceOption
    direct: bool
    pickup_wp: int


class MissionPathPlanner:
    """Generate logical (path, waypoint, state) sequences for task-event plans."""

    def __init__(self, field: Optional[FieldModel] = None) -> None:
        self.field = field or FieldModel()

    def plan(
        self,
        box_types: Sequence[int],
        zone_types: Sequence[int] = (0, 1, 2, 3),
        strategy: str = 'safe_edges',
        switch_mode: str = 'wp4_only',
        include_quiz_state: bool = False,
        quiz_type: int | None = None,
    ) -> List[MissionStep]:
        validate_box_types(box_types)
        validate_zone_types(zone_types)
        if switch_mode not in self.field.switch_modes():
            raise ValueError(f'Unknown switch_mode {switch_mode!r}')
        if quiz_type is not None and quiz_type not in range(4):
            raise ValueError(f'quiz_type must be 0~3, got {quiz_type!r}')

        allowed_paths = self.field.strategy_paths(strategy)
        tasks = self._assign_tasks(box_types, zone_types, allowed_paths, strategy, quiz_type)
        path_order: List[int] | None = None
        if strategy in ('safe_edges', 'edges', '1,5,2,4'):
            by_path = self._group_tasks_by_path(tasks)
            path_order = self._schedule_safe_edges_paths(by_path, quiz_type)
            if quiz_type is not None and path_order:
                tasks = self._rebalance_safe_edges_tasks_for_safety(tasks, path_order[0], allowed_paths)
                by_path = self._group_tasks_by_path(tasks)
                path_order = self._schedule_safe_edges_paths(by_path, quiz_type)
            ordered_tasks = self._order_safe_edges_tasks(tasks, quiz_type, path_order)
        else:
            ordered_tasks = self._order_tasks(tasks, allowed_paths, strategy, quiz_type)
        sequence = self._build_sequence(ordered_tasks, switch_mode, include_quiz_state)
        validate_sequence(sequence)
        return sequence

    def _assign_tasks(
        self,
        box_types: Sequence[int],
        zone_types: Sequence[int],
        allowed_paths: Sequence[int],
        strategy: str,
        quiz_type: int | None = None,
    ) -> List[BoxTask]:
        tasks: List[BoxTask] = []
        for box_id, box_type in enumerate(box_types):
            zone_id = self.field.zone_for_type(int(box_type), list(zone_types))
            zone_type = int(zone_types[zone_id])
            direct_pairs = self.field.direct_pick_place_pairs(box_id, zone_id, allowed_paths)
            if direct_pairs:
                pickup, place = self._choose_direct_pair(
                    direct_pairs, allowed_paths, strategy, box_id, int(box_type),
                    self.field, quiz_type,
                )
                tasks.append(BoxTask(
                    box_id, int(box_type), zone_id, zone_type, pickup, place, True,
                    self.field.box_slots[box_id].pickup_wp,
                ))
                continue

            pickup = self._choose_nearest_pickup(
                box_id, int(box_type), allowed_paths, strategy, quiz_type,
            )
            place = self._choose_nearest_place(zone_id, pickup.path, allowed_paths)
            tasks.append(BoxTask(
                box_id, int(box_type), zone_id, zone_type, pickup, place, False,
                self.field.box_slots[box_id].pickup_wp,
            ))
        return tasks

    @staticmethod
    def _safe_edges_use_quiz_edge(box_id: int, _box_type: int, quiz_type: int | None, field: FieldModel) -> bool:
        """Quiz replan: all outer-column boxes use boundary paths (col0→1, col3→5)."""
        if quiz_type is None:
            return False
        return field.box_slots[box_id].column in (0, 3)

    @staticmethod
    def _safe_edges_near_path(_box_id: int, path: int, _field: FieldModel) -> int:
        """Default: prefer lower path (nearer when sweeping from path 1)."""
        return path

    @staticmethod
    def _safe_edges_quiz_edge_path(box_id: int, path: int, field: FieldModel) -> int:
        """Quiz outer-column: col0→target 1, col3→target 5."""
        col = field.box_slots[box_id].column
        target = 1 if col == 0 else 5
        return abs(path - target)

    @classmethod
    def _safe_edges_path_rank(
        cls,
        box_id: int,
        box_type: int,
        path: int,
        field: FieldModel,
        quiz_type: int | None,
    ) -> int:
        if cls._safe_edges_use_quiz_edge(box_id, box_type, quiz_type, field):
            return cls._safe_edges_quiz_edge_path(box_id, path, field)
        return cls._safe_edges_near_path(box_id, path, field)

    @classmethod
    def _choose_direct_pair(
        cls,
        pairs: Sequence[tuple[PickupOption, PlaceOption]],
        allowed_paths: Sequence[int],
        strategy: str,
        box_id: int,
        box_type: int,
        field: FieldModel,
        quiz_type: int | None = None,
    ) -> tuple[PickupOption, PlaceOption]:
        order = {path: index for index, path in enumerate(allowed_paths)}
        if strategy in ('middle_paths', 'middle', '2,3,4'):
            center_bias = {3: 0, 2: 1, 4: 1, 1: 2, 5: 2}
            return min(pairs, key=lambda pair: (center_bias.get(pair[0].path, 9), order.get(pair[0].path, 99)))
        if strategy in ('safe_edges', 'edges', '1,5,2,4'):
            return min(
                pairs,
                key=lambda pair: (
                    cls._safe_edges_path_rank(box_id, box_type, pair[0].path, field, quiz_type),
                    order.get(pair[0].path, 99),
                ),
            )
        return min(pairs, key=lambda pair: order.get(pair[0].path, 99))

    def _choose_nearest_pickup(
        self,
        box_id: int,
        box_type: int,
        allowed_paths: Sequence[int],
        strategy: str,
        quiz_type: int | None = None,
    ) -> PickupOption:
        options = self.field.pickup_options(box_id, allowed_paths)
        if not options:
            options = self.field.pickup_options(box_id)
        order = {path: index for index, path in enumerate(allowed_paths)}
        if strategy in ('safe_edges', 'edges', '1,5,2,4'):
            return min(
                options,
                key=lambda opt: (
                    self._safe_edges_path_rank(box_id, box_type, opt.path, self.field, quiz_type),
                    order.get(opt.path, 99),
                ),
            )
        return min(options, key=lambda opt: order.get(opt.path, 99))

    def _choose_nearest_place(self, zone_id: int, from_path: int, allowed_paths: Sequence[int]) -> PlaceOption:
        options = self.field.place_options(zone_id, allowed_paths)
        if not options:
            options = self.field.place_options(zone_id)
        return min(options, key=lambda opt: (abs(opt.path - from_path), allowed_paths.index(opt.path) if opt.path in allowed_paths else 99))

    @staticmethod
    def _safe_edges_safe_pick_path(column: int, first_path: int) -> int:
        """Choose the side of each column that has already been cleared before pickup."""
        if first_path == 5:
            return {0: 1, 1: 3, 2: 4, 3: 5}[column]
        return {0: 1, 1: 2, 2: 3, 3: 5}[column]

    def _rebalance_safe_edges_tasks_for_safety(
        self,
        tasks: Sequence[BoxTask],
        first_path: int,
        allowed_paths: Sequence[int],
    ) -> List[BoxTask]:
        rebalanced: List[BoxTask] = []
        allowed = set(allowed_paths)
        for task in tasks:
            slot = self.field.box_slots[task.box_id]
            target_path = self._safe_edges_safe_pick_path(slot.column, first_path)
            pickup = next(
                (opt for opt in self.field.pickup_options(task.box_id, allowed_paths) if opt.path == target_path),
                task.pickup,
            )
            place = next(
                (opt for opt in self.field.place_options(task.zone_id, allowed_paths) if opt.path == pickup.path),
                None,
            )
            direct = place is not None
            if place is None:
                place = self._choose_nearest_place(task.zone_id, pickup.path, allowed_paths)
            if pickup.path not in allowed:
                pickup = task.pickup
            rebalanced.append(BoxTask(
                task.box_id,
                task.box_type,
                task.zone_id,
                task.zone_type,
                pickup,
                place,
                direct,
                task.pickup_wp,
            ))
        return rebalanced

    @staticmethod
    def _task_quiz_rank(task: BoxTask, quiz_type: int | None) -> int:
        if quiz_type is None:
            return 0
        return 0 if task.box_type == quiz_type else 1

    @staticmethod
    def _same_path_pick_rank(task: BoxTask) -> tuple[int, int]:
        """Within one path, pick lower wp first (wp2 before wp3) to reduce backtracking."""
        return (task.pickup_wp, task.box_id)

    @classmethod
    def _path_score(
        cls,
        path: int,
        tasks_on_path: Sequence[BoxTask],
        last_path: int | None,
        quiz_type: int | None,
        sweep_direction: int | None = None,
    ) -> float:
        if not tasks_on_path:
            return float('-inf')
        direct = sum(1 for t in tasks_on_path if t.direct)
        cross = sum(1 for t in tasks_on_path if not t.direct)
        quiz = sum(1 for t in tasks_on_path if quiz_type is not None and t.box_type == quiz_type)
        score = direct * 10.0 - cross * 5.0 + quiz * 20.0 + len(tasks_on_path)
        if last_path is not None and sweep_direction is not None:
            inner = FieldModel.inner_neighbor(last_path, sweep_direction)
            if inner is not None and path == inner:
                score += 8.0
            score -= FieldModel.path_distance(path, last_path) * 2.0
        return score

    @classmethod
    def _order_tasks_within_path(
        cls,
        tasks_on_path: Sequence[BoxTask],
        quiz_type: int | None,
    ) -> List[BoxTask]:
        return sorted(
            tasks_on_path,
            key=lambda t: (
                cls._task_quiz_rank(t, quiz_type),
                0 if t.direct else 1,
                *cls._same_path_pick_rank(t),
            ),
        )

    @classmethod
    def _group_tasks_by_path(cls, tasks: Sequence[BoxTask]) -> Dict[int, List[BoxTask]]:
        by_path: Dict[int, List[BoxTask]] = {}
        for task in tasks:
            by_path.setdefault(task.pickup.path, []).append(task)
        return by_path

    @classmethod
    def _schedule_safe_edges_paths(
        cls,
        by_path: Dict[int, List[BoxTask]],
        quiz_type: int | None,
    ) -> List[int]:
        """Score first edge, then order pickups so each active path has a cleared side."""
        remaining = set(by_path.keys())
        edge_candidates = [p for p in (1, 5) if p in remaining]
        if edge_candidates:
            tiebreak = (lambda p: -p) if quiz_type is None else (lambda p: p)
            first = max(
                edge_candidates,
                key=lambda p: (cls._path_score(p, by_path[p], None, quiz_type), tiebreak(p)),
            )
            sweep_direction = 1 if first == 1 else -1
        else:
            first = min(remaining)
            sweep_direction = 1 if first <= 3 else -1

        if quiz_type is not None:
            if first == 5:
                return [5, 1, 4, 3, 2]
            return [1, 5, 2, 3, 4]
        if sweep_direction == 1:
            return list(range(first, 6))
        return list(range(first, 0, -1))

    @classmethod
    def _order_safe_edges_tasks(
        cls,
        tasks: Sequence[BoxTask],
        quiz_type: int | None,
        path_order: Sequence[int],
    ) -> List[BoxTask]:
        by_path = cls._group_tasks_by_path(tasks)
        ordered: List[BoxTask] = []
        selected: set[int] = set()
        if quiz_type is not None:
            path_rank = {path: index for index, path in enumerate(path_order)}
            boundary_quiz_tasks = sorted(
                (
                    task for task in tasks
                    if task.box_type == quiz_type and task.pickup.path in (1, 5)
                ),
                key=lambda t: (
                    path_rank.get(t.pickup.path, 99),
                    0 if t.direct else 1,
                    *cls._same_path_pick_rank(t),
                ),
            )
            ordered.extend(boundary_quiz_tasks)
            selected.update(task.box_id for task in boundary_quiz_tasks)
        for path in path_order:
            if path in by_path:
                ordered.extend(
                    task for task in cls._order_tasks_within_path(by_path[path], quiz_type)
                    if task.box_id not in selected
                )
        return ordered

    @classmethod
    def _order_tasks(
        cls,
        tasks: Iterable[BoxTask],
        allowed_paths: Sequence[int],
        strategy: str,
        quiz_type: int | None = None,
    ) -> List[BoxTask]:
        tasks = list(tasks)
        if strategy in ('safe_edges', 'edges', '1,5,2,4'):
            by_path = cls._group_tasks_by_path(tasks)
            path_order = cls._schedule_safe_edges_paths(by_path, quiz_type)
            return cls._order_safe_edges_tasks(tasks, quiz_type, path_order)

        direct_counts: Dict[int, int] = {path: 0 for path in allowed_paths}
        quiz_counts: Dict[int, int] = {path: 0 for path in allowed_paths}
        for task in tasks:
            if task.direct:
                direct_counts[task.pickup.path] += 1
            if quiz_type is not None and task.box_type == quiz_type:
                quiz_counts[task.pickup.path] += 1
        path_order = sorted(
            allowed_paths,
            key=lambda path: (-quiz_counts[path], -direct_counts[path], path),
        )
        order = {path: index for index, path in enumerate(path_order)}
        return sorted(
            tasks,
            key=lambda t: (
                order.get(t.pickup.path, 99),
                cls._task_quiz_rank(t, quiz_type),
                0 if t.direct else 1,
                *cls._same_path_pick_rank(t),
            ),
        )

    def _build_sequence(
        self,
        tasks: Sequence[BoxTask],
        switch_mode: str,
        include_quiz_state: bool,
    ) -> List[MissionStep]:
        sequence: List[MissionStep] = []
        current_path = 0
        current_wp = 0
        start_state = MissionState.QUIZ_RECOGNITION if include_quiz_state else MissionState.TRANSIT
        sequence.append(MissionStep(0, 0, start_state, note='start'))

        def append_step(path: int, wp: int, state: MissionState, task: Optional[BoxTask] = None, note: str = '') -> None:
            nonlocal current_path, current_wp
            step = MissionStep(
                path=path,
                wp=wp,
                state=state,
                target_box=task.box_id if task and state in (
                    MissionState.PICK_LEFT,
                    MissionState.PICK_RIGHT,
                    MissionState.PLACE_LEFT,
                    MissionState.PLACE_RIGHT,
                ) else None,
                target_zone=task.zone_id if task and state in (
                    MissionState.PICK_LEFT,
                    MissionState.PICK_RIGHT,
                    MissionState.PLACE_LEFT,
                    MissionState.PLACE_RIGHT,
                ) else None,
                box_type=task.box_type if task else None,
                zone_type=task.zone_type if task else None,
                note=note,
            )
            if sequence and sequence[-1].path == path and sequence[-1].wp == wp and sequence[-1].state == state and sequence[-1].target_box == step.target_box and sequence[-1].target_zone == step.target_zone:
                return
            sequence.append(step)
            current_path, current_wp = path, wp

        def move_within_path(path: int, target_wp: int, final_state: MissionState = MissionState.TRANSIT, task: Optional[BoxTask] = None, note: str = '') -> None:
            nonlocal current_path, current_wp
            if current_path != path:
                raise RuntimeError('move_within_path called across paths')
            if current_wp == target_wp:
                append_step(path, target_wp, final_state, task, note)
                return
            step = 1 if target_wp > current_wp else -1
            for wp in range(current_wp + step, target_wp + step, step):
                is_final = wp == target_wp
                append_step(path, wp, final_state if is_final else MissionState.TRANSIT, task if is_final else None, note if is_final else 'transit')

        def move_to(path: int, target_wp: int, final_state: MissionState = MissionState.TRANSIT, task: Optional[BoxTask] = None, note: str = '') -> None:
            nonlocal current_path, current_wp
            if current_path == 0:
                append_step(path, 1, MissionState.TRANSIT, note=f'enter path {path}')
            elif current_path != path:
                if switch_mode == 'wp4_or_wp5' and target_wp == 5 and abs(path - current_path) == 1:
                    if current_wp != 4:
                        move_within_path(current_path, 4)
                    append_step(path, 5, final_state, task, note)
                    return
                step = 1 if path > current_path else -1
                for mid in range(current_path + step, path, step):
                    if current_wp != 4:
                        move_within_path(current_path, 4)
                    append_step(mid, 4, MissionState.TRANSIT, note=f'transit path {mid}')
                if current_wp != 4:
                    move_within_path(current_path, 4)
                append_step(path, 4, MissionState.TRANSIT, note=f'switch to path {path}')
            move_within_path(path, target_wp, final_state, task, note)

        for task in tasks:
            pickup_wp = self.field.box_slots[task.box_id].pickup_wp
            move_to(task.pickup.path, pickup_wp, task.pickup.state, task, f'pick box {task.box_id}')
            move_to(task.place.path, 5, task.place.state, task, f'place box {task.box_id} to zone {task.zone_id}')

        return sequence
