from __future__ import annotations

import argparse
import itertools
from pathlib import Path
from typing import Iterator, Sequence

from .package_paths import DEFAULT_OUTPUT_DIR
from .path_planner import MissionPathPlanner
from .plan_exporter import PlanExporter


def valid_box_type_permutations() -> Iterator[list[int]]:
    base = [0, 0, 1, 1, 2, 2, 3, 3]
    for perm in sorted(set(itertools.permutations(base))):
        yield list(perm)


def enumerate_scenarios(
    switch_modes: Sequence[str] = ('safe_mode', 'fast_mode'),
    zone_types: Sequence[int] = (0, 1, 2, 3),
    limit: int | None = None,
) -> Iterator[dict]:
    count = 0
    for box_types in valid_box_type_permutations():
        for switch_mode in switch_modes:
            yield {
                'switch_mode': switch_mode,
                'box_types': box_types,
                'zone_types': list(zone_types),
                'include_quiz_state': False,
            }
            count += 1
            if limit is not None and count >= limit:
                return


def export_enumerated(
    output_dir: str | Path,
    limit: int | None = None,
) -> list[Path]:
    planner = MissionPathPlanner()
    exporter = PlanExporter()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    exported: list[Path] = []
    for index, scenario in enumerate(enumerate_scenarios(limit=limit)):
        sequence = planner.plan(
            box_types=scenario['box_types'],
            zone_types=scenario['zone_types'],
            switch_mode=scenario['switch_mode'],
            include_quiz_state=scenario.get('include_quiz_state', False),
        )
        name = f"scenario_{index:04d}_{scenario['switch_mode']}"
        base = output_dir / name
        exporter.export(sequence, scenario, scenario['switch_mode'], base)
        exported.append(base)
    return exported


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description='Export front/back mission-planner scenario files.')
    parser.add_argument('--output-dir', default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument('--limit', type=int, default=20, help='Maximum scenarios to export; use 0 for all.')
    args = parser.parse_args(argv)
    limit = None if args.limit == 0 else args.limit
    exported = export_enumerated(args.output_dir, limit)
    print(f'Exported {len(exported)} scenario(s) to {Path(args.output_dir).resolve()}')


if __name__ == '__main__':
    main()
