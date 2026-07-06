from __future__ import annotations

from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PACKAGE_ROOT / 'assets'


def find_workspace_src() -> Path:
    """Locate the workspace ``src/`` directory by walking up to the git root.

    Works reliably regardless of whether the package is symlink-installed or
    copied into an install space — it always returns the source-tree path.
    """
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / '.git').exists():
            return parent / 'src'
    # Fallback: assume standard layout  ws/src/<pkg>
    return PACKAGE_ROOT.parent


# Cached at import time — always points to the source workspace, never install.
WS_SRC = find_workspace_src()

DEFAULT_OUTPUT_DIR = WS_SRC / 'legged_mission_planner_f_r' / 'tmp'


def resolve_package_share() -> Path:
    try:
        from ament_index_python.packages import get_package_share_directory

        return Path(get_package_share_directory('legged_mission_planner_f_r'))
    except Exception:
        return WS_SRC / 'legged_mission_planner_f_r'


def resolve_config_path(relative: str | Path) -> Path:
    rel = Path(relative)
    if rel.is_absolute():
        return rel
    share = resolve_package_share()
    rel_str = str(rel).replace('\\', '/')
    if rel_str.startswith('config/'):
        return share / rel_str
    return share / 'config' / rel


def resolve_assets_dir() -> Path:
    share_assets = resolve_package_share() / 'assets'
    if share_assets.is_dir():
        return share_assets
    if ASSETS_DIR.is_dir():
        return ASSETS_DIR
    return share_assets
