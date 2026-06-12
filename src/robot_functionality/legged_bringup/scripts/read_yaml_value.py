#!/usr/bin/env python3

import sys

import yaml


DEFAULTS = {
    "cmd_vx_min": -1.0,
    "cmd_vx_max": 1.0,
    "cmd_vy_min": -1.0,
    "cmd_vy_max": 1.0,
    "cmd_yaw_min": -5.0,
    "cmd_yaw_max": 5.0,
    "cmd_velocity_min": [-2.5, -2.5, -12.0],
    "cmd_velocity_max": [2.5, 2.5, 12.0],
}


def main() -> int:
    if len(sys.argv) < 3:
        print("")
        return 0

    yaml_path = sys.argv[1]
    key = sys.argv[2]

    try:
        with open(yaml_path, "r", encoding="utf-8") as stream:
            root = yaml.safe_load(stream) or {}
    except Exception:
        root = {}

    if key == "cmd_velocity_min":
        value = [
            root.get("cmd_vx_min", ""),
            root.get("cmd_vy_min", ""),
            root.get("cmd_yaw_min", ""),
        ]
    elif key == "cmd_velocity_max":
        value = [
            root.get("cmd_vx_max", ""),
            root.get("cmd_vy_max", ""),
            root.get("cmd_yaw_max", ""),
        ]
    else:
        value = root.get(key, DEFAULTS.get(key, ""))

    if value is None:
        print("")
    else:
        print(value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())