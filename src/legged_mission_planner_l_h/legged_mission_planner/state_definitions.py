from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Optional


class MissionState(IntEnum):
    QUIZ_RECOGNITION = 0
    TRANSIT = 1
    PICK_LEFT = 2
    PICK_RIGHT = 3
    PLACE_LEFT = 4
    PLACE_RIGHT = 5


STATE_LABELS = {
    MissionState.QUIZ_RECOGNITION: 'quiz_recognition',
    MissionState.TRANSIT: 'transit',
    MissionState.PICK_LEFT: 'pick_left',
    MissionState.PICK_RIGHT: 'pick_right',
    MissionState.PLACE_LEFT: 'place_left',
    MissionState.PLACE_RIGHT: 'place_right',
}

PICK_STATES = {MissionState.PICK_LEFT, MissionState.PICK_RIGHT}
PLACE_STATES = {MissionState.PLACE_LEFT, MissionState.PLACE_RIGHT}
ACTION_STATES = PICK_STATES | PLACE_STATES


def state_side(state: int | MissionState) -> Optional[str]:
    state = MissionState(state)
    if state in (MissionState.PICK_LEFT, MissionState.PLACE_LEFT):
        return 'left'
    if state in (MissionState.PICK_RIGHT, MissionState.PLACE_RIGHT):
        return 'right'
    return None


@dataclass(frozen=True)
class MissionStep:
    path: int
    wp: int
    state: MissionState
    target_box: Optional[int] = None
    target_zone: Optional[int] = None
    box_type: Optional[int] = None
    zone_type: Optional[int] = None
    note: str = ''

    def to_dict(self) -> dict:
        return {
            'path': self.path,
            'wp': self.wp,
            'state': int(self.state),
            'state_label': STATE_LABELS[self.state],
            'target_box': self.target_box,
            'target_zone': self.target_zone,
            'box_type': self.box_type,
            'zone_type': self.zone_type,
            'note': self.note,
        }
