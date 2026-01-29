"""
Advanced pixel art editor prototype with a Piskel-inspired toolset.
"""
from __future__ import annotations


import argparse
import datetime as _dt
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Set, Tuple


import pygame as pg
from history import History
from palette_system import Palette, PaletteManager
from palette_browser import PaletteBrowserUI
from export_dialog import ExportDialog
from export_utils import export_single_png, export_spritesheet, export_gif, export_zip, get_export_filename
from resize_dialog import ResizeDialog
from resize_utils import resize_frame_stack
from load_utils import open_image_file_dialog, load_image_to_canvas, create_frame_stack_from_image, save_image_file_dialog, save_export_file_dialog


Color = Tuple[int, int, int, int]
Point = Tuple[int, int]


WINDOW_SIZE = (1920, 1080)
FPS = 120


WINDOW_BG = (28, 30, 34)
SIDEBAR_BG = (38, 42, 48)
SIDEBAR_ACCENT = (94, 172, 248)
SIDEBAR_TEXT = (238, 240, 244)
SIDEBAR_MUTED = (150, 158, 168)
CANVAS_BORDER = (72, 76, 82)
STATUS_BG = (24, 26, 30)
STATUS_TEXT = (220, 224, 232)
HOVER_OUTLINE = (248, 238, 120)
SELECTION_FILL = (94, 172, 248, 60)
SELECTION_BORDER = (94, 172, 248)
PREVIEW_COLOR = (250, 250, 250, 160)
GRID_COLOR = (64, 68, 74, 120)
CHECKER_LIGHT = (210, 214, 222)
CHECKER_DARK = (170, 174, 182)


FRAMES_PANEL_WIDTH = 200
SIDEBAR_WIDTH = 260
RIGHT_PANEL_WIDTH = 260
STATUS_BAR_HEIGHT = 36
BUTTON_SIZE = (104, 46)
BUTTON_GAP = 14
BRUSH_SWATCH_SIZE = 26
BRUSH_SWATCH_GAP = 10
PALETTE_CELL = 28
PALETTE_GAP = 8
COLOR_PREVIEW_SIZE = (64, 64)


BRUSH_SIZES = [1, 2, 3, 4, 5]
ZOOM_LEVELS = [4, 6, 8, 10, 12, 16, 24, 32]
DEFAULT_ZOOM_INDEX = 2
DEFAULT_BRUSH_INDEX = 0


TRANSPARENT: Color = (0, 0, 0, 0)
DEFAULT_PRIMARY: Color = (32, 32, 32, 255)
DEFAULT_SECONDARY: Color = (255, 255, 255, 255)


TOOL_LABELS: Dict[str, str] = {
    "pen": "Pen",
    "mirror_pen": "Mirror",
    "bucket": "Bucket",
    "fill_all": "FillAll",
    "eraser": "Erase",
    "stroke": "Line",
    "rectangle": "Rect",
    "ellipse": "Ellipse",
    "move": "Pan",
    "color_replace": "Replace",
    "rect_select": "RectSel",
    "lasso_select": "Lasso",
    "zoom": "Zoom",
    "dither": "Dither",
    "picker": "Picker",
}


TOOL_TOOLTIPS: Dict[str, str] = {
    "pen": "Freehand drawing with the active brush",
    "mirror_pen": "Draw with vertical mirror symmetry",
    "bucket": "Flood fill contiguous pixels",
    "fill_all": "Fill the selection or entire canvas",
    "eraser": "Erase to transparency",
    "stroke": "Draw straight lines",
    "rectangle": "Draw filled rectangles",
    "ellipse": "Draw filled ellipses",
    "move": "Drag to pan the viewport",
    "color_replace": "Replace a color everywhere in the selection",
    "rect_select": "Create a rectangular selection",
    "lasso_select": "Free-form selection",
    "zoom": "Left click to zoom in, right click to zoom out",
    "dither": "Freehand alternating primary/secondary",
    "picker": "Sample colors into primary/secondary",
}


TOOL_ORDER = [
    "pen",
    "mirror_pen",
    "bucket",
    "fill_all",
    "eraser",
    "stroke",
    "rectangle",
    "ellipse",
    "move",
    "color_replace",
    "rect_select",
    "lasso_select",
    "zoom",
    "dither",
    "picker",
]


PALETTE_COLORS: List[Color] = [
    # Grayscale (8 colors)
    (0, 0, 0, 255),           # Black
    (32, 32, 32, 255),        # Very Dark Gray
    (64, 64, 64, 255),        # Dark Gray
    (96, 96, 96, 255),        # Medium Dark Gray
    (128, 128, 128, 255),     # Medium Gray
    (160, 160, 160, 255),     # Medium Light Gray
    (192, 192, 192, 255),     # Light Gray
    (255, 255, 255, 255),     # White
    
    # Reds (8 colors)
    (128, 0, 0, 255),         # Dark Red
    (192, 0, 0, 255),         # Red
    (255, 0, 0, 255),         # Bright Red
    (255, 64, 64, 255),       # Light Red
    (128, 32, 32, 255),       # Brown Red
    (255, 128, 128, 255),     # Pink Red
    (255, 192, 192, 255),     # Light Pink
    (128, 64, 64, 255),       # Dusty Red
    
    # Oranges (8 colors)
    (128, 64, 0, 255),        # Dark Orange
    (192, 96, 0, 255),        # Orange Brown
    (255, 128, 0, 255),       # Orange
    (255, 160, 64, 255),      # Light Orange
    (255, 192, 128, 255),     # Peach
    (128, 96, 64, 255),       # Brown
    (160, 120, 80, 255),      # Tan
    (255, 224, 192, 255),     # Light Peach
    
    # Yellows (8 colors)
    (128, 128, 0, 255),       # Dark Yellow
    (192, 192, 0, 255),       # Olive Yellow
    (255, 255, 0, 255),       # Yellow
    (255, 255, 128, 255),     # Light Yellow
    (255, 255, 192, 255),     # Pale Yellow
    (128, 128, 64, 255),      # Olive
    (192, 192, 128, 255),     # Light Olive
    (255, 255, 224, 255),     # Cream
    
    # Greens (8 colors)
    (0, 64, 0, 255),          # Dark Green
    (0, 128, 0, 255),         # Green
    (0, 192, 0, 255),         # Bright Green
    (64, 255, 64, 255),       # Light Green
    (128, 255, 128, 255),     # Pale Green
    (64, 128, 64, 255),       # Forest Green
    (32, 96, 32, 255),        # Dark Forest
    (192, 255, 192, 255),     # Very Light Green
    
    # Cyans (8 colors)
    (0, 128, 128, 255),       # Teal
    (0, 192, 192, 255),       # Cyan
    (0, 255, 255, 255),       # Bright Cyan
    (128, 255, 255, 255),     # Light Cyan
    (192, 255, 255, 255),     # Pale Cyan
    (64, 128, 128, 255),      # Dark Teal
    (96, 160, 160, 255),      # Muted Teal
    (224, 255, 255, 255),     # Very Light Cyan
    
    # Blues (8 colors)
    (0, 0, 128, 255),         # Dark Blue
    (0, 0, 192, 255),         # Blue
    (0, 0, 255, 255),         # Bright Blue
    (64, 64, 255, 255),       # Light Blue
    (128, 128, 255, 255),     # Sky Blue
    (32, 32, 128, 255),       # Navy
    (96, 96, 192, 255),       # Periwinkle
    (192, 192, 255, 255),     # Pale Blue
    
    # Purples/Magentas (8 colors)
    (128, 0, 128, 255),       # Purple
    (192, 0, 192, 255),       # Magenta
    (255, 0, 255, 255),       # Bright Magenta
    (255, 128, 255, 255),     # Light Magenta
    (255, 192, 255, 255),     # Pink
    (96, 0, 96, 255),         # Dark Purple
    (160, 96, 160, 255),      # Lavender
    (224, 192, 224, 255),     # Light Lavender
]




def workspace_rect(window_size: Tuple[int, int]) -> pg.Rect:
    left = FRAMES_PANEL_WIDTH + SIDEBAR_WIDTH
    width = max(1, window_size[0] - left - RIGHT_PANEL_WIDTH)
    height = max(1, window_size[1] - STATUS_BAR_HEIGHT)
    return pg.Rect(left, 0, width, height)


def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(value, max_value))




def iter_brush_points(center: Point, size: int) -> Iterator[Point]:
    radius = size // 2
    cx, cy = center
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            yield (cx + dx, cy + dy)




def bresenham_line(start: Point, end: Point) -> List[Point]:
    x0, y0 = start
    x1, y1 = end
    points: List[Point] = []
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    error = dx + dy
    x, y = x0, y0
    while True:
        points.append((x, y))
        if x == x1 and y == y1:
            break
        e2 = 2 * error
        if e2 >= dy:
            error += dy
            x += sx
        if e2 <= dx:
            error += dx
            y += sy
    return points




def rect_points(start: Point, end: Point) -> Set[Point]:
    x0, y0 = start
    x1, y1 = end
    left, right = sorted((x0, x1))
    top, bottom = sorted((y0, y1))
    return {(x, y) for x in range(left, right + 1) for y in range(top, bottom + 1)}




def ellipse_points(start: Point, end: Point) -> Set[Point]:
    x0, y0 = start
    x1, y1 = end
    left, right = sorted((x0, x1))
    top, bottom = sorted((y0, y1))
    width = right - left + 1
    height = bottom - top + 1
    if width <= 0 or height <= 0:
        return set()
    temp = pg.Surface((width, height), pg.SRCALPHA)
    pg.draw.ellipse(temp, (255, 255, 255, 255), temp.get_rect())
    mask = pg.mask.from_surface(temp)
    points: Set[Point] = set()
    for y in range(height):
        for x in range(width):
            if mask.get_at((x, y)):
                points.add((left + x, top + y))
    return points




class Selection:
    def __init__(self, points: Set[Point]) -> None:
        self.points = points
        if points:
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            self.bounds = pg.Rect(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)
        else:
            self.bounds = pg.Rect(0, 0, 0, 0)


    def is_empty(self) -> bool:
        return not self.points


    def contains(self, x: int, y: int) -> bool:
        return (x, y) in self.points


    def iter_points(self) -> Iterator[Point]:
        return iter(self.points)




@dataclass
class Layer:
    name: str
    surface: pg.Surface
    visible: bool = True
    opacity: int = 255


    def clear(self) -> None:
        self.surface.fill(TRANSPARENT)




class PixelCanvas:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.layers: List[Layer] = []
        self.active_index = 0
        self.checker = self._build_checker()
        self._composite_surface = pg.Surface((width, height), pg.SRCALPHA)
        self._composite_surface.fill(TRANSPARENT)
        self._dirty = True
        self._layer_counter = 1
        self.add_layer()


    def _mark_dirty(self) -> None:
        self._dirty = True


    @property
    def active_layer(self) -> Layer:
        return self.layers[self.active_index]


    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height


    def add_layer(self, name: Optional[str] = None, index: Optional[int] = None) -> Layer:
        if name is None:
            name = f"Layer {self._layer_counter}"
        self._layer_counter += 1
        surface = pg.Surface((self.width, self.height), pg.SRCALPHA)
        surface.fill(TRANSPARENT)
        layer = Layer(name=name, surface=surface)
        if index is None:
            index = len(self.layers)
        self.layers.insert(index, layer)
        self.set_active(index)
        self._mark_dirty()
        return layer


    def remove_layer(self, index: Optional[int] = None) -> bool:
        if len(self.layers) <= 1:
            return False
        if index is None:
            index = self.active_index
        if not (0 <= index < len(self.layers)):
            return False
        self.layers.pop(index)
        self.active_index = min(index, len(self.layers) - 1)
        self._mark_dirty()
        return True


    def move_layer_up(self, index: Optional[int] = None) -> bool:
        if index is None:
            index = self.active_index
        if index >= len(self.layers) - 1:
            return False
        self.layers[index], self.layers[index + 1] = self.layers[index + 1], self.layers[index]
        if self.active_index == index:
            self.active_index += 1
        elif self.active_index == index + 1:
            self.active_index -= 1
        self._mark_dirty()
        return True


    def move_layer_down(self, index: Optional[int] = None) -> bool:
        if index is None:
            index = self.active_index
        if index <= 0:
            return False
        self.layers[index], self.layers[index - 1] = self.layers[index - 1], self.layers[index]
        if self.active_index == index:
            self.active_index -= 1
        elif self.active_index == index - 1:
            self.active_index += 1
        self._mark_dirty()
        return True


    def toggle_visibility(self, index: Optional[int] = None) -> bool:
        if index is None:
            index = self.active_index
        if not (0 <= index < len(self.layers)):
            return False
        layer = self.layers[index]
        layer.visible = not layer.visible
        self._mark_dirty()
        return layer.visible


    def set_active(self, index: int) -> None:
        index = int(clamp(index, 0, len(self.layers) - 1))
        self.active_index = index


    def composite_surface(self) -> pg.Surface:
        if self._dirty:
            self._composite_surface.fill(TRANSPARENT)
            for layer in self.layers:
                if not layer.visible or layer.opacity <= 0:
                    continue
                if layer.opacity >= 255:
                    self._composite_surface.blit(layer.surface, (0, 0))
                else:
                    temp = layer.surface.copy()
                    temp.set_alpha(layer.opacity)
                    self._composite_surface.blit(temp, (0, 0))
            self._dirty = False
        return self._composite_surface


    def get_active_color(self, x: int, y: int) -> Color:
        color = self.active_layer.surface.get_at((x, y))
        return (color.r, color.g, color.b, color.a)


    def sample_color(self, x: int, y: int) -> Color:
        color = self.composite_surface().get_at((x, y))
        return (color.r, color.g, color.b, color.a)


    def paint_points(self, points: Iterable[Point], color: Color) -> int:
        count = 0
        surface = self.active_layer.surface
        for x, y in points:
            if self.in_bounds(x, y):
                surface.set_at((x, y), color)
                count += 1
        if count:
            self._mark_dirty()
        return count


    def flood_fill(self, start: Point, source_color: Color, new_color: Color, selection: Optional[Selection]) -> int:
        if source_color == new_color:
            return 0
        surface = self.active_layer.surface
        queue: List[Point] = [start]
        visited: Set[Point] = set()
        filled = 0
        while queue:
            x, y = queue.pop()
            if (x, y) in visited:
                continue
            visited.add((x, y))
            if not self.in_bounds(x, y):
                continue
            if selection and not selection.contains(x, y):
                continue
            if self.get_active_color(x, y) != source_color:
                continue
            surface.set_at((x, y), new_color)
            filled += 1
            queue.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
        if filled:
            self._mark_dirty()
        return filled


    def replace_color(self, target: Color, replacement: Color, selection: Optional[Selection]) -> int:
        if target == replacement:
            return 0
        surface = self.active_layer.surface
        replaced = 0
        for y in range(self.height):
            for x in range(self.width):
                if selection and not selection.contains(x, y):
                    continue
                if self.get_active_color(x, y) == target:
                    surface.set_at((x, y), replacement)
                    replaced += 1
        if replaced:
            self._mark_dirty()
        return replaced


    def fill_selection(self, color: Color, selection: Optional[Selection]) -> int:
        if selection and not selection.is_empty():
            count = self.paint_points(selection.points, color)
        else:
            surface = self.active_layer.surface
            surface.fill(color)
            count = self.width * self.height
        if count:
            self._mark_dirty()
        return count


    def clear_active(self) -> None:
        self.active_layer.clear()
        self._mark_dirty()


    def shifted(self, offset: Point) -> None:
        dx, dy = offset
        if dx == 0 and dy == 0:
            return
        surface = self.active_layer.surface
        original = surface.copy()
        surface.fill(TRANSPARENT)
        surface.blit(original, (dx, dy))
        self._mark_dirty()


    def export_surface(self) -> pg.Surface:
        return self.composite_surface().copy()


    def clone(self) -> "PixelCanvas":
        """Deep-copy this canvas, including all layers and their pixels."""
        new_canvas = PixelCanvas(self.width, self.height)
        # Rebuild layer list with deep-copied surfaces
        new_canvas.layers = []
        for layer in self.layers:
            new_surface = layer.surface.copy()
            new_layer = Layer(
                name=layer.name,
                surface=new_surface,
                visible=layer.visible,
                opacity=layer.opacity,
            )
            new_canvas.layers.append(new_layer)
        # Preserve active layer index and counters
        if new_canvas.layers:
            new_canvas.active_index = int(clamp(self.active_index, 0, len(new_canvas.layers) - 1))
        else:
            new_canvas.active_index = 0
        new_canvas._layer_counter = self._layer_counter
        # Reset composite/dirtiness so it will rebuild
        new_canvas._dirty = True
        new_canvas._composite_surface = pg.Surface((self.width, self.height), pg.SRCALPHA)
        new_canvas._composite_surface.fill(TRANSPARENT)
        return new_canvas


    def layers_for_display(self) -> List[Tuple[int, Layer]]:
        return list(reversed(list(enumerate(self.layers))))


    def _build_checker(self) -> pg.Surface:
        surface = pg.Surface((self.width, self.height))
        toggle = False
        for y in range(self.height):
            toggle = not toggle
            for x in range(self.width):
                color = CHECKER_LIGHT if toggle else CHECKER_DARK
                surface.set_at((x, y), color)
                toggle = not toggle
        return surface.convert()






@dataclass
class Frame:
    name: str
    canvas: PixelCanvas




class FrameStack:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.frames: List[Frame] = []
        self.active_index = 0
        self.add_frame()


    def _relabel(self) -> None:
        for idx, frame in enumerate(self.frames, start=1):
            frame.name = f"Frame {idx}"


    @property
    def count(self) -> int:
        return len(self.frames)


    @property
    def active_frame(self) -> Frame:
        return self.frames[self.active_index]


    @property
    def active_canvas(self) -> PixelCanvas:
        return self.active_frame.canvas


    def set_active(self, index: int) -> bool:
        if not self.frames:
            return False
        index = int(clamp(index, 0, len(self.frames) - 1))
        if index == self.active_index:
            return False
        self.active_index = index
        return True


    def add_frame(self, index: Optional[int] = None, canvas: Optional[PixelCanvas] = None) -> int:
        if canvas is None:
            canvas = PixelCanvas(self.width, self.height)
        if index is None:
            index = len(self.frames)
        index = int(clamp(index, 0, len(self.frames)))
        frame = Frame(name="", canvas=canvas)
        self.frames.insert(index, frame)
        self._relabel()
        self.active_index = index
        return index


    def duplicate_active(self) -> Optional[int]:
        if not self.frames:
            return None
        clone = self.active_canvas.clone()
        index = self.active_index + 1
        inserted = self.add_frame(index=index, canvas=clone)
        return inserted


    def remove_frame(self, index: Optional[int] = None) -> bool:
        if len(self.frames) <= 1:
            return False
        if index is None:
            index = self.active_index
        if not (0 <= index < len(self.frames)):
            return False
        self.frames.pop(index)
        self.active_index = min(index, len(self.frames) - 1)
        self._relabel()
        return True


    def move_active_up(self) -> bool:
        idx = self.active_index
        if idx >= len(self.frames) - 1:
            return False
        self.frames[idx], self.frames[idx + 1] = self.frames[idx + 1], self.frames[idx]
        self.active_index += 1
        self._relabel()
        return True


    def move_active_down(self) -> bool:
        idx = self.active_index
        if idx <= 0:
            return False
        self.frames[idx], self.frames[idx - 1] = self.frames[idx - 1], self.frames[idx]
        self.active_index -= 1
        self._relabel()
        return True


    def frames_for_display(self) -> List[Tuple[int, Frame]]:
        return list(enumerate(self.frames))


    def clone(self) -> 'FrameStack':
        """Create a deep copy of this frame stack."""
        new_stack = FrameStack(self.width, self.height)
        new_stack.frames = []
        
        for frame in self.frames:
            cloned_canvas = frame.canvas.clone()
            cloned_frame = Frame(name=frame.name, canvas=cloned_canvas)
            new_stack.frames.append(cloned_frame)
        
        new_stack.active_index = self.active_index
        return new_stack


class AnimationPlayer:
    def __init__(self, frame_stack: FrameStack) -> None:
        self.frame_stack = frame_stack
        self.playing = False
        self.fps = 12  # Animation FPS (default 12 FPS for smooth animation)
        self.frame_time = 1000 // self.fps  # Milliseconds per frame
        self.last_frame_time = 0
        self.current_frame_index = 0
        self.loop = True

    def set_fps(self, fps: int) -> None:
        """Set animation FPS and recalculate frame time."""
        self.fps = max(1, min(60, fps))  # Clamp between 1 and 60 FPS
        self.frame_time = 1000 // self.fps

    def play(self) -> None:
        """Start animation playback."""
        if self.frame_stack.count > 1:
            self.playing = True
            self.last_frame_time = pg.time.get_ticks()

    def pause(self) -> None:
        """Pause animation playback."""
        self.playing = False

    def toggle(self) -> None:
        """Toggle animation playback."""
        if self.playing:
            self.pause()
        else:
            self.play()

    def update(self) -> None:
        """Update animation frame based on elapsed time."""
        if not self.playing or self.frame_stack.count <= 1:
            return

        current_time = pg.time.get_ticks()
        elapsed = current_time - self.last_frame_time

        if elapsed >= self.frame_time:
            # Advance to next frame
            self.current_frame_index += 1
            
            if self.current_frame_index >= self.frame_stack.count:
                if self.loop:
                    self.current_frame_index = 0
                else:
                    self.current_frame_index = self.frame_stack.count - 1
                    self.pause()
            
            # Update frame stack to show current animation frame
            self.frame_stack.set_active(self.current_frame_index)
            self.last_frame_time = current_time

    def reset(self) -> None:
        """Reset animation to first frame."""
        self.current_frame_index = 0
        self.playing = False
        if self.frame_stack.count > 0:
            self.frame_stack.set_active(0)


