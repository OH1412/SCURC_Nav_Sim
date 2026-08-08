from __future__ import annotations

from .state_definitions import MissionState


def derive_motion_planner(path: int, wp: int, state: int) -> int:
    """Derive Nav2 motion_planner id for a mission step.

    0 = already backing / corridor rear approach (fallback pick at 4-1)
    1 = forward strategy (all place waypoints)
    2 = walk backward then pick (all other pick waypoints)
    3 = straight (x-only, no yaw/vy, no path heading relation)
    """
    state = int(state)
    if state == int(MissionState.PICK):
        # 保底 4-1：启动后已倒着靠近，直接用 0；其余吸取点倒着走 2
        return 0 if path == 4 and wp == 1 else 2
    if state == int(MissionState.PLACE):
        return 1
    return 0


def is_bt_export_step(state: int) -> bool:
    """BT export includes pick/place steps only."""
    return int(state) in (int(MissionState.PICK), int(MissionState.PLACE))
