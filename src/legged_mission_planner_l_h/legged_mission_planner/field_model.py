from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from .state_definitions import MissionState


@dataclass(frozen=True)
class PickupOption:
    path: int
    state: MissionState


@dataclass(frozen=True)
class PlaceOption:
    path: int
    state: MissionState


@dataclass(frozen=True)
class BoxSlot:
    box_id: int
    row: str
    column: int
    pickup_wp: int
    pickup_options: tuple[PickupOption, ...]


@dataclass(frozen=True)
class PlacementZone:
    zone_id: int
    default_type: int
    place_options: tuple[PlaceOption, ...]


class FieldModel:
    """Logical task-field model, independent from measured coordinates."""

    def __init__(self) -> None:
        self.box_slots: Dict[int, BoxSlot] = {
            0: BoxSlot(0, 'upper', 0, 3, (PickupOption(1, MissionState.PICK_LEFT), PickupOption(2, MissionState.PICK_RIGHT))),
            1: BoxSlot(1, 'upper', 1, 3, (PickupOption(2, MissionState.PICK_LEFT), PickupOption(3, MissionState.PICK_RIGHT))),
            2: BoxSlot(2, 'upper', 2, 3, (PickupOption(3, MissionState.PICK_LEFT), PickupOption(4, MissionState.PICK_RIGHT))),
            3: BoxSlot(3, 'upper', 3, 3, (PickupOption(4, MissionState.PICK_LEFT), PickupOption(5, MissionState.PICK_RIGHT))),
            4: BoxSlot(4, 'lower', 0, 2, (PickupOption(1, MissionState.PICK_LEFT), PickupOption(2, MissionState.PICK_RIGHT))),
            5: BoxSlot(5, 'lower', 1, 2, (PickupOption(2, MissionState.PICK_LEFT), PickupOption(3, MissionState.PICK_RIGHT))),
            6: BoxSlot(6, 'lower', 2, 2, (PickupOption(3, MissionState.PICK_LEFT), PickupOption(4, MissionState.PICK_RIGHT))),
            7: BoxSlot(7, 'lower', 3, 2, (PickupOption(4, MissionState.PICK_LEFT), PickupOption(5, MissionState.PICK_RIGHT))),
        }
        self.placement_zones: Dict[int, PlacementZone] = {
            0: PlacementZone(0, 0, (PlaceOption(1, MissionState.PLACE_LEFT), PlaceOption(2, MissionState.PLACE_RIGHT))),
            1: PlacementZone(1, 1, (PlaceOption(2, MissionState.PLACE_LEFT), PlaceOption(3, MissionState.PLACE_RIGHT))),
            2: PlacementZone(2, 2, (PlaceOption(3, MissionState.PLACE_LEFT), PlaceOption(4, MissionState.PLACE_RIGHT))),
            3: PlacementZone(3, 3, (PlaceOption(4, MissionState.PLACE_LEFT), PlaceOption(5, MissionState.PLACE_RIGHT))),
        }

    @staticmethod
    def strategy_paths(strategy: str) -> List[int]:
        aliases = {
            'safe_edges': [1, 2, 3, 4, 5],
            'edges': [1, 2, 3, 4, 5],
            '1,5,2,4': [1, 2, 3, 4, 5],
            'middle_paths': [2, 3, 4],
            'middle': [2, 3, 4],
            '2,3,4': [2, 3, 4],
        }
        key = strategy.strip().lower()
        if key not in aliases:
            raise ValueError(f'Unknown strategy {strategy!r}')
        return aliases[key]

    @staticmethod
    def switch_modes() -> set[str]:
        return {'wp4_only', 'wp4_or_wp5'}

    # Paths numbered right (1) to left (5).
    PATH_NEIGHBORS: Dict[int, tuple[int, ...]] = {
        1: (2,),
        2: (1, 3),
        3: (2, 4),
        4: (3, 5),
        5: (4,),
    }

    @classmethod
    def inner_neighbor(cls, path: int, direction: int) -> int | None:
        """Next path along sweep direction (+1: 1→5, -1: 5→1)."""
        nxt = path + direction
        return nxt if 1 <= nxt <= 5 else None

    @classmethod
    def path_distance(cls, a: int, b: int) -> int:
        return abs(a - b)

    def zone_for_type(self, box_type: int, zone_types: List[int]) -> int:
        for zone_id, zone_type in enumerate(zone_types):
            if int(zone_type) == int(box_type):
                return zone_id
        raise ValueError(f'No placement zone configured for box type {box_type}')

    def pickup_options(self, box_id: int, allowed_paths: Optional[Iterable[int]] = None) -> List[PickupOption]:
        options = list(self.box_slots[box_id].pickup_options)
        if allowed_paths is not None:
            allowed = set(allowed_paths)
            options = [opt for opt in options if opt.path in allowed]
        return options

    def place_options(self, zone_id: int, allowed_paths: Optional[Iterable[int]] = None) -> List[PlaceOption]:
        options = list(self.placement_zones[zone_id].place_options)
        if allowed_paths is not None:
            allowed = set(allowed_paths)
            options = [opt for opt in options if opt.path in allowed]
        return options

    def direct_pick_place_pairs(self, box_id: int, zone_id: int, allowed_paths: Iterable[int]) -> list[tuple[PickupOption, PlaceOption]]:
        pickups = self.pickup_options(box_id, allowed_paths)
        places = self.place_options(zone_id, allowed_paths)
        return [(p, d) for p in pickups for d in places if p.path == d.path]
