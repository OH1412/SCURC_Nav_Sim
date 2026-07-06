from __future__ import annotations

from collections import Counter
from typing import Iterable, Sequence

from .state_definitions import MissionStep, MissionState


def validate_box_types(box_types: Sequence[int]) -> None:
    if len(box_types) != 8:
        raise ValueError(f'Expected 8 box types, got {len(box_types)}')
    counts = Counter(int(v) for v in box_types)
    expected = {0, 1, 2, 3}
    if set(counts) != expected or any(counts[t] != 2 for t in expected):
        raise ValueError(f'Box types must contain exactly two of each type 0..3, got {dict(counts)}')


def validate_zone_types(zone_types: Sequence[int]) -> None:
    if len(zone_types) != 4:
        raise ValueError(f'Expected 4 zone types, got {len(zone_types)}')
    if set(int(v) for v in zone_types) != {0, 1, 2, 3}:
        raise ValueError(f'Zone types must be a permutation of 0..3, got {list(zone_types)}')


def validate_sequence(sequence: Iterable[MissionStep]) -> None:
    for index, step in enumerate(sequence):
        if step.path < 0 or step.path > 5:
            raise ValueError(f'Step {index} has invalid path {step.path}')
        if step.wp < 0 or step.wp > 5:
            raise ValueError(f'Step {index} has invalid waypoint {step.wp}')
        MissionState(step.state)
