from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

import yaml

from .package_paths import DEFAULT_OUTPUT_DIR, DEFAULT_SCENARIO_FILE, WS_SRC


def default_scenario_path(params: Mapping | None = None) -> Path:
    if params is None:
        return DEFAULT_SCENARIO_FILE
    rel = params.get('base_scenario_file', 'tmp/base_scenario.yaml')
    rel_path = Path(str(rel))
    if rel_path.is_absolute():
        return rel_path
    return WS_SRC / 'legged_mission_planner_f_r' / rel_path


def _validate_scenario(scenario: Mapping) -> None:
    box_types = scenario.get('box_types')
    zone_types = scenario.get('zone_types')
    if not isinstance(box_types, list) or len(box_types) != 8:
        raise ValueError('box_types must be a list of 8 integers')
    if not isinstance(zone_types, list) or len(zone_types) != 4:
        raise ValueError('zone_types must be a list of 4 integers')
    for value in box_types:
        if int(value) not in range(4):
            raise ValueError(f'box type out of range 0~3: {value!r}')
    for value in zone_types:
        if int(value) not in range(4):
            raise ValueError(f'zone type out of range 0~3: {value!r}')


def save_base_scenario(
    scenario: Mapping,
    path: str | Path,
    *,
    output_dir: str | Path | None = None,
) -> Path:
    _validate_scenario(scenario)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        'box_types': [int(v) for v in scenario['box_types']],
        'zone_types': [int(v) for v in scenario['zone_types']],
        'output_dir': str(output_dir or DEFAULT_OUTPUT_DIR),
        'saved_at': datetime.now(timezone.utc).isoformat(),
    }
    with path.open('w', encoding='utf-8') as f:
        yaml.safe_dump(payload, f, allow_unicode=True, sort_keys=False)
    return path


def load_base_scenario(path: str | Path) -> dict:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f'基础场景文件不存在: {path}')
    with path.open('r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}
    _validate_scenario(data)
    output_dir = data.get('output_dir')
    return {
        'box_types': [int(v) for v in data['box_types']],
        'zone_types': [int(v) for v in data['zone_types']],
        'output_dir': Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR,
        'saved_at': data.get('saved_at'),
    }