@dataclass
class AppState:
    frame_stack: FrameStack
    primary_color: Color = DEFAULT_PRIMARY
    secondary_color: Color = DEFAULT_SECONDARY
    brush_index: int = DEFAULT_BRUSH_INDEX
    zoom_index: int = DEFAULT_ZOOM_INDEX
    origin: pg.Vector2 = field(default_factory=lambda: pg.Vector2(FRAMES_PANEL_WIDTH + SIDEBAR_WIDTH + 40, 40))
    status: str = "Ready"
    show_grid: bool = True
    selection: Optional[Selection] = None
    hover_cell: Optional[Point] = None
    animation_player: Optional[AnimationPlayer] = field(init=False)

    def __post_init__(self) -> None:
        self.animation_player = AnimationPlayer(self.frame_stack)


    @property
    def canvas(self) -> PixelCanvas:
        return self.frame_stack.active_canvas


    @property
    def frame_index(self) -> int:
        return self.frame_stack.active_index


    @property
    def frame_count(self) -> int:
        return self.frame_stack.count


    def brush_size(self) -> int:
        return BRUSH_SIZES[self.brush_index]


    def pixel_size(self) -> int:
        return ZOOM_LEVELS[self.zoom_index]


    def canvas_rect(self) -> pg.Rect:
        return pg.Rect(
            int(self.origin.x),
            int(self.origin.y),
            self.canvas.width * self.pixel_size(),
            self.canvas.height * self.pixel_size(),
        )


    def set_status(self, message: str) -> None:
        self.status = message


    def apply_brush(self, point: Point, color: Color) -> int:
        valid: List[Point] = []
        for px, py in iter_brush_points(point, self.brush_size()):
            if not self.canvas.in_bounds(px, py):
                continue
            if self.selection and not self.selection.contains(px, py):
                continue
            valid.append((px, py))
        return self.canvas.paint_points(valid, color)


    def apply_points(self, points: Iterable[Point], color: Color) -> int:
        valid: List[Point] = []
        for x, y in points:
            if not self.canvas.in_bounds(x, y):
                continue
            if self.selection and not self.selection.contains(x, y):
                continue
            valid.append((x, y))
        return self.canvas.paint_points(valid, color)


    def color_for_button(self, button: int) -> Color:
        if button == 1:
            return self.primary_color
        if button == 3:
            return self.secondary_color
        return self.primary_color


    def swap_colors(self) -> None:
        self.primary_color, self.secondary_color = self.secondary_color, self.primary_color


    def clear_selection(self) -> None:
        self.selection = None
        self.set_status("Selection cleared")


    def set_selection(self, selection: Optional[Selection]) -> None:
        if selection and selection.is_empty():
            selection = None
        self.selection = selection
        if selection:
            self.set_status("Selection active")
        else:
            self.set_status("Selection cleared")


    def ensure_visible(self, window_size: Tuple[int, int]) -> None:
        workspace = workspace_rect(window_size)
        pixel_size = self.pixel_size()
        canvas_width = self.canvas.width * pixel_size
        canvas_height = self.canvas.height * pixel_size


        max_x = workspace.left
        min_x = workspace.right - canvas_width
        if canvas_width <= workspace.width:
            centered_x = workspace.left + (workspace.width - canvas_width) / 2
            self.origin.x = centered_x
        else:
            self.origin.x = clamp(self.origin.x, min_x, max_x)


        max_y = workspace.top
        min_y = workspace.bottom - canvas_height
        if canvas_height <= workspace.height:
            centered_y = workspace.top + (workspace.height - canvas_height) / 2
            self.origin.y = centered_y
        else:
            self.origin.y = clamp(self.origin.y, min_y, max_y)


    def center_canvas(self, window_size: Tuple[int, int]) -> None:
        workspace = workspace_rect(window_size)
        pixel_size = self.pixel_size()
        canvas_width = self.canvas.width * pixel_size
        canvas_height = self.canvas.height * pixel_size
        self.origin.x = workspace.left + (workspace.width - canvas_width) / 2
        self.origin.y = workspace.top + (workspace.height - canvas_height) / 2
        self.ensure_visible(window_size)


    def center_on_cell(self, cell: Point, window_size: Tuple[int, int]) -> None:
        workspace = workspace_rect(window_size)
        pixel_size = self.pixel_size()
        focus = pg.Vector2(cell[0] + 0.5, cell[1] + 0.5)
        self.origin = pg.Vector2(
            workspace.centerx - focus.x * pixel_size,
            workspace.centery - focus.y * pixel_size,
        )
        self.ensure_visible(window_size)


    def adjust_zoom(self, new_index: int, focus_cell: Optional[Point], window_size: Tuple[int, int]) -> None:
        new_index = int(clamp(new_index, 0, len(ZOOM_LEVELS) - 1))
        if new_index == self.zoom_index:
            return
        old_size = self.pixel_size()
        self.zoom_index = new_index
        new_size = self.pixel_size()
        if focus_cell is None:
            focus_cell = (self.canvas.width // 2, self.canvas.height // 2)
        focus = pg.Vector2(focus_cell[0] + 0.5, focus_cell[1] + 0.5)
        screen_focus = self.origin + focus * old_size
        self.origin = screen_focus - focus * new_size
        self.ensure_visible(window_size)


    def select_frame(self, index: int, window_size: Tuple[int, int]) -> None:
        if self.frame_stack.set_active(index):
            self.selection = None
            self.hover_cell = None
            self.ensure_visible(window_size)
            self.set_status(f"Frame {self.frame_index + 1} active")


    def add_blank_frame(self, window_size: Tuple[int, int]) -> None:
        new_index = self.frame_stack.add_frame(index=self.frame_index + 1)
        self.selection = None
        self.hover_cell = None
        self.ensure_visible(window_size)
        self.set_status(f"Added frame {new_index + 1}")


    def duplicate_frame(self, window_size: Tuple[int, int]) -> None:
        result = self.frame_stack.duplicate_active()
        if result is None:
            self.set_status("No frame to duplicate")
            return
        self.selection = None
        self.hover_cell = None
        self.ensure_visible(window_size)
        self.set_status(f"Duplicated to frame {result + 1}")


    def delete_frame(self, window_size: Tuple[int, int]) -> None:
        if self.frame_stack.remove_frame():
            self.selection = None
            self.hover_cell = None
            self.ensure_visible(window_size)
            self.set_status("Removed frame")
        else:
            self.set_status("Cannot remove last frame")


    def move_frame_up(self) -> None:
        if self.frame_stack.move_active_up():
            self.set_status("Frame moved forward")
        else:
            self.set_status("Frame already at end")


    def move_frame_down(self) -> None:
        if self.frame_stack.move_active_down():
            self.set_status("Frame moved backward")
        else:
            self.set_status("Frame already at start")
class Tool:
    name: str


    def on_select(self, state: AppState) -> None:
        self.reset()


    def on_mouse_down(
        self,
        state: AppState,
        cell: Optional[Point],
        button: int,
        mouse_pos: Tuple[int, int],
        window_size: Tuple[int, int],
    ) -> None:
        raise NotImplementedError


    def on_mouse_up(self, state: AppState, button: int) -> None:
        pass


    def on_mouse_move(
        self,
        state: AppState,
        cell: Optional[Point],
        buttons: Tuple[int, int, int],
        mouse_pos: Tuple[int, int],
        window_size: Tuple[int, int],
    ) -> None:
        pass


    def draw_overlay(
        self,
        surface: pg.Surface,
        state: AppState,
        canvas_rect: pg.Rect,
        pixel_size: int,
    ) -> None:
        pass


    def reset(self) -> None:
        pass




class PenTool(Tool):
    name = "pen"


    def __init__(self) -> None:
        self.last_cell: Optional[Point] = None
        self.active_button: Optional[int] = None


    def reset(self) -> None:
        self.last_cell = None
        self.active_button = None


    def _draw_points(self, state: AppState, points: Iterable[Point], color: Color) -> None:
        for point in points:
            state.apply_brush(point, color)


    def _handle_draw(self, state: AppState, cell: Point) -> None:
        if self.active_button is None:
            return
        color = state.color_for_button(self.active_button)
        if self.last_cell is None:
            self._draw_points(state, [cell], color)
        else:
            points = bresenham_line(self.last_cell, cell)
            self._draw_points(state, points, color)
        self.last_cell = cell


    def on_mouse_down(
        self,
        state: AppState,
        cell: Optional[Point],
        button: int,
        mouse_pos: Tuple[int, int],
        window_size: Tuple[int, int],
    ) -> None:
        if cell is None:
            return
        self.active_button = button
        self.last_cell = cell
        self._handle_draw(state, cell)


    def on_mouse_move(
        self,
        state: AppState,
        cell: Optional[Point],
        buttons: Tuple[int, int, int],
        mouse_pos: Tuple[int, int],
        window_size: Tuple[int, int],
    ) -> None:
        if cell is None:
            return
        if self.active_button is None:
            if buttons[0]:
                self.active_button = 1
            elif buttons[2]:
                self.active_button = 3
        if self.active_button is None:
            return
        if (self.active_button == 1 and not buttons[0]) or (
            self.active_button == 3 and not buttons[2]
        ):
            return
        self._handle_draw(state, cell)


    def on_mouse_up(self, state: AppState, button: int) -> None:
        if button == self.active_button:
            self.active_button = None
            self.last_cell = None




class MirrorPenTool(PenTool):
    name = "mirror_pen"


    def _draw_points(self, state: AppState, points: Iterable[Point], color: Color) -> None:
        width = state.canvas.width
        painted: Set[Point] = set()
        for px, py in points:
            if not state.canvas.in_bounds(px, py):
                continue
            mirrored_x = width - 1 - px
            for cx in (px, mirrored_x):
                if state.selection and not state.selection.contains(cx, py):
                    continue
                if (cx, py) in painted:
                    continue
                state.apply_brush((cx, py), color)
                painted.add((cx, py))




class BucketTool(Tool):
    name = "bucket"


    def on_mouse_down(
        self,
        state: AppState,
        cell: Optional[Point],
        button: int,
        mouse_pos: Tuple[int, int],
        window_size: Tuple[int, int],
    ) -> None:
        if cell is None:
            return
        color = state.color_for_button(button)
        target = state.canvas.get_active_color(*cell)
        filled = state.canvas.flood_fill(cell, target, color, state.selection)
        state.set_status(f"Flood filled {filled} pixels")




class FillAllTool(Tool):
    name = "fill_all"


    def on_mouse_down(
        self,
        state: AppState,
        cell: Optional[Point],
        button: int,
        mouse_pos: Tuple[int, int],
        window_size: Tuple[int, int],
    ) -> None:
        color = state.color_for_button(button)
        filled = state.canvas.fill_selection(color, state.selection)
        state.set_status(f"Filled {filled} pixels")




class EraserTool(PenTool):
    name = "eraser"


    def _handle_draw(self, state: AppState, cell: Point) -> None:
        if self.active_button is None:
            return
        points = [cell] if self.last_cell is None else bresenham_line(self.last_cell, cell)
        for point in points:
            state.apply_brush(point, TRANSPARENT)
        self.last_cell = cell




class StrokeTool(Tool):
    name = "stroke"


    def __init__(self) -> None:
        self.start: Optional[Point] = None
        self.preview: List[Point] = []
        self.button: Optional[int] = None


    def reset(self) -> None:
        self.start = None
        self.preview = []
        self.button = None


    def on_mouse_down(
        self,
        state: AppState,
        cell: Optional[Point],
        button: int,
        mouse_pos: Tuple[int, int],
        window_size: Tuple[int, int],
    ) -> None:
        if cell is None:
            return
        self.start = cell
        self.button = button
        self.preview = [cell]


    def on_mouse_move(
        self,
        state: AppState,
        cell: Optional[Point],
        buttons: Tuple[int, int, int],
        mouse_pos: Tuple[int, int],
        window_size: Tuple[int, int],
    ) -> None:
        if self.start is None or cell is None:
            return
        if self.button == 1 and not buttons[0]:
            return
        if self.button == 3 and not buttons[2]:
            return
        self.preview = bresenham_line(self.start, cell)


    def on_mouse_up(self, state: AppState, button: int) -> None:
        if self.start is None or self.button != button:
            self.reset()
            return
        color = state.color_for_button(button)
        for point in self.preview:
            state.apply_brush(point, color)
        state.set_status("Line committed")
        self.reset()


    def draw_overlay(
        self,
        surface: pg.Surface,
        state: AppState,
        canvas_rect: pg.Rect,
        pixel_size: int,
    ) -> None:
        if not self.preview:
            return
        overlay = pg.Surface(canvas_rect.size, pg.SRCALPHA)
        for px, py in self.preview:
            rect = pg.Rect(
                (px * pixel_size, py * pixel_size),
                (pixel_size, pixel_size),
            )
            pg.draw.rect(overlay, PREVIEW_COLOR, rect)
        surface.blit(overlay, canvas_rect.topleft)




class ShapeTool(Tool):
    def __init__(self) -> None:
        self.start: Optional[Point] = None
        self.preview: Set[Point] = set()
        self.button: Optional[int] = None


    def reset(self) -> None:
        self.start = None
        self.preview = set()
        self.button = None


    def _shape_points(self, start: Point, end: Point) -> Set[Point]:
        raise NotImplementedError


    def on_mouse_down(
        self,
        state: AppState,
        cell: Optional[Point],
        button: int,
        mouse_pos: Tuple[int, int],
        window_size: Tuple[int, int],
    ) -> None:
        if cell is None:
            return
        self.start = cell
        self.button = button
        self.preview = {cell}


    def on_mouse_move(
        self,
        state: AppState,
        cell: Optional[Point],
        buttons: Tuple[int, int, int],
        mouse_pos: Tuple[int, int],
        window_size: Tuple[int, int],
    ) -> None:
        if self.start is None or cell is None:
            return
        if self.button == 1 and not buttons[0]:
            return
        if self.button == 3 and not buttons[2]:
            return
        self.preview = self._shape_points(self.start, cell)


    def on_mouse_up(self, state: AppState, button: int) -> None:
        if self.start is None or self.button != button:
            self.reset()
            return
        color = state.color_for_button(button)
        state.apply_points(self.preview, color)
        self.reset()


    def draw_overlay(
        self,
        surface: pg.Surface,
        state: AppState,
        canvas_rect: pg.Rect,
        pixel_size: int,
    ) -> None:
        if not self.preview:
            return
        overlay = pg.Surface(canvas_rect.size, pg.SRCALPHA)
        for px, py in self.preview:
            rect = pg.Rect(
                (px * pixel_size, py * pixel_size),
                (pixel_size, pixel_size),
            )
            pg.draw.rect(overlay, PREVIEW_COLOR, rect)
        surface.blit(overlay, canvas_rect.topleft)




class RectangleTool(ShapeTool):
    name = "rectangle"


    def _shape_points(self, start: Point, end: Point) -> Set[Point]:
        return rect_points(start, end)




class EllipseTool(ShapeTool):
    name = "ellipse"


    def _shape_points(self, start: Point, end: Point) -> Set[Point]:
        return ellipse_points(start, end)


class MoveTool(Tool):
    name = "move"


    def __init__(self) -> None:
        self.dragging = False
        self.start_mouse = pg.Vector2(0, 0)
        self.start_origin = pg.Vector2(0, 0)


    def reset(self) -> None:
        self.dragging = False


    def on_mouse_down(
        self,
        state: AppState,
        cell: Optional[Point],
        button: int,
        mouse_pos: Tuple[int, int],
        window_size: Tuple[int, int],
    ) -> None:
        if button != 1:
            return
        self.dragging = True
        self.start_mouse = pg.Vector2(mouse_pos)
        self.start_origin = state.origin.copy()


    def on_mouse_move(
        self,
        state: AppState,
        cell: Optional[Point],
        buttons: Tuple[int, int, int],
        mouse_pos: Tuple[int, int],
        window_size: Tuple[int, int],
    ) -> None:
        if not self.dragging:
            return
        current = pg.Vector2(mouse_pos)
        delta = current - self.start_mouse
        state.origin = self.start_origin + delta


    def on_mouse_up(self, state: AppState, button: int) -> None:
        if button == 1:
            self.dragging = False




class ColorReplaceTool(Tool):
    name = "color_replace"


    def on_mouse_down(
        self,
        state: AppState,
        cell: Optional[Point],
        button: int,
        mouse_pos: Tuple[int, int],
        window_size: Tuple[int, int],
    ) -> None:
        if cell is None:
            return
        target = state.canvas.get_active_color(*cell)
        replacement = state.color_for_button(button)
        replaced = state.canvas.replace_color(target, replacement, state.selection)
        state.set_status(f"Replaced {replaced} pixels")




class RectSelectTool(Tool):
    name = "rect_select"


    def __init__(self) -> None:
        self.start: Optional[Point] = None
        self.preview: Set[Point] = set()


    def reset(self) -> None:
        self.start = None
        self.preview = set()


    def on_mouse_down(
        self,
        state: AppState,
        cell: Optional[Point],
        button: int,
        mouse_pos: Tuple[int, int],
        window_size: Tuple[int, int],
    ) -> None:
        if button != 1 or cell is None:
            return
        self.start = cell
        self.preview = {cell}


    def on_mouse_move(
        self,
        state: AppState,
        cell: Optional[Point],
        buttons: Tuple[int, int, int],
        mouse_pos: Tuple[int, int],
        window_size: Tuple[int, int],
    ) -> None:
        if self.start is None or cell is None:
            return
        if not buttons[0]:
            return
        self.preview = rect_points(self.start, cell)


    def on_mouse_up(self, state: AppState, button: int) -> None:
        if button != 1 or self.start is None:
            self.reset()
            return
        selection = Selection(self.preview.copy())
        state.set_selection(selection)
        self.reset()


    def draw_overlay(
        self,
        surface: pg.Surface,
        state: AppState,
        canvas_rect: pg.Rect,
        pixel_size: int,
    ) -> None:
        if not self.preview:
            return
        overlay = pg.Surface(canvas_rect.size, pg.SRCALPHA)
        for px, py in self.preview:
            rect = pg.Rect(
                (px * pixel_size, py * pixel_size),
                (pixel_size, pixel_size),
            )
            pg.draw.rect(overlay, PREVIEW_COLOR, rect)
        surface.blit(overlay, canvas_rect.topleft)




class LassoSelectTool(Tool):
    name = "lasso_select"


    def __init__(self) -> None:
        self.path: List[Point] = []
        self.active = False


    def reset(self) -> None:
        self.path = []
        self.active = False


    def on_mouse_down(
        self,
        state: AppState,
        cell: Optional[Point],
        button: int,
        mouse_pos: Tuple[int, int],
        window_size: Tuple[int, int],
    ) -> None:
        if button != 1 or cell is None:
            return
        self.path = [cell]
        self.active = True


    def on_mouse_move(
        self,
        state: AppState,
        cell: Optional[Point],
        buttons: Tuple[int, int, int],
        mouse_pos: Tuple[int, int],
        window_size: Tuple[int, int],
    ) -> None:
        if not self.active or cell is None:
            return
        if not buttons[0]:
            return
        if self.path and self.path[-1] == cell:
            return
        self.path.append(cell)


    def on_mouse_up(self, state: AppState, button: int) -> None:
        if button != 1 or not self.active or len(self.path) < 3:
            self.reset()
            return
        surface = pg.Surface((state.canvas.width, state.canvas.height), pg.SRCALPHA)
        polygon = [(x + 0.5, y + 0.5) for x, y in self.path]
        pg.draw.polygon(surface, (255, 255, 255, 255), polygon)
        mask = pg.mask.from_surface(surface)
        points: Set[Point] = set()
        for y in range(state.canvas.height):
            for x in range(state.canvas.width):
                if mask.get_at((x, y)):
                    points.add((x, y))
        state.set_selection(Selection(points))
        self.reset()


    def draw_overlay(
        self,
        surface: pg.Surface,
        state: AppState,
        canvas_rect: pg.Rect,
        pixel_size: int,
    ) -> None:
        if not self.path:
            return
        overlay = pg.Surface(canvas_rect.size, pg.SRCALPHA)
        for px, py in self.path:
            rect = pg.Rect(
                (px * pixel_size, py * pixel_size),
                (pixel_size, pixel_size),
            )
            pg.draw.rect(overlay, PREVIEW_COLOR, rect)
        surface.blit(overlay, canvas_rect.topleft)




class ZoomTool(Tool):
    name = "zoom"


    def on_mouse_down(
        self,
        state: AppState,
        cell: Optional[Point],
        button: int,
        mouse_pos: Tuple[int, int],
        window_size: Tuple[int, int],
    ) -> None:
        if cell is None:
            return
        if button == 1:
            state.adjust_zoom(state.zoom_index + 1, cell, window_size)
            state.set_status("Zoom in")
        elif button == 3:
            state.adjust_zoom(state.zoom_index - 1, cell, window_size)
            state.set_status("Zoom out")




class DitherTool(PenTool):
    name = "dither"


    def _draw_points(self, state: AppState, points: Iterable[Point], color: Color) -> None:
        for px, py in points:
            use_primary = (px + py) % 2 == 0
            color_choice = state.primary_color if use_primary else state.secondary_color
            state.apply_brush((px, py), color_choice)




class ColorPickerTool(Tool):
    name = "picker"


    def on_mouse_down(
        self,
        state: AppState,
        cell: Optional[Point],
        button: int,
        mouse_pos: Tuple[int, int],
        window_size: Tuple[int, int],
    ) -> None:
        if cell is None:
            return
        color = state.canvas.sample_color(*cell)
        if button == 1:
            state.primary_color = color
            state.set_status("Primary color sampled")
        elif button == 3:
            state.secondary_color = color
            state.set_status("Secondary color sampled")




class ToolManager:
    def __init__(self) -> None:
        self.tools: Dict[str, Tool] = {
            "pen": PenTool(),
            "mirror_pen": MirrorPenTool(),
            "bucket": BucketTool(),
            "fill_all": FillAllTool(),
            "eraser": EraserTool(),
            "stroke": StrokeTool(),
            "rectangle": RectangleTool(),
            "ellipse": EllipseTool(),
            "move": MoveTool(),
            "color_replace": ColorReplaceTool(),
            "rect_select": RectSelectTool(),
            "lasso_select": LassoSelectTool(),
            "zoom": ZoomTool(),
            "dither": DitherTool(),
            "picker": ColorPickerTool(),
        }
        self.active: Tool = self.tools["pen"]
        self.active_name = "pen"


    def select(self, name: str, state: AppState) -> None:
        if name not in self.tools:
            return
        if self.active_name == name:
            return
        self.active.reset()
        self.active = self.tools[name]
        self.active_name = name
        self.active.on_select(state)
        state.set_status(f"Selected tool: {TOOL_LABELS.get(name, name)}")


@dataclass
class Button:
    name: str
    rect: pg.Rect
    label: str




@dataclass
class FrameEntry:
    index: int
    rect: pg.Rect




class FramesPanelUI:
    ENTRY_HEIGHT = 88
    ENTRY_GAP = 12
    BUTTON_GAP = 8
    BUTTON_HEIGHT = 30
    MARGIN = 16


    def __init__(self, height: int) -> None:
        self.rect = pg.Rect(0, 0, FRAMES_PANEL_WIDTH, height)
        self.frame_entries: List[FrameEntry] = []
        self.control_buttons: List[Button] = []
        self.animation_buttons: List[Button] = []
        self.add_button_rect = pg.Rect(0, 0, 0, 0)
        self.title_pos = (0, 0)
        self.dragging_frame: Optional[int] = None
        self.drag_offset_y = 0
        self.scroll_offset = 0
        self.max_scroll = 0
        self.scrollbar_rect = pg.Rect(0, 0, 0, 0)
        self.scrollbar_handle_rect = pg.Rect(0, 0, 0, 0)
        self.dragging_scrollbar = False
        self.scrollbar_drag_start_y = 0
        self.scrollbar_drag_start_offset = 0
        self.fps_slider_rect = pg.Rect(0, 0, 0, 0)
        self.fps_slider_handle_rect = pg.Rect(0, 0, 0, 0)
        self.dragging_fps_slider = False
        self.resize(height)


    def resize(self, height: int) -> None:
        self.rect.height = height


    def _layout(self, state: AppState) -> Tuple[List[FrameEntry], List[Button], List[Button], pg.Rect, Tuple[int, int], pg.Rect, pg.Rect]:
        margin = self.MARGIN
        content_left = self.rect.left + margin
        width = self.rect.width - margin * 2 - 16  # Extra space for scrollbar
        title_pos = (content_left, self.rect.top + margin)
        add_rect = pg.Rect(content_left, title_pos[1] + 28, width, 32)
        
        # Calculate the scrollable area
        list_start_y = add_rect.bottom + margin
        animation_buttons_y = list_start_y
        animation_buttons_height = 28
        fps_slider_y = animation_buttons_y + animation_buttons_height + 10
        fps_slider_height = 16
        animation_controls_y = fps_slider_y + fps_slider_height + 18
        controls_y = self.rect.bottom - STATUS_BAR_HEIGHT - 20 - self.BUTTON_HEIGHT
        available_height = controls_y - animation_controls_y - margin
        
        # Build entries with scroll offset
        list_y = animation_controls_y - self.scroll_offset
        entries: List[FrameEntry] = []
        for idx, _ in state.frame_stack.frames_for_display():
            rect = pg.Rect(content_left, list_y, width, self.ENTRY_HEIGHT)
            entries.append(FrameEntry(index=idx, rect=rect))
            list_y += self.ENTRY_HEIGHT + self.ENTRY_GAP
        
        # Calculate total content height and max scroll
        total_content_height = len(entries) * (self.ENTRY_HEIGHT + self.ENTRY_GAP)
        self.max_scroll = max(0, total_content_height - available_height)
        self.scroll_offset = int(clamp(self.scroll_offset, 0, self.max_scroll))
        
        # Update scrollbar dimensions
        scrollbar_width = 8
        scrollbar_x = self.rect.right - margin - scrollbar_width
        scrollbar_y = animation_controls_y
        scrollbar_height = available_height
        self.scrollbar_rect = pg.Rect(scrollbar_x, scrollbar_y, scrollbar_width, scrollbar_height)
        
        if self.max_scroll > 0:
            handle_height = max(20, int(scrollbar_height * (available_height / total_content_height)))
            handle_y = scrollbar_y + int((scrollbar_height - handle_height) * (self.scroll_offset / self.max_scroll))
            self.scrollbar_handle_rect = pg.Rect(scrollbar_x, handle_y, scrollbar_width, handle_height)
        else:
            self.scrollbar_handle_rect = pg.Rect(0, 0, 0, 0)
        
        # Animation controls (play/pause buttons)
        animation_button_width = max(50, width // 3 - 4)
        animation_buttons: List[Button] = []
        for idx, (name, label) in enumerate([("play", "Play"), ("pause", "Pause"), ("stop", "Stop")]):
            rect = pg.Rect(
                content_left + idx * (animation_button_width + 6),
                animation_buttons_y,
                animation_button_width,
                28,
            )
            animation_buttons.append(Button(name=name, rect=rect, label=label))
        
        # FPS slider
        fps_label_width = 60
        fps_slider_width = max(40, width - fps_label_width - 8)
        self.fps_slider_rect = pg.Rect(content_left, fps_slider_y, fps_slider_width, fps_slider_height)
        fps_handle_x = content_left + int((state.animation_player.fps - 1) / 59 * fps_slider_width)
        self.fps_slider_handle_rect = pg.Rect(fps_handle_x - 4, fps_slider_y - 2, 8, fps_slider_height + 4)
        
        # Frame control buttons
        button_width = max(48, (width - self.BUTTON_GAP) // 2)
        control_buttons: List[Button] = []
        for idx, (name, label) in enumerate([("dup", "Dup"), ("del", "Del")]):
            rect = pg.Rect(
                content_left + idx * (button_width + self.BUTTON_GAP),
                controls_y,
                button_width,
                self.BUTTON_HEIGHT,
            )
            control_buttons.append(Button(name=name, rect=rect, label=label))
        return entries, control_buttons, animation_buttons, add_rect, title_pos, self.fps_slider_rect, self.fps_slider_handle_rect


    def _draw_preview(self, surface: pg.Surface, rect: pg.Rect, canvas: PixelCanvas) -> None:
        preview_rect = rect.inflate(-40, -34)  # Give more space on left for frame number
        preview_rect.height = max(40, preview_rect.height)
        preview_rect.left = rect.left + 30  # Ensure space for frame number
        pg.draw.rect(surface, SIDEBAR_BG, preview_rect, border_radius=6)
        if canvas.width == 0 or canvas.height == 0:
            pg.draw.rect(surface, CANVAS_BORDER, preview_rect, width=1, border_radius=6)
            return
        scale = min(
            (preview_rect.width - 4) / canvas.width,
            (preview_rect.height - 4) / canvas.height,
        )
        scale = max(scale, 1 / max(canvas.width, canvas.height))
        scaled_size = (
            max(1, int(canvas.width * scale)),
            max(1, int(canvas.height * scale)),
        )
        checker = pg.transform.scale(canvas.checker, scaled_size)
        composite = canvas.composite_surface()
        pixels = pg.transform.scale(composite, scaled_size)
        offset = (
            preview_rect.left + (preview_rect.width - scaled_size[0]) // 2,
            preview_rect.top + (preview_rect.height - scaled_size[1]) // 2,
        )
        surface.blit(checker, offset)
        surface.blit(pixels, offset)
        pg.draw.rect(surface, CANVAS_BORDER, preview_rect, width=1, border_radius=6)


    def render(self, surface: pg.Surface, fonts: Dict[str, pg.font.Font], state: AppState) -> None:
        pg.draw.rect(surface, SIDEBAR_BG, self.rect)
        # Draw separator line on the right edge
        pg.draw.line(surface, CANVAS_BORDER, (self.rect.right - 1, self.rect.top), (self.rect.right - 1, self.rect.bottom), width=2)
        entries, controls, animation_buttons, add_rect, title_pos, fps_slider_rect, fps_handle_rect = self._layout(state)
        title_font = fonts["title"]
        label_font = fonts["label"]
        small_font = fonts["small"]
        surface.blit(title_font.render("Frames", True, SIDEBAR_TEXT), title_pos)
        add_text = label_font.render("+ Add Frame", True, SIDEBAR_TEXT)
        pg.draw.rect(surface, SIDEBAR_ACCENT, add_rect, border_radius=8)
        surface.blit(add_text, add_text.get_rect(center=add_rect.center))
        
        # Draw animation controls
        for button in animation_buttons:
            color = SIDEBAR_ACCENT if (
                (button.name == "play" and not state.animation_player.playing) or
                (button.name == "pause" and state.animation_player.playing)
            ) else CANVAS_BORDER
            pg.draw.rect(surface, color, button.rect, border_radius=4)
            # Use smaller font for animation buttons
            text_surface = small_font.render(button.label, True, SIDEBAR_TEXT)
            surface.blit(text_surface, text_surface.get_rect(center=button.rect.center))
        
        # Draw FPS slider
        pg.draw.rect(surface, CANVAS_BORDER, fps_slider_rect, border_radius=8)
        pg.draw.rect(surface, SIDEBAR_ACCENT, fps_handle_rect, border_radius=4)
        fps_text = small_font.render(f"{state.animation_player.fps} FPS", True, SIDEBAR_MUTED)
        surface.blit(
            fps_text,
            (
                fps_slider_rect.right + 8,
                fps_slider_rect.centery - fps_text.get_height() // 2,
            ),
        )
        
        # Create clipping rect for scrollable frame entries
        list_top = fps_slider_rect.bottom + 18
        clip_rect = pg.Rect(
            self.rect.left,
            list_top,
            self.rect.width,
            self.control_buttons[0].rect.top - list_top if self.control_buttons else self.rect.bottom - list_top
        )
        original_clip = surface.get_clip()
        surface.set_clip(clip_rect)
        
        for entry in entries:
            frame = state.frame_stack.frames[entry.index]
            rect = entry.rect
            # Only draw if visible in clip area
            if rect.bottom < clip_rect.top or rect.top > clip_rect.bottom:
                continue
            is_active = entry.index == state.frame_index
            is_dragging = entry.index == self.dragging_frame
            # Slightly transparent if dragging
            if is_dragging:
                pg.draw.rect(surface, SIDEBAR_BG, rect, border_radius=10)
                pg.draw.rect(surface, SIDEBAR_ACCENT, rect, width=3, border_radius=10)
            else:
                pg.draw.rect(surface, SIDEBAR_BG, rect, border_radius=10)
                border_color = SIDEBAR_ACCENT if is_active else CANVAS_BORDER
                pg.draw.rect(surface, border_color, rect, width=2, border_radius=10)
            index_label = small_font.render(str(entry.index + 1), True, SIDEBAR_TEXT)
            surface.blit(index_label, (rect.left + 8, rect.top + 6))
            self._draw_preview(surface, rect, frame.canvas)
        
        # Restore original clip
        surface.set_clip(original_clip)
        
        # Draw scrollbar if needed
        if self.max_scroll > 0:
            pg.draw.rect(surface, CANVAS_BORDER, self.scrollbar_rect, border_radius=4)
            pg.draw.rect(surface, SIDEBAR_ACCENT, self.scrollbar_handle_rect, border_radius=4)
        
        for button in controls:
            pg.draw.rect(surface, CANVAS_BORDER, button.rect, border_radius=6)
            text_surface = label_font.render(button.label, True, SIDEBAR_TEXT)
            surface.blit(text_surface, text_surface.get_rect(center=button.rect.center))
        self.frame_entries = entries
        self.control_buttons = controls
        self.animation_buttons = animation_buttons
        self.add_button_rect = add_rect
        self.title_pos = title_pos


    def handle_mouse_down(self, state: AppState, pos: Tuple[int, int], button: int, window_size: Tuple[int, int]) -> bool:
        if not self.rect.collidepoint(pos):
            return False
        entries, controls, animation_buttons, add_rect, _, fps_slider_rect, fps_handle_rect = self._layout(state)
        if button == 1:
            # Check animation buttons
            for btn in animation_buttons:
                if btn.rect.collidepoint(pos):
                    if btn.name == "play":
                        state.animation_player.play()
                        state.set_status("Playing animation")
                    elif btn.name == "pause":
                        state.animation_player.pause()
                        state.set_status("Animation paused")
                    elif btn.name == "stop":
                        state.animation_player.reset()
                        state.set_status("Animation stopped")
                    return True
            
            # Check FPS slider
            if self.fps_slider_handle_rect.collidepoint(pos):
                self.dragging_fps_slider = True
                return True
            elif self.fps_slider_rect.collidepoint(pos):
                # Jump to position on slider
                relative_x = pos[0] - self.fps_slider_rect.left
                ratio = clamp(relative_x / self.fps_slider_rect.width, 0, 1)
                new_fps = int(1 + ratio * 59)  # 1-60 FPS
                state.animation_player.set_fps(new_fps)
                state.set_status(f"Animation FPS: {new_fps}")
                return True
            
            # Check scrollbar handle click
            if self.scrollbar_handle_rect.collidepoint(pos):
                self.dragging_scrollbar = True
                self.scrollbar_drag_start_y = pos[1]
                self.scrollbar_drag_start_offset = self.scroll_offset
                return True
            
            # Check scrollbar track click (jump to position)
            if self.scrollbar_rect.collidepoint(pos) and self.max_scroll > 0:
                # Calculate target scroll position
                relative_y = pos[1] - self.scrollbar_rect.top
                scroll_ratio = relative_y / self.scrollbar_rect.height
                self.scroll_offset = int(scroll_ratio * self.max_scroll)
                return True
            
            for entry in entries:
                if entry.rect.collidepoint(pos):
                    # Start dragging
                    self.dragging_frame = entry.index
                    self.drag_offset_y = pos[1] - entry.rect.top
                    state.select_frame(entry.index, window_size)
                    return True
            for ctrl in controls:
                if ctrl.rect.collidepoint(pos):
                    if ctrl.name == "dup":
                        state.duplicate_frame(window_size)
                    elif ctrl.name == "del":
                        state.delete_frame(window_size)
                    return True
            if add_rect.collidepoint(pos):
                state.add_blank_frame(window_size)
                return True
        return True


    def handle_mouse_up(self, state: AppState) -> None:
        self.dragging_frame = None
        self.drag_offset_y = 0
        self.dragging_scrollbar = False
        self.dragging_fps_slider = False


    def handle_mouse_move(self, state: AppState, pos: Tuple[int, int], window_size: Tuple[int, int]) -> None:
        # Handle FPS slider dragging
        if self.dragging_fps_slider:
            relative_x = pos[0] - self.fps_slider_rect.left
            ratio = clamp(relative_x / self.fps_slider_rect.width, 0, 1)
            new_fps = int(1 + ratio * 59)  # 1-60 FPS
            state.animation_player.set_fps(new_fps)
            return
        
        # Handle scrollbar dragging
        if self.dragging_scrollbar:
            if self.max_scroll > 0:
                delta_y = pos[1] - self.scrollbar_drag_start_y
                scroll_range = self.scrollbar_rect.height - self.scrollbar_handle_rect.height
                if scroll_range > 0:
                    scroll_delta = (delta_y / scroll_range) * self.max_scroll
                    self.scroll_offset = int(clamp(self.scrollbar_drag_start_offset + scroll_delta, 0, self.max_scroll))
            return
        
        if self.dragging_frame is None:
            return
        entries, _, _, _, _, fps_slider_rect, fps_handle_rect = self._layout(state)
        drag_center_y = pos[1] - self.drag_offset_y + self.ENTRY_HEIGHT // 2
        # Find which frame position we're hovering over
        for entry in entries:
            if entry.rect.top <= drag_center_y < entry.rect.bottom:
                if entry.index != self.dragging_frame:
                    # Swap frames
                    frames = state.frame_stack.frames
                    frames[self.dragging_frame], frames[entry.index] = frames[entry.index], frames[self.dragging_frame]
                    if state.frame_stack.active_index == self.dragging_frame:
                        state.frame_stack.active_index = entry.index
                    elif state.frame_stack.active_index == entry.index:
                        state.frame_stack.active_index = self.dragging_frame
                    self.dragging_frame = entry.index
                    state.frame_stack._relabel()
                    state.set_status(f"Moved frame to position {entry.index + 1}")
                break




 


class PaletteEditorUI:
    """Piskel-style palette editor modal with full color editing capabilities."""
    def __init__(self) -> None:
        self.active = False
        self.palette: Optional[Palette] = None
        self.dialog_rect = pg.Rect(0, 0, 650, 700)
        self.palette_name_input = ""
        self.palette_name_cursor_pos = 0
        self.palette_name_cursor_blink_time = 0
        self.editing_name = False
        self.name_input_rect = pg.Rect(0, 0, 0, 0)
        
        # Color grid
        self.color_cells: List[Tuple[pg.Rect, int]] = []  # (rect, color_index)
        self.add_color_rect = pg.Rect(0, 0, 0, 0)
        self.selected_color_index: Optional[int] = None
        self.scroll_offset = 0
        self.max_scroll = 0
        
        # Color picker area (right side)
        self.hue_sat_rect = pg.Rect(0, 0, 0, 0)
        self.hue_slider_rect = pg.Rect(0, 0, 0, 0)
        self.hex_input_rect = pg.Rect(0, 0, 0, 0)
        self.hex_input_text = ""
        self.hex_cursor_pos = 0
        self.hex_input_active = False
        
        # RGB/HSV sliders
        self.r_slider_rect = pg.Rect(0, 0, 0, 0)
        self.g_slider_rect = pg.Rect(0, 0, 0, 0)
        self.b_slider_rect = pg.Rect(0, 0, 0, 0)
        self.h_slider_rect = pg.Rect(0, 0, 0, 0)
        self.s_slider_rect = pg.Rect(0, 0, 0, 0)
        self.v_slider_rect = pg.Rect(0, 0, 0, 0)
        
        # Current editing color
        self.edit_color = (0, 0, 0, 255)
        self.dragging_slider: Optional[str] = None
        self.dragging_hue_sat = False
        self.dragging_hue_slider = False
        
        # Buttons
        self.Save_button_rect = pg.Rect(0, 0, 0, 0)
        self.delete_button_rect = pg.Rect(0, 0, 0, 0)
        self.cancel_button_rect = pg.Rect(0, 0, 0, 0)
        self.save_button_rect = pg.Rect(0, 0, 0, 0)
        
        # Save feedback
        self.save_feedback_timer = 0  # Frames to show "Saved!" message
        self.Save_button_pressed = False  # For button press animation
        
        # Preview
        self.preview_rect = pg.Rect(0, 0, 0, 0)
    
    def open(self, palette: Palette, window_size: Tuple[int, int]) -> None:
        """Open the palette editor."""
        self.active = True
        self.palette = palette
        self.palette_name_input = palette.name
        self.palette_name_cursor_pos = len(self.palette_name_input)
        self.editing_name = False
        self.selected_color_index = None
        self.scroll_offset = 0
        
        # Center dialog
        self.dialog_rect.center = (window_size[0] // 2, window_size[1] // 2)
        self._layout_elements()
    
    def _layout_elements(self) -> None:
        """Layout all UI elements."""
        margin = 20
        
        # Title and name input at top
        self.name_input_rect = pg.Rect(
            self.dialog_rect.left + 200,
            self.dialog_rect.top + 20,
            200, 40
        )
        
        # Save button next to name
        self.Save_button_rect = pg.Rect(
            self.name_input_rect.right + 10,
            self.dialog_rect.top + 20,
            140, 40
        )
        
        # Left side: color grid (palette colors)
        grid_left = self.dialog_rect.left + margin
        grid_top = self.name_input_rect.bottom + 20
        grid_width = 280
        grid_height = self.dialog_rect.height - (grid_top - self.dialog_rect.top) - 80
        
        cell_size = 40
        cell_gap = 4
        cols = 6
        
        self.color_cells = []
        if self.palette:
            x = grid_left
            y = grid_top - self.scroll_offset
            for idx in range(len(self.palette.colors)):
                rect = pg.Rect(x, y, cell_size, cell_size)
                self.color_cells.append((rect, idx))
                x += cell_size + cell_gap
                if (idx + 1) % cols == 0:
                    x = grid_left
                    y += cell_size + cell_gap
            
            # Add color button
            self.add_color_rect = pg.Rect(x, y, cell_size, cell_size)
        
        # Right side: color picker
        picker_left = grid_left + grid_width + 30
        picker_top = grid_top
        
        # Hue/Sat picker (2D)
        hs_size = 200
        self.hue_sat_rect = pg.Rect(picker_left, picker_top, hs_size, hs_size)
        
        # Hue slider (vertical)
        self.hue_slider_rect = pg.Rect(
            self.hue_sat_rect.right + 10,
            picker_top,
            20, hs_size
        )
        
        # Hex input
        self.hex_input_rect = pg.Rect(
            picker_left,
            self.hue_sat_rect.bottom + 10,
            100, 28
        )
        
        # RGB sliders
        slider_width = 140
        slider_height = 20
        slider_top = self.hex_input_rect.bottom + 20
        label_width = 20
        
        self.h_slider_rect = pg.Rect(picker_left + label_width, slider_top, slider_width, slider_height)
        self.s_slider_rect = pg.Rect(picker_left + label_width, slider_top + 30, slider_width, slider_height)
        self.v_slider_rect = pg.Rect(picker_left + label_width, slider_top + 60, slider_width, slider_height)
        self.r_slider_rect = pg.Rect(picker_left + label_width, slider_top + 100, slider_width, slider_height)
        self.g_slider_rect = pg.Rect(picker_left + label_width, slider_top + 130, slider_width, slider_height)
        self.b_slider_rect = pg.Rect(picker_left + label_width, slider_top + 160, slider_width, slider_height)
        
        # Bottom buttons (define first to calculate available space)
        button_width = 100
        button_height = 36
        button_y = self.dialog_rect.bottom - margin - button_height
        button_gap = 10
        
        # Preview box (ensure it doesn't overlap with buttons)
        available_height = button_y - (self.b_slider_rect.bottom + 20) - 10
        preview_height = min(60, max(40, available_height))
        self.preview_rect = pg.Rect(
            picker_left,
            self.b_slider_rect.bottom + 15,
            180, preview_height
        )
        
        self.cancel_button_rect = pg.Rect(
            self.dialog_rect.right - margin - button_width * 3 - button_gap * 2,
            button_y, button_width, button_height
        )
        self.delete_button_rect = pg.Rect(
            self.cancel_button_rect.right + button_gap,
            button_y, button_width, button_height
        )
        self.save_button_rect = pg.Rect(
            self.delete_button_rect.right + button_gap,
            button_y, button_width, button_height
        )
    
    def close(self) -> None:
        """Close the palette editor."""
        self.active = False
        self.palette = None
        self.selected_color_index = None
    
    def _select_color(self, index: int) -> None:
        """Select a color for editing."""
        if self.palette and 0 <= index < len(self.palette.colors):
            self.selected_color_index = index
            self.edit_color = self.palette.colors[index]
            self.hex_input_text = self._color_to_hex(self.edit_color)
            self.hex_cursor_pos = len(self.hex_input_text)
    
    def _color_to_hex(self, color: Color) -> str:
        """Convert color to hex string."""
        return f"{color[0]:02X}{color[1]:02X}{color[2]:02X}"
    
    def _hex_to_color(self, hex_str: str) -> Optional[Color]:
        """Convert hex string to color."""
        try:
            if len(hex_str) == 6:
                r = int(hex_str[0:2], 16)
                g = int(hex_str[2:4], 16)
                b = int(hex_str[4:6], 16)
                return (r, g, b, 255)
        except ValueError:
            pass
        return None
    
    def _rgb_to_hsv(self, r: int, g: int, b: int) -> Tuple[float, float, float]:
        """Convert RGB to HSV. H in [0, 360), S and V in [0, 1]."""
        r, g, b = r / 255.0, g / 255.0, b / 255.0
        max_c = max(r, g, b)
        min_c = min(r, g, b)
        diff = max_c - min_c
        
        if diff == 0:
            h = 0
        elif max_c == r:
            h = (60 * ((g - b) / diff) + 360) % 360
        elif max_c == g:
            h = (60 * ((b - r) / diff) + 120) % 360
        else:
            h = (60 * ((r - g) / diff) + 240) % 360
        
        s = 0 if max_c == 0 else (diff / max_c)
        v = max_c
        return h, s, v
    
    def _hsv_to_rgb(self, h: float, s: float, v: float) -> Tuple[int, int, int]:
        """Convert HSV to RGB. H in [0, 360), S and V in [0, 1]."""
        c = v * s
        x = c * (1 - abs((h / 60) % 2 - 1))
        m = v - c
        
        if h < 60:
            r, g, b = c, x, 0
        elif h < 120:
            r, g, b = x, c, 0
        elif h < 180:
            r, g, b = 0, c, x
        elif h < 240:
            r, g, b = 0, x, c
        elif h < 300:
            r, g, b = x, 0, c
        else:
            r, g, b = c, 0, x
        
        return (int((r + m) * 255), int((g + m) * 255), int((b + m) * 255))
    
    def render(self, surface: pg.Surface, fonts: Dict[str, pg.font.Font]) -> None:
        """Render the palette editor."""
        if not self.active or not self.palette:
            return
        
        # Semi-transparent overlay
        overlay = pg.Surface(surface.get_size(), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))
        
        # Dialog background
        pg.draw.rect(surface, (45, 48, 54), self.dialog_rect, border_radius=10)
        pg.draw.rect(surface, SIDEBAR_ACCENT, self.dialog_rect, width=2, border_radius=10)
        
        # Title and name input
        title_font = fonts.get("title", fonts["label"])
        label_font = fonts["label"]
        small_font = fonts["small"]
        
        title = title_font.render("Edit Palette", True, SIDEBAR_TEXT)
        surface.blit(title, (self.dialog_rect.left + 20, self.dialog_rect.top + 25))
        
        # Name input field
        pg.draw.rect(surface, STATUS_BG, self.name_input_rect, border_radius=4)
        pg.draw.rect(surface, SIDEBAR_ACCENT if self.editing_name else CANVAS_BORDER, self.name_input_rect, width=2, border_radius=4)
        name_text = label_font.render(self.palette_name_input, True, SIDEBAR_TEXT)
        surface.blit(name_text, (self.name_input_rect.left + 5, self.name_input_rect.centery - name_text.get_height() // 2))
        
        # Draw cursor if editing name
        if self.editing_name:
            self.palette_name_cursor_blink_time += 1
            if self.palette_name_cursor_blink_time % 60 < 30:  # Blink every 0.5 seconds at 60 FPS
                cursor_text = self.palette_name_input[:self.palette_name_cursor_pos]
                cursor_x = self.name_input_rect.left + 5 + label_font.size(cursor_text)[0]
                cursor_y_top = self.name_input_rect.centery - name_text.get_height() // 2
                cursor_y_bottom = cursor_y_top + name_text.get_height()
                pg.draw.line(surface, SIDEBAR_TEXT, (cursor_x, cursor_y_top), (cursor_x, cursor_y_bottom), 2)
        
        # Save to file button
        # Button press animation - offset button slightly when pressed
        button_rect = self.Save_button_rect.copy()
        if self.Save_button_pressed and self.save_feedback_timer > 170:  # First 10 frames
            button_rect.y += 2
        
        pg.draw.rect(surface, CANVAS_BORDER, button_rect, border_radius=4)
        Save_text = small_font.render("Save to file", True, SIDEBAR_TEXT)
        surface.blit(Save_text, Save_text.get_rect(center=button_rect.center))
        
        # Show "Saved!" message next to button
        if self.save_feedback_timer > 0:
            self.save_feedback_timer -= 1
            # Fade out effect in the last 60 frames
            alpha = min(255, int((self.save_feedback_timer / 60) * 255)) if self.save_feedback_timer < 60 else 255
            saved_text = label_font.render("✓ Saved!", True, (100, 255, 100))
            saved_surf = pg.Surface((saved_text.get_width(), saved_text.get_height()), pg.SRCALPHA)
            saved_surf.fill((0, 0, 0, 0))
            saved_text.set_alpha(alpha)
            saved_surf.blit(saved_text, (0, 0))
            surface.blit(saved_surf, (button_rect.right + 10, button_rect.centery - saved_text.get_height() // 2))
            
            # Reset button press state after animation
            if self.save_feedback_timer == 170:
                self.Save_button_pressed = False
        
        # Color grid
        for rect, color_idx in self.color_cells:
            if rect.bottom < self.dialog_rect.top or rect.top > self.dialog_rect.bottom:
                continue
            color = self.palette.colors[color_idx]
            pg.draw.rect(surface, color[:3], rect)
            border_color = SIDEBAR_ACCENT if color_idx == self.selected_color_index else CANVAS_BORDER
            pg.draw.rect(surface, border_color, rect, width=2 if color_idx == self.selected_color_index else 1)
            # Number label
            num_text = small_font.render(str(color_idx + 1), True, (255, 255, 255) if sum(color[:3]) < 384 else (0, 0, 0))
            surface.blit(num_text, (rect.left + 2, rect.top + 2))
        
        # Add color button
        pg.draw.rect(surface, STATUS_BG, self.add_color_rect)
        pg.draw.rect(surface, SIDEBAR_ACCENT, self.add_color_rect, width=2, border_radius=5)
        plus_text = title_font.render("+", True, SIDEBAR_ACCENT)
        surface.blit(plus_text, plus_text.get_rect(center=self.add_color_rect.center))
        
        # Right side: Color picker (if color selected)
        if self.selected_color_index is not None:
            # Hue/Sat gradient
            self._render_hue_sat_picker(surface)
            
            # Hue slider
            self._render_hue_slider(surface)
            
            # Hex input
            pg.draw.rect(surface, STATUS_BG, self.hex_input_rect, border_radius=3)
            pg.draw.rect(surface, SIDEBAR_ACCENT if self.hex_input_active else CANVAS_BORDER, self.hex_input_rect, width=2, border_radius=3)
            hex_label = small_font.render("#", True, SIDEBAR_TEXT)
            surface.blit(hex_label, (self.hex_input_rect.left - 12, self.hex_input_rect.centery - hex_label.get_height() // 2))
            hex_text = label_font.render(self.hex_input_text, True, SIDEBAR_TEXT)
            surface.blit(hex_text, (self.hex_input_rect.left + 5, self.hex_input_rect.centery - hex_text.get_height() // 2))
            
            # Sliders
            self._render_sliders(surface, fonts)
            
            # Preview
            pg.draw.rect(surface, self.edit_color[:3], self.preview_rect)
            pg.draw.rect(surface, CANVAS_BORDER, self.preview_rect, width=2)
        
        # Bottom buttons
        pg.draw.rect(surface, (100, 100, 100), self.cancel_button_rect, border_radius=4)
        cancel_text = label_font.render("Cancel", True, SIDEBAR_TEXT)
        surface.blit(cancel_text, cancel_text.get_rect(center=self.cancel_button_rect.center))
        
        pg.draw.rect(surface, (180, 50, 50), self.delete_button_rect, border_radius=4)
        delete_text = label_font.render("Delete", True, SIDEBAR_TEXT)
        surface.blit(delete_text, delete_text.get_rect(center=self.delete_button_rect.center))
        
        pg.draw.rect(surface, (80, 180, 80), self.save_button_rect, border_radius=4)
        save_text = label_font.render("Save", True, SIDEBAR_TEXT)
        surface.blit(save_text, save_text.get_rect(center=self.save_button_rect.center))
    
    def _render_hue_sat_picker(self, surface: pg.Surface) -> None:
        """Render the 2D hue/saturation picker."""
        if not hasattr(self, '_hs_surface') or self._hs_surface.get_size() != self.hue_sat_rect.size:
            self._hs_surface = pg.Surface(self.hue_sat_rect.size)
            h, s, v = self._rgb_to_hsv(*self.edit_color[:3])
            for y in range(self.hue_sat_rect.height):
                for x in range(self.hue_sat_rect.width):
                    s_val = x / self.hue_sat_rect.width
                    v_val = 1 - (y / self.hue_sat_rect.height)
                    rgb = self._hsv_to_rgb(h, s_val, v_val)
                    self._hs_surface.set_at((x, y), rgb)
        
        surface.blit(self._hs_surface, self.hue_sat_rect)
        pg.draw.rect(surface, CANVAS_BORDER, self.hue_sat_rect, width=2)
    
    def _render_hue_slider(self, surface: pg.Surface) -> None:
        """Render the vertical hue slider."""
        for y in range(self.hue_slider_rect.height):
            hue = (y / self.hue_slider_rect.height) * 360
            rgb = self._hsv_to_rgb(hue, 1.0, 1.0)
            pg.draw.line(surface, rgb, 
                        (self.hue_slider_rect.left, self.hue_slider_rect.top + y),
                        (self.hue_slider_rect.right, self.hue_slider_rect.top + y))
        pg.draw.rect(surface, CANVAS_BORDER, self.hue_slider_rect, width=2)
    
    def _render_sliders(self, surface: pg.Surface, fonts: Dict[str, pg.font.Font]) -> None:
        """Render RGB and HSV sliders."""
        small_font = fonts["small"]
        h, s, v = self._rgb_to_hsv(*self.edit_color[:3])
        r, g, b = self.edit_color[:3]
        
        sliders = [
            ("H", self.h_slider_rect, h / 360, (94, 172, 248)),
            ("S", self.s_slider_rect, s, (94, 172, 248)),
            ("V", self.v_slider_rect, v, (94, 172, 248)),
            ("R", self.r_slider_rect, r / 255, (255, 100, 100)),
            ("G", self.g_slider_rect, g / 255, (100, 255, 100)),
            ("B", self.b_slider_rect, b / 255, (100, 100, 255)),
        ]
        
        for label, rect, value, color in sliders:
            # Background
            pg.draw.rect(surface, STATUS_BG, rect, border_radius=3)
            # Fill
            fill_rect = pg.Rect(rect.left, rect.top, int(rect.width * value), rect.height)
            pg.draw.rect(surface, color, fill_rect, border_radius=3)
            # Border
            pg.draw.rect(surface, CANVAS_BORDER, rect, width=1, border_radius=3)
            # Label
            label_text = small_font.render(label, True, SIDEBAR_TEXT)
            surface.blit(label_text, (rect.left - 18, rect.centery - label_text.get_height() // 2))
            # Value
            if label in ["R", "G", "B"]:
                val_text = small_font.render(str(int(value * 255)), True, SIDEBAR_TEXT)
            else:
                val_text = small_font.render(str(int(value * 100 if label != "H" else value * 360)), True, SIDEBAR_TEXT)
            surface.blit(val_text, (rect.right + 5, rect.centery - val_text.get_height() // 2))
    
    def handle_mouse_down(self, pos: Tuple[int, int], button: int, state: Optional['AppState'] = None) -> bool:
        """Handle mouse down events. Returns True if event was handled."""
        if not self.active or not self.palette:
            return False
        
        if button == 1:
            # Check buttons
            if self.cancel_button_rect.collidepoint(pos):
                self.close()
                return True
            
            if self.save_button_rect.collidepoint(pos):
                if self.palette_name_input.strip():
                    self.palette.name = self.palette_name_input.strip()
                self.close()
                return True
            
            if self.Save_button_rect.collidepoint(pos):
                # Export palette
                from pathlib import Path
                export_dir = Path("exports/palettes")
                export_dir.mkdir(parents=True, exist_ok=True)
                filename = f"{self.palette.name.replace(' ', '_')}.json"
                manager = PaletteManager()
                manager.save_palette(self.palette, export_dir / filename)
                if state:
                    state.set_status(f"Palette saved to {filename}")
                # Show feedback on the dialog
                self.save_feedback_timer = 180  # Show for 3 seconds at 60 FPS
                self.Save_button_pressed = True
                return True
            
            if self.delete_button_rect.collidepoint(pos) and self.selected_color_index is not None:
                # Delete selected color
                self.palette.remove_color(self.selected_color_index)
                self.selected_color_index = None
                self._layout_elements()
                return True
            
            # Check color cells
            for rect, color_idx in self.color_cells:
                if rect.collidepoint(pos):
                    self._select_color(color_idx)
                    return True
            
            # Add color button
            if self.add_color_rect.collidepoint(pos):
                self.palette.add_color((255, 255, 255, 255))
                self._layout_elements()
                self._select_color(len(self.palette.colors) - 1)
                return True
            
            # Name input
            if self.name_input_rect.collidepoint(pos):
                self.editing_name = True
                return True
            else:
                self.editing_name = False
            
            # Color picker interactions
            if self.selected_color_index is not None:
                if self.hue_sat_rect.collidepoint(pos):
                    self.dragging_hue_sat = True
                    self._update_from_hue_sat(pos)
                    return True
                
                if self.hue_slider_rect.collidepoint(pos):
                    self.dragging_hue_slider = True
                    self._update_from_hue_slider(pos)
                    return True
                
                # Check sliders
                for slider_name, slider_rect in [("h", self.h_slider_rect), ("s", self.s_slider_rect), 
                                                   ("v", self.v_slider_rect), ("r", self.r_slider_rect),
                                                   ("g", self.g_slider_rect), ("b", self.b_slider_rect)]:
                    if slider_rect.collidepoint(pos):
                        self.dragging_slider = slider_name
                        self._update_from_slider(slider_name, pos)
                        return True
                
                if self.hex_input_rect.collidepoint(pos):
                    self.hex_input_active = True
                    return True
        
        return False
    
    def handle_mouse_up(self) -> None:
        """Handle mouse up events."""
        self.dragging_slider = None
        self.dragging_hue_sat = False
        self.dragging_hue_slider = False
    
    def handle_mouse_move(self, pos: Tuple[int, int]) -> None:
        """Handle mouse move events."""
        if self.dragging_hue_sat:
            self._update_from_hue_sat(pos)
        elif self.dragging_hue_slider:
            self._update_from_hue_slider(pos)
        elif self.dragging_slider:
            self._update_from_slider(self.dragging_slider, pos)
    
    def handle_key_down(self, event: pg.event.Event) -> None:
        """Handle keyboard input for palette name and hex input editing."""
        # Handle palette name editing
        if self.editing_name:
            if event.key == pg.K_RETURN or event.key == pg.K_KP_ENTER:
                # Apply new name
                if self.palette_name_input.strip():
                    self.palette.name = self.palette_name_input.strip()
                self.editing_name = False
            elif event.key == pg.K_ESCAPE:
                # Cancel editing
                self.palette_name_input = self.palette.name
                self.editing_name = False
            elif event.key == pg.K_BACKSPACE:
                if self.palette_name_cursor_pos > 0:
                    self.palette_name_input = self.palette_name_input[:self.palette_name_cursor_pos-1] + self.palette_name_input[self.palette_name_cursor_pos:]
                    self.palette_name_cursor_pos -= 1
                    self.palette_name_cursor_blink_time = 0
            elif event.key == pg.K_LEFT:
                if self.palette_name_cursor_pos > 0:
                    self.palette_name_cursor_pos -= 1
                    self.palette_name_cursor_blink_time = 0
            elif event.key == pg.K_RIGHT:
                if self.palette_name_cursor_pos < len(self.palette_name_input):
                    self.palette_name_cursor_pos += 1
                    self.palette_name_cursor_blink_time = 0
            elif event.key == pg.K_HOME:
                self.palette_name_cursor_pos = 0
                self.palette_name_cursor_blink_time = 0
            elif event.key == pg.K_END:
                self.palette_name_cursor_pos = len(self.palette_name_input)
                self.palette_name_cursor_blink_time = 0
            elif event.key == pg.K_DELETE:
                if self.palette_name_cursor_pos < len(self.palette_name_input):
                    self.palette_name_input = self.palette_name_input[:self.palette_name_cursor_pos] + self.palette_name_input[self.palette_name_cursor_pos+1:]
                    self.palette_name_cursor_blink_time = 0
            else:
                # Add character if it's valid
                char = event.unicode
                if char and char.isprintable() and len(self.palette_name_input) < 30:
                    self.palette_name_input = self.palette_name_input[:self.palette_name_cursor_pos] + char + self.palette_name_input[self.palette_name_cursor_pos:]
                    self.palette_name_cursor_pos += 1
                    self.palette_name_cursor_blink_time = 0
            return
        
        # Handle hex input editing
        if self.hex_input_active:
            if event.key == pg.K_RETURN or event.key == pg.K_KP_ENTER:
                # Apply hex color
                new_color = self._hex_to_color(self.hex_input_text)
                if new_color and self.selected_color_index is not None:
                    self.edit_color = new_color
                    self.palette.colors[self.selected_color_index] = new_color
                self.hex_input_active = False
            elif event.key == pg.K_ESCAPE:
                # Cancel hex input
                if self.selected_color_index is not None:
                    self.hex_input_text = self._color_to_hex(self.edit_color)
                self.hex_input_active = False
            elif event.key == pg.K_BACKSPACE:
                if self.hex_cursor_pos > 0:
                    self.hex_input_text = self.hex_input_text[:self.hex_cursor_pos-1] + self.hex_input_text[self.hex_cursor_pos:]
                    self.hex_cursor_pos -= 1
            elif event.key == pg.K_LEFT:
                if self.hex_cursor_pos > 0:
                    self.hex_cursor_pos -= 1
            elif event.key == pg.K_RIGHT:
                if self.hex_cursor_pos < len(self.hex_input_text):
                    self.hex_cursor_pos += 1
            elif event.key == pg.K_HOME:
                self.hex_cursor_pos = 0
            elif event.key == pg.K_END:
                self.hex_cursor_pos = len(self.hex_input_text)
            elif event.key == pg.K_DELETE:
                if self.hex_cursor_pos < len(self.hex_input_text):
                    self.hex_input_text = self.hex_input_text[:self.hex_cursor_pos] + self.hex_input_text[self.hex_cursor_pos+1:]
            else:
                # Add character if it's a valid hex digit
                char = event.unicode.upper()
                if char in '0123456789ABCDEF' and len(self.hex_input_text) < 6:
                    self.hex_input_text = self.hex_input_text[:self.hex_cursor_pos] + char + self.hex_input_text[self.hex_cursor_pos:]
                    self.hex_cursor_pos += 1
    
    def _update_from_hue_sat(self, pos: Tuple[int, int]) -> None:
        """Update color from hue/sat picker position."""
        if not self.palette or self.selected_color_index is None:
            return
        
        rel_x = clamp(pos[0] - self.hue_sat_rect.left, 0, self.hue_sat_rect.width - 1)
        rel_y = clamp(pos[1] - self.hue_sat_rect.top, 0, self.hue_sat_rect.height - 1)
        
        s = rel_x / self.hue_sat_rect.width
        v = 1 - (rel_y / self.hue_sat_rect.height)
        h, _, _ = self._rgb_to_hsv(*self.edit_color[:3])
        
        rgb = self._hsv_to_rgb(h, s, v)
        self.edit_color = (*rgb, 255)
        self.palette.colors[self.selected_color_index] = self.edit_color
        self.hex_input_text = self._color_to_hex(self.edit_color)
    
    def _update_from_hue_slider(self, pos: Tuple[int, int]) -> None:
        """Update color from hue slider position."""
        if not self.palette or self.selected_color_index is None:
            return
        
        rel_y = clamp(pos[1] - self.hue_slider_rect.top, 0, self.hue_slider_rect.height - 1)
        h = (rel_y / self.hue_slider_rect.height) * 360
        _, s, v = self._rgb_to_hsv(*self.edit_color[:3])
        
        rgb = self._hsv_to_rgb(h, s, v)
        self.edit_color = (*rgb, 255)
        self.palette.colors[self.selected_color_index] = self.edit_color
        self.hex_input_text = self._color_to_hex(self.edit_color)
        # Regenerate hue/sat surface
        if hasattr(self, '_hs_surface'):
            delattr(self, '_hs_surface')
    
    def _update_from_slider(self, slider_name: str, pos: Tuple[int, int]) -> None:
        """Update color from slider position."""
        if not self.palette or self.selected_color_index is None:
            return
        
        slider_map = {
            "h": self.h_slider_rect, "s": self.s_slider_rect, "v": self.v_slider_rect,
            "r": self.r_slider_rect, "g": self.g_slider_rect, "b": self.b_slider_rect
        }
        
        rect = slider_map[slider_name]
        rel_x = clamp(pos[0] - rect.left, 0, rect.width - 1)
        value = rel_x / rect.width
        
        r, g, b = self.edit_color[:3]
        h, s, v = self._rgb_to_hsv(r, g, b)
        
        if slider_name == "h":
            h = value * 360
            rgb = self._hsv_to_rgb(h, s, v)
        elif slider_name == "s":
            s = value
            rgb = self._hsv_to_rgb(h, s, v)
        elif slider_name == "v":
            v = value
            rgb = self._hsv_to_rgb(h, s, v)
        elif slider_name == "r":
            rgb = (int(value * 255), g, b)
        elif slider_name == "g":
            rgb = (r, int(value * 255), b)
        elif slider_name == "b":
            rgb = (r, g, int(value * 255))
        else:
            return
        
        self.edit_color = (*rgb, 255)
        self.palette.colors[self.selected_color_index] = self.edit_color
        self.hex_input_text = self._color_to_hex(self.edit_color)


class ColorPicker:
    """An enhanced color picker dialog with RGB sliders, hex input, and palette integration."""
    def __init__(self) -> None:
        self.active = False
        self.color = (255, 255, 255, 255)
        self.dialog_rect = pg.Rect(0, 0, 450, 380)
        self.r_slider_rect = pg.Rect(0, 0, 0, 0)
        self.g_slider_rect = pg.Rect(0, 0, 0, 0)
        self.b_slider_rect = pg.Rect(0, 0, 0, 0)
        self.ok_button_rect = pg.Rect(0, 0, 0, 0)
        self.cancel_button_rect = pg.Rect(0, 0, 0, 0)
        self.add_to_palette_button_rect = pg.Rect(0, 0, 0, 0)
        self.preview_rect = pg.Rect(0, 0, 0, 0)
        self.hex_input_rect = pg.Rect(0, 0, 0, 0)
        self.dragging_slider: Optional[str] = None  # 'r', 'g', or 'b'
        self.hex_input_active = False
        self.hex_input_text = ""
        self.hex_cursor_pos = 0  # Cursor position in hex input
        self.hex_cursor_blink_time = 0  # Time tracker for cursor blinking
        self.add_to_palette_callback: Optional[callable] = None
    
    def open(self, color: Color, window_size: Tuple[int, int]) -> None:
        """Open the color picker with the given initial color."""
        self.active = True
        self.color = color
        self.hex_input_text = self._color_to_hex(color)
        self.hex_input_active = False
        self.hex_cursor_pos = len(self.hex_input_text)
        self.hex_cursor_blink_time = 0
        # Center the dialog
        self.dialog_rect.center = (window_size[0] // 2, window_size[1] // 2)
        
        # Layout elements
        margin = 20
        slider_height = 24
        slider_width = self.dialog_rect.width - margin * 2 - 120
        
        # Preview on left, hex input on right
        self.preview_rect = pg.Rect(self.dialog_rect.left + margin, self.dialog_rect.top + 50, 100, 80)
        self.hex_input_rect = pg.Rect(self.preview_rect.right + 15, self.dialog_rect.top + 50, 120, 32)
        
        # RGB sliders below preview
        start_y = self.preview_rect.bottom + 30
        label_width = 100
        self.r_slider_rect = pg.Rect(self.dialog_rect.left + margin + label_width, start_y, slider_width, slider_height)
        self.g_slider_rect = pg.Rect(self.dialog_rect.left + margin + label_width, start_y + 45, slider_width, slider_height)
        self.b_slider_rect = pg.Rect(self.dialog_rect.left + margin + label_width, start_y + 90, slider_width, slider_height)
        
        # Buttons at bottom
        button_width = 120
        button_height = 36
        button_y = self.dialog_rect.bottom - margin - button_height
        button_gap = 10
        
        self.add_to_palette_button_rect = pg.Rect(self.dialog_rect.left + margin, button_y, button_width, button_height)
        self.ok_button_rect = pg.Rect(self.dialog_rect.right - margin - button_width * 2 - button_gap, button_y, button_width, button_height)
        self.cancel_button_rect = pg.Rect(self.dialog_rect.right - margin - button_width, button_y, button_width, button_height)
    
    def close(self) -> None:
        """Close the color picker."""
        self.active = False
        self.dragging_slider = None
    
    def render(self, surface: pg.Surface, fonts: Dict[str, pg.font.Font]) -> None:
        """Render the color picker dialog."""
        if not self.active:
            return
        
        # Draw semi-transparent overlay
        overlay = pg.Surface(surface.get_size(), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))
        
        # Draw dialog background with darker color for better contrast
        dialog_bg = (32, 36, 42)
        pg.draw.rect(surface, dialog_bg, self.dialog_rect, border_radius=12)
        pg.draw.rect(surface, SIDEBAR_ACCENT, self.dialog_rect, width=3, border_radius=12)
        
        # Draw title
        title_font = fonts["title"]
        label_font = fonts["label"]
        small_font = fonts["small"]
        title = title_font.render("Color Picker", True, (255, 255, 255))
        surface.blit(title, (self.dialog_rect.left + 20, self.dialog_rect.top + 15))
        
        # Draw color preview
        pg.draw.rect(surface, self.color, self.preview_rect, border_radius=8)
        pg.draw.rect(surface, (200, 200, 200), self.preview_rect, width=2, border_radius=8)
        
        # Draw hex input label and field
        hex_label = small_font.render("HEX:", True, (220, 220, 220))
        surface.blit(hex_label, (self.hex_input_rect.left, self.hex_input_rect.top - 20))
        
        # Hex input box
        input_bg = (50, 54, 60) if not self.hex_input_active else (60, 64, 70)
        pg.draw.rect(surface, input_bg, self.hex_input_rect, border_radius=4)
        border_color = SIDEBAR_ACCENT if self.hex_input_active else (100, 104, 110)
        pg.draw.rect(surface, border_color, self.hex_input_rect, width=2, border_radius=4)
        
        hex_text = label_font.render(f"#{self.hex_input_text}", True, (255, 255, 255))
        hex_text_rect = hex_text.get_rect(center=self.hex_input_rect.center)
        surface.blit(hex_text, hex_text_rect)
        
        # Draw blinking cursor when hex input is active
        if self.hex_input_active:
            # Blink cursor every 530ms
            self.hex_cursor_blink_time += 16  # Approximate frame time
            if (self.hex_cursor_blink_time // 530) % 2 == 0:
                # Calculate cursor position
                cursor_x = hex_text_rect.left + label_font.size(f"#{self.hex_input_text[:self.hex_cursor_pos]}")[0]
                cursor_y_top = self.hex_input_rect.centery - 10
                cursor_y_bottom = self.hex_input_rect.centery + 10
                pg.draw.line(surface, (255, 255, 255), (cursor_x, cursor_y_top), (cursor_x, cursor_y_bottom), 2)
        
        # Draw RGB sliders
        r, g, b, a = self.color
        sliders = [
            ('R', self.r_slider_rect, r, (220, 60, 60)),
            ('G', self.g_slider_rect, g, (60, 220, 60)),
            ('B', self.b_slider_rect, b, (60, 140, 220)),
        ]
        
        for label, rect, value, slider_color in sliders:
            # Draw label with better positioning
            label_text = label_font.render(f"{label}: {value:3d}", True, (240, 240, 240))
            surface.blit(label_text, (rect.left - 95, rect.centery - label_text.get_height() // 2))
            
            # Draw slider track
            pg.draw.rect(surface, (50, 54, 60), rect, border_radius=6)
            pg.draw.rect(surface, (100, 104, 110), rect, width=1, border_radius=6)
            
            # Draw slider fill
            fill_width = int((value / 255) * rect.width)
            if fill_width > 0:
                fill_rect = pg.Rect(rect.left, rect.top, fill_width, rect.height)
                pg.draw.rect(surface, slider_color, fill_rect, border_radius=6)
            
            # Draw handle
            handle_x = rect.left + fill_width
            handle_rect = pg.Rect(handle_x - 5, rect.top - 3, 10, rect.height + 6)
            pg.draw.rect(surface, (240, 240, 240), handle_rect, border_radius=5)
            pg.draw.rect(surface, (100, 104, 110), handle_rect, width=2, border_radius=5)
        
        # Draw buttons with better contrast
        # Add to Palette button
        pg.draw.rect(surface, (80, 140, 200), self.add_to_palette_button_rect, border_radius=8)
        pg.draw.rect(surface, (100, 160, 220), self.add_to_palette_button_rect, width=2, border_radius=8)
        add_text = label_font.render("Add to Palette", True, (255, 255, 255))
        surface.blit(add_text, add_text.get_rect(center=self.add_to_palette_button_rect.center))
        
        # OK button
        pg.draw.rect(surface, (60, 180, 120), self.ok_button_rect, border_radius=8)
        ok_text = label_font.render("OK", True, (255, 255, 255))
        surface.blit(ok_text, ok_text.get_rect(center=self.ok_button_rect.center))
        
        # Cancel button
        pg.draw.rect(surface, (60, 64, 70), self.cancel_button_rect, border_radius=8)
        pg.draw.rect(surface, (120, 124, 130), self.cancel_button_rect, width=2, border_radius=8)
        cancel_text = label_font.render("Cancel", True, (220, 220, 220))
        surface.blit(cancel_text, cancel_text.get_rect(center=self.cancel_button_rect.center))
    
    def handle_mouse_down(self, pos: Tuple[int, int]) -> Optional[tuple]:
        """Handle mouse click. Returns ('ok', color) if OK was clicked, ('add', color) if Add to Palette was clicked, None otherwise."""
        if not self.active:
            return None
        
        if self.ok_button_rect.collidepoint(pos):
            self.close()
            return ('ok', self.color)
        
        if self.cancel_button_rect.collidepoint(pos):
            self.close()
            return ('cancel', None)
        
        if self.add_to_palette_button_rect.collidepoint(pos):
            # Don't close the dialog, just return the color to be added
            if self.add_to_palette_callback:
                self.add_to_palette_callback(self.color)
            return ('add', self.color)
        
        # Check hex input click
        if self.hex_input_rect.collidepoint(pos):
            self.hex_input_active = True
            self.hex_cursor_pos = len(self.hex_input_text)
            self.hex_cursor_blink_time = 0
            return None
        else:
            # Clicked outside hex input - apply any changes
            if self.hex_input_active:
                new_color = self._hex_to_color(self.hex_input_text)
                if new_color:
                    self.color = new_color
            self.hex_input_active = False
        
        # Check slider clicks
        if self.r_slider_rect.collidepoint(pos):
            self.dragging_slider = 'r'
            self._update_slider(pos)
        elif self.g_slider_rect.collidepoint(pos):
            self.dragging_slider = 'g'
            self._update_slider(pos)
        elif self.b_slider_rect.collidepoint(pos):
            self.dragging_slider = 'b'
            self._update_slider(pos)
        
        return None
    
    def handle_mouse_up(self) -> None:
        """Handle mouse release."""
        self.dragging_slider = None
    
    def handle_mouse_move(self, pos: Tuple[int, int]) -> None:
        """Handle mouse movement for slider dragging."""
        if self.dragging_slider:
            self._update_slider(pos)
    
    def handle_key_down(self, event: pg.event.Event) -> None:
        """Handle keyboard input for hex field."""
        if not self.hex_input_active:
            return
        
        if event.key == pg.K_RETURN or event.key == pg.K_KP_ENTER:
            # Apply hex color
            new_color = self._hex_to_color(self.hex_input_text)
            if new_color:
                self.color = new_color
            self.hex_input_active = False
        elif event.key == pg.K_ESCAPE:
            # Cancel hex input
            self.hex_input_text = self._color_to_hex(self.color)
            self.hex_input_active = False
        elif event.key == pg.K_BACKSPACE:
            if self.hex_cursor_pos > 0:
                self.hex_input_text = self.hex_input_text[:self.hex_cursor_pos-1] + self.hex_input_text[self.hex_cursor_pos:]
                self.hex_cursor_pos -= 1
                self.hex_cursor_blink_time = 0
        elif event.key == pg.K_v and pg.key.get_mods() & pg.KMOD_CTRL:
            # Paste from clipboard (not implemented in pygame by default)
            pass
        elif event.key == pg.K_LEFT:
            if self.hex_cursor_pos > 0:
                self.hex_cursor_pos -= 1
                self.hex_cursor_blink_time = 0
        elif event.key == pg.K_RIGHT:
            if self.hex_cursor_pos < len(self.hex_input_text):
                self.hex_cursor_pos += 1
                self.hex_cursor_blink_time = 0
        elif event.key == pg.K_HOME:
            self.hex_cursor_pos = 0
            self.hex_cursor_blink_time = 0
        elif event.key == pg.K_END:
            self.hex_cursor_pos = len(self.hex_input_text)
            self.hex_cursor_blink_time = 0
        elif event.key == pg.K_DELETE:
            if self.hex_cursor_pos < len(self.hex_input_text):
                self.hex_input_text = self.hex_input_text[:self.hex_cursor_pos] + self.hex_input_text[self.hex_cursor_pos+1:]
                self.hex_cursor_blink_time = 0
        else:
            # Add character if it's a valid hex digit
            char = event.unicode.upper()
            if char in '0123456789ABCDEF' and len(self.hex_input_text) < 6:
                self.hex_input_text = self.hex_input_text[:self.hex_cursor_pos] + char + self.hex_input_text[self.hex_cursor_pos:]
                self.hex_cursor_pos += 1
                self.hex_cursor_blink_time = 0
    
    def _update_slider(self, pos: Tuple[int, int]) -> None:
        """Update slider value based on mouse position."""
        r, g, b, a = self.color
        
        if self.dragging_slider == 'r':
            value = int(clamp((pos[0] - self.r_slider_rect.left) / self.r_slider_rect.width * 255, 0, 255))
            self.color = (value, g, b, a)
        elif self.dragging_slider == 'g':
            value = int(clamp((pos[0] - self.g_slider_rect.left) / self.g_slider_rect.width * 255, 0, 255))
            self.color = (r, value, b, a)
        elif self.dragging_slider == 'b':
            value = int(clamp((pos[0] - self.b_slider_rect.left) / self.b_slider_rect.width * 255, 0, 255))
            self.color = (r, g, value, a)
        
        # Update hex input when sliders change
        self.hex_input_text = self._color_to_hex(self.color)
    
    def _color_to_hex(self, color: Color) -> str:
        """Convert RGB color to hex string."""
        r, g, b, a = color
        return f"{r:02X}{g:02X}{b:02X}"
    
    def _hex_to_color(self, hex_str: str) -> Optional[Color]:
        """Convert hex string to RGB color."""
        hex_str = hex_str.strip().upper().replace('#', '')
        if len(hex_str) != 6:
            return None
        try:
            r = int(hex_str[0:2], 16)
            g = int(hex_str[2:4], 16)
            b = int(hex_str[4:6], 16)
            return (r, g, b, 255)
        except ValueError:
            return None


class SidebarUI:
    def __init__(self, height: int, palette_manager: PaletteManager) -> None:
        self.rect = pg.Rect(FRAMES_PANEL_WIDTH, 0, SIDEBAR_WIDTH, height)
        self.tool_buttons: List[Button] = []
        self.brush_buttons: List[Button] = []
        self.palette_cells: List[Tuple[pg.Rect, Color]] = []
        self.palette_manager = palette_manager
        self.swap_rect = pg.Rect(self.rect.left + 24, height - 120, 48, 24)
        self.palette_scroll_offset = 0
        self.palette_max_scroll = 0
        self.palette_scrollbar_rect = pg.Rect(0, 0, 0, 0)
        self.palette_scrollbar_handle_rect = pg.Rect(0, 0, 0, 0)
        self.dragging_palette_scrollbar = False
        self.palette_scrollbar_drag_start_y = 0
        self.palette_scrollbar_drag_start_offset = 0
        self.palette_start_y = 0
        self.palette_label_pos = (0, 0)
        # Palette UI elements (Piskel-style)
        self.palette_dropdown_rect = pg.Rect(0, 0, 0, 0)
        self.palette_add_button_rect = pg.Rect(0, 0, 0, 0)
        self.palette_edit_button_rect = pg.Rect(0, 0, 0, 0)
        self.palette_load_button_rect = pg.Rect(0, 0, 0, 0)
        self.palette_dropdown_open = False
        self.palette_dropdown_options: List[Tuple[pg.Rect, int]] = []  # (rect, palette_index)
        self.export_button_rect = pg.Rect(0, 0, 0, 0)
        self._build_buttons(height)

    def _build_buttons(self, height: int) -> None:
        start_x = FRAMES_PANEL_WIDTH + 28
        start_y = 48
        for index, size in enumerate(BRUSH_SIZES):
            rect = pg.Rect(
                start_x + index * (BRUSH_SWATCH_SIZE + BRUSH_SWATCH_GAP),
                start_y,
                BRUSH_SWATCH_SIZE,
                BRUSH_SWATCH_SIZE,
            )
            self.brush_buttons.append(Button(name=str(index), rect=rect, label=str(size)))
        tool_start_y = start_y + BRUSH_SWATCH_SIZE + 50
        col_width = (SIDEBAR_WIDTH - 32 * 2 - BUTTON_GAP) // 2
        for idx, tool_name in enumerate(TOOL_ORDER):
            row = idx // 2
            col = idx % 2
            rect = pg.Rect(
                FRAMES_PANEL_WIDTH + 28 + col * (col_width + BUTTON_GAP),
                tool_start_y + row * (BUTTON_SIZE[1] + BUTTON_GAP),
                col_width,
                BUTTON_SIZE[1],
            )
            label = TOOL_LABELS.get(tool_name, tool_name)
            self.tool_buttons.append(Button(tool_name, rect, label))
        # Palette section - will be built dynamically in render with scroll support
        self.palette_start_y = self.tool_buttons[-1].rect.bottom + 44
        self.palette_label_pos = (FRAMES_PANEL_WIDTH + 28, self.palette_start_y)
        
        # Position swap and color previews at bottom with more spacing
        bottom_y = height - STATUS_BAR_HEIGHT - 16
        self.primary_rect = pg.Rect(FRAMES_PANEL_WIDTH + 28, bottom_y - COLOR_PREVIEW_SIZE[1], COLOR_PREVIEW_SIZE[0], COLOR_PREVIEW_SIZE[1])
        self.secondary_rect = pg.Rect(
            self.primary_rect.right + 12,
            bottom_y - COLOR_PREVIEW_SIZE[1],
            COLOR_PREVIEW_SIZE[0],
            COLOR_PREVIEW_SIZE[1],
        )
        self.swap_rect = pg.Rect(FRAMES_PANEL_WIDTH + 28, self.primary_rect.top - 34, 56, 26)


    def _render_palette(self, surface: pg.Surface, fonts: Dict[str, pg.font.Font]) -> None:
        """Render the color palette with scrollbar support and Piskel-style controls."""
        small_font = fonts["small"]
        label_font = fonts["label"]
        
        # Render palette header (Piskel-style)
        header_y = self.palette_start_y - 8
        
        # Palette dropdown selector - full width on first row
        sidebar_content_width = SIDEBAR_WIDTH - 56
        dropdown_height = 36
        self.palette_dropdown_rect = pg.Rect(FRAMES_PANEL_WIDTH + 28, header_y, sidebar_content_width, dropdown_height)
        pg.draw.rect(surface, STATUS_BG, self.palette_dropdown_rect, border_radius=4)
        pg.draw.rect(surface, CANVAS_BORDER, self.palette_dropdown_rect, width=1, border_radius=4)
        
        # Show current palette name with dropdown arrow
        palette_name = self.palette_manager.active_palette.name
        if len(palette_name) > 18:
            palette_name = palette_name[:16] + "..."
        name_text = small_font.render(palette_name, True, SIDEBAR_TEXT)
        surface.blit(name_text, (self.palette_dropdown_rect.left + 8, self.palette_dropdown_rect.centery - name_text.get_height() // 2))
        
        # Dropdown arrow
        arrow_text = small_font.render("▼" if not self.palette_dropdown_open else "▲", True, SIDEBAR_TEXT)
        surface.blit(arrow_text, (self.palette_dropdown_rect.right - 35, self.palette_dropdown_rect.centery - arrow_text.get_height() // 2))
        
        # Second row: Three buttons below dropdown
        button_row_y = header_y + dropdown_height + 4
        button_size = 36
        button_gap = 6
        
        # Calculate button width to fit three buttons evenly across the width
        total_gap_space = button_gap * 2  # Two gaps between three buttons
        button_width = (sidebar_content_width - total_gap_space) // 3
        
        # Add palette button (+)
        self.palette_add_button_rect = pg.Rect(FRAMES_PANEL_WIDTH + 28, button_row_y, button_width, button_size)
        pg.draw.rect(surface, STATUS_BG, self.palette_add_button_rect, border_radius=4)
        pg.draw.rect(surface, SIDEBAR_ACCENT, self.palette_add_button_rect, width=1, border_radius=4)
        plus_text = label_font.render("+", True, SIDEBAR_ACCENT)
        surface.blit(plus_text, plus_text.get_rect(center=self.palette_add_button_rect.center))
        
        # Edit palette button (pencil icon - using "✎")
        self.palette_edit_button_rect = pg.Rect(self.palette_add_button_rect.right + button_gap, button_row_y, button_width, button_size)
        pg.draw.rect(surface, STATUS_BG, self.palette_edit_button_rect, border_radius=4)
        pg.draw.rect(surface, CANVAS_BORDER, self.palette_edit_button_rect, width=1, border_radius=4)
        edit_text = label_font.render("✎", True, SIDEBAR_TEXT)
        surface.blit(edit_text, edit_text.get_rect(center=self.palette_edit_button_rect.center))
        
        # Load palette button (folder icon - using "📂")
        self.palette_load_button_rect = pg.Rect(self.palette_edit_button_rect.right + button_gap, button_row_y, button_width, button_size)
        pg.draw.rect(surface, STATUS_BG, self.palette_load_button_rect, border_radius=4)
        pg.draw.rect(surface, CANVAS_BORDER, self.palette_load_button_rect, width=1, border_radius=4)
        load_text = small_font.render("📂", True, SIDEBAR_TEXT)
        surface.blit(load_text, load_text.get_rect(center=self.palette_load_button_rect.center))
        
        # Render dropdown menu if open
        if self.palette_dropdown_open:
            self._render_palette_dropdown(surface, small_font)
        
        # Calculate available height for palette (between header and swap button)
        # Account for dropdown (36px) + gap (4px) + buttons (36px) + spacing (8px) = 84px
        palette_content_start = self.palette_start_y + 84
        available_height = self.swap_rect.top - palette_content_start - 16
        
        # Calculate grid dimensions to fit sidebar
        start_x = FRAMES_PANEL_WIDTH + 28
        content_width = SIDEBAR_WIDTH - 56 - 20  # Leave space for scrollbar and margins
        
        cell_size = 32
        cell_gap = 6
        
        # Calculate how many columns fit (cell_size + gap) * cols - gap <= content_width
        cols = max(1, (content_width + cell_gap) // (cell_size + cell_gap))
        cols = min(cols, 5)  # Cap at 5 columns for better layout
        
        # Build palette cells with scroll offset
        x = start_x
        y = palette_content_start - self.palette_scroll_offset
        self.palette_cells = []
        
        # Use active palette colors
        palette_colors = self.palette_manager.active_palette.colors
        
        for idx, color in enumerate(palette_colors):
            rect = pg.Rect(x, y, cell_size, cell_size)
            self.palette_cells.append((rect, color))
            x += cell_size + cell_gap
            if (idx + 1) % cols == 0:
                x = start_x
                y += cell_size + cell_gap
        
        # Calculate total content height and max scroll
        num_rows = (len(palette_colors) + cols - 1) // cols
        total_content_height = num_rows * (cell_size + cell_gap)
        self.palette_max_scroll = max(0, total_content_height - available_height)
        self.palette_scroll_offset = int(clamp(self.palette_scroll_offset, 0, self.palette_max_scroll))
        
        # Update scrollbar dimensions
        scrollbar_width = 8
        scrollbar_x = self.rect.right - 28 - scrollbar_width
        scrollbar_y = palette_content_start
        scrollbar_height = available_height
        self.palette_scrollbar_rect = pg.Rect(scrollbar_x, scrollbar_y, scrollbar_width, scrollbar_height)
        
        if self.palette_max_scroll > 0:
            handle_height = max(20, int(scrollbar_height * (available_height / total_content_height)))
            handle_y = scrollbar_y + int((scrollbar_height - handle_height) * (self.palette_scroll_offset / self.palette_max_scroll))
            self.palette_scrollbar_handle_rect = pg.Rect(scrollbar_x, handle_y, scrollbar_width, handle_height)
        else:
            self.palette_scrollbar_handle_rect = pg.Rect(0, 0, 0, 0)
        
        # Create clipping rect for scrollable palette
        clip_rect = pg.Rect(start_x, palette_content_start, content_width, available_height)
        original_clip = surface.get_clip()
        surface.set_clip(clip_rect)
        
        # Render palette colors
        for rect, color in self.palette_cells:
            # Only draw if visible in clip area
            if rect.bottom >= clip_rect.top and rect.top <= clip_rect.bottom:
                pg.draw.rect(surface, color, rect, border_radius=6)
                pg.draw.rect(surface, SIDEBAR_MUTED, rect, width=1, border_radius=6)
        
        # Restore original clip
        surface.set_clip(original_clip)
        
        # Draw scrollbar if needed
        if self.palette_max_scroll > 0:
            pg.draw.rect(surface, CANVAS_BORDER, self.palette_scrollbar_rect, border_radius=4)
            pg.draw.rect(surface, SIDEBAR_ACCENT, self.palette_scrollbar_handle_rect, border_radius=4)
    
    def _render_palette_dropdown(self, surface: pg.Surface, font: pg.font.Font) -> None:
        """Render the palette dropdown menu."""
        self.palette_dropdown_options = []
        option_height = 36
        dropdown_width = self.palette_dropdown_rect.width
        
        # Dropdown background (render above the button, not below)
        dropdown_menu_height = min(len(self.palette_manager.palettes) * option_height, 200)
        dropdown_menu_rect = pg.Rect(
            self.palette_dropdown_rect.left,
            self.palette_dropdown_rect.top - dropdown_menu_height - 2,
            dropdown_width,
            dropdown_menu_height
        )
        
        # Draw dropdown with shadow effect
        shadow_rect = dropdown_menu_rect.copy()
        shadow_rect.inflate_ip(4, 4)
        pg.draw.rect(surface, (0, 0, 0, 100), shadow_rect, border_radius=4)
        pg.draw.rect(surface, (35, 38, 42), dropdown_menu_rect, border_radius=4)
        pg.draw.rect(surface, SIDEBAR_ACCENT, dropdown_menu_rect, width=2, border_radius=4)
        
        # Render palette options
        for idx, palette in enumerate(self.palette_manager.palettes):
            option_rect = pg.Rect(
                dropdown_menu_rect.left,
                dropdown_menu_rect.top + idx * option_height,
                dropdown_width,
                option_height
            )
            
            # Skip if outside dropdown bounds
            if option_rect.bottom > dropdown_menu_rect.bottom:
                break
            
            self.palette_dropdown_options.append((option_rect, idx))
            
            # Highlight active palette
            if idx == self.palette_manager.active_index:
                pg.draw.rect(surface, SIDEBAR_ACCENT, option_rect, border_radius=3)
                text_color = (255, 255, 255)
            else:
                text_color = SIDEBAR_TEXT
            
            # Palette name
            name = palette.name
            if len(name) > 18:
                name = name[:16] + "..."
            text = font.render(name, True, text_color)
            surface.blit(text, (option_rect.left + 6, option_rect.centery - text.get_height() // 2))
            
            # Show color count
            count_text = font.render(f"({len(palette.colors)})", True, SIDEBAR_MUTED)
            surface.blit(count_text, (option_rect.right - count_text.get_width() - 6, option_rect.centery - count_text.get_height() // 2))


    def render(
        self,
        surface: pg.Surface,
        fonts: Dict[str, pg.font.Font],
        state: AppState,
        active_tool: str,
    ) -> None:
        pg.draw.rect(surface, SIDEBAR_BG, self.rect)
        # Draw separator lines on left and right edges
        pg.draw.line(surface, CANVAS_BORDER, (self.rect.left, self.rect.top), (self.rect.left, self.rect.bottom), width=2)
        pg.draw.line(surface, CANVAS_BORDER, (self.rect.right - 1, self.rect.top), (self.rect.right - 1, self.rect.bottom), width=2)
        title_font = fonts["title"]
        label_font = fonts["label"]
        small_font = fonts["small"]


        brush_label = title_font.render("Brush", True, SIDEBAR_TEXT)
        surface.blit(brush_label, (self.rect.left + 28, self.rect.top + 18))
        for idx, button in enumerate(self.brush_buttons):
            is_active = idx == state.brush_index
            color = SIDEBAR_ACCENT if is_active else CANVAS_BORDER
            pg.draw.rect(surface, color, button.rect, border_radius=6)
            text = label_font.render(button.label, True, SIDEBAR_TEXT)
            text_rect = text.get_rect(center=button.rect.center)
            surface.blit(text, text_rect)


        tools_label = title_font.render("Tools", True, SIDEBAR_TEXT)
        surface.blit(tools_label, (self.rect.left + 28, self.brush_buttons[0].rect.bottom + 24))
        for button in self.tool_buttons:
            is_active = button.name == active_tool
            rect_color = SIDEBAR_ACCENT if is_active else CANVAS_BORDER
            pg.draw.rect(surface, rect_color, button.rect, border_radius=8, width=2 if not is_active else 0)
            text_color = WINDOW_BG if is_active else SIDEBAR_TEXT
            text = label_font.render(button.label, True, text_color)
            text_rect = text.get_rect(center=button.rect.center)
            surface.blit(text, text_rect)


        palette_label = title_font.render("Palette", True, SIDEBAR_TEXT)
        surface.blit(palette_label, self.palette_label_pos)
        self._render_palette(surface, fonts)


        swap_text = small_font.render("Swap", True, SIDEBAR_TEXT)
        pg.draw.rect(surface, CANVAS_BORDER, self.swap_rect, border_radius=6)
        surface.blit(swap_text, swap_text.get_rect(center=self.swap_rect.center))


        pg.draw.rect(surface, state.secondary_color, self.secondary_rect, border_radius=8)
        pg.draw.rect(surface, state.primary_color, self.primary_rect, border_radius=8)
        pg.draw.rect(surface, SIDEBAR_MUTED, self.primary_rect, width=2, border_radius=8)
        pg.draw.rect(surface, SIDEBAR_MUTED, self.secondary_rect, width=2, border_radius=8)


    def handle_mouse_down(
        self,
        state: AppState,
        tool_manager: ToolManager,
        pos: Tuple[int, int],
        button: int,
        color_picker: ColorPicker,
        window_size: Tuple[int, int],
        palette_editor: Optional['PaletteEditorUI'] = None,
        palette_browser: Optional['PaletteBrowserUI'] = None,
    ) -> bool:
        if not self.rect.collidepoint(pos):
            return False
        if button == 1:
            # Check palette dropdown options (if dropdown is open)
            if self.palette_dropdown_open:
                for option_rect, palette_idx in self.palette_dropdown_options:
                    if option_rect.collidepoint(pos):
                        self.palette_manager.active_index = palette_idx
                        self.palette_dropdown_open = False
                        state.set_status(f"Switched to palette: {self.palette_manager.active_palette.name}")
                        return True
                # Click outside dropdown - close it
                self.palette_dropdown_open = False
                return True
            
            # Check palette dropdown toggle
            if self.palette_dropdown_rect.collidepoint(pos):
                self.palette_dropdown_open = not self.palette_dropdown_open
                return True
            
            # Check palette add button
            if self.palette_add_button_rect.collidepoint(pos):
                self.palette_manager.clone_active()
                state.set_status(f"Created new palette: {self.palette_manager.active_palette.name}")
                return True
            
            # Check palette edit button
            if self.palette_edit_button_rect.collidepoint(pos) and palette_editor:
                palette_editor.open(self.palette_manager.active_palette, window_size)
                return True
            
            # Check palette load button
            if self.palette_load_button_rect.collidepoint(pos) and palette_browser:
                self._load_palette_from_file(state, palette_browser, window_size)
                return True
            
            # Check palette scrollbar handle click
            if self.palette_scrollbar_handle_rect.collidepoint(pos):
                self.dragging_palette_scrollbar = True
                self.palette_scrollbar_drag_start_y = pos[1]
                self.palette_scrollbar_drag_start_offset = self.palette_scroll_offset
                return True
            
            # Check palette scrollbar track click (jump to position)
            if self.palette_scrollbar_rect.collidepoint(pos) and self.palette_max_scroll > 0:
                relative_y = pos[1] - self.palette_scrollbar_rect.top
                scroll_ratio = relative_y / self.palette_scrollbar_rect.height
                self.palette_scroll_offset = int(scroll_ratio * self.palette_max_scroll)
                return True
            
            for idx, brush_button in enumerate(self.brush_buttons):
                if brush_button.rect.collidepoint(pos):
                    state.brush_index = idx
                    state.set_status(f"Brush size set to {BRUSH_SIZES[idx]}")
                    return True
            for button_info in self.tool_buttons:
                if button_info.rect.collidepoint(pos):
                    tool_manager.select(button_info.name, state)
                    return True
            if self.swap_rect.collidepoint(pos):
                state.swap_colors()
                state.set_status("Swapped colors")
                return True
            if self.primary_rect.collidepoint(pos):
                # Open color picker on left click
                color_picker.open(state.primary_color, window_size)
                return True
        if button == 3:
            if self.secondary_rect.collidepoint(pos):
                # Open color picker on right click
                color_picker.open(state.secondary_color, window_size)
                return True
        for rect, color in self.palette_cells:
            if rect.collidepoint(pos):
                if button == 1:
                    state.primary_color = color
                    state.set_status("Primary color updated")
                elif button == 3:
                    state.secondary_color = color
                    state.set_status("Secondary color updated")
                return True
        return True


    def handle_mouse_up(self) -> None:
        """Handle mouse button release."""
        self.dragging_palette_scrollbar = False


    def handle_mouse_move(self, pos: Tuple[int, int]) -> None:
        """Handle mouse movement for palette scrollbar dragging."""
        if self.dragging_palette_scrollbar:
            if self.palette_max_scroll > 0:
                delta_y = pos[1] - self.palette_scrollbar_drag_start_y
                scroll_range = self.palette_scrollbar_rect.height - self.palette_scrollbar_handle_rect.height
                if scroll_range > 0:
                    scroll_delta = (delta_y / scroll_range) * self.palette_max_scroll
                    self.palette_scroll_offset = int(clamp(self.palette_scrollbar_drag_start_offset + scroll_delta, 0, self.palette_max_scroll))
    
    def _load_palette_from_file(self, state: 'EditorState', palette_browser: 'PaletteBrowserUI', window_size: Tuple[int, int]) -> None:
        """Open the palette browser to load a palette from a file."""
        from pathlib import Path
        
        palette_dir = Path("exports/palettes")
        if not palette_dir.exists():
            state.set_status("No saved palettes found. Save a palette first!")
            return
        
        # Get all .json files in the palette directory
        palette_files = list(palette_dir.glob("*.json"))
        if not palette_files:
            state.set_status("No saved palettes found. Save a palette first!")
            return
        
        # Open the palette browser
        palette_browser.open(window_size)




@dataclass
class LayerRow:
    index: int
    rect: pg.Rect
    toggle_rect: pg.Rect




class RightPanelUI:
    ROW_HEIGHT = 32
    ROW_GAP = 8

    def __init__(self, window_size: Tuple[int, int]) -> None:
        self.layer_buttons: List[Button] = []
        self.layer_rows: List[LayerRow] = []
        self.minimap_canvas_rect: Optional[pg.Rect] = None
        self.minimap_scale: float = 0.0
        self.inner_left = 0
        self.layers_area_width = 0
        self.overview_label_pos = (0, 0)
        self.layers_label_pos = (0, 0)
        self.layers_start_y = 0
        self.minimap_rect = pg.Rect(0, 0, 0, 0)
        self.rect = pg.Rect(0, 0, 0, 0)
        self.layers_scroll_offset = 0
        self.layers_max_scroll = 0
        self.layers_scrollbar_rect = pg.Rect(0, 0, 0, 0)
        self.layers_scrollbar_handle_rect = pg.Rect(0, 0, 0, 0)
        self.dragging_layers_scrollbar = False
        self.layers_scrollbar_drag_start_y = 0
        self.layers_scrollbar_drag_start_offset = 0
        # Drag and drop for layers
        self.dragging_layer: Optional[int] = None
        self.drag_offset_y = 0
        # Layer name editing
        self.editing_layer: Optional[int] = None
        self.layer_name_input: str = ""
        self.layer_name_cursor_pos: int = 0
        self.layer_name_cursor_blink_time: float = 0.0
        self.last_click_time: float = 0.0
        self.last_click_layer: Optional[int] = None
        self.export_button_rect = pg.Rect(0, 0, 0, 0)
        self.resize(window_size)


    def resize(self, window_size: Tuple[int, int]) -> None:
        width, height = window_size
        self.rect = pg.Rect(width - RIGHT_PANEL_WIDTH, 0, RIGHT_PANEL_WIDTH, height)
        self.inner_left = self.rect.left + 16
        inner_width = RIGHT_PANEL_WIDTH - 32


        self.overview_label_pos = (self.inner_left, self.rect.top + 12)
        minimap_top = self.overview_label_pos[1] + 28
        self.minimap_rect = pg.Rect(self.inner_left, minimap_top, inner_width, inner_width)


        buttons_top = self.minimap_rect.bottom + 20
        button_width = (inner_width - 8) // 2 if inner_width > 0 else 0
        button_height = 28
        names = [("add", "+"), ("delete", "-")]
        self.layer_buttons = []
        for idx, (name, label) in enumerate(names):
            rect = pg.Rect(self.inner_left + idx * (button_width + 8), buttons_top, button_width, button_height)
            self.layer_buttons.append(Button(name=name, rect=rect, label=label))


        self.layers_label_pos = (self.inner_left, buttons_top + button_height + 16)
        self.layers_start_y = self.layers_label_pos[1] + 24
        self.layers_area_width = inner_width


    def render(self, surface: pg.Surface, fonts: Dict[str, pg.font.Font], state: AppState, workspace: pg.Rect) -> None:
        pg.draw.rect(surface, SIDEBAR_BG, self.rect)
        # Draw separator line on the left edge
        pg.draw.line(surface, CANVAS_BORDER, (self.rect.left, self.rect.top), (self.rect.left, self.rect.bottom), width=2)
        title_font = fonts["title"]
        label_font = fonts["label"]


        overview_label = title_font.render("Overview", True, SIDEBAR_TEXT)
        surface.blit(overview_label, self.overview_label_pos)
        self._render_minimap(surface, state, workspace)


        for button in self.layer_buttons:
            pg.draw.rect(surface, CANVAS_BORDER, button.rect, border_radius=6)
            text = label_font.render(button.label, True, SIDEBAR_TEXT)
            surface.blit(text, text.get_rect(center=button.rect.center))


        layers_label = title_font.render("Layers", True, SIDEBAR_TEXT)
        surface.blit(layers_label, self.layers_label_pos)
        self._render_layers(surface, label_font, state)
        
        # Export button below layers section
        export_y = self.layers_start_y + (self.rect.bottom - STATUS_BAR_HEIGHT - self.layers_start_y - 16) // 2 + 24
        inner_width = RIGHT_PANEL_WIDTH - 32
        self.export_button_rect = pg.Rect(
            self.inner_left,
            export_y,
            inner_width,
            50
        )
        pg.draw.rect(surface, (255, 200, 0), self.export_button_rect, border_radius=8)
        export_text = label_font.render("Export (Ctrl+E)", True, (0, 0, 0))
        surface.blit(export_text, export_text.get_rect(center=self.export_button_rect.center))


    def _render_minimap(self, surface: pg.Surface, state: AppState, workspace: pg.Rect) -> None:
        pg.draw.rect(surface, STATUS_BG, self.minimap_rect, border_radius=8)
        pg.draw.rect(surface, CANVAS_BORDER, self.minimap_rect, width=2, border_radius=8)
        content_rect = self.minimap_rect.inflate(-8, -8)
        self.minimap_canvas_rect = None
        self.minimap_scale = 0.0
        if state.canvas.width == 0 or state.canvas.height == 0:
            return
        scale = min(
            content_rect.width / state.canvas.width if state.canvas.width else 0,
            content_rect.height / state.canvas.height if state.canvas.height else 0,
        )
        if scale <= 0:
            return
        scaled_size = (
            max(1, int(state.canvas.width * scale)),
            max(1, int(state.canvas.height * scale)),
        )
        checker = pg.transform.scale(state.canvas.checker, scaled_size)
        composite = state.canvas.composite_surface()
        pixels = pg.transform.scale(composite, scaled_size)
        map_rect = pixels.get_rect(center=content_rect.center)
        surface.blit(checker, map_rect)
        surface.blit(pixels, map_rect)
        pg.draw.rect(surface, CANVAS_BORDER, map_rect, width=1)
        self.minimap_scale = scale
        self.minimap_canvas_rect = map_rect


        canvas_rect = state.canvas_rect()
        visible = canvas_rect.clip(workspace)
        if visible.width > 0 and visible.height > 0:
            pixel_size = state.pixel_size()
            offset_x = (visible.left - canvas_rect.left) / pixel_size
            offset_y = (visible.top - canvas_rect.top) / pixel_size
            width_cells = visible.width / pixel_size
            height_cells = visible.height / pixel_size
            viewport_rect = pg.Rect(
                map_rect.left + offset_x * scale,
                map_rect.top + offset_y * scale,
                max(2, width_cells * scale),
                max(2, height_cells * scale),
            )
            pg.draw.rect(surface, SIDEBAR_ACCENT, viewport_rect, width=2)


    def _prepare_layer_layout(self, state: AppState) -> Tuple[List[LayerRow], int, pg.Rect]:
        row_height = self.ROW_HEIGHT
        row_gap = self.ROW_GAP
        # Limit layers section to about half the remaining space
        total_remaining_height = self.rect.bottom - STATUS_BAR_HEIGHT - self.layers_start_y - 16
        available_height = min(total_remaining_height, total_remaining_height // 2)
        num_layers = len(state.canvas.layers)
        total_content_height = num_layers * (row_height + row_gap)
        self.layers_max_scroll = max(0, total_content_height - available_height)
        self.layers_scroll_offset = int(clamp(self.layers_scroll_offset, 0, self.layers_max_scroll))

        scrollbar_width = 8
        scrollbar_x = self.rect.right - 16 - scrollbar_width
        scrollbar_y = self.layers_start_y
        scrollbar_height = available_height
        self.layers_scrollbar_rect = pg.Rect(scrollbar_x, scrollbar_y, scrollbar_width, scrollbar_height)

        if self.layers_max_scroll > 0:
            handle_height = max(20, int(scrollbar_height * (available_height / total_content_height)))
            handle_y = scrollbar_y + int((scrollbar_height - handle_height) * (self.layers_scroll_offset / self.layers_max_scroll))
            self.layers_scrollbar_handle_rect = pg.Rect(scrollbar_x, handle_y, scrollbar_width, handle_height)
        else:
            self.layers_scrollbar_handle_rect = pg.Rect(0, 0, 0, 0)

        layers_width = self.layers_area_width - (16 if self.layers_max_scroll > 0 else 0)
        row_y = self.layers_start_y - self.layers_scroll_offset
        rows: List[LayerRow] = []
        for actual_index, _ in state.canvas.layers_for_display():
            row_rect = pg.Rect(self.inner_left, row_y, layers_width, row_height)
            toggle_rect = pg.Rect(row_rect.left + 8, row_rect.centery - 8, 16, 16)
            rows.append(LayerRow(index=actual_index, rect=row_rect, toggle_rect=toggle_rect))
            row_y += row_height + row_gap

        clip_rect = pg.Rect(self.inner_left, self.layers_start_y, self.layers_area_width, available_height)
        return rows, layers_width, clip_rect


    def _render_layers(self, surface: pg.Surface, font: pg.font.Font, state: AppState) -> None:
        rows, layers_width, clip_rect = self._prepare_layer_layout(state)
        original_clip = surface.get_clip()
        surface.set_clip(clip_rect)
        self.layer_rows = rows

        for row in rows:
            layer = state.canvas.layers[row.index]
            row_rect = row.rect
            toggle_rect = row.toggle_rect

            if row_rect.bottom >= clip_rect.top and row_rect.top <= clip_rect.bottom:
                pg.draw.rect(surface, SIDEBAR_BG, row_rect, border_radius=6)
                border_color = SIDEBAR_ACCENT if row.index == state.canvas.active_index else CANVAS_BORDER
                pg.draw.rect(surface, border_color, row_rect, width=2, border_radius=6)
                if layer.visible:
                    pg.draw.rect(surface, SIDEBAR_ACCENT, toggle_rect, border_radius=4)
                else:
                    pg.draw.rect(surface, SIDEBAR_MUTED, toggle_rect, width=2, border_radius=4)
                    pg.draw.line(surface, SIDEBAR_MUTED, toggle_rect.topleft, toggle_rect.bottomright, width=2)
                    pg.draw.line(surface, SIDEBAR_MUTED, toggle_rect.topright, toggle_rect.bottomleft, width=2)
                
                # Render layer name or edit field
                if row.index == self.editing_layer:
                    # Draw editable text field with background
                    text_rect = pg.Rect(toggle_rect.right + 8, row_rect.top + 4, row_rect.width - (toggle_rect.right - row_rect.left) - 16, row_rect.height - 8)
                    pg.draw.rect(surface, STATUS_BG, text_rect, border_radius=3)
                    pg.draw.rect(surface, SIDEBAR_ACCENT, text_rect, width=2, border_radius=3)
                    
                    # Render text
                    name_color = SIDEBAR_TEXT
                    label_surface = font.render(self.layer_name_input, True, name_color)
                    label_pos = (text_rect.left + 4, text_rect.centery - label_surface.get_height() // 2)
                    surface.blit(label_surface, label_pos)
                    
                    # Draw blinking cursor
                    self.layer_name_cursor_blink_time += 1 / FPS
                    if self.layer_name_cursor_blink_time % 1.0 < 0.5:
                        # Calculate cursor position
                        cursor_text = self.layer_name_input[:self.layer_name_cursor_pos]
                        cursor_x = text_rect.left + 4 + font.size(cursor_text)[0]
                        cursor_top = text_rect.top + 4
                        cursor_bottom = text_rect.bottom - 4
                        pg.draw.line(surface, SIDEBAR_ACCENT, (cursor_x, cursor_top), (cursor_x, cursor_bottom), width=2)
                else:
                    # Normal display
                    name_color = SIDEBAR_TEXT if layer.visible else SIDEBAR_MUTED
                    label_surface = font.render(layer.name, True, name_color)
                    label_pos = (toggle_rect.right + 8, row_rect.centery - label_surface.get_height() // 2)
                    surface.blit(label_surface, label_pos)

        # Draw dragging layer on top if dragging
        if self.dragging_layer is not None and 0 <= self.dragging_layer < len(state.canvas.layers):
            layer = state.canvas.layers[self.dragging_layer]
            mouse_pos = pg.mouse.get_pos()
            drag_y = mouse_pos[1] - self.drag_offset_y
            row_rect = pg.Rect(self.inner_left, drag_y, layers_width, self.ROW_HEIGHT)
            toggle_rect = pg.Rect(row_rect.left + 8, row_rect.centery - 8, 16, 16)

            pg.draw.rect(surface, SIDEBAR_BG, row_rect, border_radius=6)
            pg.draw.rect(surface, SIDEBAR_ACCENT, row_rect, width=3, border_radius=6)
            if layer.visible:
                pg.draw.rect(surface, SIDEBAR_ACCENT, toggle_rect, border_radius=4)
            else:
                pg.draw.rect(surface, SIDEBAR_MUTED, toggle_rect, width=2, border_radius=4)
                pg.draw.line(surface, SIDEBAR_MUTED, toggle_rect.topleft, toggle_rect.bottomright, width=2)
                pg.draw.line(surface, SIDEBAR_MUTED, toggle_rect.topright, toggle_rect.bottomleft, width=2)
            name_color = SIDEBAR_TEXT if layer.visible else SIDEBAR_MUTED
            label_surface = font.render(layer.name, True, name_color)
            label_pos = (toggle_rect.right + 8, row_rect.centery - label_surface.get_height() // 2)
            surface.blit(label_surface, label_pos)

        surface.set_clip(original_clip)

        if self.layers_max_scroll > 0:
            pg.draw.rect(surface, CANVAS_BORDER, self.layers_scrollbar_rect, border_radius=4)
            pg.draw.rect(surface, SIDEBAR_ACCENT, self.layers_scrollbar_handle_rect, border_radius=4)


    def handle_mouse_down(self, state: AppState, pos: Tuple[int, int], button: int, window_size: Tuple[int, int], workspace: pg.Rect) -> bool:
        if not self.rect.collidepoint(pos):
            return False

        if button == 1:
            # Check export button
            if self.export_button_rect.collidepoint(pos):
                # Will be handled by main loop
                return True
            
            if self.minimap_rect.collidepoint(pos) and self.minimap_canvas_rect and self.minimap_scale > 0:
                clamped_x = clamp(pos[0], self.minimap_canvas_rect.left, self.minimap_canvas_rect.right - 1)
                clamped_y = clamp(pos[1], self.minimap_canvas_rect.top, self.minimap_canvas_rect.bottom - 1)
                rel_x = (clamped_x - self.minimap_canvas_rect.left) / self.minimap_scale
                rel_y = (clamped_y - self.minimap_canvas_rect.top) / self.minimap_scale
                rel_x = clamp(rel_x, 0, state.canvas.width - 1)
                rel_y = clamp(rel_y, 0, state.canvas.height - 1)
                state.center_on_cell((int(rel_x), int(rel_y)), window_size)
                state.set_status("Recentered via overview")
                return True

            if self.layers_scrollbar_handle_rect.collidepoint(pos):
                self.dragging_layers_scrollbar = True
                self.layers_scrollbar_drag_start_y = pos[1]
                self.layers_scrollbar_drag_start_offset = self.layers_scroll_offset
                return True

            if self.layers_scrollbar_rect.collidepoint(pos) and self.layers_max_scroll > 0:
                relative_y = pos[1] - self.layers_scrollbar_rect.top
                scroll_ratio = relative_y / self.layers_scrollbar_rect.height
                self.layers_scroll_offset = int(scroll_ratio * self.layers_max_scroll)
                return True

            for btn in self.layer_buttons:
                if btn.rect.collidepoint(pos):
                    self._handle_layer_button(state, btn.name)
                    return True

            rows, _, _ = self._prepare_layer_layout(state)
            self.layer_rows = rows
            for row in rows:
                if row.toggle_rect.collidepoint(pos):
                    visible = state.canvas.toggle_visibility(row.index)
                    state.set_status("Layer visible" if visible else "Layer hidden")
                    return True
                if row.rect.collidepoint(pos):
                    # Check for double-click to enter edit mode
                    current_time = pg.time.get_ticks() / 1000.0
                    if (self.last_click_layer == row.index and 
                        current_time - self.last_click_time < 0.5):
                        # Double-click detected - enter edit mode
                        self.editing_layer = row.index
                        layer = state.canvas.layers[row.index]
                        self.layer_name_input = layer.name
                        self.layer_name_cursor_pos = len(self.layer_name_input)
                        self.layer_name_cursor_blink_time = 0.0
                        state.set_status("Editing layer name - Press Enter to save, Esc to cancel")
                        self.last_click_layer = None  # Reset to prevent triple-click issues
                    else:
                        # Single click - select layer and prepare for drag
                        self.dragging_layer = row.index
                        self.drag_offset_y = pos[1] - row.rect.top
                        state.canvas.set_active(row.index)
                        state.set_status(f"Active layer: {state.canvas.active_layer.name}")
                        self.last_click_time = current_time
                        self.last_click_layer = row.index
                    return True

        return True


    def handle_mouse_up(self) -> None:
        self.dragging_layers_scrollbar = False
        self.dragging_layer = None


    def handle_mouse_move(self, pos: Tuple[int, int], state: AppState) -> None:
        if self.dragging_layers_scrollbar:
            if self.layers_max_scroll > 0:
                delta_y = pos[1] - self.layers_scrollbar_drag_start_y
                scroll_range = self.layers_scrollbar_rect.height - self.layers_scrollbar_handle_rect.height
                if scroll_range > 0:
                    scroll_delta = (delta_y / scroll_range) * self.layers_max_scroll
                    self.layers_scroll_offset = int(clamp(self.layers_scrollbar_drag_start_offset + scroll_delta, 0, self.layers_max_scroll))
            return

        if self.dragging_layer is None:
            return

        rows = self.layer_rows or self._prepare_layer_layout(state)[0]
        drag_center_y = pos[1] - self.drag_offset_y + self.ROW_HEIGHT // 2

        # Clamp to first/last row if dragging beyond bounds
        if rows:
            if drag_center_y < rows[0].rect.top:
                target_index = rows[0].index
            elif drag_center_y >= rows[-1].rect.bottom:
                target_index = rows[-1].index
            else:
                target_index = self.dragging_layer
                for row in rows:
                    if row.rect.top <= drag_center_y < row.rect.bottom:
                        target_index = row.index
                        break
        else:
            return

        if target_index == self.dragging_layer:
            return

        layers = state.canvas.layers
        layers[self.dragging_layer], layers[target_index] = layers[target_index], layers[self.dragging_layer]

        if state.canvas.active_index == self.dragging_layer:
            state.canvas.active_index = target_index
        elif state.canvas.active_index == target_index:
            state.canvas.active_index = self.dragging_layer

        self.dragging_layer = target_index
        state.canvas._mark_dirty()

        display_position = next(
            (idx for idx, (actual_idx, _) in enumerate(state.canvas.layers_for_display()) if actual_idx == target_index),
            0,
        )
        state.set_status(f"Moved layer to position {display_position + 1}")

        new_rows, _, _ = self._prepare_layer_layout(state)
        self.layer_rows = new_rows


    def handle_key_down(self, event: pg.event.Event, state: AppState) -> bool:
        """Handle keyboard input for layer name editing.
        
        Returns True if the event was handled.
        """
        if self.editing_layer is None:
            return False
        
        if event.key == pg.K_RETURN or event.key == pg.K_KP_ENTER:
            # Apply new name
            if self.layer_name_input.strip():
                layer = state.canvas.layers[self.editing_layer]
                old_name = layer.name
                layer.name = self.layer_name_input.strip()
                state.set_status(f"Renamed '{old_name}' to '{layer.name}'")
            self.editing_layer = None
            return True
        elif event.key == pg.K_ESCAPE:
            # Cancel editing
            state.set_status("Layer rename cancelled")
            self.editing_layer = None
            return True
        elif event.key == pg.K_BACKSPACE:
            if self.layer_name_cursor_pos > 0:
                self.layer_name_input = self.layer_name_input[:self.layer_name_cursor_pos-1] + self.layer_name_input[self.layer_name_cursor_pos:]
                self.layer_name_cursor_pos -= 1
                self.layer_name_cursor_blink_time = 0
            return True
        elif event.key == pg.K_LEFT:
            if self.layer_name_cursor_pos > 0:
                self.layer_name_cursor_pos -= 1
                self.layer_name_cursor_blink_time = 0
            return True
        elif event.key == pg.K_RIGHT:
            if self.layer_name_cursor_pos < len(self.layer_name_input):
                self.layer_name_cursor_pos += 1
                self.layer_name_cursor_blink_time = 0
            return True
        elif event.key == pg.K_HOME:
            self.layer_name_cursor_pos = 0
            self.layer_name_cursor_blink_time = 0
            return True
        elif event.key == pg.K_END:
            self.layer_name_cursor_pos = len(self.layer_name_input)
            self.layer_name_cursor_blink_time = 0
            return True
        elif event.key == pg.K_DELETE:
            if self.layer_name_cursor_pos < len(self.layer_name_input):
                self.layer_name_input = self.layer_name_input[:self.layer_name_cursor_pos] + self.layer_name_input[self.layer_name_cursor_pos+1:]
                self.layer_name_cursor_blink_time = 0
            return True
        else:
            # Add character if it's valid
            char = event.unicode
            if char and char.isprintable() and len(self.layer_name_input) < 30:
                self.layer_name_input = self.layer_name_input[:self.layer_name_cursor_pos] + char + self.layer_name_input[self.layer_name_cursor_pos:]
                self.layer_name_cursor_pos += 1
                self.layer_name_cursor_blink_time = 0
            return True


    def _handle_layer_button(self, state: AppState, button_name: str) -> None:
        """Handle layer button clicks (add/delete)."""
        if button_name == "add":
            state.canvas.add_layer()
            state.set_status(f"Added layer: {state.canvas.active_layer.name}")
        elif button_name == "delete":
            if state.canvas.remove_layer():
                state.set_status(f"Deleted layer. Active: {state.canvas.active_layer.name}")
            else:
                state.set_status("Cannot delete the only layer")


class Renderer:
    def __init__(self, screen: pg.Surface, fonts: Dict[str, pg.font.Font]) -> None:
        self.screen = screen
        self.fonts = fonts


    def draw_canvas(self, state: AppState, tool_manager: ToolManager) -> pg.Rect:
        workspace = workspace_rect(self.screen.get_size())
        canvas_rect = state.canvas_rect()
        pixel_size = state.pixel_size()


        checker = pg.transform.scale(
            state.canvas.checker,
            (canvas_rect.width, canvas_rect.height),
        )
        composite = state.canvas.composite_surface()
        pixels = pg.transform.scale(
            composite,
            (canvas_rect.width, canvas_rect.height),
        )
        self.screen.blit(checker, canvas_rect.topleft)
        self.screen.blit(pixels, canvas_rect.topleft)


        if state.show_grid and pixel_size >= 6:
            for x in range(state.canvas.width + 1):
                px = canvas_rect.left + x * pixel_size
                pg.draw.line(
                    self.screen,
                    GRID_COLOR,
                    (px, canvas_rect.top),
                    (px, canvas_rect.bottom),
                    width=1,
                )
            for y in range(state.canvas.height + 1):
                py = canvas_rect.top + y * pixel_size
                pg.draw.line(
                    self.screen,
                    GRID_COLOR,
                    (canvas_rect.left, py),
                    (canvas_rect.right, py),
                    width=1,
                )


        if state.selection and not state.selection.is_empty():
            overlay = pg.Surface(canvas_rect.size, pg.SRCALPHA)
            for x, y in state.selection.points:
                rect = pg.Rect(
                    (x * pixel_size, y * pixel_size),
                    (pixel_size, pixel_size),
                )
                pg.draw.rect(overlay, SELECTION_FILL, rect)
                pg.draw.rect(overlay, SELECTION_BORDER, rect, width=1)
            self.screen.blit(overlay, canvas_rect.topleft)


        tool_manager.active.draw_overlay(self.screen, state, canvas_rect, pixel_size)


        if state.hover_cell:
            hx = canvas_rect.left + state.hover_cell[0] * pixel_size
            hy = canvas_rect.top + state.hover_cell[1] * pixel_size
            center_point = (hx + pixel_size / 2, hy + pixel_size / 2)
            if workspace.collidepoint(center_point):
                pg.draw.rect(
                    self.screen,
                    HOVER_OUTLINE,
                    pg.Rect(hx, hy, pixel_size, pixel_size),
                    width=2,
                )


        pg.draw.rect(self.screen, CANVAS_BORDER, canvas_rect, width=2)
        return canvas_rect


    def draw_status(self, state: AppState, active_tool: str) -> None:
        width, height = self.screen.get_size()
        status_rect = pg.Rect(0, height - STATUS_BAR_HEIGHT, width, STATUS_BAR_HEIGHT)
        pg.draw.rect(self.screen, STATUS_BG, status_rect)
        layer = state.canvas.active_layer
        text = (
            f"Tool: {TOOL_LABELS.get(active_tool, active_tool)} "
            f"| Frame {state.frame_index + 1}/{state.frame_count} "
            f"| Layer {layer.name} ({state.canvas.active_index + 1}/{len(state.canvas.layers)}) "
            f"| Brush {state.brush_size()} "
            f"| Zoom x{state.pixel_size()} "
            f"| {state.status}"
        )
        surface = self.fonts["status"].render(text, True, STATUS_TEXT)
        self.screen.blit(surface, (16, height - STATUS_BAR_HEIGHT + 8))




def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pixel art editor prototype")
    parser.add_argument("--width", type=int, default=64, help="Canvas width in pixels")
    parser.add_argument("--height", type=int, default=64, help="Canvas height in pixels")
    parser.add_argument(
        "--save-dir",
        type=Path,
        default=Path("exports"),
        help="Directory for PNG exports",
    )
    parser.add_argument(
        "--title",
        default="Codex Pixel Studio",
        help="Window title",
    )
    return parser.parse_args()




def cell_from_pos(state: AppState, pos: Tuple[int, int]) -> Optional[Point]:
    canvas_rect = state.canvas_rect()
    if not canvas_rect.collidepoint(pos):
        return None
    rel_x = pos[0] - canvas_rect.left
    rel_y = pos[1] - canvas_rect.top
    pixel_size = state.pixel_size()
    cell_x = rel_x // pixel_size
    cell_y = rel_y // pixel_size
    if state.canvas.in_bounds(int(cell_x), int(cell_y)):
        return int(cell_x), int(cell_y)
    return None




def save_canvas(state: AppState, save_dir: Optional[Path] = None) -> Optional[Path]:
    """
    Save canvas with file dialog or to specified directory.
    
    Args:
        save_dir: Directory to save to (if None, uses file dialog)
        
    Returns:
        Path to saved file or None if cancelled
    """
    if save_dir:
        # Original behavior - save to specified directory with timestamp
        timestamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"pixel_art_{timestamp}.png"
        destination = (save_dir / filename).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        pg.image.save(state.canvas.export_surface(), destination.as_posix())
        return destination
    else:
        # Use file dialog to let user choose location
        default_name = f"pixel_art_{_dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        file_path = save_image_file_dialog(default_name)
        
        if file_path:
            try:
                pg.image.save(state.canvas.export_surface(), file_path)
                return Path(file_path)
            except Exception as e:
                print(f"Error saving image: {e}")
                return None
        else:
            return None  # User cancelled




def main() -> None:
    args = parse_args()
    pg.init()
    screen = pg.display.set_mode(WINDOW_SIZE, pg.RESIZABLE)
    pg.display.set_caption(args.title)


    fonts = {
        "title": pg.font.SysFont("bahnschrift", 36),
        "label": pg.font.SysFont("bahnschrift", 32),
        "small": pg.font.SysFont("bahnschrift", 28),
        "status": pg.font.SysFont("consolas", 32),
    }


    # Initialize palette system (Piskel-style)
    palette_manager = PaletteManager()
    
    frame_stack = FrameStack(args.width, args.height)
    state = AppState(frame_stack=frame_stack)
    state.center_canvas(screen.get_size())
    tool_manager = ToolManager()
    frames_panel = FramesPanelUI(WINDOW_SIZE[1])
    sidebar = SidebarUI(WINDOW_SIZE[1], palette_manager)
    right_panel = RightPanelUI(WINDOW_SIZE)
    renderer = Renderer(screen, fonts)
    color_picker = ColorPicker()
    palette_editor = PaletteEditorUI()
    palette_browser = PaletteBrowserUI()
    export_dialog = ExportDialog()
    resize_dialog = ResizeDialog()
    color_picker_target: Optional[str] = None  # Track if we're editing 'primary' or 'secondary'
    
    # Initialize history system (stores up to 50 states)
    history = History(max_size=50)
    # Save initial state
    history.push(state.frame_stack.clone())
    # Track if canvas was modified (for history saving)
    canvas_modified = False


    clock = pg.time.Clock()
    running = True


    while running:
        clock.tick(FPS)
        window_size = screen.get_size()
        workspace = workspace_rect(window_size)
        mouse_pos = pg.mouse.get_pos()
        state.hover_cell = cell_from_pos(state, mouse_pos)
        
        # Update animation player
        state.animation_player.update()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False
            elif event.type == pg.VIDEORESIZE:
                new_width = max(event.w, FRAMES_PANEL_WIDTH + SIDEBAR_WIDTH + RIGHT_PANEL_WIDTH + 400)
                new_height = max(event.h, 600)
                screen = pg.display.set_mode((new_width, new_height), pg.RESIZABLE)
                renderer = Renderer(screen, fonts)
                frames_panel.resize(new_height)
                sidebar = SidebarUI(new_height, palette_manager)
                right_panel.resize((new_width, new_height))
                state.ensure_visible((new_width, new_height))
            elif event.type == pg.KEYDOWN:
                # Handle resize dialog keyboard input first
                if resize_dialog.active:
                    resize_dialog.handle_key_down(event)
                    continue
                
                # Handle palette editor keyboard input first
                if palette_editor.active:
                    palette_editor.handle_key_down(event)
                    continue
                
                # Handle color picker keyboard input
                if color_picker.active:
                    color_picker.handle_key_down(event)
                    continue
                
                # Handle layer name editing
                if right_panel.handle_key_down(event, state):
                    continue
                
                mods = pg.key.get_mods()
                if event.key == pg.K_ESCAPE:
                    running = False
                elif event.key == pg.K_z and mods & pg.KMOD_CTRL and mods & pg.KMOD_SHIFT:
                    # Redo (Ctrl+Shift+Z)
                    restored_stack = history.redo()
                    if restored_stack:
                        state.frame_stack = restored_stack
                        state.selection = None
                        state.hover_cell = None
                        state.set_status(f"Redo ({history.current_index + 1}/{len(history.states)})")
                    else:
                        state.set_status("Nothing to redo")
                elif event.key == pg.K_z and mods & pg.KMOD_CTRL:
                    # Undo (Ctrl+Z)
                    restored_stack = history.undo()
                    if restored_stack:
                        state.frame_stack = restored_stack
                        state.selection = None
                        state.hover_cell = None
                        state.set_status(f"Undo ({history.current_index + 1}/{len(history.states)})")
                    else:
                        state.set_status("Nothing to undo")
                elif event.key == pg.K_s and mods & pg.KMOD_CTRL:
                    # Save image with file dialog (Ctrl+S)
                    state.set_status("Opening save dialog...")
                    try:
                        pg.event.set_grab(False)
                        pg.mouse.set_visible(True)
                        pg.display.iconify()
                    except Exception:
                        pass
                    saved = save_canvas(state)  # Use file dialog
                    try:
                        screen = pg.display.set_mode(window_size, pg.RESIZABLE)
                    except Exception:
                        pass
                    if saved:
                        try:
                            rel = saved.relative_to(Path.cwd())
                            state.set_status(f"Saved {rel}")
                        except ValueError:
                            state.set_status(f"Saved {saved}")
                    else:
                        state.set_status("Save cancelled")
                elif event.key == pg.K_e and mods & pg.KMOD_CTRL:
                    # Open export dialog (Ctrl+E)
                    export_dialog.open(window_size, state.canvas.width, state.canvas.height)
                    state.set_status("Export dialog opened (Ctrl+E)")
                elif event.key == pg.K_r and mods & pg.KMOD_CTRL:
                    # Open resize dialog (Ctrl+R)
                    resize_dialog.open(window_size, state.canvas.width, state.canvas.height)
                    state.set_status("Resize dialog opened (Ctrl+R)")
                elif event.key == pg.K_l and mods & pg.KMOD_CTRL:
                    # Load image (Ctrl+L)
                    state.set_status("Opening file dialog...")
                    image_path = open_image_file_dialog()
                    if image_path:
                        try:
                            result = load_image_to_canvas(image_path)
                            if result:
                                surface, width, height = result
                                new_stack = create_frame_stack_from_image(surface, width, height)
                                state.frame_stack = new_stack
                                state.selection = None
                                history.push(state.frame_stack.clone())
                                filename = Path(image_path).name
                                state.set_status(f"Loaded image: {filename} ({width}×{height})")
                            else:
                                state.set_status("Failed to load image")
                        except Exception as e:
                            print(f"\nError loading image: {e}")
                            traceback.print_exc()
                            state.set_status(f"Error loading image: {str(e)}")
                    else:
                        state.set_status("Load cancelled")
                elif event.key == pg.K_g:
                    state.show_grid = not state.show_grid
                    state.set_status(f"Grid {'enabled' if state.show_grid else 'disabled'}")
                elif event.key == pg.K_SPACE:
                    # Space bar to toggle animation play/pause
                    if state.frame_stack.count > 1:
                        state.animation_player.toggle()
                        state.set_status("Animation playing" if state.animation_player.playing else "Animation paused")
                    else:
                        state.set_status("Need at least 2 frames to play animation")
                elif event.key == pg.K_PERIOD:
                    # Period (.) to stop animation and reset to first frame
                    state.animation_player.reset()
                    state.set_status("Animation stopped and reset")
                elif event.key == pg.K_COMMA:
                    # Comma (,) to decrease FPS
                    new_fps = max(1, state.animation_player.fps - 1)
                    state.animation_player.set_fps(new_fps)
                    state.set_status(f"Animation FPS: {new_fps}")
                elif event.key == pg.K_SLASH:
                    # Slash (/) to increase FPS
                    new_fps = min(60, state.animation_player.fps + 1)
                    state.animation_player.set_fps(new_fps)
                    state.set_status(f"Animation FPS: {new_fps}")
                elif event.key == pg.K_d and mods & pg.KMOD_CTRL:
                    state.clear_selection()
                elif event.key == pg.K_a and mods & pg.KMOD_CTRL:
                    all_points = {(x, y) for y in range(state.canvas.height) for x in range(state.canvas.width)}
                    state.set_selection(Selection(all_points))
                elif event.key == pg.K_LEFTBRACKET:
                    state.brush_index = max(0, state.brush_index - 1)
                    state.set_status(f"Brush size {state.brush_size()}")
                elif event.key == pg.K_RIGHTBRACKET:
                    state.brush_index = min(len(BRUSH_SIZES) - 1, state.brush_index + 1)
                    state.set_status(f"Brush size {state.brush_size()}")
            elif event.type == pg.MOUSEWHEEL:
                # Handle palette browser scroll first if active
                if palette_browser.active:
                    palette_browser.handle_scroll(event.y)
                    continue
                
                mouse_pos = pg.mouse.get_pos()
                if frames_panel.rect.collidepoint(mouse_pos):
                    # Scroll the frames panel
                    scroll_amount = event.y * 30  # Scroll speed
                    frames_panel.scroll_offset = int(clamp(frames_panel.scroll_offset - scroll_amount, 0, frames_panel.max_scroll))
                elif right_panel.rect.collidepoint(mouse_pos):
                    # Scroll the layers panel
                    scroll_amount = event.y * 30  # Scroll speed
                    right_panel.layers_scroll_offset = int(clamp(right_panel.layers_scroll_offset - scroll_amount, 0, right_panel.layers_max_scroll))
                elif sidebar.rect.collidepoint(mouse_pos):
                    # Scroll the palette
                    scroll_amount = event.y * 30  # Scroll speed
                    sidebar.palette_scroll_offset = int(clamp(sidebar.palette_scroll_offset - scroll_amount, 0, sidebar.palette_max_scroll))
            elif event.type == pg.MOUSEBUTTONDOWN:
                # Handle resize dialog first if it's active
                if resize_dialog.active:
                    if resize_dialog.handle_mouse_down(event.pos, event.button):
                        # Check if resize button was clicked
                        if resize_dialog.resize_button_rect.collidepoint(event.pos):
                            # Perform resize
                            new_width, new_height, anchor = resize_dialog.get_resize_params()
                            try:
                                new_stack = resize_frame_stack(state.frame_stack, new_width, new_height, anchor)
                                state.frame_stack = new_stack
                                state.selection = None
                                history.push(state.frame_stack.clone())
                                state.set_status(f"Canvas resized to {new_width}×{new_height}")
                                resize_dialog.close()
                            except Exception as e:
                                print("\n" + "="*60)
                                print("RESIZE ERROR:")
                                print("="*60)
                                traceback.print_exc()
                                print("="*60 + "\n")
                                state.set_status(f"Resize failed: {str(e)}")
                    continue
                
                # Handle export dialog if it's active
                if export_dialog.active:
                    if export_dialog.handle_mouse_down(event.pos, event.button):
                        # Check if Save button was clicked
                        if export_dialog.Save_button_rect.collidepoint(event.pos):
                            # Perform export with file dialog
                            state.set_status("Opening export dialog...")
                            try:
                                pg.event.set_grab(False)
                                pg.mouse.set_visible(True)
                                pg.display.iconify()
                            except Exception:
                                pass
                            
                            # Get all frames as surfaces
                            frames = []
                            for frame in state.frame_stack.frames:
                                frames.append(frame.canvas.export_surface())
                            
                            # Generate default filename
                            base_name = f"pixel_art_{_dt.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                            
                            # Determine filename based on export format
                            if export_dialog.export_format == "gif":
                                default_filename = f"{base_name}.gif"
                            elif export_dialog.export_format == "zip":
                                default_filename = f"{base_name}_frames.zip"
                            else:  # png
                                if export_dialog.spritesheet_mode:
                                    default_filename = f"{base_name}_spritesheet.png"
                                else:
                                    default_filename = f"{base_name}.png"
                            
                            # Open file dialog
                            file_path = save_export_file_dialog(default_filename, export_dialog.export_format)
                            try:
                                screen = pg.display.set_mode(window_size, pg.RESIZABLE)
                            except Exception:
                                pass
                            
                            if file_path:
                                try:
                                    filepath = Path(file_path)
                                    
                                    # Export based on format
                                    if export_dialog.export_format == "gif":
                                        export_gif(frames, filepath, export_dialog.scale, duration=100, loop=export_dialog.loop_gif)
                                        state.set_status(f"Exported GIF: {filepath.name}")
                                    elif export_dialog.export_format == "png":
                                        if export_dialog.spritesheet_mode:
                                            export_spritesheet(frames, filepath, export_dialog.scale)
                                            state.set_status(f"Exported spritesheet: {filepath.name}")
                                        else:
                                            # Export current frame only
                                            export_single_png(state.canvas.export_surface(), filepath, export_dialog.scale)
                                            state.set_status(f"Exported PNG: {filepath.name}")
                                    elif export_dialog.export_format == "zip":
                                        export_zip(frames, filepath, export_dialog.scale, base_name)
                                        state.set_status(f"Exported ZIP: {filepath.name}")
                                    
                                    export_dialog.close()
                                except Exception as e:
                                    state.set_status(f"Export failed: {str(e)}")
                            else:
                                state.set_status("Export cancelled")
                            continue
                
                # Handle palette browser if it's active
                if palette_browser.active:
                    result = palette_browser.handle_mouse_down(event.pos, palette_manager)
                    if result == 'load':
                        state.set_status(f"Loaded palette: {palette_manager.active_palette.name}")
                    elif result == 'delete':
                        state.set_status("Palette file deleted")
                    continue
                
                # Handle palette editor if it's active
                if palette_editor.active:
                    if palette_editor.handle_mouse_down(event.pos, event.button, state):
                        continue
                
                # Handle color picker first if it's active
                if color_picker.active:
                    # Store which color we're editing before potentially closing the picker
                    was_editing_primary = color_picker_target == "primary"
                    result = color_picker.handle_mouse_down(event.pos)
                    if result is not None:
                        action, color = result
                        if action == 'ok':
                            # User clicked OK - apply the color
                            if was_editing_primary:
                                state.primary_color = color
                                state.set_status("Primary color updated")
                            else:
                                state.secondary_color = color
                                state.set_status("Secondary color updated")
                            color_picker_target = None
                        elif action == 'cancel':
                            # User clicked Cancel
                            color_picker_target = None
                        elif action == 'add':
                            # User clicked Add to Palette - add color to global palette
                            if color not in PALETTE_COLORS:
                                # Add to the end of the palette
                                PALETTE_COLORS.append(color)
                                state.set_status(f"Color #{color_picker._color_to_hex(color)} added to palette")
                            else:
                                state.set_status("Color already in palette")
                            # Don't close the picker, user can continue adjusting
                    continue
                
                # Store target when opening color picker
                old_active = color_picker.active
                if frames_panel.handle_mouse_down(state, event.pos, event.button, window_size):
                    # Frame operations (add, delete, duplicate, reorder) occurred
                    history.push(state.frame_stack.clone())
                    continue
                if sidebar.handle_mouse_down(state, tool_manager, event.pos, event.button, color_picker, window_size, palette_editor, palette_browser):
                    # Check if color picker was just opened
                    if not old_active and color_picker.active:
                        # Determine which color box was clicked
                        if sidebar.primary_rect.collidepoint(event.pos) and event.button == 1:
                            color_picker_target = "primary"
                        elif sidebar.secondary_rect.collidepoint(event.pos) and event.button == 3:
                            color_picker_target = "secondary"
                    continue
                if right_panel.handle_mouse_down(state, event.pos, event.button, window_size, workspace):
                    # Check if export button was clicked
                    if right_panel.export_button_rect.collidepoint(event.pos) and event.button == 1:
                        export_dialog.open(window_size, state.canvas.width, state.canvas.height)
                        state.set_status("Export dialog opened")
                    else:
                        # Layer operations (add, delete, reorder, visibility) occurred
                        history.push(state.frame_stack.clone())
                    continue
                
                # Don't allow canvas interaction if any modal is open
                if resize_dialog.active or export_dialog.active or palette_editor.active or palette_browser.active or color_picker.active:
                    continue
                
                cell = cell_from_pos(state, event.pos)
                # Mark that we're starting a potential drawing operation
                canvas_modified = True
                tool_manager.active.on_mouse_down(
                    state,
                    cell,
                    event.button,
                    event.pos,
                    window_size,
                )
            elif event.type == pg.MOUSEBUTTONUP:
                if resize_dialog.active:
                    continue
                if export_dialog.active:
                    export_dialog.handle_mouse_up(event.pos)
                    continue
                if palette_browser.active:
                    palette_browser.handle_mouse_up(event.pos)
                    continue
                if palette_editor.active:
                    palette_editor.handle_mouse_up()
                    continue
                if color_picker.active:
                    color_picker.handle_mouse_up()
                    continue
                frames_panel.handle_mouse_up(state)
                sidebar.handle_mouse_up()
                right_panel.handle_mouse_up()
                tool_manager.active.on_mouse_up(state, event.button)
                # Save to history after drawing operation completes
                if canvas_modified:
                    history.push(state.frame_stack.clone())
                    canvas_modified = False
            elif event.type == pg.MOUSEMOTION:
                if resize_dialog.active:
                    continue
                if export_dialog.active:
                    export_dialog.handle_mouse_move(event.pos)
                    continue
                if palette_browser.active:
                    palette_browser.handle_mouse_move(event.pos)
                    continue
                if palette_editor.active:
                    palette_editor.handle_mouse_move(event.pos)
                    continue
                if color_picker.active:
                    color_picker.handle_mouse_move(event.pos)
                    continue
                frames_panel.handle_mouse_move(state, event.pos, window_size)
                sidebar.handle_mouse_move(event.pos)
                right_panel.handle_mouse_move(event.pos, state)
                buttons = pg.mouse.get_pressed(3)
                cell = cell_from_pos(state, event.pos)
                tool_manager.active.on_mouse_move(
                    state,
                    cell,
                    buttons,
                    event.pos,
                    window_size,
                )


        screen.fill(WINDOW_BG)
        renderer.draw_canvas(state, tool_manager)
        frames_panel.render(screen, fonts, state)
        sidebar.render(screen, fonts, state, tool_manager.active_name)
        right_panel.render(screen, fonts, state, workspace)
        renderer.draw_status(state, tool_manager.active_name)
        # Render color picker on top of everything else
        color_picker.render(screen, fonts)
        # Render palette editor on top of color picker
        palette_editor.render(screen, fonts)
        # Render palette browser on top of palette editor
        palette_browser.render(screen, fonts)
        # Render export dialog on top of everything
        export_dialog.render(screen, fonts)
        # Render resize dialog on top of export dialog
        resize_dialog.render(screen, fonts)
        pg.display.flip()


    pg.quit()




if __name__ == "__main__":
    main()