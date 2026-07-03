from __future__ import annotations

import argparse
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import ImageTk

from .package_paths import DEFAULT_OUTPUT_DIR, resolve_assets_dir
from .path_planner import MissionPathPlanner
from .plan_exporter import PlanExporter
from .pose_resolver import load_yaml
from .quiz_listener import QuizResultListener
from .ui_assets import ITEM_TYPES, icon_image, photo_image, zone_swatch_image
from .ui_field_canvas import FieldCanvas
from .ui_visualizer import draw_plan_on_image, write_text_summary


class MissionPlannerUI:
    def __init__(self, field_layout: str, mission_params: str | None = None) -> None:
        self.field_layout = Path(field_layout)
        self.field_layout_data = load_yaml(self.field_layout)
        self.mission_params = Path(mission_params) if mission_params else None
        self.params = load_yaml(self.mission_params) if self.mission_params and self.mission_params.exists() else {}
        self.box_types = [i % 4 for i in range(8)]
        self.zone_types = [0, 1, 2, 3]
        self.output_dir = DEFAULT_OUTPUT_DIR
        self._palette_photos: list = []
        self._preview_photo = None
        self._quiz_icon_photo = None

        self.quiz_topic = str(self.params.get('quiz_result_topic', '/mission/quiz_type'))
        self.quiz_timeout_s = float(self.params.get('quiz_wait_timeout_s', 10.0))

        self._base_plan: dict | None = None
        self._base_sequence = None
        self._scenario: dict | None = None
        self._quiz_listener: QuizResultListener | None = None
        self._quiz_wait_deadline: float | None = None
        self._quiz_poll_after_id: str | None = None
        self._quiz_waiting = False
        self._quiz_result_pending: int | None = None

        self.root = tk.Tk()
        self.strategy = tk.StringVar(self.root, value=self.params.get('default_strategy', 'safe_edges'))
        self.switch_mode = tk.StringVar(self.root, value=self.params.get('default_switch_mode', 'wp4_only'))
        self.selected_brush = tk.IntVar(self.root, value=0)
        self.root.title('ROBOCON 2026 任务赛路径规划')
        self.root.minsize(980, 720)
        self.root.configure(bg='#f8f9fa')
        self._setup_style()
        self._build()
        self._select_brush(0)

    def _setup_style(self) -> None:
        style = ttk.Style(self.root)
        if 'clam' in style.theme_names():
            style.theme_use('clam')
        style.configure('Title.TLabel', font=('Sans', 15, 'bold'), background='#f8f9fa', foreground='#1d3557')
        style.configure('Hint.TLabel', font=('Sans', 10), background='#f8f9fa', foreground='#495057')
        style.configure('Card.TFrame', background='#ffffff', relief='flat')
        style.configure('Accent.TButton', font=('Sans', 11, 'bold'), padding=8)

    def _build(self) -> None:
        header = ttk.Frame(self.root, style='Card.TFrame', padding=12)
        header.pack(fill='x', padx=14, pady=(14, 8))
        ttk.Label(header, text='ROBOCON 2026 仿生足式机器人 · 任务赛路径规划', style='Title.TLabel').pack(anchor='w')
        ttk.Label(
            header,
            text='点击左侧物资种类，再点击场上归位区或箱子完成标注；上方为归位区，下方为物资箱存放区。',
            style='Hint.TLabel',
        ).pack(anchor='w', pady=(4, 0))

        body = ttk.Frame(self.root, padding=(14, 0, 14, 14))
        body.pack(fill='both', expand=True)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        sidebar = ttk.Frame(body, style='Card.TFrame', padding=14, width=280)
        sidebar.grid(row=0, column=0, sticky='ns', padx=(0, 12))
        sidebar.grid_propagate(False)

        ttk.Label(sidebar, text='物资种类', font=('Sans', 12, 'bold'), background='#ffffff', foreground='#1d3557').pack(anchor='w')
        ttk.Label(sidebar, text='选中后点击场上位置标注', background='#ffffff', foreground='#6c757d').pack(anchor='w', pady=(2, 10))

        palette = ttk.Frame(sidebar, style='Card.TFrame')
        palette.pack(fill='x')
        self._brush_buttons: dict[int, tk.Button] = {}
        for item in ITEM_TYPES:
            row = tk.Frame(palette, bg='#ffffff', pady=6)
            row.pack(fill='x')
            icon = photo_image(icon_image(item.type_id, 56), self.root)
            zone = photo_image(zone_swatch_image(item.type_id, 40), self.root)
            self._palette_photos.extend([icon, zone])
            preview = tk.Frame(row, bg='#ffffff')
            preview.pack(fill='x')
            icon_label = tk.Label(preview, image=icon, bg='#ffffff')
            icon_label.image = icon
            icon_label.pack(side='left', padx=(0, 6))
            zone_label = tk.Label(preview, image=zone, bg='#ffffff')
            zone_label.image = zone
            zone_label.pack(side='left', padx=(0, 6))
            btn = tk.Button(
                preview,
                text=f'{item.label}（{item.short}）',
                anchor='w',
                padx=8,
                pady=8,
                bg='#ffffff',
                activebackground='#e9ecef',
                relief='groove',
                borderwidth=1,
                command=lambda t=item.type_id: self._select_brush(t),
            )
            btn.pack(side='left', fill='x', expand=True)
            self._brush_buttons[item.type_id] = btn

        ttk.Separator(sidebar, orient='horizontal').pack(fill='x', pady=14)
        ttk.Label(sidebar, text='规划策略', font=('Sans', 11, 'bold'), background='#ffffff').pack(anchor='w')
        ttk.Combobox(sidebar, textvariable=self.strategy, values=['safe_edges', 'middle_paths'], state='readonly').pack(fill='x', pady=(6, 8))
        ttk.Label(sidebar, text='路径切换模式', font=('Sans', 11, 'bold'), background='#ffffff').pack(anchor='w')
        ttk.Combobox(sidebar, textvariable=self.switch_mode, values=['wp4_only', 'wp4_or_wp5'], state='readonly').pack(fill='x', pady=(6, 8))

        ttk.Button(sidebar, text='选择输出目录', command=self._choose_output_dir).pack(fill='x', pady=(10, 4))
        self.plan_btn = ttk.Button(sidebar, text='规划并导出', style='Accent.TButton', command=self._plan_and_export)
        self.plan_btn.pack(fill='x', pady=4)
        self.quiz_wait_btn = ttk.Button(sidebar, text='等待智力题', command=self._start_quiz_wait, state='disabled')
        self.quiz_wait_btn.pack(fill='x', pady=4)
        ttk.Button(sidebar, text='重置为默认标注', command=self._reset_defaults).pack(fill='x', pady=4)

        self.status = ttk.Label(sidebar, text=self._status_text(), wraplength=220, background='#ffffff', foreground='#495057')
        self.status.pack(anchor='w', pady=(12, 0))

        field_card = ttk.Frame(body, style='Card.TFrame', padding=10)
        field_card.grid(row=0, column=1, sticky='nsew')
        field_card.rowconfigure(0, weight=1)
        field_card.columnconfigure(0, weight=1)

        field_top = ttk.Frame(field_card)
        field_top.grid(row=0, column=0, sticky='nsew')
        field_top.columnconfigure(0, weight=1)

        self.quiz_panel = tk.Frame(field_top, bg='#ffffff', padx=10, pady=8, highlightbackground='#dee2e6', highlightthickness=1)
        self.quiz_panel.place(relx=1.0, rely=0.0, anchor='ne', x=-4, y=4)
        self.quiz_status_label = tk.Label(
            self.quiz_panel,
            text='未启用智力题策略',
            bg='#ffffff',
            fg='#6c757d',
            font=('Sans', 10),
            anchor='w',
        )
        self.quiz_status_label.pack(side='top', anchor='w')
        self.quiz_countdown_label = tk.Label(self.quiz_panel, text='', bg='#ffffff', fg='#e63946', font=('Sans', 16, 'bold'))
        self.quiz_countdown_label.pack(side='top', anchor='w', pady=(4, 0))
        self.quiz_icon_label = tk.Label(self.quiz_panel, bg='#ffffff')
        self.quiz_icon_label.pack(side='top', anchor='w', pady=(6, 0))

        canvas_wrap = ttk.Frame(field_top)
        canvas_wrap.pack(fill='both', expand=True)
        self.field_canvas = FieldCanvas(
            canvas_wrap,
            self.box_types,
            self.zone_types,
            on_box_change=self._on_box_change,
            on_zone_change=self._on_zone_change,
            width=560,
            layout=self.field_layout_data,
        )
        self.field_canvas.pack(anchor='n')

        preview_card = ttk.LabelFrame(field_card, text='路径预览（规划后显示）', padding=8)
        preview_card.grid(row=1, column=0, sticky='ew', pady=(10, 0))
        self.preview_label = tk.Label(preview_card, bg='#f4f1de')
        self.preview_label.pack()

    def _status_text(self) -> str:
        return f'输出: {self.output_dir}\n场地图: {resolve_assets_dir() / "场地俯视图.png"}'

    def _select_brush(self, type_id: int) -> None:
        self.selected_brush.set(type_id)
        self.field_canvas.set_brush(type_id)
        for tid, btn in self._brush_buttons.items():
            color = ITEM_TYPES[tid].color
            if tid == type_id:
                btn.configure(bg=color, fg='white', activebackground=color)
            else:
                btn.configure(bg='#ffffff', fg='black', activebackground='#e9ecef')

    def _on_box_change(self, box_id: int, type_id: int) -> None:
        self.box_types[box_id] = type_id

    def _on_zone_change(self, zone_id: int, type_id: int) -> None:
        self.zone_types[zone_id] = type_id

    def _reset_defaults(self) -> None:
        self._cancel_quiz_wait()
        self.box_types = [i % 4 for i in range(8)]
        self.zone_types = [0, 1, 2, 3]
        self.field_canvas.box_types = self.box_types
        self.field_canvas.zone_types = self.zone_types
        self.field_canvas._redraw()
        self._base_plan = None
        self.quiz_wait_btn.configure(state='disabled')
        self._reset_quiz_panel()

    def _reset_quiz_panel(self) -> None:
        self.quiz_status_label.config(text='未启用智力题策略', fg='#6c757d')
        self.quiz_countdown_label.config(text='')
        self.quiz_icon_label.config(image='')
        self.quiz_icon_label.image = None

    def _choose_output_dir(self) -> None:
        selected = filedialog.askdirectory(initialdir=str(self.output_dir.parent))
        if selected:
            self.output_dir = Path(selected)
            self.status.config(text=self._status_text())

    def _build_scenario(self) -> dict:
        return {
            'box_types': list(self.box_types),
            'zone_types': list(self.zone_types),
            'strategy': self.strategy.get(),
            'switch_mode': self.switch_mode.get(),
            'include_quiz_state': False,
        }

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
        exporter = PlanExporter()
        base = self.output_dir / 'mission_plan'
        plan = exporter.export(
            sequence,
            scenario,
            scenario['strategy'],
            scenario['switch_mode'],
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
            quiz_status=quiz_status,
            quiz_type=quiz_type,
            countdown_s=countdown_s,
        )
        return plan

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
            quiz_status=quiz_status,
            quiz_type=quiz_type,
            countdown_s=countdown_s,
        )
        self._preview_photo = ImageTk.PhotoImage(preview, master=self.root)
        self.preview_label.configure(image=self._preview_photo)

    def _plan_and_export(self) -> None:
        try:
            self._cancel_quiz_wait()
            scenario = self._build_scenario()
            planner = MissionPathPlanner()
            sequence = planner.plan(
                scenario['box_types'],
                scenario['zone_types'],
                scenario['strategy'],
                scenario['switch_mode'],
            )
            plan = self._export_plan(
                sequence,
                scenario,
                quiz_type=None,
                quiz_received=False,
                quiz_wait_started=False,
                plan_source='base',
            )
            self._base_plan = plan
            self._base_sequence = sequence
            self._scenario = scenario
            self._update_preview(plan)
            self._reset_quiz_panel()
            self.quiz_wait_btn.configure(state='normal')
            messagebox.showinfo('规划完成', f'基础规划已导出到:\n{self.output_dir}\n\n可点击「等待智力题」进行二次规划。')
        except Exception as exc:
            messagebox.showerror('规划失败', str(exc))

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

    def _start_quiz_wait(self) -> None:
        if self._base_plan is None or self._scenario is None or self._base_sequence is None:
            messagebox.showwarning('提示', '请先完成「规划并导出」。')
            return
        self._cancel_quiz_wait()
        self._quiz_waiting = True
        self.quiz_wait_btn.configure(state='disabled')
        self.plan_btn.configure(state='disabled')
        self.quiz_status_label.config(text='等待智力题识别结果…', fg='#1d3557')
        self.quiz_countdown_label.config(text=f'{int(self.quiz_timeout_s)}s')
        self.quiz_icon_label.config(image='')
        self.quiz_icon_label.image = None

        self._quiz_listener = QuizResultListener(self.quiz_topic, self._on_quiz_result)
        self._quiz_listener.start()
        if not self._quiz_listener.ros_available and self._quiz_listener.error:
            self.quiz_status_label.config(text=f'未连接 ROS（{self._quiz_listener.error}）', fg='#e63946')

        self._quiz_wait_deadline = time.monotonic() + self.quiz_timeout_s
        self._update_preview(
            self._base_plan,
            quiz_status='waiting',
            countdown_s=self.quiz_timeout_s,
        )
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
            self._update_preview(
                self._base_plan,
                quiz_status='waiting',
                countdown_s=remaining,
            )
        self._quiz_poll_after_id = self.root.after(200, self._poll_quiz_wait)

    def _finalize_quiz(self, quiz_type: int) -> None:
        self._cancel_quiz_wait()
        try:
            assert self._scenario is not None
            scenario = dict(self._scenario)
            scenario['include_quiz_state'] = True
            planner = MissionPathPlanner()
            sequence = planner.plan(
                scenario['box_types'],
                scenario['zone_types'],
                scenario['strategy'],
                scenario['switch_mode'],
                include_quiz_state=True,
                quiz_type=quiz_type,
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
            self._update_preview(plan, quiz_status='received', quiz_type=quiz_type)
            item = ITEM_TYPES[quiz_type]
            self.quiz_status_label.config(text=f'智力题：{item.label}（{quiz_type}号）', fg='#1d3557')
            self.quiz_countdown_label.config(text='')
            icon = photo_image(icon_image(quiz_type, 64), self.root)
            self.quiz_icon_label.config(image=icon)
            self.quiz_icon_label.image = icon
            messagebox.showinfo('二次规划完成', f'收到智力题种类 {quiz_type}，已覆盖导出到:\n{self.output_dir}')
        except Exception as exc:
            messagebox.showerror('二次规划失败', str(exc))
        finally:
            self.plan_btn.configure(state='normal')
            self.quiz_wait_btn.configure(state='normal')

    def _finalize_quiz_timeout(self) -> None:
        self._cancel_quiz_wait()
        assert self._base_plan is not None and self._base_sequence is not None and self._scenario is not None
        plan = self._export_plan(
            self._base_sequence,
            self._scenario,
            quiz_type=None,
            quiz_received=False,
            quiz_wait_started=True,
            plan_source='base',
            quiz_status='timeout',
        )
        self._update_preview(plan, quiz_status='timeout')
        self.quiz_status_label.config(text='未收到智力题，保持基础规划', fg='#e63946')
        self.quiz_countdown_label.config(text='0s')
        self.quiz_icon_label.config(image='')
        self.quiz_icon_label.image = None
        self.plan_btn.configure(state='normal')
        self.quiz_wait_btn.configure(state='normal')

    def run(self) -> None:
        self.root.mainloop()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description='Open the mission-planner labeling UI.')
    parser.add_argument('--field-layout', required=True)
    parser.add_argument('--mission-params')
    args = parser.parse_args(argv)
    MissionPlannerUI(args.field_layout, args.mission_params).run()


if __name__ == '__main__':
    main()
