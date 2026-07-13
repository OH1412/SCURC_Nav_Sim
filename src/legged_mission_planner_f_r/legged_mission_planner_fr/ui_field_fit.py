from __future__ import annotations

from dataclasses import dataclass

from .ui_assets import field_background_image, field_image_aspect


@dataclass(frozen=True)
class FieldFitLayout:
    viewport_width: int
    viewport_height: int
    image_width: int
    image_height: int
    offset_x: int
    offset_y: int

    def pixel_to_norm(self, px: int, py: int) -> tuple[float, float] | None:
        if not self.contains_pixel(px, py):
            return None
        nx = (px - self.offset_x) / self.image_width
        ny = (py - self.offset_y) / self.image_height
        return nx, ny

    def norm_to_pixel(self, norm_x: float, norm_y: float) -> tuple[int, int]:
        px = int(round(self.offset_x + norm_x * self.image_width))
        py = int(round(self.offset_y + norm_y * self.image_height))
        return px, py

    def contains_pixel(self, px: int, py: int) -> bool:
        return (
            self.offset_x <= px < self.offset_x + self.image_width
            and self.offset_y <= py < self.offset_y + self.image_height
        )


def compute_field_fit_size(max_width: int, max_height: int) -> tuple[int, int]:
    if max_width < 1:
        max_width = 1
    if max_height < 1:
        max_height = 1
    aspect = field_image_aspect()
    width = max_width
    height = max(1, int(round(width * aspect)))
    if height > max_height:
        height = max_height
        width = max(1, int(round(height / aspect)))
    return width, height


def build_field_fit_layout(viewport_width: int, viewport_height: int) -> FieldFitLayout:
    image_width, image_height = compute_field_fit_size(viewport_width, viewport_height)
    offset_x = max(0, (viewport_width - image_width) // 2)
    offset_y = max(0, (viewport_height - image_height) // 2)
    return FieldFitLayout(
        viewport_width=viewport_width,
        viewport_height=viewport_height,
        image_width=image_width,
        image_height=image_height,
        offset_x=offset_x,
        offset_y=offset_y,
    )


def render_field_background_fitted(layout: FieldFitLayout):
    return field_background_image(layout.image_width)
