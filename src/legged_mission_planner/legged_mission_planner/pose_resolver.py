"""Deprecated: map pose resolution moved to legged_bringup.

Kept for reference during bringup migration. Mission plans no longer export poses.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

import yaml

from .state_definitions import MissionStep, state_side
from .state_definitions import MissionState


def load_yaml(path: str | Path) -> dict:
    with Path(path).open('r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


class PoseResolver:
    """Resolve logical path/waypoint steps into fixed-yaw map-frame poses."""

    def __init__(self, layout: Mapping[str, Any]) -> None:
        self.layout = dict(layout)
        frame = self.layout.get('frame', {})
        self.frame_id = frame.get('id', 'map')
        self.origin_x, self.origin_y, self.origin_yaw = [float(v) for v in frame.get('local_origin_in_map', [0.0, 0.0, 0.0])]
        self.fixed_yaw = float(frame.get('fixed_yaw', 0.0))

    @classmethod
    def from_file(cls, path: str | Path) -> 'PoseResolver':
        return cls(load_yaml(path))

    def resolve_step(self, step: MissionStep) -> dict:
        if step.path == 0 and step.wp == 0:
            local_x = 0.0
            local_y = self._center_y()
        else:
            local_x, local_y = self._local_waypoint(step.path, step.wp)
            local_x, local_y = self._apply_action_offset(local_x, local_y, step)
        map_x, map_y = self._local_to_map(local_x, local_y)
        return {
            'frame_id': self.frame_id,
            'x': round(map_x, 4),
            'y': round(map_y, 4),
            'yaw': round(self._normalize_angle(self.origin_yaw + self.fixed_yaw), 6),
        }

    def resolve_sequence(self, sequence: Iterable[MissionStep]) -> list[dict]:
        resolved = []
        for index, step in enumerate(sequence):
            item = step.to_dict()
            item['index'] = index
            item['pose'] = self.resolve_step(step)
            resolved.append(item)
        return resolved

    def _center_y(self) -> float:
        paths = self.layout.get('paths', {})
        values = [float(v['y']) for v in paths.values()]
        return sum(values) / len(values) if values else 2.0

    def _local_waypoint(self, path_id: int, wp_id: int) -> tuple[float, float]:
        override = self.layout.get('waypoint_overrides', {}).get(f'p{path_id}_w{wp_id}')
        if override:
            return float(override['x']), float(override['y'])
        paths = self.layout.get('paths', {})
        rows = self.layout.get('waypoint_rows', {})
        try:
            y = float(paths[path_id]['y'])
            x = float(rows[wp_id]['x'])
        except KeyError as exc:
            raise ValueError(f'Missing layout entry for path {path_id}, waypoint {wp_id}') from exc
        return x, y

    def _apply_action_offset(self, x: float, y: float, step: MissionStep) -> tuple[float, float]:
        side = state_side(step.state)
        if side is None:
            return x, y
        group = 'place_offsets' if MissionState(step.state) in (
            MissionState.PLACE_LEFT,
            MissionState.PLACE_RIGHT,
        ) else 'pick_offsets'
        offsets = self.layout.get(group, {}).get(side, {})
        return x + float(offsets.get('dx', 0.0)), y + float(offsets.get('dy', 0.0))

    def _local_to_map(self, local_x: float, local_y: float) -> tuple[float, float]:
        c = math.cos(self.origin_yaw)
        s = math.sin(self.origin_yaw)
        map_x = self.origin_x + c * local_x - s * local_y
        map_y = self.origin_y + s * local_x + c * local_y
        return map_x, map_y

    @staticmethod
    def _normalize_angle(angle: float) -> float:
        return math.atan2(math.sin(angle), math.cos(angle))
