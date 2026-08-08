import pytest

from legged_mission_planner_fr.scenario_store import (
    load_base_scenario,
    save_base_scenario,
)


def test_save_and_load_round_trip(tmp_path):
    scenario = {
        'box_types': [0, 1, 2, 3, 0, 1, 2, 3],
        'zone_types': [0, 1, 2, 3],
    }
    path = tmp_path / 'base_scenario.yaml'
    save_base_scenario(scenario, path, output_dir=tmp_path / 'out')
    loaded = load_base_scenario(path)
    assert loaded['box_types'] == scenario['box_types']
    assert loaded['zone_types'] == scenario['zone_types']
    assert loaded['output_dir'] == tmp_path / 'out'
    assert loaded['saved_at'] is not None


def test_validate_box_types_length(tmp_path):
    with pytest.raises(ValueError, match='box_types'):
        save_base_scenario({'box_types': [0, 1], 'zone_types': [0, 1, 2, 3]}, tmp_path / 'bad.yaml')


def test_validate_zone_types_length(tmp_path):
    with pytest.raises(ValueError, match='zone_types'):
        save_base_scenario(
            {'box_types': [0, 1, 2, 3, 0, 1, 2, 3], 'zone_types': [0, 1]},
            tmp_path / 'bad.yaml',
        )


def test_load_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_base_scenario(tmp_path / 'missing.yaml')
