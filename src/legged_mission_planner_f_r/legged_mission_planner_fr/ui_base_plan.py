from __future__ import annotations

import argparse
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .field_model import sync_boxes_to_zones
from .package_paths import DEFAULT_OUTPUT_DIR, resolve_assets_dir
from .planning_ui_common import PlanningUICommon
from .scenario_store import default_scenario_path, save_base_scenario
from .ui_assets import ITEM_TYPES, icon_image, photo_image, zone_swatch_image
from .ui_field_canvas import FieldCanvas


class MissionPlannerUI(PlanningUICommon):
    """Base-plan labeling and mission planning UI (no quiz phase)."""

    def __init__(self, field_layout: str, mission_params: str | None = None) -> None:
        self._init_planning_common(field_layout, mission_params)
        self.zone_types = [0, 1, 2, 3]
        self.box_types = [0] * 8
        sync_boxes_to_zones(self.box_types, self.zone_types)
        self.output_dir = DEFAULT_OUTPUT_DIR
        self._palette_photos: list = []

        self.root = tk.Tk()
        self.zone_order = tk.StringVar(self.root, value='0,1,2,3')
        self.selected_brush = tk.IntVar(self.root, value=0)
        self.root.title('ROBOCON 2026 · 基础路径规划')
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
        ttk.Label(header, text='ROBOCON 2026 仿生足式机器人 · 基础路径规划', style='Title.TLabel').pack(anchor='w')
        ttk.Label(
            header,
            text='标注场上箱子与归位区后点击「规划并导出」输出基础规划。完成后可启动 quiz_plan 进行智力题二次规划。',
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
        ttk.Label(sidebar, text='归位区顺序预设', font=('Sans', 11, 'bold'), background='#ffffff').pack(anchor='w')
        zone_combo = ttk.Combobox(
            sidebar,
            textvariable=self.zone_order,
            values=['0,1,2,3', '3,2,1,0'],
            state='readonly',
        )
        zone_combo.pack(fill='x', pady=(6, 8))
        zone_combo.bind('<<ComboboxSelected>>', self._on_zone_order_change)

        ttk.Button(sidebar, text='选择输出目录', command=self._choose_output_dir).pack(fill='x', pady=(10, 4))
        self.plan_btn = ttk.Button(sidebar, text='规划并导出', style='Accent.TButton', command=self._plan_and_export)
        self.plan_btn.pack(fill='x', pady=4)
        ttk.Button(sidebar, text='重置为默认标注', command=self._reset_defaults).pack(fill='x', pady=4)

        self.status = ttk.Label(sidebar, text=self._status_text(), wraplength=220, background='#ffffff', foreground='#495057')
        self.status.pack(anchor='w', pady=(12, 0))

        field_card = ttk.Frame(body, style='Card.TFrame', padding=10)
        field_card.grid(row=0, column=1, sticky='nsew')
        field_card.rowconfigure(0, weight=1)
        field_card.columnconfigure(0, weight=1)

        field_top = ttk.Frame(field_card)
        field_top.grid(row=0, column=0, sticky='nsew')
        field_top.rowconfigure(0, weight=1)
        field_top.columnconfigure(0, weight=1)

        canvas_host = ttk.Frame(field_top)
        canvas_host.grid(row=0, column=0, sticky='nsew')
        canvas_host.rowconfigure(0, weight=1)
        canvas_host.columnconfigure(0, weight=1)

        try:
            self._waypoint_config = self._resolve_waypoint_config()
        except FileNotFoundError:
            self._waypoint_config = None

        from .label_hotspots import load_default_label_hotspots

        self._label_hotspot_config = load_default_label_hotspots()
        self.field_canvas = FieldCanvas(
            canvas_host,
            self.box_types,
            self.zone_types,
            on_box_change=self._on_box_change,
            on_zone_change=self._on_zone_change,
            width=560,
            layout=self.field_layout_data,
            waypoint_config=self._waypoint_config,
            label_hotspot_config=self._label_hotspot_config,
        )
        self.field_canvas.grid(row=0, column=0, sticky='nsew')

        preview_card = ttk.LabelFrame(field_card, text='路径预览（规划后显示）', padding=8)
        preview_card.grid(row=1, column=0, sticky='ew', pady=(10, 0))
        self.preview_label = tk.Label(preview_card, bg='#f4f1de')
        self.preview_label.pack()

    def _status_text(self) -> str:
        scenario_path = default_scenario_path(self.params)
        return (
            f'输出: {self.output_dir}\n'
            f'场景: {scenario_path}\n'
            f'场地图: {resolve_assets_dir() / "场地俯视图.png"}\n'
            f'完成后可启动 quiz_plan 进行智力题二次规划'
        )

    def _sync_boxes_from_zones(self) -> None:
        sync_boxes_to_zones(self.box_types, self.zone_types)
        self.field_canvas.box_types = self.box_types

    def _on_zone_order_change(self, _event=None) -> None:
        order = [int(v) for v in self.zone_order.get().split(',')]
        self.zone_types = order
        self.field_canvas.zone_types = self.zone_types
        self._sync_boxes_from_zones()
        self.field_canvas._redraw()

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
        self.zone_types = [0, 1, 2, 3]
        self.zone_order.set('0,1,2,3')
        self._sync_boxes_from_zones()
        self.field_canvas.zone_types = self.zone_types
        self.field_canvas._redraw()
        self._base_plan = None
        self._base_sequence = None
        self._scenario = None

    def _choose_output_dir(self) -> None:
        selected = filedialog.askdirectory(initialdir=str(self.output_dir.parent))
        if selected:
            self.output_dir = Path(selected)
            self.status.config(text=self._status_text())

    def _build_scenario(self) -> dict:
        return {
            'box_types': list(self.box_types),
            'zone_types': list(self.zone_types),
            'include_quiz_state': False,
        }

    def _plan_and_export(self) -> None:
        try:
            scenario = self._build_scenario()
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
            )
            self._base_plan = plan
            self._base_sequence = sequence
            self._scenario = scenario
            self._update_preview(plan)

            scenario_path = default_scenario_path(self.params)
            save_base_scenario(scenario, scenario_path, output_dir=self.output_dir)
            self.status.config(text=self._status_text())

            messagebox.showinfo(
                '规划完成',
                f'基础规划已导出到:\n{self.output_dir}\n\n'
                f'mission_plan.yaml / mission_quintuple.yaml / mission_plan.png\n'
                f'场景已保存: {scenario_path}\n\n'
                f'请启动 quiz_plan 进行智力题二次规划。',
            )
        except Exception as exc:
            messagebox.showerror('规划失败', str(exc))

    def run(self) -> None:
        self.root.mainloop()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description='Base mission planner UI (click-to-label, no quiz phase).')
    parser.add_argument('--field-layout', required=True)
    parser.add_argument('--mission-params')
    args = parser.parse_args(argv)
    MissionPlannerUI(args.field_layout, args.mission_params).run()


if __name__ == '__main__':
    main()
