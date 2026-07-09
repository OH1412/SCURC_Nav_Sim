from __future__ import annotations

import tkinter as tk
from typing import Callable, Tuple

from PIL import Image

from .ui_assets import (
    BOX_HOTSPOTS,
    FIELD_REF_HEIGHT,
    FIELD_REF_WIDTH,
    ZONE_HOTSPOTS,
    field_overlay_sizes,
    photo_image,
    render_field_state,
    render_path_on_field,
)


class FieldCanvas(tk.Canvas):
    """Interactive field map composited from 场地俯视图 + scaled box/zone assets."""

    def __init__(
        self,
        master,
        box_types: list[int],
        zone_types: list[int],
        on_box_change: Callable[[int, int], None],
        on_zone_change: Callable[[int, int], None],
        width: int = 560,
        layout: dict | None = None,
        readonly: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(master, highlightthickness=0, bg='#f4f1de', **kwargs)
        self.box_types = box_types
        self.zone_types = zone_types
        self.on_box_change = on_box_change
        self.on_zone_change = on_zone_change
        self.display_width = width
        self.layout = layout or {}
        self.selected_brush = 0
        self.readonly = readonly
        self._photo = None
        self.bind('<Configure>', self._on_resize)
        if not self.readonly:
            self.bind('<Button-1>', self._on_click)
        self._redraw()

    def set_brush(self, type_id: int) -> None:
        self.selected_brush = type_id
        self._redraw()

    def _on_resize(self, event) -> None:
        if event.width < 120:
            return
        if event.width != self.display_width:
            self.display_width = event.width
            self._redraw()

    def _hotspot_px(self, norm_x: float, norm_y: float) -> Tuple[int, int]:
        height = int(self.display_width * FIELD_REF_HEIGHT / FIELD_REF_WIDTH)
        return int(norm_x * self.display_width), int(norm_y * height)

    def _redraw(self) -> None:
        self.delete('all')
        frame = render_field_state(
            self.box_types,
            self.zone_types,
            self.display_width,
            selected_brush=self.selected_brush,
        )
        self._photo = photo_image(frame, self)
        w, h = frame.size
        self.config(width=w, height=h, scrollregion=(0, 0, w, h))
        self.create_image(0, 0, image=self._photo, anchor='nw')

    def _on_click(self, event) -> None:
        if self.readonly:
            return
        zone_px, box_px = field_overlay_sizes(self.display_width)
        zone_hit = zone_px // 2 + 6
        box_hit = box_px // 2 + 6

        for zone_id, (nx, ny) in ZONE_HOTSPOTS.items():
            px, py = self._hotspot_px(nx, ny)
            if abs(event.x - px) <= zone_hit and abs(event.y - py) <= zone_hit:
                self.zone_types[zone_id] = self.selected_brush
                self.on_zone_change(zone_id, self.selected_brush)
                self._redraw()
                return

        for box_id, (nx, ny) in BOX_HOTSPOTS.items():
            px, py = self._hotspot_px(nx, ny)
            if abs(event.x - px) <= box_hit and abs(event.y - py) <= box_hit:
                self.box_types[box_id] = self.selected_brush
                self.on_box_change(box_id, self.selected_brush)
                self._redraw()
                return

    def render_path_preview(
        self,
        plan: dict,
        *,
        waypoint_config=None,
        quiz_status: str | None = None,
        quiz_type: int | None = None,
        countdown_s: float | None = None,
    ) -> Image.Image:
        return render_path_on_field(
            plan,
            self.display_width,
            layout=self.layout,
            waypoint_config=waypoint_config,
            quiz_status=quiz_status,
            quiz_type=quiz_type,
            countdown_s=countdown_s,
        )
