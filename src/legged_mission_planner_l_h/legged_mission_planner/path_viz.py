from __future__ import annotations

from typing import Any, Mapping, Tuple

from .pose_resolver import load_yaml

# Start zone center measured on 场地俯视图.png (460 x 577).
START_ZONE_NORM = (247.5 / 460.0, 502.0 / 577.0)


def step_to_local_xy(step: Mapping[str, Any], layout: Mapping[str, Any]) -> Tuple[float, float] | None:
    """Map a mission step to field-local (x, y) on a path straight line.

    Each path is a vertical line at fixed y (distance from the right wall).
    All waypoints on the same path share that y; only x changes by wp row.
    Returns None for the start step (drawn at the start-zone center).
    """
    path = int(step['path'])
    wp = int(step['wp'])
    if path == 0 and wp == 0:
        return None

    paths = layout.get('paths', {})
    rows = layout.get('waypoint_rows', {})
    # x is measured from the 6m field lower boundary; y is the path lane.
    return float(rows[wp]['x']), float(paths[path]['y'])


def resolve_layout(layout: Mapping[str, Any] | str | None) -> Mapping[str, Any]:
    if layout is None:
        return {}
    if isinstance(layout, str):
        return load_yaml(layout)
    return layout
