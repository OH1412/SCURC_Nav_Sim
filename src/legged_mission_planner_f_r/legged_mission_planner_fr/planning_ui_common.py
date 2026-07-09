from __future__ import annotations

import time
import tkinter as tk
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from PIL import ImageTk

from .motion_planner import is_bt_export_step
from .path_planner import MissionPathPlanner
from .plan_exporter import PlanExporter
from .plan_ready_publisher import PlanReadyPublisher
from .quintuple_exporter import export_quintuple
from .quiz_listener import QuizResultListener
from .ui_assets import ITEM_TYPES, icon_image, photo_image
from .ui_visualizer import draw_plan_on_image, write_text_summary
from .waypoint_config import WaypointConfig
from .yaml_utils import load_yaml

if TYPE_CHECKING:
    from .ui_field_canvas import FieldCanvas


class PlanningUICommon:
    """Shared planning, export, and quiz-wait logic for base/quiz UIs."""

    field_layout: Path
    field_layout_data: dict
    params: dict
    output_dir: Path
    root: tk.Tk
    field_canvas: FieldCanvas
    preview_label: tk.Label

    quiz_topic: str
    plan_ready_topic: str
    quiz_timeout_s: float

    _plan_ready_publisher: PlanReadyPublisher
    _base_plan: dict | None
    _base_sequence: list | None
    _scenario: dict | None
    _quiz_listener: QuizResultListener | None
    _quiz_wait_deadline: float | None
    _quiz_poll_after_id: str | None
    _quiz_waiting: bool
    _quiz_result_pending: int | None
    _waypoint_config: WaypointConfig | None
    _preview_photo: object | None
    _on_quiz_finalize_success: Callable[[], None] | None
    _on_quiz_finalize_timeout: Callable[[], None] | None

    quiz_status_label: tk.Label
    quiz_countdown_label: tk.Label
    quiz_icon_label: tk.Label

    def _init_planning_common(self, field_layout: str | Path, mission_params: str | Path | None) -> None:
        self.field_layout = Path(field_layout)
        self.field_layout_data = load_yaml(self.field_layout)
        self.mission_params = Path(mission_params) if mission_params else None
        self.params = (
            load_yaml(self.mission_params)
            if self.mission_params and self.mission_params.exists()
            else {}
        )
        self.quiz_topic = str(self.params.get('quiz_result_topic', '/mission/quiz_type'))
        self.plan_ready_topic = str(self.params.get('plan_ready_topic', '/mission/plan_ready'))
        self.quiz_timeout_s = float(self.params.get('quiz_wait_timeout_s', 20.0))
        self._plan_ready_publisher = PlanReadyPublisher(self.plan_ready_topic)
        self._base_plan = None
        self._base_sequence = None
        self._scenario = None
        self._quiz_listener = None
        self._quiz_wait_deadline = None
        self._quiz_poll_after_id = None
        self._quiz_waiting = False
        self._quiz_result_pending = None
        self._waypoint_config = None
        self._preview_photo = None
        self._on_quiz_finalize_success = None
        self._on_quiz_finalize_timeout = None

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
        quiz_type: int | None = None,
        quiz_received: bool = False,
        quiz_wait_started: bool = False,
        plan_source: str = 'base',
        quiz_status: str | None = None,
        countdown_s: float | None = None,
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
            quiz_status=quiz_status,
            quiz_type=quiz_type,
            countdown_s=countdown_s,
        )
        export_quintuple(
            bt_sequence,
            self.output_dir / 'mission_quintuple.yaml',
            waypoint_config=waypoint_config,
        )
        self._waypoint_config = waypoint_config
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
        quiz_status: str | None = None,
        quiz_type: int | None = None,
        countdown_s: float | None = None,
    ) -> None:
        preview = self.field_canvas.render_path_preview(
            plan,
            waypoint_config=self._waypoint_config,
            quiz_status=quiz_status,
            quiz_type=quiz_type,
            countdown_s=countdown_s,
        )
        self._preview_photo = ImageTk.PhotoImage(preview, master=self.root)
        self.preview_label.configure(image=self._preview_photo)

    def _reset_quiz_panel(self) -> None:
        self.quiz_status_label.config(text='未启用智力题策略', fg='#6c757d')
        self.quiz_countdown_label.config(text='')
        self.quiz_icon_label.config(image='')
        self.quiz_icon_label.image = None

    def _cancel_quiz_wait(self) -> None:
        if self._quiz_poll_after_id is not None:
            self.root.after_cancel(self._quiz_poll_after_id)
            self._quiz_poll_after_id = None
        self._quiz_waiting = False
        self._quiz_wait_deadline = None
        self._quiz_result_pending = None
        if self._quiz_listener is not None:
            self._quiz_listener.stop()
            self._quiz_listener = None

    def _on_quiz_result(self, quiz_type: int) -> None:
        self._quiz_result_pending = quiz_type

    def _start_quiz_wait(
        self,
        *,
        on_finalize_success: Callable[[], None] | None = None,
        on_finalize_timeout: Callable[[], None] | None = None,
    ) -> None:
        if self._base_plan is None or self._scenario is None:
            from tkinter import messagebox

            messagebox.showwarning('提示', '缺少基础规划数据，无法等待智力题。')
            return
        self._cancel_quiz_wait()
        self._quiz_waiting = True
        self._on_quiz_finalize_success = on_finalize_success
        self._on_quiz_finalize_timeout = on_finalize_timeout
        self.quiz_status_label.config(text='等待智力题识别结果…', fg='#1d3557')
        self.quiz_countdown_label.config(text=f'{int(self.quiz_timeout_s)}s')
        self.quiz_icon_label.config(image='')
        self.quiz_icon_label.image = None

        self._quiz_listener = QuizResultListener(self.quiz_topic, self._on_quiz_result)
        self._quiz_listener.start()
        if not self._quiz_listener.ros_available and self._quiz_listener.error:
            self.quiz_status_label.config(text=f'未连接 ROS（{self._quiz_listener.error}）', fg='#e63946')

        self._quiz_wait_deadline = time.monotonic() + self.quiz_timeout_s
        self._update_preview(self._base_plan, quiz_status='waiting', countdown_s=self.quiz_timeout_s)
        self._poll_quiz_wait()

    def _poll_quiz_wait(self) -> None:
        if not self._quiz_waiting or self._quiz_wait_deadline is None:
            return

        remaining = self._quiz_wait_deadline - time.monotonic()
        if self._quiz_result_pending is not None:
            self._finalize_quiz(self._quiz_result_pending)
            return

        if self._quiz_listener is not None and self._quiz_listener.result is not None:
            self._finalize_quiz(self._quiz_listener.result)
            return

        if remaining <= 0:
            self._finalize_quiz_timeout()
            return

        secs = max(0, int(remaining + 0.999))
        self.quiz_countdown_label.config(text=f'{secs}s')
        if self._base_plan is not None:
            self._update_preview(self._base_plan, quiz_status='waiting', countdown_s=remaining)
        self._quiz_poll_after_id = self.root.after(200, self._poll_quiz_wait)

    def _finalize_quiz(self, quiz_type: int) -> None:
        from tkinter import messagebox

        self._cancel_quiz_wait()
        try:
            assert self._scenario is not None
            scenario = {
                'box_types': list(self._scenario['box_types']),
                'zone_types': list(self._scenario['zone_types']),
                'include_quiz_state': True,
            }
            planner, waypoint_config = self._build_planner()
            self._waypoint_config = waypoint_config
            sequence = planner.plan(
                scenario['box_types'],
                scenario['zone_types'],
                include_quiz_state=True,
                quiz_type=quiz_type,
                waypoint_config=waypoint_config,
            )
            plan = self._export_plan(
                sequence,
                scenario,
                quiz_type=quiz_type,
                quiz_received=True,
                quiz_wait_started=True,
                plan_source='quiz',
                quiz_status='received',
            )
            self._base_plan = plan
            self._base_sequence = sequence
            self._update_preview(plan, quiz_status='received', quiz_type=quiz_type)
            item = ITEM_TYPES[quiz_type]
            self.quiz_status_label.config(text=f'智力题：{item.label}（{quiz_type}号）', fg='#1d3557')
            self.quiz_countdown_label.config(text='')
            icon = photo_image(icon_image(quiz_type, 64), self.root)
            self.quiz_icon_label.config(image=icon)
            self.quiz_icon_label.image = icon
            messagebox.showinfo('二次规划完成', f'收到智力题种类 {quiz_type}，已覆盖导出到:\n{self.output_dir}')
            if self._on_quiz_finalize_success is not None:
                self._on_quiz_finalize_success()
        except Exception as exc:
            messagebox.showerror('二次规划失败', str(exc))
        finally:
            self._on_quiz_finalize_success = None
            self._on_quiz_finalize_timeout = None

    def _finalize_quiz_timeout(self) -> None:
        from tkinter import messagebox

        self._cancel_quiz_wait()
        if self._base_plan is not None:
            self._update_preview(self._base_plan, quiz_status='timeout')
        self.quiz_status_label.config(text='未收到智力题，保持基础规划', fg='#e63946')
        self.quiz_countdown_label.config(text='0s')
        self.quiz_icon_label.config(image='')
        self.quiz_icon_label.image = None
        # 不写盘，但用已有基础规划触发 BT 转换链
        self._publish_plan_ready(plan_source='base')
        messagebox.showinfo('智力题超时', f'未在 {int(self.quiz_timeout_s)}s 内收到智力题，保留基础规划输出。')
        if self._on_quiz_finalize_timeout is not None:
            self._on_quiz_finalize_timeout()
        self._on_quiz_finalize_success = None
        self._on_quiz_finalize_timeout = None
