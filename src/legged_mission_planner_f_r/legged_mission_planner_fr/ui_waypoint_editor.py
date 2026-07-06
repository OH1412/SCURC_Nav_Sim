from __future__ import annotations

import argparse
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

from .package_paths import WS_SRC
from .ui_assets import FIELD_REF_HEIGHT, FIELD_REF_WIDTH, field_background_image, photo_image
from .waypoint_yaml_exporter import (
    WaypointUI,
    export_waypoint_yamls,
    load_ui_points,
    waypoint_id,
)

# 始终指向工作空间源码目录，无论是否 symlink-install
DEFAULT_UI_POINTS_OUT = WS_SRC / 'legged_mission_planner_f_r' / 'config' / 'ui_points.yaml'
DEFAULT_MISSION_PLAN_OUT = (
    WS_SRC / 'robot_functionality' / 'legged_mission_bt' / 'config' / 'mission_plan_hardcoded.yaml'
)

MARKER_RADIUS = 7
MARKER_COLOR = '#e63946'
MARKER_OUTLINE = '#ffffff'
LABEL_COLOR = '#1d3557'


class WaypointEditorCanvas(tk.Canvas):
    """Field map canvas for clicking path waypoints in normalized image coordinates."""

    def __init__(self, master, width: int = 560, **kwargs) -> None:
        super().__init__(master, highlightthickness=0, bg='#f4f1de', **kwargs)
        self.display_width = width
        self._photo = None
        self._completed_paths: dict[int, list[WaypointUI]] = {}
        self._current_path_id: int | None = None
        self._current_points: list[WaypointUI] = []
        self.bind('<Configure>', self._on_resize)
        self.bind('<Button-1>', self._on_click)
        self._redraw_background()

    @property
    def completed_paths(self) -> dict[int, list[WaypointUI]]:
        return self._completed_paths

    @property
    def current_path_id(self) -> int | None:
        return self._current_path_id

    @property
    def current_points(self) -> list[WaypointUI]:
        return self._current_points

    @property
    def display_height(self) -> int:
        return int(self.display_width * FIELD_REF_HEIGHT / FIELD_REF_WIDTH)

    def set_completed_paths(self, paths: dict[int, list[WaypointUI]]) -> None:
        self._completed_paths = {k: list(v) for k, v in paths.items()}
        self._current_path_id = None
        self._current_points = []
        self._redraw_all()

    def start_path(self, path_id: int, *, replace: bool = False) -> None:
        if not replace and path_id in self._completed_paths:
            raise ValueError(f'path {path_id} already completed')
        self._current_path_id = path_id
        self._current_points = []
        self._redraw_all()

    def finish_current_path(self) -> None:
        if self._current_path_id is None:
            raise RuntimeError('no active path')
        if not self._current_points:
            raise RuntimeError('current path has no waypoints')
        self._completed_paths[self._current_path_id] = list(self._current_points)
        self._current_path_id = None
        self._current_points = []
        self._redraw_all()

    def all_paths(self) -> dict[int, list[WaypointUI]]:
        merged = {k: list(v) for k, v in self._completed_paths.items()}
        if self._current_path_id is not None and self._current_points:
            merged[self._current_path_id] = list(self._current_points)
        return merged

    def _on_resize(self, event) -> None:
        if event.width < 120:
            return
        if event.width != self.display_width:
            self.display_width = event.width
            self._redraw_all()

    def _pixel_to_norm(self, px: int, py: int) -> tuple[float, float]:
        w = self.display_width
        h = self.display_height
        return px / w, py / h

    def _norm_to_pixel(self, norm_x: float, norm_y: float) -> tuple[int, int]:
        w = self.display_width
        h = self.display_height
        return int(round(norm_x * w)), int(round(norm_y * h))

    def _on_click(self, event) -> None:
        if self._current_path_id is None:
            return

        # 在弹窗前立即计算归一化坐标，防止窗口缩放导致漂移
        norm_x, norm_y = self._pixel_to_norm(event.x, event.y)

        # 弹出状态输入对话框
        state = simpledialog.askinteger(
            '航点状态',
            '请输入状态:\n  0 = 智力题识别\n  1 = 纯走点\n  2 = 吸取\n  3 = 放置',
            parent=self.winfo_toplevel(),
            minvalue=0,
            maxvalue=3,
        )
        if state is None:  # 用户取消
            return

        # 根据状态弹出目标编号对话框
        target_id = -1
        if state == 2:  # 吸取 → 箱子编号 0-7
            target_id = simpledialog.askinteger(
                '箱子编号',
                '请输入箱子编号 (0-7):',
                parent=self.winfo_toplevel(),
                minvalue=0,
                maxvalue=7,
            )
            if target_id is None:  # 用户取消
                return
        elif state == 3:  # 放置 → 归还区编号 0-3
            target_id = simpledialog.askinteger(
                '归还区编号',
                '请输入归还区编号 (0-3):',
                parent=self.winfo_toplevel(),
                minvalue=0,
                maxvalue=3,
            )
            if target_id is None:  # 用户取消
                return
        # state 0, 1: target_id 保持 -1

        wp_index = len(self._current_points) + 1
        self._current_points.append(
            WaypointUI(
                path_id=self._current_path_id,
                wp_index=wp_index,
                norm_x=norm_x,
                norm_y=norm_y,
                state=state,
                target_id=target_id,
            )
        )
        self._draw_waypoint(
            self._current_path_id,
            wp_index,
            norm_x,
            norm_y,
            highlight=True,
        )

    def _redraw_background(self) -> None:
        frame = field_background_image(self.display_width)
        self._photo = photo_image(frame, self)
        w, h = frame.size
        self.config(width=w, height=h, scrollregion=(0, 0, w, h))

    def _redraw_all(self) -> None:
        self.delete('all')
        self._redraw_background()
        if self._photo is not None:
            self.create_image(0, 0, image=self._photo, anchor='nw', tags='background')

        for path_id, waypoints in sorted(self._completed_paths.items()):
            for wp in waypoints:
                self._draw_waypoint(
                    path_id,
                    wp.wp_index,
                    wp.norm_x,
                    wp.norm_y,
                    highlight=False,
                )

        if self._current_path_id is not None:
            for wp in self._current_points:
                self._draw_waypoint(
                    self._current_path_id,
                    wp.wp_index,
                    wp.norm_x,
                    wp.norm_y,
                    highlight=True,
                )

    def _draw_waypoint(
        self,
        path_id: int,
        wp_index: int,
        norm_x: float,
        norm_y: float,
        *,
        highlight: bool,
    ) -> None:
        px, py = self._norm_to_pixel(norm_x, norm_y)
        color = MARKER_COLOR if highlight else '#457b9d'
        tag = f'wp_{path_id}_{wp_index}'
        r = MARKER_RADIUS
        self.create_oval(
            px - r,
            py - r,
            px + r,
            py + r,
            fill=color,
            outline=MARKER_OUTLINE,
            width=2,
            tags=tag,
        )
        label = waypoint_id(path_id, wp_index)
        self.create_text(
            px,
            py - r - 8,
            text=label,
            fill=LABEL_COLOR,
            font=('Sans', 9, 'bold'),
            tags=tag,
        )


