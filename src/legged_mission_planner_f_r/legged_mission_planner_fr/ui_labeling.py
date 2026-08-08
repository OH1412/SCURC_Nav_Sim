"""Deprecated: use ui_base_plan.BaseMissionPlannerUI instead."""

from __future__ import annotations

import warnings

from .ui_base_plan import BaseMissionPlannerUI, main

MissionPlannerUI = BaseMissionPlannerUI

warnings.warn(
    'legged_mission_planner_fr.ui_labeling is deprecated; use ui_base_plan instead.',
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ['MissionPlannerUI', 'main']
