from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .package_paths import resolve_config_path
from .state_definitions import MissionState
from .waypoint_yaml_exporter import WaypointUI, load_ui_points

UI_POINTS_FILE = 'ui_points_fast_mode.yaml'


@dataclass(frozen=True)
class StepMeta:
    path: int
    wp: int
    state: int
    target_id: int
    motion_planner: int
    norm_x: float
    norm_y: float


class WaypointConfig:
    """Calibrated waypoint layout loaded from ui_points_fast_mode.yaml."""

    def __init__(self, paths: Mapping[int, list[WaypointUI]]) -> None:
        self._paths = dict(paths)
        self._pick_for_box: dict[int, StepMeta] = {}
        self._place_for_zone: dict[int, StepMeta] = {}
        self._meta: dict[tuple[int, int], StepMeta] = {}
        self._max_wp: dict[int, int] = {}
        self._build_indexes()

    @classmethod
    def from_yaml(cls, path: str | Path) -> 'WaypointConfig':
        return cls(load_ui_points(path))

    @classmethod
    def load_default(cls) -> 'WaypointConfig | None':
        config_path = resolve_config_path(UI_POINTS_FILE)
        if not config_path.exists():
            return None
        return cls.from_yaml(config_path)

    def _build_indexes(self) -> None:
        for path_id, waypoints in self._paths.items():
            if waypoints:
                self._max_wp[path_id] = max(wp.wp_index for wp in waypoints)
            for wp in waypoints:
                meta = StepMeta(
                    path=path_id,
                    wp=wp.wp_index,
                    state=wp.state,
                    target_id=wp.target_id,
                    motion_planner=wp.motion_planner,
                    norm_x=wp.norm_x,
                    norm_y=wp.norm_y,
                )
                self._meta[(path_id, wp.wp_index)] = meta
                if wp.state == int(MissionState.PICK) and wp.target_id >= 0:
                    self._pick_for_box[wp.target_id] = meta
                if wp.state == int(MissionState.PLACE) and wp.target_id >= 0:
                    self._place_for_zone[wp.target_id] = meta

        missing_boxes = sorted(set(range(8)) - set(self._pick_for_box))
        if missing_boxes:
            raise ValueError(f'ui_points missing pick waypoints for boxes: {missing_boxes}')
        missing_zones = sorted(set(range(4)) - set(self._place_for_zone))
        if missing_zones:
            raise ValueError(f'ui_points missing place waypoints for zones: {missing_zones}')

    def max_wp(self, path: int) -> int:
        if path not in self._max_wp:
            raise ValueError(f'Unknown path {path} in ui_points')
        return self._max_wp[path]

    def get_meta(self, path: int, wp: int) -> StepMeta | None:
        return self._meta.get((path, wp))

    def pick_for_box(self, box_id: int) -> StepMeta:
        return self._pick_for_box[box_id]

    def place_for_zone(self, zone_id: int) -> StepMeta:
        return self._place_for_zone[zone_id]

    def coord(self, path: int, wp: int) -> tuple[float, float]:
        meta = self.get_meta(path, wp)
        if meta is None:
            raise KeyError(f'No ui_points entry for path {path} wp {wp}')
        return meta.norm_x, meta.norm_y

    def box_hotspots(self) -> dict[int, tuple[float, float]]:
        """Normalized centers for field-diagram box labeling (from pick waypoints)."""
        return {
            box_id: (self.pick_for_box(box_id).norm_x, self.pick_for_box(box_id).norm_y)
            for box_id in range(8)
        }

    def zone_hotspots(self) -> dict[int, tuple[float, float]]:
        """Normalized centers for field-diagram zone labeling (from place waypoints)."""
        return {
            zone_id: (self.place_for_zone(zone_id).norm_x, self.place_for_zone(zone_id).norm_y)
            for zone_id in range(4)
        }
