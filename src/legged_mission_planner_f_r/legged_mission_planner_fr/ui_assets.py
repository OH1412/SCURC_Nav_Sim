from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, Mapping, Tuple

from PIL import Image, ImageDraw, ImageTk

from .package_paths import resolve_assets_dir
from .path_viz import START_ZONE_NORM, resolve_layout, step_to_local_xy, step_to_pixel_ui_points

try:
    _RESAMPLE = Image.Resampling.LANCZOS
except AttributeError:
    _RESAMPLE = Image.LANCZOS

FIELD_IMAGE = '场地俯视图.png'
PATH_IMAGE = '路径和航点设置图.png'

BOX_FILES: Dict[int, str] = {
    0: '绿色箱子-0.png',
    1: '灰色箱子-1.png',
    2: '蓝色箱子-2.png',
    3: '红色箱子-3.png',
}
ZONE_FILES: Dict[int, str] = {
    0: '绿放置区-0.png',
    1: '灰放置区-1.png',
    2: '蓝放置区-2.png',
    3: '红放置区-3.png',
}

# Measured on 场地俯视图.png (460 x 577).
FIELD_REF_WIDTH = 460
FIELD_REF_HEIGHT = 577
ZONE_SIZE_REF = 27
BOX_SIZE_REF = 34

# Yellow 6m x 4m competition area on 场地俯视图.png (460 x 577).
# y0 = top edge (x=6m), y1 = bottom edge (x=0m); start zone is below y1.
FIELD_PLAYABLE_X0 = 115
FIELD_PLAYABLE_Y0 = 72
FIELD_PLAYABLE_X1 = 377
FIELD_PLAYABLE_Y1 = 459
FIELD_LENGTH_M = 6.0
FIELD_WIDTH_M = 4.0

# Normalized hotspot centers on the field diagram (right -> left numbering).
ZONE_HOTSPOTS: Dict[int, Tuple[float, float]] = {
    0: (326 / FIELD_REF_WIDTH, 136 / FIELD_REF_HEIGHT),
    1: (274 / FIELD_REF_WIDTH, 136 / FIELD_REF_HEIGHT),
    2: (222 / FIELD_REF_WIDTH, 136 / FIELD_REF_HEIGHT),
    3: (170 / FIELD_REF_WIDTH, 136 / FIELD_REF_HEIGHT),
}
BOX_HOTSPOTS: Dict[int, Tuple[float, float]] = {
    0: (331 / FIELD_REF_WIDTH, 299.5 / FIELD_REF_HEIGHT),
    1: (275 / FIELD_REF_WIDTH, 299.5 / FIELD_REF_HEIGHT),
    2: (220 / FIELD_REF_WIDTH, 299.5 / FIELD_REF_HEIGHT),
    3: (165 / FIELD_REF_WIDTH, 299.5 / FIELD_REF_HEIGHT),
    4: (331 / FIELD_REF_WIDTH, 355 / FIELD_REF_HEIGHT),
    5: (275 / FIELD_REF_WIDTH, 355 / FIELD_REF_HEIGHT),
    6: (220 / FIELD_REF_WIDTH, 355 / FIELD_REF_HEIGHT),
    7: (165 / FIELD_REF_WIDTH, 355 / FIELD_REF_HEIGHT),
}


@dataclass(frozen=True)
class ItemType:
    type_id: int
    label: str
    short: str
    color: str


ITEM_TYPES: Tuple[ItemType, ...] = (
    ItemType(0, '食品', '绿', '#2ecc71'),
    ItemType(1, '工具', '灰', '#95a5a6'),
    ItemType(2, '仪器', '蓝', '#3498db'),
    ItemType(3, '药品', '红', '#e74c3c'),
)


def _load_rgba(filename: str) -> Image.Image:
    return Image.open(resolve_assets_dir() / filename).convert('RGBA')


def _make_white_transparent(img: Image.Image, threshold: int = 245) -> Image.Image:
    pixels = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = pixels[x, y]
            if r >= threshold and g >= threshold and b >= threshold:
                pixels[x, y] = (r, g, b, 0)
    return img


def _resize_square(img: Image.Image, size: int) -> Image.Image:
    if size <= 0:
        size = 1
    return img.resize((size, size), _RESAMPLE)


@lru_cache(maxsize=8)
def _box_source(type_id: int) -> Image.Image:
    return _make_white_transparent(_load_rgba(BOX_FILES[type_id]))


