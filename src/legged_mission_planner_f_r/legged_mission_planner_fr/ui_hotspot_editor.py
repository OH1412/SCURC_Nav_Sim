from __future__ import annotations

import argparse
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from .label_hotspots import (
    LABEL_HOTSPOTS_FILE,
    LabelHotspotConfig,
    NormRect,
    load_default_label_hotspots,
    load_label_hotspots,
    write_label_hotspots,
)
from .package_paths import WS_SRC
from .ui_assets import photo_image
from .ui_field_fit import FieldFitLayout, build_field_fit_layout, render_field_background_fitted

DEFAULT_OUT = WS_SRC / 'legged_mission_planner_f_r' / 'config' / LABEL_HOTSPOTS_FILE

BOX_IDS = list(range(8))
ZONE_IDS = list(range(4))
MAX_UNDO = 64


class HotspotEditorCanvas(tk.Canvas):
    def __init__(self, master, on_target_changed=None, on_history_changed=None, **kwargs) -> None:
        super().__init__(master, highlightthickness=0, bg='#f4f1de', **kwargs)
        self._photo = None
        self._on_target_changed = on_target_changed
        self._on_history_changed = on_history_changed
        self._hotspot_config = LabelHotspotConfig(boxes={}, zones={})
        self._undo_stack: list[LabelHotspotConfig] = []
        self._targets: list[tuple[str, int]] = [('box', i) for i in BOX_IDS] + [('zone', i) for i in ZONE_IDS]
        self._target_index = 0
        self._drag_start: tuple[float, float] | None = None
        self._drag_rect_id: int | None = None
        self._fit = build_field_fit_layout(560, 400)
        self.bind('<Configure>', self._on_resize)
        self.bind('<ButtonPress-1>', self._on_press)
        self.bind('<B1-Motion>', self._on_drag)
        self.bind('<ButtonRelease-1>', self._on_release)

    @property
    def hotspot_config(self) -> LabelHotspotConfig:
        return self._hotspot_config

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    def set_hotspot_config(self, config: LabelHotspotConfig, *, clear_history: bool = True) -> None:
        self._hotspot_config = config.clone()
        self._target_index = 0
        if clear_history:
            self._undo_stack.clear()
            self._notify_history()
        self._redraw_all()

    def push_undo_snapshot(self) -> None:
        self._undo_stack.append(self._hotspot_config.clone())
        if len(self._undo_stack) > MAX_UNDO:
            self._undo_stack.pop(0)
        self._notify_history()

    def undo(self) -> bool:
        if not self._undo_stack:
            return False
        self._hotspot_config = self._undo_stack.pop().clone()
        self._notify_history()
        self._redraw_all()
        if self._on_target_changed is not None:
            self._on_target_changed()
        return True

    def clear_current_target(self) -> None:
        kind, slot_id = self.current_target()
        if kind == 'box' and slot_id in self._hotspot_config.boxes:
            self.push_undo_snapshot()
            del self._hotspot_config.boxes[slot_id]
        elif kind == 'zone' and slot_id in self._hotspot_config.zones:
            self.push_undo_snapshot()
            del self._hotspot_config.zones[slot_id]
        else:
            return
        self._redraw_all()
        if self._on_target_changed is not None:
            self._on_target_changed()

    def _notify_history(self) -> None:
        if self._on_history_changed is not None:
            self._on_history_changed()

    def current_target(self) -> tuple[str, int]:
        return self._targets[self._target_index]

    def target_label(self) -> str:
        kind, slot_id = self.current_target()
        return f'{"箱子" if kind == "box" else "归还区"} {slot_id}'

    def _on_resize(self, event) -> None:
        if event.width < 80 or event.height < 80:
            return
        new_fit = build_field_fit_layout(event.width, event.height)
        if (
            new_fit.viewport_width == self._fit.viewport_width
            and new_fit.viewport_height == self._fit.viewport_height
            and new_fit.image_width == self._fit.image_width
            and new_fit.image_height == self._fit.image_height
        ):
            return
        self._fit = new_fit
        self._redraw_all()

    def _on_press(self, event) -> None:
        norm = self._fit.pixel_to_norm(event.x, event.y)
        if norm is None:
            return
        self._drag_start = norm
        if self._drag_rect_id is not None:
            self.delete(self._drag_rect_id)
        self._drag_rect_id = self.create_rectangle(
            event.x, event.y, event.x, event.y, outline='#e63946', width=2, dash=(4, 2)
        )

    def _on_drag(self, event) -> None:
        if self._drag_start is None or self._drag_rect_id is None:
            return
        x0, y0 = self._fit.norm_to_pixel(self._drag_start[0], self._drag_start[1])
        self.coords(self._drag_rect_id, x0, y0, event.x, event.y)

    def _on_release(self, event) -> None:
        if self._drag_start is None:
            return
        end = self._fit.pixel_to_norm(event.x, event.y)
        if end is None:
            self._drag_start = None
            self._drag_rect_id = None
            self._redraw_all()
            return

        rect = NormRect.from_drag(self._drag_start[0], self._drag_start[1], end[0], end[1])
        if rect.norm_x1 - rect.norm_x0 < 0.01 or rect.norm_y1 - rect.norm_y0 < 0.01:
            self._drag_start = None
            self._drag_rect_id = None
            self._redraw_all()
            return

        self.push_undo_snapshot()
        kind, slot_id = self.current_target()
        if kind == 'box':
            self._hotspot_config.boxes[slot_id] = rect
        else:
            self._hotspot_config.zones[slot_id] = rect

        self._drag_start = None
        self._drag_rect_id = None
        if self._target_index < len(self._targets) - 1:
            self._target_index += 1
        self._redraw_all()
        if self._on_target_changed is not None:
            self._on_target_changed()

    def _redraw_background(self) -> None:
        frame = render_field_background_fitted(self._fit)
        self._photo = photo_image(frame, self)
        super().configure(
            width=self._fit.viewport_width,
            height=self._fit.viewport_height,
            scrollregion=(0, 0, self._fit.viewport_width, self._fit.viewport_height),
        )

    def _draw_rect(self, rect: NormRect, *, color: str, label: str) -> None:
        x0, y0 = self._fit.norm_to_pixel(rect.norm_x0, rect.norm_y0)
        x1, y1 = self._fit.norm_to_pixel(rect.norm_x1, rect.norm_y1)
        self.create_rectangle(x0, y0, x1, y1, outline=color, width=2)
        self.create_text(x0 + 4, y0 + 4, text=label, anchor='nw', fill=color, font=('Sans', 10, 'bold'))

    def _redraw_all(self) -> None:
        self.delete('all')
        self._redraw_background()
        if self._photo is not None:
            self.create_image(
                self._fit.offset_x,
                self._fit.offset_y,
                image=self._photo,
                anchor='nw',
            )

        for box_id, rect in sorted(self._hotspot_config.boxes.items()):
            self._draw_rect(rect, color='#2ecc71', label=f'box{box_id}')

        for zone_id, rect in sorted(self._hotspot_config.zones.items()):
            self._draw_rect(rect, color='#3498db', label=f'zone{zone_id}')

        kind, slot_id = self.current_target()
        label = f'当前: {"箱子" if kind == "box" else "归还区"} {slot_id}'
        self.create_text(12, 12, text=label, anchor='nw', fill='#e63946', font=('Sans', 11, 'bold'))


