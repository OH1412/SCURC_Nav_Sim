from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import yaml

from .state_definitions import MissionStep

FORMAT_VERSION = 2


class PlanExporter:
    """Export logical mission sequences (path, wp, state) without map poses."""

    def build_plan(
        self,
        sequence: Sequence[MissionStep],
        scenario: Mapping,
        strategy: str,
        switch_mode: str,
        *,
        quiz_type: int | None = None,
        quiz_received: bool = False,
        quiz_wait_started: bool = False,
        plan_source: str = 'base',
    ) -> dict:
        return {
            'format_version': FORMAT_VERSION,
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'strategy': strategy,
            'switch_mode': switch_mode,
            'scenario': dict(scenario),
            'quiz_type': quiz_type,
            'quiz_received': quiz_received,
            'quiz_wait_started': quiz_wait_started,
            'plan_source': plan_source,
            'sequence': self._logical_sequence(sequence),
        }

    @staticmethod
    def _logical_sequence(sequence: Sequence[MissionStep]) -> list[dict]:
        exported: list[dict] = []
        for step_no, step in enumerate(sequence, start=1):
            item = step.to_dict()
            item['step'] = step_no
            exported.append(item)
        return exported

    @staticmethod
    def write_yaml(plan: Mapping, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w', encoding='utf-8') as f:
            yaml.safe_dump(dict(plan), f, allow_unicode=True, sort_keys=False)

    @staticmethod
    def write_json(plan: Mapping, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w', encoding='utf-8') as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)

    def export(
        self,
        sequence: Sequence[MissionStep],
        scenario: Mapping,
        strategy: str,
        switch_mode: str,
        output_base: str | Path,
        **quiz_meta,
    ) -> dict:
        plan = self.build_plan(sequence, scenario, strategy, switch_mode, **quiz_meta)
        output_base = Path(output_base)
        self.write_yaml(plan, output_base.with_suffix('.yaml'))
        self.write_json(plan, output_base.with_suffix('.json'))
        return plan
