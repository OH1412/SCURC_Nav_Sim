from __future__ import annotations

from .state_definitions import MissionState


def derive_motion_planner(path: int, wp: int, state: int) -> int:
    """Derive Nav2 motion_planner id for a mission step.

    0 = corridor multi-phase (transit, not exported to BT)
    1 = edge front-tangent (path1 wp1 forward pick, all place)
    2 = edge rear-tangent (backward pick)
    """
    state = int(state)
    if state == int(MissionState.PICK):
        return 1 if path == 1 and wp == 1 else 2
    if state == int(MissionState.PLACE):
        return 1
    return 0


def is_bt_export_step(state: int) -> bool:
    """BT export includes pick/place steps only."""
    return int(state) in (int(MissionState.PICK), int(MissionState.PLACE))