class HotspotEditorApp:
    def __init__(self, output_path: Path, load_existing: bool) -> None:
        self.output_path = output_path
        self.root = tk.Tk()
        self.root.title('箱子/归还区 点击区域标定')
        self.root.minsize(720, 640)
        self.root.configure(bg='#f8f9fa')
        self._build()

        if load_existing and self.output_path.exists():
            self.canvas.set_hotspot_config(load_label_hotspots(self.output_path))
        else:
            existing = load_default_label_hotspots()
            if existing is not None:
                self.canvas.set_hotspot_config(existing)
        self._update_status()

        self.root.bind('<Control-z>', lambda _e: self._undo())
        self.root.bind('<Control-s>', lambda _e: self._save())

    def _build(self) -> None:
        header = ttk.Frame(self.root, padding=12)
        header.pack(fill='x')
        ttk.Label(
            header,
            text='在场地图上拖拽矩形框选 8 个箱子与 4 个归还区的可点击区域',
            font=('Sans', 12, 'bold'),
        ).pack(anchor='w')
        ttk.Label(
            header,
            text='图片自动适应窗口。顺序：箱子 0→7，归还区 0→3。Ctrl+S 保存，Ctrl+Z 撤回。',
        ).pack(anchor='w', pady=(4, 0))

        body = ttk.Frame(self.root, padding=(12, 0, 12, 12))
        body.pack(fill='both', expand=True)
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)

        canvas_host = ttk.Frame(body)
        canvas_host.grid(row=0, column=0, sticky='nsew')
        canvas_host.rowconfigure(0, weight=1)
        canvas_host.columnconfigure(0, weight=1)

        self.canvas = HotspotEditorCanvas(
            canvas_host,
            on_target_changed=self._update_status,
            on_history_changed=self._update_undo_button,
        )
        self.canvas.grid(row=0, column=0, sticky='nsew')

        controls = ttk.Frame(self.root, padding=(12, 0, 12, 12))
        controls.pack(fill='x')
        self.status_var = tk.StringVar(self.root)
        ttk.Label(controls, textvariable=self.status_var).pack(side='left')
        self.undo_btn = ttk.Button(controls, text='撤回', command=self._undo, state='disabled')
        self.undo_btn.pack(side='right', padx=4)
        ttk.Button(controls, text='清除当前', command=self._clear_current).pack(side='right', padx=4)
        ttk.Button(controls, text='上一个', command=self._prev_target).pack(side='right', padx=4)
        ttk.Button(controls, text='下一个', command=self._next_target).pack(side='right', padx=4)
        ttk.Button(controls, text='保存', command=self._save).pack(side='right', padx=4)

    def _update_undo_button(self) -> None:
        state = 'normal' if self.canvas.can_undo else 'disabled'
        self.undo_btn.configure(state=state)

    def _update_status(self) -> None:
        cfg = self.canvas.hotspot_config
        self.status_var.set(
            f'当前: {self.canvas.target_label()} | '
            f'已完成 箱子 {len(cfg.boxes)}/8, 归还区 {len(cfg.zones)}/4 | '
            f'输出: {self.output_path}'
        )
        self._update_undo_button()

    def _prev_target(self) -> None:
        if self.canvas._target_index > 0:
            self.canvas._target_index -= 1
            self.canvas._redraw_all()
            self._update_status()

    def _next_target(self) -> None:
        if self.canvas._target_index < len(self.canvas._targets) - 1:
            self.canvas._target_index += 1
            self.canvas._redraw_all()
            self._update_status()

    def _clear_current(self) -> None:
        self.canvas.clear_current_target()

    def _undo(self) -> None:
        if not self.canvas.undo():
            messagebox.showinfo('撤回', '没有可撤回的操作')

    def _save(self) -> None:
        cfg = self.canvas.hotspot_config.clone()
        if not cfg.is_complete():
            if not messagebox.askyesno(
                '未完成',
                f'当前仅完成 箱子 {len(cfg.boxes)}/8, 归还区 {len(cfg.zones)}/4。\n仍要保存吗？',
            ):
                return
        try:
            saved = write_label_hotspots(cfg, self.output_path)
        except OSError as exc:
            messagebox.showerror('保存失败', f'无法写入文件:\n{self.output_path}\n\n{exc}')
            return
        messagebox.showinfo('已保存', f'点击区域已写入:\n{saved}')
        self._update_status()

    def run(self) -> None:
        self.root.mainloop()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description='Label box/zone click regions on the field image.')
    parser.add_argument('--output', default=str(DEFAULT_OUT))
    parser.add_argument('--load-existing', action='store_true', default=True)
    parser.add_argument('--no-load-existing', dest='load_existing', action='store_false')
    args = parser.parse_args(argv)
    HotspotEditorApp(Path(args.output), load_existing=args.load_existing).run()


if __name__ == '__main__':
    main()
