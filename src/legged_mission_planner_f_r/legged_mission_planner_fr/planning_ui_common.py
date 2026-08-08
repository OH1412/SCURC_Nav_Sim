from __future__ import annotations

import tkinter as tk
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import ImageTk

from .motion_planner import is_bt_export_step
from .path_planner import MissionPathPlanner
from .plan_exporter import PlanExporter
from .plan_ready_publisher import PlanReadyPublisher
from .quintuple_exporter import export_quintuple
from .ui_visualizer import draw_plan_on_image, write_text_summary
from .waypoint_config import WaypointConfig
from .yaml_utils import load_yaml

if TYPE_CHECKING:
    from .ui_field_canvas import FieldCanvas


class PlanningUICommon:
    """Shared planning and export logic for the mission planner UI."""

    field_layout: Path
    field_layout_data: dict
    params: dict
    output_dir: Path
    root: tk.Tk
    field_canvas: FieldCanvas
    preview_label: tk.Label

    plan_ready_topic: str

    _plan_ready_publisher: PlanReadyPublisher
    _base_plan: dict | None
    _base_sequence: list | None
    _scenario: dict | None
    _waypoint_config: WaypointConfig | None
    _preview_photo: object | None

    def _init_planning_common(self, field_layout: str | Path, mission_params: str | Path | None) -> None:
        self.field_layout = Path(field_layout)
        self.field_layout_data = load_yaml(self.field_layout)
        self.mission_params = Path(mission_params) if mission_params else None
        self.params = (
            load_yaml(self.mission_params)
            if self.mission_params and self.mission_params.exists()
            else {}
        )
        self.plan_ready_topic = str(self.params.get('plan_ready_topic', '/mission/plan_ready'))
        self._plan_ready_publisher = PlanReadyPublisher(self.plan_ready_topic)
        self._base_plan = None
        self._base_sequence = None
        self._scenario = None
        self._waypoint_config = None
        self._preview_photo = None

    def _resolve_waypoint_config(self) -> WaypointConfig:
        from .package_paths import resolve_config_path

        ui_points_cfg = self.params.get('ui_points', {})
        rel_path = ui_points_cfg.get('file', 'ui_points_fast_mode.yaml')
        config_path = resolve_config_path(rel_path)
        if config_path.exists():
            return WaypointConfig.from_yaml(config_path)
        loaded = WaypointConfig.load_default()
        if loaded is None:
            raise FileNotFoundError(
                f'需要 ui_points_fast_mode.yaml，查找路径: '
                f'{resolve_config_path("ui_points_fast_mode.yaml")}'
            )
        return loaded

    def _build_planner(self) -> tuple[MissionPathPlanner, WaypointConfig]:
        waypoint_config = self._resolve_waypoint_config()
        planner = MissionPathPlanner(waypoint_config=waypoint_config)
        return planner, waypoint_config

    def _export_plan(
        self,
        sequence,
        scenario: dict,
        *,
        quiz_type: int = -1,
        quiz_received: bool = False,
        quiz_wait_started: bool = False,
        plan_source: str = 'base',
        quiz_status: str | None = None,
        countdown_s: float | None = None,
        publish_ready: bool = True,
    ) -> dict:
        waypoint_config = self._resolve_waypoint_config()
        bt_sequence = [s for s in sequence if is_bt_export_step(int(s.state))]
        exporter = PlanExporter()
        base = self.output_dir / 'mission_plan'
        plan = exporter.export(
            bt_sequence,
            scenario,
            base,
            quiz_type=quiz_type,
            quiz_received=quiz_received,
            quiz_wait_started=quiz_wait_started,
            plan_source=plan_source,
        )
        write_text_summary(plan, self.output_dir / 'mission_plan.csv')
        draw_plan_on_image(
            plan,
            output_path=self.output_dir / 'mission_plan.png',
            display_width=560,
            layout=self.field_layout_data,
            waypoint_config=waypoint_config,
            quiz_type=quiz_type if quiz_received else None,
            quiz_status=quiz_status,
            countdown_s=countdown_s,
        )
        export_quintuple(
            bt_sequence,
            self.output_dir / 'mission_quintuple.yaml',
            waypoint_config=waypoint_config,
        )
        self._waypoint_config = waypoint_config
        if publish_ready:
            self._publish_plan_ready(plan_source=plan_source)
        return plan

    def _publish_plan_ready(self, *, plan_source: str) -> None:
        if not self._plan_ready_publisher.publish(plan_source=plan_source):
            if self._plan_ready_publisher.error:
                print(f'[plan_ready] ROS 不可用: {self._plan_ready_publisher.error}')

    def _update_preview(
        self,
        plan: dict,
        *,
        quiz_type: int | None = None,
        quiz_status: str | None = None,
        countdown_s: float | None = None,
    ) -> None:
        preview = self.field_canvas.render_path_preview(
            plan,
            waypoint_config=self._waypoint_config,
            quiz_type=quiz_type,
            quiz_status=quiz_status,
            countdown_s=countdown_s,
        )
        self._preview_photo = ImageTk.PhotoImage(preview, master=self.root)
        self.preview_label.configure(image=self._preview_photo)
