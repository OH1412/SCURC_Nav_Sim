import pytest

from legged_mission_planner_fr.motion_planner import derive_motion_planner, is_bt_export_step
from legged_mission_planner_fr.state_definitions import MissionState


@pytest.mark.parametrize(
    ('path', 'wp', 'state', 'expected'),
    [
        (4, 1, MissionState.PICK, 0),  # 保底 box6：已倒着靠近
        (2, 1, MissionState.PICK, 2),  # 其它吸取：倒着走
        (2, 2, MissionState.PICK, 2),
        (3, 2, MissionState.PICK, 2),
        (5, 1, MissionState.PICK, 2),
        (2, 3, MissionState.PLACE, 1),  # 归放区：向前策略
        (4, 3, MissionState.PLACE, 1),
        (2, 2, MissionState.TRANSIT, 0),
        (0, 0, MissionState.QUIZ_RECOGNITION, 0),
    ],
)
def test_derive_motion_planner(path, wp, state, expected):
    assert derive_motion_planner(path, wp, int(state)) == expected


@pytest.mark.parametrize(
    ('state', 'exported'),
    [
        (MissionState.PICK, True),
        (MissionState.PLACE, True),
        (MissionState.TRANSIT, False),
        (MissionState.QUIZ_RECOGNITION, False),
    ],
)
def test_is_bt_export_step(state, exported):
    assert is_bt_export_step(int(state)) is exported
