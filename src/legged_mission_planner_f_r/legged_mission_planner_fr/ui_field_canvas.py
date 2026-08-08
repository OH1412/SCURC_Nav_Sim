from __future__ import annotations

import tkinter as tk
from typing import Callable

from PIL import Image

from .label_hotspots import LabelHotspotConfig, load_default_label_hotspots
from .ui_assets import (
    field_overlay_sizes,
    photo_image,
    render_field_state,
    render_path_on_field,
    resolve_box_zone_hotspots,
)
from .ui_field_fit import build_field_fit_layout
from .waypoint_config import WaypointConfig


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
        waypoint_config: WaypointConfig | None = None,
        label_hotspot_config: LabelHotspotConfig | None = None,
        **kwargs,
    ) -> None:
        super().__init__(master, highlightthickness=0, bg='#f4f1de', **kwargs)
        self.box_types = box_types
        self.zone_types = zone_types
        self.on_box_change = on_box_change
        self.on_zone_change = on_zone_change
        self.display_width = width
        self.display_height = 1
        self.layout = layout or {}
        self.selected_brush = 0
        self.readonly = readonly
        self.waypoint_config = waypoint_config
        self.label_hotspot_config = label_hotspot_config or load_default_label_hotspots()
        self._box_hotspots, self._zone_hotspots = resolve_box_zone_hotspots(
            waypoint_config,
            self.label_hotspot_config,
        )
        self._photo = None
        self._fit = build_field_fit_layout(width, 400)
        self.bind('<Configure>', self._on_resize)
        if not self.readonly:
            self.bind('<Button-1>', self._on_click)
        self._redraw()

    def set_brush(self, type_id: int) -> None:
        self.selected_brush = type_id
        self._redraw()

    def _on_resize(self, event) -> None:
        if event.width < 80 or event.height < 80:
            return
        new_fit = build_field_fit_layout(event.width, event.height)
        if (
            new_fit.image_width == self._fit.image_width
            and new_fit.image_height == self._fit.image_height
            and new_fit.viewport_width == self._fit.viewport_width
            and new_fit.viewport_height == self._fit.viewport_height
        ):
            return
        self._fit = new_fit
        self.display_width = new_fit.image_width
        self.display_height = new_fit.image_height
        self._redraw()

    def _redraw(self) -> None:
        self.delete('all')
        frame = render_field_state(
            self.box_types,
            self.zone_types,
            self.display_width,
            selected_brush=self.selected_brush,
            waypoint_config=self.waypoint_config,
            label_hotspot_config=self.label_hotspot_config,
            box_hotspots=self._box_hotspots,
            zone_hotspots=self._zone_hotspots,
        )
        self._photo = photo_image(frame, self)
        self.configure(
            width=self._fit.viewport_width,
            height=self._fit.viewport_height,
            scrollregion=(0, 0, self._fit.viewport_width, self._fit.viewport_height),
        )
        self.create_image(self._fit.offset_x, self._fit.offset_y, image=self._photo, anchor='nw')

    def _click_norm(self, event) -> tuple[float, float] | None:
        return self._fit.pixel_to_norm(event.x, event.y)

    def _on_click(self, event) -> None:
        if self.readonly:
            return

        norm = self._click_norm(event)
        if norm is None:
            return
        norm_x, norm_y = norm

        if self.label_hotspot_config is not None:
            zone_id = self.label_hotspot_config.hit_zone(norm_x, norm_y)
            if zone_id is not None:
                self.zone_types[zone_id] = self.selected_brush
                self.on_zone_change(zone_id, self.selected_brush)
                self._redraw()
                return
            box_id = self.label_hotspot_config.hit_box(norm_x, norm_y)
            if box_id is not None:
                self.box_types[box_id] = self.selected_brush
                self.on_box_change(box_id, self.selected_brush)
                self._redraw()
                return
            if self.label_hotspot_config.is_complete():
                return

        zone_px, box_px = field_overlay_sizes(self.display_width)
        zone_hit = zone_px // 2 + 6
        box_hit = box_px // 2 + 6

        for zone_id, (nx, ny) in self._zone_hotspots.items():
            if self.label_hotspot_config is not None and zone_id in self.label_hotspot_config.zones:
                continue
            px, py = self._fit.norm_to_pixel(nx, ny)
            if abs(event.x - px) <= zone_hit and abs(event.y - py) <= zone_hit:
                self.zone_types[zone_id] = self.selected_brush
                self.on_zone_change(zone_id, self.selected_brush)
                self._redraw()
                return

        for box_id, (nx, ny) in self._box_hotspots.items():
            if self.label_hotspot_config is not None and box_id in self.label_hotspot_config.boxes:
                continue
            px, py = self._fit.norm_to_pixel(nx, ny)
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
            label_hotspot_config=self.label_hotspot_config,
            quiz_status=quiz_status,
            quiz_type=quiz_type,
            countdown_s=countdown_s,
        )
