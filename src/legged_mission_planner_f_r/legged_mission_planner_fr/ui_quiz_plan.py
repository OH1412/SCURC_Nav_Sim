from __future__ import annotations

import argparse
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from .package_paths import DEFAULT_OUTPUT_DIR, resolve_assets_dir
from .planning_ui_common import PlanningUICommon
from .scenario_store import default_scenario_path, load_base_scenario
from .ui_field_canvas import FieldCanvas
from .yaml_utils import load_yaml


class QuizMissionPlannerUI(PlanningUICommon):
    """Read-only quiz replanning UI: auto-waits for quiz topic and overwrites exports."""

    def __init__(self, field_layout: str, mission_params: str | None = None) -> None:
        self._init_planning_common(field_layout, mission_params)
        self._on_quiz_finalize_success = None
        self._on_quiz_finalize_timeout = None

        scenario_path = default_scenario_path(self.params)
        try:
            stored = load_base_scenario(scenario_path)
        except FileNotFoundError as exc:
            self._fatal_startup(str(exc))
            return

        self.box_types = stored['box_types']
        self.zone_types = stored['zone_types']
        self.output_dir = Path(stored.get('output_dir', DEFAULT_OUTPUT_DIR))
        self._scenario = {
            'box_types': list(self.box_types),
            'zone_types': list(self.zone_types),
            'include_quiz_state': False,
        }

        plan_path = self.output_dir / 'mission_plan.yaml'
        if not plan_path.exists():
            self._fatal_startup(f'基础规划文件不存在: {plan_path}\n请先完成基础规划。')
            return

        self._base_plan = load_yaml(plan_path)
        self._base_sequence = None
        try:
            self._waypoint_config = self._resolve_waypoint_config()
        except FileNotFoundError:
            self._waypoint_config = None

        self.root = tk.Tk()
        self.root.title('ROBOCON 2026 · 智力题二次规划')
        self.root.minsize(980, 720)
        self.root.configure(bg='#f8f9fa')
        self._setup_style()
        self._build()
        self._update_preview(self._base_plan)
        self.root.after(100, self._auto_start_quiz_wait)

    def _fatal_startup(self, message: str) -> None:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror('无法启动智力题规划', message)
        root.destroy()
        sys.exit(1)

    def _setup_style(self) -> None:
        style = ttk.Style(self.root)
        if 'clam' in style.theme_names():
            style.theme_use('clam')
        style.configure('Title.TLabel', font=('Sans', 15, 'bold'), background='#f8f9fa', foreground='#1d3557')
        style.configure('Hint.TLabel', font=('Sans', 10), background='#f8f9fa', foreground='#495057')
        style.configure('Card.TFrame', background='#ffffff', relief='flat')

    def _build(self) -> None:
        header = ttk.Frame(self.root, style='Card.TFrame', padding=12)
        header.pack(fill='x', padx=14, pady=(14, 8))
        ttk.Label(header, text='ROBOCON 2026 仿生足式机器人 · 智力题二次规划', style='Title.TLabel').pack(anchor='w')
        ttk.Label(
            header,
            text=f'已加载基础场景，自动等待智力题话题 {int(self.quiz_timeout_s)}s（只读，不可点击标注）。',
            style='Hint.TLabel',
        ).pack(anchor='w', pady=(4, 0))

        body = ttk.Frame(self.root, padding=(14, 0, 14, 14))
        body.pack(fill='both', expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        field_card = ttk.Frame(body, style='Card.TFrame', padding=10)
        field_card.grid(row=0, column=0, sticky='nsew')
        field_card.rowconfigure(0, weight=1)
        field_card.columnconfigure(0, weight=1)

        field_top = ttk.Frame(field_card)
        field_top.grid(row=0, column=0, sticky='nsew')
        field_top.columnconfigure(0, weight=1)

        self.quiz_panel = tk.Frame(field_top, bg='#ffffff', padx=10, pady=8, highlightbackground='#dee2e6', highlightthickness=1)
        self.quiz_panel.place(relx=1.0, rely=0.0, anchor='ne', x=-4, y=4)
        self.quiz_status_label = tk.Label(
            self.quiz_panel,
            text='准备等待智力题…',
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
            on_box_change=lambda *_: None,
            on_zone_change=lambda *_: None,
            width=560,
            layout=self.field_layout_data,
            readonly=True,
        )
        self.field_canvas.pack(anchor='n')

        preview_card = ttk.LabelFrame(field_card, text='路径预览', padding=8)
        preview_card.grid(row=1, column=0, sticky='ew', pady=(10, 0))
        self.preview_label = tk.Label(preview_card, bg='#f4f1de')
        self.preview_label.pack()

        info = ttk.Label(
            field_card,
            text=f'输出目录: {self.output_dir}\n场地图: {resolve_assets_dir() / "场地俯视图.png"}',
            foreground='#495057',
        )
        info.grid(row=2, column=0, sticky='w', pady=(8, 0))

    def _auto_start_quiz_wait(self) -> None:
        self._start_quiz_wait()

    def run(self) -> None:
        self.root.mainloop()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description='Front/back quiz mission replanner UI.')
    parser.add_argument('--field-layout', required=True)
    parser.add_argument('--mission-params')
    args = parser.parse_args(argv)
    QuizMissionPlannerUI(args.field_layout, args.mission_params).run()


if __name__ == '__main__':
    main()
