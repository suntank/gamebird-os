"""
Canvas resize dialog for pixel art app.
"""
from typing import Optional, Tuple, Dict
import pygame as pg

# UI Colors
SIDEBAR_BG = (38, 42, 48)
SIDEBAR_ACCENT = (94, 172, 248)
SIDEBAR_TEXT = (238, 240, 244)
SIDEBAR_MUTED = (150, 158, 168)
STATUS_BG = (24, 26, 30)
CANVAS_BORDER = (72, 76, 82)


class ResizeDialog:
    """Dialog for resizing the canvas."""
    
    def __init__(self) -> None:
        self.active = False
        self.dialog_rect = pg.Rect(0, 0, 550, 500)
        
        # Resize settings
        self.new_width = 32
        self.new_height = 32
        self.current_width = 32
        self.current_height = 32
        
        # Anchor position for resize (where to anchor the existing content)
        self.anchor = "center"  # "center", "top-left", "top-right", "bottom-left", "bottom-right"
        
        # UI elements
        self.width_input_rect = pg.Rect(0, 0, 0, 0)
        self.height_input_rect = pg.Rect(0, 0, 0, 0)
        self.anchor_buttons = {}  # Dict of anchor position -> rect
        self.resize_button_rect = pg.Rect(0, 0, 0, 0)
        self.cancel_button_rect = pg.Rect(0, 0, 0, 0)
        
        # Input editing
        self.editing_field = None  # "width" or "height"
        self.width_input_text = ""
        self.height_input_text = ""
        self.cursor_pos = 0
        self.cursor_blink_time = 0.0
        
    def open(self, window_size: Tuple[int, int], current_width: int, current_height: int) -> None:
        """Open the resize dialog."""
        self.active = True
        self.current_width = current_width
        self.current_height = current_height
        self.new_width = current_width
        self.new_height = current_height
        self.width_input_text = str(current_width)
        self.height_input_text = str(current_height)
        self.editing_field = None
        self.anchor = "center"
        
        # Center dialog
        self.dialog_rect.center = (window_size[0] // 2, window_size[1] // 2)
        
        # Layout UI elements
        self._layout_elements()
    
    def close(self) -> None:
        """Close the resize dialog."""
        self.active = False
        self.editing_field = None
    
    def _layout_elements(self) -> None:
        """Layout all UI elements within the dialog."""
        margin = 20
        
        # Width and height inputs
        input_y = self.dialog_rect.top + 120
        input_width = 120
        input_height = 50
        center_x = self.dialog_rect.centerx
        
        self.width_input_rect = pg.Rect(
            center_x - input_width - 25,
            input_y,
            input_width,
            input_height
        )
        self.height_input_rect = pg.Rect(
            center_x + 25,
            input_y,
            input_width,
            input_height
        )
        
        # Anchor position buttons (3x3 grid)
        anchor_y = input_y + 130
        button_size = 50
        button_gap = 15
        grid_width = button_size * 3 + button_gap * 2
        grid_start_x = self.dialog_rect.centerx - grid_width // 2
        
        anchor_positions = [
            ("top-left", 0, 0),
            ("top-center", 1, 0),
            ("top-right", 2, 0),
            ("center-left", 0, 1),
            ("center", 1, 1),
            ("center-right", 2, 1),
            ("bottom-left", 0, 2),
            ("bottom-center", 1, 2),
            ("bottom-right", 2, 2),
        ]
        
        self.anchor_buttons = {}
        for anchor, col, row in anchor_positions:
            x = grid_start_x + col * (button_size + button_gap)
            y = anchor_y + row * (button_size + button_gap)
            self.anchor_buttons[anchor] = pg.Rect(x, y, button_size, button_size)
        
        # Bottom buttons
        bottom_button_width = 120
        bottom_button_height = 50
        bottom_y = self.dialog_rect.bottom - margin - bottom_button_height
        
        self.resize_button_rect = pg.Rect(
            self.dialog_rect.right - margin - bottom_button_width * 2 - 10,
            bottom_y,
            bottom_button_width,
            bottom_button_height
        )
        self.cancel_button_rect = pg.Rect(
            self.dialog_rect.right - margin - bottom_button_width,
            bottom_y,
            bottom_button_width,
            bottom_button_height
        )
    
    def handle_mouse_down(self, pos: Tuple[int, int], button: int) -> bool:
        """Handle mouse down events. Returns True if event was handled."""
        if not self.active:
            return False
        
        if button == 1:
            # Check input fields
            if self.width_input_rect.collidepoint(pos):
                self.editing_field = "width"
                self.cursor_pos = len(self.width_input_text)
                return True
            elif self.height_input_rect.collidepoint(pos):
                self.editing_field = "height"
                self.cursor_pos = len(self.height_input_text)
                return True
            else:
                self.editing_field = None
            
            # Check anchor buttons
            for anchor, rect in self.anchor_buttons.items():
                if rect.collidepoint(pos):
                    self.anchor = anchor
                    return True
            
            # Check buttons
            if self.cancel_button_rect.collidepoint(pos):
                self.close()
                return True
            elif self.resize_button_rect.collidepoint(pos):
                return True  # Will be handled by caller
        
        return False
    
    def handle_key_down(self, event: pg.event.Event) -> None:
        """Handle keyboard input for text fields."""
        if not self.editing_field:
            return
        
        if event.key == pg.K_ESCAPE:
            self.editing_field = None
        elif event.key == pg.K_RETURN or event.key == pg.K_KP_ENTER:
            # Apply the input
            if self.editing_field == "width":
                try:
                    self.new_width = max(1, min(512, int(self.width_input_text)))
                    self.width_input_text = str(self.new_width)
                except ValueError:
                    self.width_input_text = str(self.new_width)
            elif self.editing_field == "height":
                try:
                    self.new_height = max(1, min(512, int(self.height_input_text)))
                    self.height_input_text = str(self.new_height)
                except ValueError:
                    self.height_input_text = str(self.new_height)
            self.editing_field = None
        elif event.key == pg.K_BACKSPACE:
            if self.editing_field == "width" and self.width_input_text:
                self.width_input_text = self.width_input_text[:-1]
                self.cursor_pos = len(self.width_input_text)
            elif self.editing_field == "height" and self.height_input_text:
                self.height_input_text = self.height_input_text[:-1]
                self.cursor_pos = len(self.height_input_text)
        elif event.unicode.isdigit():
            # Only allow digits
            if self.editing_field == "width":
                self.width_input_text += event.unicode
                self.cursor_pos = len(self.width_input_text)
            elif self.editing_field == "height":
                self.height_input_text += event.unicode
                self.cursor_pos = len(self.height_input_text)
    
    def get_resize_params(self) -> Tuple[int, int, str]:
        """Get the resize parameters (width, height, anchor)."""
        # Parse current text inputs to ensure we use the latest values
        # even if user didn't press Enter
        width = self.new_width
        height = self.new_height
        
        if self.width_input_text:
            try:
                width = max(1, min(512, int(self.width_input_text)))
            except ValueError:
                width = self.new_width
        
        if self.height_input_text:
            try:
                height = max(1, min(512, int(self.height_input_text)))
            except ValueError:
                height = self.new_height
        
        return (width, height, self.anchor)
    
    def render(self, surface: pg.Surface, fonts: Dict[str, pg.font.Font]) -> None:
        """Render the resize dialog."""
        if not self.active:
            return
        
        title_font = fonts["title"]
        label_font = fonts["label"]
        small_font = fonts["small"]
        
        # Update cursor blink
        self.cursor_blink_time += 1 / 60.0
        
        # Semi-transparent overlay
        overlay = pg.Surface(surface.get_size(), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))
        
        # Dialog background
        pg.draw.rect(surface, SIDEBAR_BG, self.dialog_rect, border_radius=10)
        pg.draw.rect(surface, SIDEBAR_ACCENT, self.dialog_rect, width=2, border_radius=10)
        
        # Title
        title = title_font.render("Resize Canvas", True, SIDEBAR_TEXT)
        surface.blit(title, (self.dialog_rect.left + 20, self.dialog_rect.top + 20))
        
        # Current size info
        info_text = small_font.render(f"Current: {self.current_width} × {self.current_height}", True, SIDEBAR_MUTED)
        surface.blit(info_text, (self.dialog_rect.left + 20, self.dialog_rect.top + 60))
        
        # Width label and input
        width_label = label_font.render("Width", True, SIDEBAR_TEXT)
        surface.blit(width_label, (self.width_input_rect.centerx - width_label.get_width() // 2, self.width_input_rect.top - 35))
        
        is_editing_width = self.editing_field == "width"
        border_color = SIDEBAR_ACCENT if is_editing_width else CANVAS_BORDER
        pg.draw.rect(surface, STATUS_BG, self.width_input_rect, border_radius=4)
        pg.draw.rect(surface, border_color, self.width_input_rect, width=2, border_radius=4)
        
        width_text = label_font.render(self.width_input_text or str(self.new_width), True, SIDEBAR_TEXT)
        surface.blit(width_text, width_text.get_rect(center=self.width_input_rect.center))
        
        # Draw cursor for width input
        if is_editing_width and int(self.cursor_blink_time * 2) % 2 == 0:
            cursor_x = self.width_input_rect.centerx + width_text.get_width() // 2 + 2
            cursor_y = self.width_input_rect.centery - 12
            pg.draw.line(surface, SIDEBAR_TEXT, (cursor_x, cursor_y), (cursor_x, cursor_y + 24), 2)
        
        # "×" between inputs
        x_text = label_font.render("×", True, SIDEBAR_TEXT)
        surface.blit(x_text, (self.dialog_rect.centerx - x_text.get_width() // 2, self.width_input_rect.centery - x_text.get_height() // 2))
        
        # Height label and input
        height_label = label_font.render("Height", True, SIDEBAR_TEXT)
        surface.blit(height_label, (self.height_input_rect.centerx - height_label.get_width() // 2, self.height_input_rect.top - 35))
        
        is_editing_height = self.editing_field == "height"
        border_color = SIDEBAR_ACCENT if is_editing_height else CANVAS_BORDER
        pg.draw.rect(surface, STATUS_BG, self.height_input_rect, border_radius=4)
        pg.draw.rect(surface, border_color, self.height_input_rect, width=2, border_radius=4)
        
        height_text = label_font.render(self.height_input_text or str(self.new_height), True, SIDEBAR_TEXT)
        surface.blit(height_text, height_text.get_rect(center=self.height_input_rect.center))
        
        # Draw cursor for height input
        if is_editing_height and int(self.cursor_blink_time * 2) % 2 == 0:
            cursor_x = self.height_input_rect.centerx + height_text.get_width() // 2 + 2
            cursor_y = self.height_input_rect.centery - 12
            pg.draw.line(surface, SIDEBAR_TEXT, (cursor_x, cursor_y), (cursor_x, cursor_y + 24), 2)
        
        # Anchor label
        anchor_label = label_font.render("Anchor Content:", True, SIDEBAR_TEXT)
        first_button_y = list(self.anchor_buttons.values())[0].top
        surface.blit(anchor_label, (self.dialog_rect.left + 20, first_button_y - 35))
        
        # Anchor buttons (3x3 grid)
        for anchor, rect in self.anchor_buttons.items():
            is_selected = anchor == self.anchor
            bg_color = SIDEBAR_ACCENT if is_selected else STATUS_BG
            pg.draw.rect(surface, bg_color, rect, border_radius=4)
            if not is_selected:
                pg.draw.rect(surface, CANVAS_BORDER, rect, width=2, border_radius=4)
            
            # Draw a small square in the button to indicate position
            inner_size = 8
            inner_rect = pg.Rect(0, 0, inner_size, inner_size)
            inner_rect.center = rect.center
            pg.draw.rect(surface, (0, 0, 0) if is_selected else SIDEBAR_TEXT, inner_rect, border_radius=2)
        
        # Bottom buttons
        pg.draw.rect(surface, SIDEBAR_ACCENT, self.resize_button_rect, border_radius=6)
        resize_text = label_font.render("Resize", True, (0, 0, 0))
        surface.blit(resize_text, resize_text.get_rect(center=self.resize_button_rect.center))
        
        pg.draw.rect(surface, CANVAS_BORDER, self.cancel_button_rect, border_radius=6)
        cancel_text = label_font.render("Cancel", True, SIDEBAR_TEXT)
        surface.blit(cancel_text, cancel_text.get_rect(center=self.cancel_button_rect.center))
