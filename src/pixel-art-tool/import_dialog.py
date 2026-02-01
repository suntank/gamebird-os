"""
Import dialog for pixel art app - supports importing images as single image or spritesheet.
"""
from typing import Optional, Tuple, Dict, List
import pygame as pg
from pathlib import Path
from PIL import Image
import io

# UI Colors
SIDEBAR_BG = (38, 42, 48)
SIDEBAR_ACCENT = (94, 172, 248)
SIDEBAR_TEXT = (238, 240, 244)
SIDEBAR_MUTED = (150, 158, 168)
STATUS_BG = (24, 26, 30)
CANVAS_BORDER = (72, 76, 82)


class ImportDialog:
    """Dialog for importing images as single image or spritesheet."""
    
    def __init__(self) -> None:
        self.active = False
        self.dialog_rect = pg.Rect(0, 0, 500, 450)
        
        # Import settings
        self.import_mode = "single"  # "single" or "spritesheet"
        self.smooth_resize = True
        
        # Single image settings
        self.resize_width = 32
        self.resize_height = 32
        
        # Spritesheet settings
        self.frame_width = 32
        self.frame_height = 32
        self.offset_x = 0
        self.offset_y = 0
        
        # Loaded image data
        self.image_path: Optional[Path] = None
        self.image_name = ""
        self.original_image: Optional[Image.Image] = None
        self.original_width = 0
        self.original_height = 0
        self.preview_surface: Optional[pg.Surface] = None
        
        # UI elements
        self.close_button_rect = pg.Rect(0, 0, 0, 0)
        self.single_radio_rect = pg.Rect(0, 0, 0, 0)
        self.spritesheet_radio_rect = pg.Rect(0, 0, 0, 0)
        self.smooth_checkbox_rect = pg.Rect(0, 0, 0, 0)
        self.import_button_rect = pg.Rect(0, 0, 0, 0)
        
        # Input fields rects
        self.resize_width_rect = pg.Rect(0, 0, 0, 0)
        self.resize_height_rect = pg.Rect(0, 0, 0, 0)
        self.frame_width_rect = pg.Rect(0, 0, 0, 0)
        self.frame_height_rect = pg.Rect(0, 0, 0, 0)
        self.offset_x_rect = pg.Rect(0, 0, 0, 0)
        self.offset_y_rect = pg.Rect(0, 0, 0, 0)
        
        # Text input state
        self.editing_field: Optional[str] = None
        self.input_text = ""
        self.cursor_blink_time = 0
        
        # Preview rect
        self.preview_rect = pg.Rect(0, 0, 0, 0)
        
    def open(self, window_size: Tuple[int, int], image_path: Path) -> bool:
        """Open the import dialog with the specified image. Returns False if image couldn't be loaded."""
        try:
            self.original_image = Image.open(image_path)
            self.original_image = self.original_image.convert("RGBA")
            self.original_width, self.original_height = self.original_image.size
            self.image_path = image_path
            self.image_name = image_path.name
            
            # Set default resize to original dimensions
            self.resize_width = self.original_width
            self.resize_height = self.original_height
            
            # Create preview surface
            self._update_preview()
            
            self.active = True
            self.editing_field = None
            
            # Center dialog
            self.dialog_rect.center = (window_size[0] // 2, window_size[1] // 2)
            
            # Layout UI elements
            self._layout_elements()
            return True
            
        except Exception as e:
            print(f"Failed to load image: {e}")
            return False
    
    def close(self) -> None:
        """Close the import dialog."""
        self.active = False
        self.editing_field = None
        self.original_image = None
        self.preview_surface = None
    
    def _update_preview(self) -> None:
        """Update the preview surface from the original image."""
        if self.original_image is None:
            return
        
        # Scale to fit preview area (max 100x100)
        max_size = 100
        scale = min(max_size / self.original_width, max_size / self.original_height, 1.0)
        preview_w = max(1, int(self.original_width * scale))
        preview_h = max(1, int(self.original_height * scale))
        
        preview_img = self.original_image.resize((preview_w, preview_h), Image.Resampling.NEAREST)
        
        # Convert PIL image to pygame surface
        mode = preview_img.mode
        size = preview_img.size
        data = preview_img.tobytes()
        self.preview_surface = pg.image.fromstring(data, size, mode)
    
    def _layout_elements(self) -> None:
        """Layout all UI elements within the dialog."""
        margin = 20
        left = self.dialog_rect.left + margin
        
        # Close button (X) in top right
        self.close_button_rect = pg.Rect(
            self.dialog_rect.right - 40,
            self.dialog_rect.top + 10,
            30, 30
        )
        
        # Single image radio button
        radio_y = self.dialog_rect.top + 80
        radio_size = 16
        self.single_radio_rect = pg.Rect(left, radio_y, radio_size, radio_size)
        
        # Resize inputs (below single image option)
        input_y = radio_y + 30
        input_width = 50
        input_height = 28
        
        self.resize_width_rect = pg.Rect(left + 80, input_y, input_width, input_height)
        self.resize_height_rect = pg.Rect(left + 160, input_y, input_width, input_height)
        
        # Smooth resize checkbox
        self.smooth_checkbox_rect = pg.Rect(left + 20, input_y + 40, 20, 20)
        
        # Spritesheet radio button
        sprite_y = input_y + 90
        self.spritesheet_radio_rect = pg.Rect(left, sprite_y, radio_size, radio_size)
        
        # Frame size inputs
        frame_input_y = sprite_y + 30
        self.frame_width_rect = pg.Rect(left + 80, frame_input_y, input_width, input_height)
        self.frame_height_rect = pg.Rect(left + 160, frame_input_y, input_width, input_height)
        
        # Offset inputs
        offset_y = frame_input_y + 40
        self.offset_x_rect = pg.Rect(left + 80, offset_y, input_width, input_height)
        self.offset_y_rect = pg.Rect(left + 160, offset_y, input_width, input_height)
        
        # Preview area (right side)
        self.preview_rect = pg.Rect(
            self.dialog_rect.right - margin - 120,
            self.dialog_rect.top + 80,
            120, 120
        )
        
        # Import button (bottom right)
        self.import_button_rect = pg.Rect(
            self.dialog_rect.right - margin - 80,
            self.dialog_rect.bottom - margin - 40,
            80, 40
        )
    
    def handle_mouse_down(self, pos: Tuple[int, int], button: int) -> bool:
        """Handle mouse down events. Returns True if event was handled."""
        if not self.active:
            return False
        
        # Only handle events if mouse is within dialog bounds
        if not self.dialog_rect.collidepoint(pos):
            return False
        
        if button == 1:
            # Close any active text editing first
            self._commit_text_input()
            
            # Check close button
            if self.close_button_rect.collidepoint(pos):
                self.close()
                return True
            
            # Check radio buttons
            if self.single_radio_rect.collidepoint(pos) or self._single_label_hit(pos):
                self.import_mode = "single"
                return True
            if self.spritesheet_radio_rect.collidepoint(pos) or self._spritesheet_label_hit(pos):
                self.import_mode = "spritesheet"
                return True
            
            # Check smooth resize checkbox
            if self.smooth_checkbox_rect.collidepoint(pos):
                self.smooth_resize = not self.smooth_resize
                return True
            
            # Check input fields
            input_fields = [
                ("resize_width", self.resize_width_rect, self.resize_width),
                ("resize_height", self.resize_height_rect, self.resize_height),
                ("frame_width", self.frame_width_rect, self.frame_width),
                ("frame_height", self.frame_height_rect, self.frame_height),
                ("offset_x", self.offset_x_rect, self.offset_x),
                ("offset_y", self.offset_y_rect, self.offset_y),
            ]
            
            for field_name, rect, value in input_fields:
                if rect.collidepoint(pos):
                    self.editing_field = field_name
                    self.input_text = str(value)
                    return True
            
            # Check import button
            if self.import_button_rect.collidepoint(pos):
                return True  # Will be handled by caller
        
        return False
    
    def _single_label_hit(self, pos: Tuple[int, int]) -> bool:
        """Check if click is on single image label area."""
        label_rect = pg.Rect(
            self.single_radio_rect.right + 5,
            self.single_radio_rect.top - 2,
            150, 20
        )
        return label_rect.collidepoint(pos)
    
    def _spritesheet_label_hit(self, pos: Tuple[int, int]) -> bool:
        """Check if click is on spritesheet label area."""
        label_rect = pg.Rect(
            self.spritesheet_radio_rect.right + 5,
            self.spritesheet_radio_rect.top - 2,
            150, 20
        )
        return label_rect.collidepoint(pos)
    
    def _commit_text_input(self) -> None:
        """Commit the current text input to the appropriate field."""
        if self.editing_field is None:
            return
        
        try:
            value = max(1, int(self.input_text)) if self.input_text else 1
        except ValueError:
            value = 1
        
        if self.editing_field == "resize_width":
            self.resize_width = value
        elif self.editing_field == "resize_height":
            self.resize_height = value
        elif self.editing_field == "frame_width":
            self.frame_width = value
        elif self.editing_field == "frame_height":
            self.frame_height = value
        elif self.editing_field == "offset_x":
            self.offset_x = max(0, value - 1) if self.input_text else 0  # Allow 0 for offset
        elif self.editing_field == "offset_y":
            self.offset_y = max(0, value - 1) if self.input_text else 0
        
        self.editing_field = None
        self.input_text = ""
    
    def handle_mouse_up(self, pos: Tuple[int, int]) -> None:
        """Handle mouse up events."""
        pass
    
    def handle_mouse_move(self, pos: Tuple[int, int]) -> None:
        """Handle mouse move events."""
        pass
    
    def handle_key(self, event: pg.event.Event) -> bool:
        """Handle keyboard events. Returns True if event was handled."""
        if not self.active:
            return False
        
        if event.key == pg.K_ESCAPE:
            if self.editing_field:
                self.editing_field = None
                self.input_text = ""
            else:
                self.close()
            return True
        
        if event.key == pg.K_RETURN or event.key == pg.K_KP_ENTER:
            self._commit_text_input()
            return True
        
        if event.key == pg.K_TAB:
            self._commit_text_input()
            # Cycle to next field
            fields = ["resize_width", "resize_height", "frame_width", "frame_height", "offset_x", "offset_y"]
            if self.editing_field in fields:
                idx = fields.index(self.editing_field)
                self.editing_field = fields[(idx + 1) % len(fields)]
                value = getattr(self, self.editing_field.replace("_", "_"))
                self.input_text = str(value)
            return True
        
        if self.editing_field:
            if event.key == pg.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
                return True
            elif event.unicode.isdigit():
                self.input_text += event.unicode
                return True
        
        return False
    
    def get_import_result(self) -> Optional[Dict]:
        """Get the import settings as a dictionary."""
        if self.original_image is None:
            return None
        
        return {
            "mode": self.import_mode,
            "image": self.original_image,
            "image_path": self.image_path,
            "smooth_resize": self.smooth_resize,
            "resize_width": self.resize_width,
            "resize_height": self.resize_height,
            "frame_width": self.frame_width,
            "frame_height": self.frame_height,
            "offset_x": self.offset_x,
            "offset_y": self.offset_y,
        }
    
    def render(self, surface: pg.Surface, fonts: Dict[str, pg.font.Font]) -> None:
        """Render the import dialog."""
        if not self.active:
            return
        
        title_font = fonts["title"]
        label_font = fonts["label"]
        small_font = fonts["small"]
        
        # Update cursor blink
        self.cursor_blink_time = (self.cursor_blink_time + 1) % 60
        
        # Semi-transparent overlay
        overlay = pg.Surface(surface.get_size(), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))
        
        # Dialog background with yellow border (like Piskel)
        pg.draw.rect(surface, SIDEBAR_BG, self.dialog_rect, border_radius=0)
        pg.draw.rect(surface, (255, 200, 0), self.dialog_rect, width=3, border_radius=0)
        
        # Title bar
        title_bar = pg.Rect(self.dialog_rect.left, self.dialog_rect.top, self.dialog_rect.width, 50)
        pg.draw.rect(surface, (255, 200, 0), title_bar)
        
        # Title text
        title = title_font.render("Import and Merge", True, (0, 0, 0))
        surface.blit(title, (self.dialog_rect.left + 20, self.dialog_rect.top + 12))
        
        # Close button (X)
        x_text = title_font.render("X", True, (0, 0, 0))
        surface.blit(x_text, x_text.get_rect(center=self.close_button_rect.center))
        
        # File name
        name_y = self.dialog_rect.top + 60
        name_label = label_font.render("Name : ", True, SIDEBAR_TEXT)
        surface.blit(name_label, (self.dialog_rect.left + 20, name_y))
        name_value = label_font.render(self.image_name, True, (255, 200, 0))
        surface.blit(name_value, (self.dialog_rect.left + 20 + name_label.get_width(), name_y))
        
        margin = 20
        left = self.dialog_rect.left + margin
        
        # Single image option
        self._draw_radio(surface, self.single_radio_rect, self.import_mode == "single")
        single_text = label_font.render("Import as single image", True, SIDEBAR_TEXT)
        surface.blit(single_text, (self.single_radio_rect.right + 8, self.single_radio_rect.centery - single_text.get_height() // 2))
        
        # Resize inputs
        resize_y = self.resize_width_rect.centery
        resize_label = label_font.render("Resize to", True, SIDEBAR_TEXT)
        surface.blit(resize_label, (left + 20, resize_y - resize_label.get_height() // 2))
        
        self._draw_input_field(surface, label_font, self.resize_width_rect, 
                               self.resize_width, "resize_width")
        
        x_text = label_font.render("x", True, SIDEBAR_TEXT)
        surface.blit(x_text, (self.resize_width_rect.right + 8, resize_y - x_text.get_height() // 2))
        
        self._draw_input_field(surface, label_font, self.resize_height_rect,
                               self.resize_height, "resize_height")
        
        # Smooth resize checkbox
        self._draw_checkbox(surface, self.smooth_checkbox_rect, self.smooth_resize)
        smooth_text = label_font.render("Smooth resize", True, SIDEBAR_TEXT)
        surface.blit(smooth_text, (self.smooth_checkbox_rect.right + 8, 
                                   self.smooth_checkbox_rect.centery - smooth_text.get_height() // 2))
        
        # Spritesheet option
        self._draw_radio(surface, self.spritesheet_radio_rect, self.import_mode == "spritesheet")
        sprite_text = label_font.render("Import as spritesheet", True, SIDEBAR_TEXT)
        surface.blit(sprite_text, (self.spritesheet_radio_rect.right + 8, 
                                   self.spritesheet_radio_rect.centery - sprite_text.get_height() // 2))
        
        # Frame size inputs
        frame_y = self.frame_width_rect.centery
        frame_label = label_font.render("Frame size", True, SIDEBAR_TEXT)
        surface.blit(frame_label, (left + 20, frame_y - frame_label.get_height() // 2))
        
        self._draw_input_field(surface, label_font, self.frame_width_rect,
                               self.frame_width, "frame_width")
        
        x_text2 = label_font.render("x", True, SIDEBAR_TEXT)
        surface.blit(x_text2, (self.frame_width_rect.right + 8, frame_y - x_text2.get_height() // 2))
        
        self._draw_input_field(surface, label_font, self.frame_height_rect,
                               self.frame_height, "frame_height")
        
        # Offset inputs
        offset_y = self.offset_x_rect.centery
        offset_label = label_font.render("Offset", True, SIDEBAR_TEXT)
        surface.blit(offset_label, (left + 20, offset_y - offset_label.get_height() // 2))
        
        self._draw_input_field(surface, label_font, self.offset_x_rect,
                               self.offset_x, "offset_x")
        
        x_text3 = label_font.render("x", True, SIDEBAR_TEXT)
        surface.blit(x_text3, (self.offset_x_rect.right + 8, offset_y - x_text3.get_height() // 2))
        
        self._draw_input_field(surface, label_font, self.offset_y_rect,
                               self.offset_y, "offset_y")
        
        # Preview area
        pg.draw.rect(surface, STATUS_BG, self.preview_rect)
        pg.draw.rect(surface, CANVAS_BORDER, self.preview_rect, width=1)
        
        if self.preview_surface:
            preview_pos = self.preview_surface.get_rect(center=self.preview_rect.center)
            surface.blit(self.preview_surface, preview_pos)
        
        # Import button
        pg.draw.rect(surface, STATUS_BG, self.import_button_rect, border_radius=4)
        pg.draw.rect(surface, CANVAS_BORDER, self.import_button_rect, width=1, border_radius=4)
        import_text = label_font.render("import", True, SIDEBAR_TEXT)
        surface.blit(import_text, import_text.get_rect(center=self.import_button_rect.center))
    
    def _draw_radio(self, surface: pg.Surface, rect: pg.Rect, selected: bool) -> None:
        """Draw a radio button."""
        pg.draw.circle(surface, SIDEBAR_TEXT, rect.center, rect.width // 2, width=2)
        if selected:
            pg.draw.circle(surface, (255, 100, 100), rect.center, rect.width // 2 - 4)
    
    def _draw_checkbox(self, surface: pg.Surface, rect: pg.Rect, checked: bool) -> None:
        """Draw a checkbox."""
        pg.draw.rect(surface, STATUS_BG, rect, border_radius=2)
        pg.draw.rect(surface, SIDEBAR_TEXT, rect, width=2, border_radius=2)
        if checked:
            # Draw checkmark
            pg.draw.line(surface, (255, 100, 100),
                        (rect.left + 4, rect.centery),
                        (rect.centerx, rect.bottom - 4), 2)
            pg.draw.line(surface, (255, 100, 100),
                        (rect.centerx, rect.bottom - 4),
                        (rect.right - 4, rect.top + 4), 2)
    
    def _draw_input_field(self, surface: pg.Surface, font: pg.font.Font,
                          rect: pg.Rect, value: int, field_name: str) -> None:
        """Draw a numeric input field."""
        is_editing = self.editing_field == field_name
        
        pg.draw.rect(surface, (255, 255, 255) if is_editing else STATUS_BG, rect, border_radius=2)
        pg.draw.rect(surface, SIDEBAR_ACCENT if is_editing else CANVAS_BORDER, rect, width=1, border_radius=2)
        
        if is_editing:
            display_text = self.input_text
            text_color = (0, 0, 0)
            # Draw cursor
            if self.cursor_blink_time < 30:
                text_surface = font.render(display_text, True, text_color)
                cursor_x = rect.left + 4 + text_surface.get_width()
                pg.draw.line(surface, text_color, 
                           (cursor_x, rect.top + 4), 
                           (cursor_x, rect.bottom - 4), 1)
        else:
            display_text = str(value)
            text_color = SIDEBAR_TEXT
        
        text_surface = font.render(display_text, True, text_color)
        surface.blit(text_surface, (rect.left + 4, rect.centery - text_surface.get_height() // 2))