@lru_cache(maxsize=8)
def _zone_source(type_id: int) -> Image.Image:
    return _load_rgba(ZONE_FILES[type_id])


@lru_cache(maxsize=32)
def box_image(type_id: int, size: int) -> Image.Image:
    return _resize_square(_box_source(type_id), size)


@lru_cache(maxsize=32)
def box_marker_image(type_id: int, size: int) -> Image.Image:
    """Box icon on opaque white tile for field overlay (readable on yellow background)."""
    source = _resize_square(_load_rgba(BOX_FILES[type_id]), max(8, size - 4))
    marker = Image.new('RGBA', (size, size), (255, 255, 255, 255))
    offset = (size - source.width) // 2
    marker.paste(source, (offset, offset), source)
    border = ITEM_TYPES[type_id].color
    ImageDraw.Draw(marker).rectangle((0, 0, size - 1, size - 1), outline=border, width=max(1, size // 12))
    return marker


@lru_cache(maxsize=32)
def zone_image(type_id: int, size: int) -> Image.Image:
    return _resize_square(_zone_source(type_id), size)


def icon_image(type_id: int, size: int = 72) -> Image.Image:
    return box_image(type_id, size)


def zone_swatch_image(type_id: int, size: int = 56) -> Image.Image:
    return zone_image(type_id, size)


def field_background_image(target_width: int) -> Image.Image:
    img = _load_rgba(FIELD_IMAGE)
    scale = target_width / img.width
    target_height = max(1, int(img.height * scale))
    return img.resize((target_width, target_height), _RESAMPLE)


def path_background_image(target_width: int) -> Image.Image:
    img = _load_rgba(PATH_IMAGE)
    scale = target_width / img.width
    target_height = max(1, int(img.height * scale))
    return img.resize((target_width, target_height), _RESAMPLE)


def field_overlay_sizes(display_width: int) -> Tuple[int, int]:
    scale = display_width / FIELD_REF_WIDTH
    zone_px = max(10, int(round(ZONE_SIZE_REF * scale)))
    box_px = max(8, int(round(BOX_SIZE_REF * scale)))
    return zone_px, box_px


def local_xy_to_pixel(local_x: float, local_y: float, img_width: int, img_height: int) -> Tuple[int, int]:
    """Map field-local meters to diagram pixels.

    x=0 is the lower edge of the 6m yellow field; x=6 is the upper edge.
    1m along x equals exactly 1/6 of the field height on the diagram.
    y=0 is the right edge; y=4 is the left edge.
    """
    sx = img_width / FIELD_REF_WIDTH
    sy = img_height / FIELD_REF_HEIGHT
    x0 = FIELD_PLAYABLE_X0 * sx
    y_top = FIELD_PLAYABLE_Y0 * sy
    x1 = FIELD_PLAYABLE_X1 * sx
    y_bottom = FIELD_PLAYABLE_Y1 * sy
    playable_w = x1 - x0
    playable_h = y_bottom - y_top

    clamped_x = max(0.0, min(FIELD_LENGTH_M, float(local_x)))
    clamped_y = max(0.0, min(FIELD_WIDTH_M, float(local_y)))
    px = x0 + (1.0 - clamped_y / FIELD_WIDTH_M) * playable_w
    py = y_bottom - (clamped_x / FIELD_LENGTH_M) * playable_h
    return int(round(px)), int(round(py))


def norm_to_pixel(norm_x: float, norm_y: float, img_width: int, img_height: int) -> Tuple[int, int]:
    return int(round(norm_x * img_width)), int(round(norm_y * img_height))


def step_to_pixel(step: Mapping[str, Any], layout: Mapping[str, Any], img_width: int, img_height: int) -> Tuple[int, int]:
    local = step_to_local_xy(step, layout)
    if local is None:
        return norm_to_pixel(START_ZONE_NORM[0], START_ZONE_NORM[1], img_width, img_height)
    return local_xy_to_pixel(local[0], local[1], img_width, img_height)


def overlay_boxes_and_zones(
    canvas: Image.Image,
    box_types: Tuple[int, ...] | list[int],
    zone_types: Tuple[int, ...] | list[int],
    display_width: int,
    *,
    draw_labels: bool = False,
) -> Image.Image:
    """Paste operator-selected box icons and placement-zone swatches onto the field."""
    canvas = canvas.convert('RGBA').copy()
    draw = ImageDraw.Draw(canvas) if draw_labels else None
    zone_px, box_px = field_overlay_sizes(display_width)

    for zone_id, (nx, ny) in ZONE_HOTSPOTS.items():
        if zone_id >= len(zone_types):
            continue
        px = int(nx * canvas.width)
        py = int(ny * canvas.height)
        sprite = zone_image(zone_types[zone_id], zone_px)
        canvas.paste(sprite, (px - zone_px // 2, py - zone_px // 2), sprite)
        if draw is not None:
            draw.text((px - 3, py + zone_px // 2 + 2), str(zone_id), fill='#1d3557')

    for box_id, (nx, ny) in BOX_HOTSPOTS.items():
        if box_id >= len(box_types):
            continue
        px = int(nx * canvas.width)
        py = int(ny * canvas.height)
        sprite = box_marker_image(box_types[box_id], box_px)
        canvas.paste(sprite, (px - box_px // 2, py - box_px // 2), sprite)
        if draw is not None:
            draw.text((px - 3, py + box_px // 2 + 2), str(box_id), fill='#1d3557')

    return canvas


def render_path_on_field(
    plan: Mapping,
    display_width: int,
    layout: Mapping[str, Any] | str | None = None,
    *,
    waypoint_config=None,
    quiz_status: str | None = None,
    quiz_type: int | None = None,
    countdown_s: float | None = None,
) -> Image.Image:
    """Draw operator-labeled boxes/zones and planned path on 场地俯视图."""
    field_layout = resolve_layout(layout)
    scenario = plan.get('scenario', {})
    box_types = scenario.get('box_types', [i % 4 for i in range(8)])
    zone_types = scenario.get('zone_types', [0, 1, 2, 3])
    use_ui_points = (
        waypoint_config is not None
        and plan.get('switch_mode') == 'fast_mode'
    )

    canvas = field_background_image(display_width)
    canvas = overlay_boxes_and_zones(canvas, box_types, zone_types, display_width)

    overlay = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    w, h = canvas.size

    points: list[Tuple[int, int]] = []
    for step in plan.get('sequence', []):
        if use_ui_points:
            pixel = step_to_pixel_ui_points(step, waypoint_config, w, h)
            if pixel is not None:
                points.append(pixel)
        else:
            points.append(step_to_pixel(step, field_layout, w, h))

    if len(points) > 1:
        draw.line(points, fill=(230, 57, 70, 230), width=3)

    for px, py in points:
        r = 5
        draw.ellipse((px - r, py - r, px + r, py + r), fill=(29, 53, 87, 240), outline=(255, 255, 255, 200))

    canvas = Image.alpha_composite(canvas.convert('RGBA'), overlay)
    return _draw_quiz_overlay(canvas, quiz_status, quiz_type, countdown_s)


def _draw_quiz_overlay(
    canvas: Image.Image,
    quiz_status: str | None,
    quiz_type: int | None,
    countdown_s: float | None,
) -> Image.Image:
    if quiz_status is None:
        return canvas

    overlay = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    w, h = canvas.size
    bar_h = max(36, h // 14)
    y0 = 8
    draw.rectangle((8, y0, w - 8, y0 + bar_h), fill=(29, 53, 87, 200))

    if quiz_status == 'waiting' and countdown_s is not None:
        secs = max(0, int(countdown_s + 0.999))
        text = f'Quiz wait {secs}s'
        draw.text((16, y0 + bar_h // 2 - 6), text, fill=(255, 255, 255, 255))
    elif quiz_status == 'received' and quiz_type is not None:
        icon = box_image(quiz_type, bar_h - 8)
        overlay.paste(icon, (w - bar_h - 8, y0 + 4), icon)
        text = f'Quiz type {quiz_type}'
        draw.text((16, y0 + bar_h // 2 - 6), text, fill=(255, 255, 255, 255))
    elif quiz_status == 'timeout':
        draw.text((16, y0 + bar_h // 2 - 6), 'Quiz timeout - base plan', fill=(255, 200, 100, 255))

    return Image.alpha_composite(canvas.convert('RGBA'), overlay)


def render_field_state(
    box_types: Tuple[int, ...] | list[int],
    zone_types: Tuple[int, ...] | list[int],
    display_width: int,
    selected_brush: int | None = None,
) -> Image.Image:
    del selected_brush  # brush hint is shown in the tkinter sidebar (PIL default font lacks CJK).
    canvas = field_background_image(display_width)
    return overlay_boxes_and_zones(canvas, box_types, zone_types, display_width, draw_labels=True)


def photo_image(pil_image: Image.Image, master) -> ImageTk.PhotoImage:
    return ImageTk.PhotoImage(pil_image, master=master)
