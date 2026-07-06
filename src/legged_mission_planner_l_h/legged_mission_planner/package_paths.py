from __future__ import annotations

from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = PACKAGE_ROOT / 'tmp'
ASSETS_DIR = PACKAGE_ROOT / 'assets'


def resolve_assets_dir() -> Path:
    if ASSETS_DIR.is_dir():
        return ASSETS_DIR
    try:
        from ament_index_python.packages import get_package_share_directory

        return Path(get_package_share_directory('legged_mission_planner')) / 'assets'
    except Exception:
        return ASSETS_DIR
