from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

from .state_definitions import MissionState


FALLBACK_BOX_ID = 6
PATH4_FIRST_BOX_ID = 2
PATH4_LAST_BOX_ID = 6
PATH4_BOX_IDS = (PATH4_FIRST_BOX_ID, PATH4_LAST_BOX_ID)
MAIN_PATHS = (2, 3, 4, 5)
MAX_WAYPOINT = 4

COLUMN_BOX_IDS: Dict[int, tuple[int, ...]] = {
    0: (0, 4),
    1: (1, 5),
    2: (2, 6),
    3: (3, 7),
}


def sync_boxes_to_zones(box_types: list[int], zone_types: Sequence[int]) -> None:
    """Align each column's box types with its placement zone type."""
    if len(box_types) != 8:
        raise ValueError(f'Expected 8 box types, got {len(box_types)}')
    if len(zone_types) != 4:
        raise ValueError(f'Expected 4 zone types, got {len(zone_types)}')
    for zone_id, zone_type in enumerate(zone_types):
        for box_id in COLUMN_BOX_IDS[zone_id]:
            box_types[box_id] = int(zone_type)


@dataclass(frozen=True)
class BoxSlot:
    box_id: int
    row: str
    column: int
    pick_path: int
    pick_wp: int
    pick_state: MissionState


@dataclass(frozen=True)
class PlacementZone:
    zone_id: int
    default_type: int
    place_path: int


class FieldModel:
    """Logical task-field model for front/back suction planning."""

    def __init__(self) -> None:
        self.box_slots: Dict[int, BoxSlot] = {
            0: BoxSlot(0, 'upper', 0, 2, 2, MissionState.PICK),
            1: BoxSlot(1, 'upper', 1, 3, 2, MissionState.PICK),
            2: BoxSlot(2, 'upper', 2, 4, 2, MissionState.PICK),
            3: BoxSlot(3, 'upper', 3, 5, 2, MissionState.PICK),
            4: BoxSlot(4, 'lower', 0, 2, 1, MissionState.PICK),
            5: BoxSlot(5, 'lower', 1, 3, 1, MissionState.PICK),
            6: BoxSlot(6, 'lower', 2, 4, 1, MissionState.PICK),
            7: BoxSlot(7, 'lower', 3, 5, 1, MissionState.PICK),
        }
        self.placement_zones: Dict[int, PlacementZone] = {
            0: PlacementZone(0, 0, 2),
            1: PlacementZone(1, 1, 3),
            2: PlacementZone(2, 2, 4),
            3: PlacementZone(3, 3, 5),
        }

    PATH_NEIGHBORS: Dict[int, tuple[int, ...]] = {
        2: (3,),
        3: (2, 4),
        4: (3, 5),
        5: (4,),
    }

    @classmethod
    def path_distance(cls, a: int, b: int) -> int:
        return abs(a - b)

    def zone_for_type(self, box_type: int, zone_types: Sequence[int]) -> int:
        for zone_id, zone_type in enumerate(zone_types):
            if int(zone_type) == int(box_type):
                return zone_id
        raise ValueError(f'No placement zone configured for box type {box_type}')

    def place_path_for_zone(self, zone_id: int) -> int:
        return self.placement_zones[zone_id].place_path

    def _build_task(
        self,
        box_id: int,
        box_types: Sequence[int],
        zone_types: Sequence[int],
        waypoint_config=None,
    ) -> dict:
        slot = self.box_slots[box_id]
        box_type = int(box_types[box_id])
        zone_id = self.zone_for_type(box_type, zone_types)
        place_path = self.place_path_for_zone(zone_id)
        if waypoint_config is not None:
            pick_meta = waypoint_config.pick_for_box(box_id)
            place_meta = waypoint_config.place_for_zone(zone_id)
            pick_path = pick_meta.path
            pick_wp = pick_meta.wp
            place_wp = place_meta.wp
        else:
            pick_path = slot.pick_path
            pick_wp = slot.pick_wp
            place_wp = MAX_WAYPOINT
        return {
            'box_id': box_id,
            'box_type': box_type,
            'zone_id': zone_id,
            'zone_type': int(zone_types[zone_id]),
            'pick_path': pick_path,
            'pick_wp': pick_wp,
            'pick_state': slot.pick_state,
            'place_path': place_path,
            'place_wp': place_wp,
            'place_state': MissionState.PLACE,
            'row': slot.row,
            'direct': pick_path == place_path,
        }

    def build_path4_task(
        self,
        box_id: int,
        box_types: Sequence[int],
        zone_types: Sequence[int],
        waypoint_config=None,
    ) -> dict:
        """Build a pick/place task for path4 box2 (first) or box6 (last)."""
        if box_id not in PATH4_BOX_IDS:
            raise ValueError(f'path4 task only supports box ids {PATH4_BOX_IDS}, got {box_id}')
        return self._build_task(box_id, box_types, zone_types, waypoint_config)

    def main_tasks(
        self,
        box_types: Sequence[int],
        zone_types: Sequence[int],
        waypoint_config=None,
    ) -> List[dict]:
        """Build pick/place tasks for boxes 0,1,3 and 4,5,7 (path4 box2/box6 handled separately)."""
        return [
            self._build_task(box_id, box_types, zone_types, waypoint_config)
            for box_id in (0, 1, 3, 4, 5, 7)
        ]
