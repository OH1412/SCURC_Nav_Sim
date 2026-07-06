from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any, Mapping

from .ui_assets import render_path_on_field


def _csv_cell(value: Any) -> str:
    if value is None:
        return ''
    return str(value)


def write_text_summary(plan: Mapping, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator='\n')

    writer.writerow(['field', 'value'])
    for key in (
        'planner_variant',
        'switch_mode',
        'format_version',
        'max_waypoint',
        'quiz_type',
        'quiz_received',
        'quiz_wait_started',
        'plan_source',
    ):
        writer.writerow([key, _csv_cell(plan.get(key))])

    scenario = plan.get('scenario') or {}
    writer.writerow(['box_types', _csv_cell(scenario.get('box_types'))])
    writer.writerow(['zone_types', _csv_cell(scenario.get('zone_types'))])

    writer.writerow([])

    sequence_header = [
        'step', 'path', 'wp', 'state', 'state_label',
        'target_box', 'target_zone', 'box_type', 'zone_type', 'note',
    ]
    writer.writerow(sequence_header)
    for step in plan.get('sequence', []):
        writer.writerow([
            _csv_cell(step.get('step')),
            _csv_cell(step.get('path')),
            _csv_cell(step.get('wp')),
            _csv_cell(step.get('state')),
            _csv_cell(step.get('state_label', '')),
            _csv_cell(step.get('target_box')),
            _csv_cell(step.get('target_zone')),
            _csv_cell(step.get('box_type')),
            _csv_cell(step.get('zone_type')),
            _csv_cell(step.get('note', '')),
        ])

    path.write_text('\ufeff' + buffer.getvalue(), encoding='utf-8')


def draw_plan_on_image(
    plan: Mapping,
    background_path: str | Path | None = None,
    output_path: str | Path | None = None,
    display_width: int = 520,
    layout: Mapping | str | None = None,
    *,
    waypoint_config=None,
    quiz_status: str | None = None,
    quiz_type: int | None = None,
    countdown_s: float | None = None,
) -> bool:
    del background_path
    try:
        from PIL import Image  # noqa: F401
    except Exception:
        return False

    if output_path is None:
        return False

    img = render_path_on_field(
        plan,
        display_width,
        layout=layout,
        waypoint_config=waypoint_config,
        quiz_status=quiz_status,
        quiz_type=quiz_type,
        countdown_s=countdown_s,
    )
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)
    return True
