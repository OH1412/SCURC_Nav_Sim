"""Deprecated: waypoint calibration will move to legged_bringup.

Run manually: python -m legged_mission_planner.calibrate_waypoints
"""
from __future__ import annotations

import argparse
from pathlib import Path

import yaml


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description='Create or update waypoint calibration YAML from manual input.')
    parser.add_argument('--output', default='field_layout_calibrated.yaml')
    parser.add_argument('--fixed-yaw', type=float, default=0.0)
    args = parser.parse_args(argv)

    print('手动标定模式：依次输入 path wp x y。空行结束。')
    overrides = {}
    while True:
        line = input('path wp x y> ').strip()
        if not line:
            break
        path_id, wp_id, x, y = line.split()
        overrides[f'p{int(path_id)}_w{int(wp_id)}'] = {'x': float(x), 'y': float(y)}

    data = {
        'frame': {'id': 'map', 'local_origin_in_map': [0.0, 0.0, 0.0], 'fixed_yaw': args.fixed_yaw},
        'waypoint_overrides': overrides,
    }
    output = Path(args.output)
    with output.open('w', encoding='utf-8') as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
    print(f'已保存 {output}')


if __name__ == '__main__':
    main()
