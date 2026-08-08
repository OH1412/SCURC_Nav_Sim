from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Optional


class MissionState(IntEnum):
    QUIZ_RECOGNITION = 0   # 智力题识别
    TRANSIT = 1             # 纯走点
    PICK = 2                # 吸取（合并原 PICK_FRONT 和 PICK_BACK）
    PLACE = 3               # 放置（原 PLACE_FRONT=4 改为 3）


STATE_LABELS = {
    MissionState.QUIZ_RECOGNITION: 'quiz_recognition',
    MissionState.TRANSIT: 'transit',
    MissionState.PICK: 'pick',
    MissionState.PLACE: 'place',
}

PICK_STATES = {MissionState.PICK}
PLACE_STATES = {MissionState.PLACE}
ACTION_STATES = PICK_STATES | PLACE_STATES


def state_direction(state: int | MissionState) -> Optional[str]:
    # 前后吸取方向现在由行为树根据箱子 ID 在 BT 包中自行判断
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