class WaypointEditorUI:
    def __init__(
        self,
        *,
        ui_points_out: Path,
        mission_plan_out: Path,
        load_existing: Path | None = None,
    ) -> None:
        self.ui_points_out = ui_points_out
        self.mission_plan_out = mission_plan_out

        self.root = tk.Tk()
        self.root.title('ROBOCON 2026 前后吸取 · 航点标定')
        self.root.minsize(900, 680)
        self.root.configure(bg='#f8f9fa')
        self.path_var = tk.StringVar(self.root, value='1')
        self.status_var = tk.StringVar(self.root, value='请输入路径号并开始标定')
        self._setup_style()
        self._build()

        if load_existing and load_existing.exists():
            self._load_existing(load_existing)

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
        ttk.Label(header, text='航点标定 · 路径规划与行为树对齐', style='Title.TLabel').pack(anchor='w')
        ttk.Label(
            header,
            text='输入路径号后在图上依次点击航点；完成一条路径后点「本路径完成」，全部完成后导出 YAML。',
            style='Hint.TLabel',
        ).pack(anchor='w', pady=(4, 0))

        body = ttk.Frame(self.root, padding=(14, 0, 14, 14))
        body.pack(fill='both', expand=True)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        sidebar = ttk.Frame(body, style='Card.TFrame', padding=14, width=280)
        sidebar.grid(row=0, column=0, sticky='ns', padx=(0, 12))
        sidebar.grid_propagate(False)

        ttk.Label(sidebar, text='路径设置', font=('Sans', 12, 'bold'), background='#ffffff', foreground='#1d3557').pack(anchor='w')
        path_row = ttk.Frame(sidebar, style='Card.TFrame')
        path_row.pack(fill='x', pady=(8, 4))
        ttk.Label(path_row, text='路径号', background='#ffffff').pack(side='left')
        ttk.Entry(path_row, textvariable=self.path_var, width=8).pack(side='left', padx=(8, 0))
        ttk.Button(path_row, text='开始', command=self._start_path).pack(side='left', padx=(8, 0))

        ttk.Label(sidebar, textvariable=self.status_var, background='#ffffff', foreground='#6c757d', wraplength=240).pack(
            anchor='w', pady=(12, 16)
        )

        ttk.Button(
            sidebar,
            text='本路径航点设置完成',
            style='Accent.TButton',
            command=self._finish_path,
        ).pack(fill='x', pady=(0, 8))

        ttk.Button(
            sidebar,
            text='全部完成并导出',
            style='Accent.TButton',
            command=self._export_all,
        ).pack(fill='x')

        canvas_frame = ttk.Frame(body)
        canvas_frame.grid(row=0, column=1, sticky='nsew')
        self.canvas = WaypointEditorCanvas(canvas_frame, width=620)
        self.canvas.pack(fill='both', expand=True)

    def _parse_path_id(self) -> int | None:
        text = self.path_var.get().strip()
        if not text:
            messagebox.showwarning('输入错误', '请输入路径号')
            return None
        try:
            path_id = int(text)
        except ValueError:
            messagebox.showwarning('输入错误', '路径号必须是整数')
            return None
        if path_id < 1:
            messagebox.showwarning('输入错误', '路径号必须 ≥ 1')
            return None
        return path_id

    def _update_status(self) -> None:
        canvas = self.canvas
        if canvas.current_path_id is not None:
            next_wp = len(canvas.current_points) + 1
            self.status_var.set(
                f'当前路径 {canvas.current_path_id}，下一航点 {next_wp}（已点 {len(canvas.current_points)} 个）'
            )
            return
        completed = sorted(canvas.completed_paths.keys())
        if completed:
            self.status_var.set(f'已完成路径: {", ".join(str(p) for p in completed)}。请输入下一路径号。')
        else:
            self.status_var.set('请输入路径号并开始标定')

    def _start_path(self) -> None:
        path_id = self._parse_path_id()
        if path_id is None:
            return

        if path_id in self.canvas.completed_paths:
            if not messagebox.askyesno('覆盖确认', f'路径 {path_id} 已存在，是否重新标定并覆盖？'):
                return
            self.canvas.start_path(path_id, replace=True)
        else:
            try:
                self.canvas.start_path(path_id)
            except ValueError as exc:
                messagebox.showwarning('无法开始', str(exc))
                return

        self._update_status()

    def _finish_path(self) -> None:
        if self.canvas.current_path_id is None:
            messagebox.showinfo('提示', '请先输入路径号并点击「开始」')
            return
        if not self.canvas.current_points:
            messagebox.showwarning('提示', '当前路径还没有点击任何航点')
            return
        try:
            self.canvas.finish_current_path()
        except RuntimeError as exc:
            messagebox.showwarning('无法完成', str(exc))
            return
        self._update_status()

    def _export_all(self) -> None:
        if self.canvas.current_path_id is not None and self.canvas.current_points:
            if not messagebox.askyesno(
                '未保存的路径',
                f'路径 {self.canvas.current_path_id} 尚未点「本路径完成」，是否先保存当前路径再导出？',
            ):
                return
            try:
                self.canvas.finish_current_path()
            except RuntimeError as exc:
                messagebox.showwarning('无法导出', str(exc))
                return

        all_paths = self.canvas.all_paths()
        if not all_paths:
            messagebox.showwarning('无法导出', '还没有标定任何航点')
            return

        # 弹出后缀输入对话框
        suffix = simpledialog.askstring(
            '导出文件名后缀',
            '请输入文件名后缀（将用于 ui_points_<后缀>.yaml 和 mission_plan_hardcoded_<后缀>.yaml）:',
            parent=self.root,
        )
        if suffix is None:  # 用户取消
            return
        suffix = suffix.strip()
        if not suffix:
            if not messagebox.askyesno('后缀为空', '文件名后缀为空，将使用默认文件名（无后缀）。是否继续？'):
                return
            ui_out = self.ui_points_out
            bt_out = self.mission_plan_out
        else:
            # 清理后缀：非字母数字替换为下划线
            safe_suffix = ''.join(c if c.isalnum() or c in '_-' else '_' for c in suffix)
            ui_out = self.ui_points_out.parent / f'ui_points_{safe_suffix}.yaml'
            bt_out = self.mission_plan_out.parent / f'mission_plan_hardcoded_{safe_suffix}.yaml'

        ui_path, bt_path = export_waypoint_yamls(
            all_paths,
            ui_out,
            bt_out,
        )
        messagebox.showinfo(
            '导出成功',
            f'已保存:\n{ui_path}\n{bt_path}',
        )
        self._update_status()

    def _load_existing(self, path: Path) -> None:
        try:
            paths = load_ui_points(path)
        except Exception as exc:
            messagebox.showwarning('加载失败', f'无法读取 {path}:\n{exc}')
            return
        self.canvas.set_completed_paths(paths)
        self._update_status()

    def run(self) -> None:
        self.root.mainloop()


def default_bt_config_dir() -> Path:
    return DEFAULT_MISSION_PLAN_OUT.parent


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description='Waypoint editor for front/back suction mission planner.')
    parser.add_argument('--ui-points-out', default=str(DEFAULT_UI_POINTS_OUT))
    parser.add_argument('--mission-plan-out', default=str(DEFAULT_MISSION_PLAN_OUT))
    parser.add_argument('--bt-config-dir', default='', help='Override BT config directory for mission_plan_hardcoded.yaml')
    parser.add_argument('--load-existing', default='', help='Load existing ui_points.yaml to continue editing')
    args = parser.parse_args(argv)

    mission_plan_out = Path(args.mission_plan_out)
    if args.bt_config_dir:
        mission_plan_out = Path(args.bt_config_dir) / 'mission_plan_hardcoded.yaml'

    load_existing = Path(args.load_existing) if args.load_existing else None
    if load_existing is None and Path(args.ui_points_out).exists():
        load_existing = Path(args.ui_points_out)

    ui = WaypointEditorUI(
        ui_points_out=Path(args.ui_points_out),
        mission_plan_out=mission_plan_out,
        load_existing=load_existing,
    )
    ui.run()


if __name__ == '__main__':
    main()
