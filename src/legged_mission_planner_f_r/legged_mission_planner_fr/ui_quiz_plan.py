"""Quiz-based replan UI: loads base scenario, auto-starts countdown, replans on quiz received."""

from __future__ import annotations

import argparse
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from PIL import ImageTk

from .label_hotspots import load_default_label_hotspots
from .package_paths import DEFAULT_OUTPUT_DIR
from .planning_ui_common import PlanningUICommon
from .plan_ready_publisher import PlanReadyPublisher
from .quiz_listener import QuizResultListener
from .scenario_store import default_scenario_path, load_base_scenario
from .ui_assets import ITEM_TYPES, icon_image, photo_image, render_path_on_field


class QuizPlanUI(PlanningUICommon):
    """Quiz-only UI: auto countdown on launch, replan when quiz received. No manual interaction needed."""

    def __init__(self, field_layout: str, mission_params: str | None = None) -> None:
        self._init_planning_common(field_layout, mission_params)

        self.quiz_topic = str(self.params.get('quiz_result_topic', '/mission/quiz_type'))
        self.quiz_timeout_default_s = float(self.params.get('quiz_wait_timeout_s', 15.0))
        self.base_plan_ready_topic = str(
            self.params.get('base_plan_ready_topic', '/mission/base_plan_ready')
        )
        self.quiz_plan_ready_topic = str(
            self.params.get('quiz_plan_ready_topic', '/mission/quiz_plan_ready')
        )
        self._base_plan_ready_publisher = PlanReadyPublisher(
            self.base_plan_ready_topic,
            node_name='quiz_base_plan_ready_pub',
        )
        self._quiz_plan_ready_publisher = PlanReadyPublisher(
            self.quiz_plan_ready_topic,
            node_name='quiz_plan_ready_pub',
        )

        self._quiz_listener: QuizResultListener | None = None
        self._quiz_wait_deadline: float | None = None
        self._quiz_poll_after_id: str | None = None
        self._quiz_waiting = False
        self._quiz_result_pending: int | None = None

        # Load base scenario
        self.scenario_path = default_scenario_path(self.params)
        try:
            loaded = load_base_scenario(self.scenario_path)
            self.box_types = loaded['box_types']
            self.zone_types = loaded['zone_types']
            self.output_dir = loaded.get('output_dir', DEFAULT_OUTPUT_DIR)
            self._scenario_loaded = True
            self._load_error = None
        except FileNotFoundError as e:
            self.box_types = [0] * 8
            self.zone_types = [0, 1, 2, 3]
            self.output_dir = DEFAULT_OUTPUT_DIR
            self._scenario_loaded = False
            self._load_error = str(e)

        self._palette_photos: list = []
        self._label_hotspot_config = load_default_label_hotspots()
        self._display_width = 700

        self.root = tk.Tk()
        self.quiz_timeout_var = tk.DoubleVar(self.root, value=self.quiz_timeout_default_s)
        self.root.title('ROBOCON 2026 · 智力题规划')
        self.root.minsize(700, 650)
        self.root.configure(bg='#f8f9fa')
        self._setup_style()
        self._build()

        # Auto-start: countdown begins IMMEDIATELY, base plan generated in parallel
        if self._scenario_loaded:
            self.root.after(50, self._start_countdown_only)
            self.root.after(100, self._generate_and_show_base_plan)

    def _setup_style(self) -> None:
        style = ttk.Style(self.root)
        if 'clam' in style.theme_names():
            style.theme_use('clam')
        style.configure('Title.TLabel', font=('Sans', 15, 'bold'), background='#f8f9fa', foreground='#1d3557')
        style.configure('Hint.TLabel', font=('Sans', 10), background='#f8f9fa', foreground='#495057')
        style.configure('Card.TFrame', background='#ffffff', relief='flat')
        style.configure('Accent.TButton', font=('Sans', 11, 'bold'), padding=8)

    def _build(self) -> None:
        # ── Header ──
        header = ttk.Frame(self.root, style='Card.TFrame', padding=12)
        header.pack(fill='x', padx=14, pady=(14, 8))
        ttk.Label(header, text='ROBOCON 2026 仿生足式机器人 · 智力题规划', style='Title.TLabel').pack(anchor='w')
        ttk.Label(
            header,
            text='启动后自动倒计时，收到智力题则自动二次规划覆盖导出，超时保持基础规划。',
            style='Hint.TLabel',
        ).pack(anchor='w', pady=(4, 0))

        # ── Main body ──
        body = ttk.Frame(self.root, padding=14)
        body.pack(fill='both', expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(1, weight=1)

        # ── Scenario info + countdown row ──
        top_row = ttk.Frame(body, style='Card.TFrame')
        top_row.grid(row=0, column=0, sticky='ew', pady=(0, 12))
        top_row.columnconfigure(0, weight=1)

        # Scenario info card (left)
        info_card = ttk.Frame(top_row, style='Card.TFrame', padding=14)
        info_card.grid(row=0, column=0, sticky='nsew', padx=(0, 8))

        if self._scenario_loaded:
            ttk.Label(
                info_card,
                text=f'已加载场景: {self.scenario_path.name}',
                font=('Sans', 11, 'bold'),
                background='#ffffff',
                foreground='#1d3557',
            ).pack(anchor='w')
            box_summary = ', '.join(f'box{i}={t}' for i, t in enumerate(self.box_types))
            zone_summary = ', '.join(f'zone{i}={t}' for i, t in enumerate(self.zone_types))
            ttk.Label(
                info_card,
                text=f'箱子: [{box_summary}]',
                background='#ffffff',
                foreground='#495057',
            ).pack(anchor='w', pady=(4, 0))
            ttk.Label(
                info_card,
                text=f'归放区: [{zone_summary}]',
                background='#ffffff',
                foreground='#495057',
            ).pack(anchor='w')
        else:
            ttk.Label(
                info_card,
                text=f'⚠ 场景加载失败: {self._load_error}',
                font=('Sans', 11, 'bold'),
                background='#ffffff',
                foreground='#e63946',
            ).pack(anchor='w')
            ttk.Label(
                info_card,
                text='请先运行 base_plan 完成基础规划。',
                background='#ffffff',
                foreground='#495057',
            ).pack(anchor='w', pady=(4, 0))

        # Countdown card (right)
        countdown_card = ttk.Frame(top_row, style='Card.TFrame', padding=14)
        countdown_card.grid(row=0, column=1, sticky='ns')

        self.countdown_label = tk.Label(
            countdown_card,
            text=f'{int(self.quiz_timeout_default_s)}',
            font=('Sans', 56, 'bold'),
            bg='#ffffff',
            fg='#e63946',
        )
        self.countdown_label.pack()

        self.quiz_status_label = tk.Label(
            countdown_card,
            text='初始化中…',
            bg='#ffffff',
            fg='#6c757d',
            font=('Sans', 12),
        )
        self.quiz_status_label.pack(pady=(8, 4))

        # Quiz type icon
        self.quiz_icon_label = tk.Label(countdown_card, bg='#ffffff')
        self.quiz_icon_label.pack(pady=(4, 0))

        # ── Controls row ──
        controls_row = ttk.Frame(body, style='Card.TFrame')
        controls_row.grid(row=1, column=0, sticky='ew', pady=(0, 12))

        ttk.Label(controls_row, text='等待时长（秒）:', background='#ffffff', font=('Sans', 11)).pack(side='left', padx=(14, 8))
        timeout_spin = ttk.Spinbox(
            controls_row,
            from_=1,
            to=120,
            increment=1,
            textvariable=self.quiz_timeout_var,
            width=6,
        )
        timeout_spin.pack(side='left')

        self.restart_btn = ttk.Button(
            controls_row,
            text='重新开始倒计时',
            command=self._restart_quiz_wait,
            state='normal',
        )
        self.restart_btn.pack(side='left', padx=20)

        # ── Preview area (base plan / quiz plan image) ──
        preview_card = ttk.LabelFrame(body, text='基础路径规划预览', padding=8)
        preview_card.grid(row=2, column=0, sticky='nsew', pady=(0, 0))
        preview_card.columnconfigure(0, weight=1)
        preview_card.rowconfigure(0, weight=1)
        self.preview_card = preview_card  # keep ref to update title later
        self.preview_label = tk.Label(preview_card, bg='#f4f1de')
        self.preview_label.pack()

    # ── Preview: override to avoid depending on field_canvas ──────────────
    def _update_preview(
        self,
        plan: dict,
        *,
        quiz_type: int | None = None,
        quiz_status: str | None = None,
        countdown_s: float | None = None,
    ) -> None:
        """Render plan preview using render_path_on_field directly (no FieldCanvas)."""
        preview = render_path_on_field(
            plan,
            self._display_width,
            layout=self.field_layout_data,
            waypoint_config=self._waypoint_config,
            label_hotspot_config=self._label_hotspot_config,
            quiz_status=quiz_status,
            quiz_type=quiz_type,
            countdown_s=countdown_s,
        )
        self._preview_photo = ImageTk.PhotoImage(preview, master=self.root)
        self.preview_label.configure(image=self._preview_photo)

    def _publish_plan_ready(self, *, plan_source: str) -> None:
        """Quiz UI 不使用通用 plan_ready；见 _publish_base/quiz_plan_ready。"""
        pass

    def _publish_base_plan_ready(self) -> None:
        try:
            if not self._base_plan_ready_publisher.publish(plan_source='base'):
                if self._base_plan_ready_publisher.error:
                    print(
                        f'[quiz_plan] base_plan_ready ROS 不可用: '
                        f'{self._base_plan_ready_publisher.error}'
                    )
                return
            print(f'[quiz_plan] 已发布 {self.base_plan_ready_topic}', flush=True)
        except ValueError as e:
            if 'generator already executing' in str(e):
                print('[quiz_plan] 跳过 base_plan_ready（quiz listener 占用 rclpy）')
            else:
                raise

    def _publish_quiz_plan_ready(self, *, plan_source: str) -> None:
        try:
            if not self._quiz_plan_ready_publisher.publish(plan_source=plan_source):
                if self._quiz_plan_ready_publisher.error:
                    print(
                        f'[quiz_plan] quiz_plan_ready ROS 不可用: '
                        f'{self._quiz_plan_ready_publisher.error}'
                    )
                return
            print(
                f'[quiz_plan] 已发布 {self.quiz_plan_ready_topic} '
                f'(plan_source={plan_source})',
                flush=True,
            )
        except ValueError as e:
            if 'generator already executing' in str(e):
                print('[quiz_plan] 跳过 quiz_plan_ready（quiz listener 占用 rclpy）')
            else:
                raise

    def _current_quiz_timeout_s(self) -> float:
        try:
            value = float(self.quiz_timeout_var.get())
        except (tk.TclError, ValueError):
            value = self.quiz_timeout_default_s
        return max(1.0, min(120.0, value))

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

    def _ensure_base_plan(self) -> dict:
        """Generate and export a base plan from the loaded scenario. Returns the plan dict."""
        scenario = {
            'box_types': list(self.box_types),
            'zone_types': list(self.zone_types),
            'include_quiz_state': False,
        }
        planner, waypoint_config = self._build_planner()
        self._waypoint_config = waypoint_config
        sequence = planner.plan(
            scenario['box_types'],
            scenario['zone_types'],
            include_quiz_state=False,
            quiz_type=None,
            waypoint_config=waypoint_config,
        )
        plan = self._export_plan(
            sequence,
            scenario,
            quiz_type=-1,
            quiz_received=False,
            quiz_wait_started=False,
            plan_source='base',
            publish_ready=False,
        )
        self._base_plan = plan
        self._base_sequence = sequence
        self._scenario = scenario
        self._publish_base_plan_ready()
        return plan

    def _start_countdown_only(self) -> None:
        """Start countdown and quiz listener IMMEDIATELY (no base plan generation)."""
        if not self._scenario_loaded:
            return

        self._cancel_quiz_wait()

        timeout_s = self._current_quiz_timeout_s()
        self._quiz_waiting = True
        self.restart_btn.configure(state='normal')
        self.quiz_status_label.config(text='等待智力题识别结果…', fg='#1d3557')
        self.countdown_label.config(text=f'{int(timeout_s)}', fg='#e63946')
        self.quiz_icon_label.config(image='')
        self.quiz_icon_label.image = None

        self._quiz_listener = QuizResultListener(self.quiz_topic, self._on_quiz_result)
        self._quiz_listener.start()
        if not self._quiz_listener.ros_available and self._quiz_listener.error:
            self.quiz_status_label.config(text=f'⚠ ROS 未连接（{self._quiz_listener.error}）', fg='#e63946')

        self._quiz_wait_deadline = time.monotonic() + timeout_s
        self._poll_quiz_wait()

    def _generate_and_show_base_plan(self) -> None:
        """Generate base plan and update preview (runs in parallel with countdown)."""
        try:
            plan = self._ensure_base_plan()
            if self._quiz_waiting:
                self._update_preview(plan, quiz_status='waiting',
                                     countdown_s=max(0, self._quiz_wait_deadline - time.monotonic() if self._quiz_wait_deadline else 0))
        except Exception as exc:
            messagebox.showerror('基础规划失败', str(exc))

    def _start_quiz_wait(self) -> None:
        """Restart: generate base plan + show preview + start countdown."""
        if not self._scenario_loaded:
            messagebox.showwarning('提示', '场景加载失败，请先运行 base_plan 完成基础规划。')
            return

        self._cancel_quiz_wait()

        # Generate base plan + show preview first
        try:
            plan = self._ensure_base_plan()
            self._update_preview(plan, quiz_status='waiting', countdown_s=self._current_quiz_timeout_s())
        except Exception as exc:
            messagebox.showerror('基础规划失败', str(exc))
            return

        # Then start countdown
        self._start_countdown_only()

    def _restart_quiz_wait(self) -> None:
        self.preview_card.config(text='基础路径规划预览')
        self._start_quiz_wait()

    def _poll_quiz_wait(self) -> None:
        if not self._quiz_waiting or self._quiz_wait_deadline is None:
            return

        try:
            remaining = self._quiz_wait_deadline - time.monotonic()

            # Check for pending result from callback
            if self._quiz_result_pending is not None:
                self._finalize_quiz(self._quiz_result_pending)
                return

            # Check for result from listener
            if self._quiz_listener is not None and self._quiz_listener.result is not None:
                self._finalize_quiz(self._quiz_listener.result)
                return

            if remaining <= 0:
                self._finalize_quiz_timeout()
                return

            secs = max(0, int(remaining + 0.999))
            self.countdown_label.config(text=f'{secs}')
            if self._base_plan is not None:
                self._update_preview(
                    self._base_plan,
                    quiz_status='waiting',
                    countdown_s=remaining,
                )
        except Exception:
            pass  # keep polling even if one tick fails
        finally:
            if self._quiz_waiting:
                self._quiz_poll_after_id = self.root.after(200, self._poll_quiz_wait)

    def _finalize_quiz(self, quiz_type: int) -> None:
        self._cancel_quiz_wait()
        try:
            # Ensure base plan has been generated (needed for _scenario)
            if self._scenario is None:
                self._ensure_base_plan()
            scenario = dict(self._scenario)
            scenario['include_quiz_state'] = True
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
                publish_ready=False,
            )
            self._publish_quiz_plan_ready(plan_source='quiz')
            self._update_preview(plan, quiz_status='received', quiz_type=quiz_type)
            self.preview_card.config(text='智力题路径规划预览（已覆盖导出）')
            item = ITEM_TYPES[quiz_type]
            self.quiz_status_label.config(text=f'✓ 收到智力题：{item.label}（{quiz_type}号），已覆盖导出', fg='#2a9d8f')
            self.countdown_label.config(text='✓', fg='#2a9d8f')
            icon = photo_image(icon_image(quiz_type, 64), self.root)
            self.quiz_icon_label.config(image=icon)
            self.quiz_icon_label.image = icon
        except Exception as exc:
            messagebox.showerror('二次规划失败', str(exc))
        finally:
            self.restart_btn.configure(state='normal')

    def _finalize_quiz_timeout(self) -> None:
        self._cancel_quiz_wait()
        self.quiz_status_label.config(text='✗ 超时未收到智力题，保持基础规划', fg='#e63946')
        self.countdown_label.config(text='0', fg='#e63946')
        self.quiz_icon_label.config(image='')
        self.quiz_icon_label.image = None
        self.restart_btn.configure(state='normal')

        # If base plan hasn't been generated yet, generate it now
        try:
            if self._base_plan is None or self._base_sequence is None or self._scenario is None:
                self._ensure_base_plan()
            plan = self._export_plan(
                self._base_sequence,
                self._scenario,
                quiz_type=-1,
                quiz_received=False,
                quiz_wait_started=True,
                plan_source='base',
                quiz_status='timeout',
                publish_ready=False,
            )
            self._publish_quiz_plan_ready(plan_source='timeout')
            self._update_preview(plan, quiz_status='timeout')
            self.preview_card.config(text='基础路径规划预览（超时，保持基础规划）')
        except Exception as exc:
            print(f'[quiz_plan] 超时导出失败: {exc}')

    def run(self) -> None:
        self.root.mainloop()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description='Quiz replan UI: auto countdown + replan on quiz received.')
    parser.add_argument('--field-layout', required=True)
    parser.add_argument('--mission-params')
    args = parser.parse_args(argv)
    QuizPlanUI(args.field_layout, args.mission_params).run()


if __name__ == '__main__':
    main()
