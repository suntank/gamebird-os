"""
Export dialog for pixel art app - supports PNG, GIF, and spritesheet exports.
"""
from typing import Optional, Tuple, Dict
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


class ExportDialog:
    """Dialog for exporting artwork as PNG, GIF, or spritesheet."""
    
    def __init__(self) -> None:
        self.active = False
        self.dialog_rect = pg.Rect(0, 0, 500, 600)
        
        # Export settings
        self.scale = 1.0
        self.min_scale = 1.0
        self.max_scale = 10.0
        self.export_format = "png"  # "png", "gif", "zip"
        self.loop_gif = True
        self.spritesheet_mode = False  # False = single frame, True = spritesheet
        self.spritesheet_cols = 0  # 0 = auto (1 row)
        
        # UI elements
        self.scale_slider_rect = pg.Rect(0, 0, 0, 0)
        self.scale_handle_rect = pg.Rect(0, 0, 0, 0)
        self.width_input_rect = pg.Rect(0, 0, 0, 0)
        self.height_input_rect = pg.Rect(0, 0, 0, 0)
        self.gif_button_rect = pg.Rect(0, 0, 0, 0)
        self.png_button_rect = pg.Rect(0, 0, 0, 0)
        self.zip_button_rect = pg.Rect(0, 0, 0, 0)
        self.loop_checkbox_rect = pg.Rect(0, 0, 0, 0)
        self.spritesheet_checkbox_rect = pg.Rect(0, 0, 0, 0)
        self.Save_button_rect = pg.Rect(0, 0, 0, 0)
        self.cancel_button_rect = pg.Rect(0, 0, 0, 0)
        
        # Interaction state
        self.dragging_scale = False
        self.canvas_width = 32
        self.canvas_height = 32
        
    def open(self, window_size: Tuple[int, int], canvas_width: int, canvas_height: int) -> None:
        """Open the export dialog."""
        self.active = True
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        
        # Center dialog
        self.dialog_rect.center = (window_size[0] // 2, window_size[1] // 2)
        
        # Layout UI elements
        self._layout_elements()
    
    def close(self) -> None:
        """Close the export dialog."""
        self.active = False
        self.dragging_scale = False
    
    def _layout_elements(self) -> None:
        """Layout all UI elements within the dialog."""
        margin = 20
        
        # Scale slider
        slider_y = self.dialog_rect.top + 80
        slider_width = self.dialog_rect.width - margin * 2 - 80
        self.scale_slider_rect = pg.Rect(
            self.dialog_rect.left + margin,
            slider_y,
            slider_width,
            8
        )
        self._update_scale_handle()
        
        # Resolution inputs
        input_y = slider_y + 50
        input_width = 80
        input_height = 40
        center_x = self.dialog_rect.centerx
        
        self.width_input_rect = pg.Rect(
            center_x - input_width - 15,
            input_y,
            input_width,
            input_height
        )
        self.height_input_rect = pg.Rect(
            center_x + 15,
            input_y,
            input_width,
            input_height
        )
        
        # Format buttons
        button_y = input_y + 70
        button_width = 80
        button_height = 40
        button_gap = 10
        
        total_width = button_width * 3 + button_gap * 2
        start_x = self.dialog_rect.centerx - total_width // 2
        
        self.gif_button_rect = pg.Rect(start_x, button_y, button_width, button_height)
        self.png_button_rect = pg.Rect(start_x + button_width + button_gap, button_y, button_width, button_height)
        self.zip_button_rect = pg.Rect(start_x + (button_width + button_gap) * 2, button_y, button_width, button_height)
        
        # Options checkboxes
        checkbox_y = button_y + 80
        checkbox_size = 24
        self.loop_checkbox_rect = pg.Rect(
            self.dialog_rect.left + margin,
            checkbox_y,
            checkbox_size,
            checkbox_size
        )
        self.spritesheet_checkbox_rect = pg.Rect(
            self.dialog_rect.left + margin,
            checkbox_y + 40,
            checkbox_size,
            checkbox_size
        )
        
        # Bottom buttons
        bottom_button_width = 120
        bottom_button_height = 50
        bottom_y = self.dialog_rect.bottom - margin - bottom_button_height
        
        self.Save_button_rect = pg.Rect(
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
    
    def _update_scale_handle(self) -> None:
        """Update the scale slider handle position."""
        # Calculate handle position based on scale
        t = (self.scale - self.min_scale) / (self.max_scale - self.min_scale)
        handle_x = self.scale_slider_rect.left + int(t * self.scale_slider_rect.width)
        handle_size = 20
        self.scale_handle_rect = pg.Rect(
            handle_x - handle_size // 2,
            self.scale_slider_rect.centery - handle_size // 2,
            handle_size,
            handle_size
        )
    
    def get_output_resolution(self) -> Tuple[int, int]:
        """Get the output resolution based on scale."""
        return (
            int(self.canvas_width * self.scale),
            int(self.canvas_height * self.scale)
        )
    
    def handle_mouse_down(self, pos: Tuple[int, int], button: int) -> bool:
        """Handle mouse down events. Returns True if event was handled."""
        if not self.active:
            return False
        
        if button == 1:
            # Check scale slider
            if self.scale_handle_rect.collidepoint(pos) or self.scale_slider_rect.collidepoint(pos):
                self.dragging_scale = True
                self._update_scale_from_mouse(pos)
                return True
            
            # Check format buttons
            if self.gif_button_rect.collidepoint(pos):
                self.export_format = "gif"
                return True
            elif self.png_button_rect.collidepoint(pos):
                self.export_format = "png"
                return True
            elif self.zip_button_rect.collidepoint(pos):
                self.export_format = "zip"
                return True
            
            # Check checkboxes
            if self.loop_checkbox_rect.collidepoint(pos):
                self.loop_gif = not self.loop_gif
                return True
            elif self.spritesheet_checkbox_rect.collidepoint(pos):
                self.spritesheet_mode = not self.spritesheet_mode
                return True
            
            # Check buttons
            if self.cancel_button_rect.collidepoint(pos):
                self.close()
                return True
            elif self.Save_button_rect.collidepoint(pos):
                return True  # Will be handled by caller
        
        return False
    
    def handle_mouse_up(self, pos: Tuple[int, int]) -> None:
        """Handle mouse up events."""
        self.dragging_scale = False
    
    def handle_mouse_move(self, pos: Tuple[int, int]) -> None:
        """Handle mouse move events."""
        if self.dragging_scale:
            self._update_scale_from_mouse(pos)
    
    def _update_scale_from_mouse(self, pos: Tuple[int, int]) -> None:
        """Update scale based on mouse position."""
        rel_x = max(0, min(self.scale_slider_rect.width, pos[0] - self.scale_slider_rect.left))
        t = rel_x / self.scale_slider_rect.width
        self.scale = self.min_scale + t * (self.max_scale - self.min_scale)
        self.scale = round(self.scale, 1)
        self._update_scale_handle()
    
    def render(self, surface: pg.Surface, fonts: Dict[str, pg.font.Font]) -> None:
        """Render the export dialog."""
        if not self.active:
            return
        
        title_font = fonts["title"]
        label_font = fonts["label"]
        small_font = fonts["small"]
        
        # Semi-transparent overlay
        overlay = pg.Surface(surface.get_size(), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))
        
        # Dialog background
        pg.draw.rect(surface, SIDEBAR_BG, self.dialog_rect, border_radius=10)
        pg.draw.rect(surface, SIDEBAR_ACCENT, self.dialog_rect, width=2, border_radius=10)
        
        # Title
        title = title_font.render("EXPORT", True, (255, 200, 0))
        surface.blit(title, (self.dialog_rect.left + 20, self.dialog_rect.top + 20))
        
        # Scale label and value
        scale_label = label_font.render("Scale", True, SIDEBAR_TEXT)
        surface.blit(scale_label, (self.scale_slider_rect.left, self.scale_slider_rect.top - 35))
        
        scale_value = label_font.render(f"{self.scale:.1f}x", True, SIDEBAR_TEXT)
        surface.blit(scale_value, (self.scale_slider_rect.right + 10, self.scale_slider_rect.top - 35))
        
        # Scale slider
        pg.draw.rect(surface, CANVAS_BORDER, self.scale_slider_rect, border_radius=4)
        pg.draw.circle(surface, SIDEBAR_ACCENT, self.scale_handle_rect.center, 10)
        
        # Resolution label
        res_label = label_font.render("Resolution", True, SIDEBAR_TEXT)
        surface.blit(res_label, (self.width_input_rect.left, self.width_input_rect.top - 35))
        
        # Resolution inputs
        width, height = self.get_output_resolution()
        
        pg.draw.rect(surface, STATUS_BG, self.width_input_rect, border_radius=4)
        pg.draw.rect(surface, CANVAS_BORDER, self.width_input_rect, width=2, border_radius=4)
        width_text = label_font.render(str(width), True, SIDEBAR_TEXT)
        surface.blit(width_text, width_text.get_rect(center=self.width_input_rect.center))
        
        # "x" between inputs
        x_text = label_font.render("×", True, SIDEBAR_TEXT)
        surface.blit(x_text, (self.dialog_rect.centerx - x_text.get_width() // 2, self.width_input_rect.centery - x_text.get_height() // 2))
        
        pg.draw.rect(surface, STATUS_BG, self.height_input_rect, border_radius=4)
        pg.draw.rect(surface, CANVAS_BORDER, self.height_input_rect, width=2, border_radius=4)
        height_text = label_font.render(str(height), True, SIDEBAR_TEXT)
        surface.blit(height_text, height_text.get_rect(center=self.height_input_rect.center))
        
        # Format buttons
        for rect, fmt, label in [
            (self.gif_button_rect, "gif", "GIF"),
            (self.png_button_rect, "png", "PNG"),
            (self.zip_button_rect, "zip", "Zip"),
        ]:
            is_selected = self.export_format == fmt
            bg_color = SIDEBAR_ACCENT if is_selected else STATUS_BG
            pg.draw.rect(surface, bg_color, rect, border_radius=4)
            if not is_selected:
                pg.draw.rect(surface, CANVAS_BORDER, rect, width=2, border_radius=4)
            
            text_color = (0, 0, 0) if is_selected else SIDEBAR_TEXT
            btn_text = label_font.render(label, True, text_color)
            surface.blit(btn_text, btn_text.get_rect(center=rect.center))
        
        # Format description
        desc_y = self.gif_button_rect.bottom + 20
        if self.export_format == "gif":
            desc = small_font.render("Convert your sprite to an animated GIF.", True, SIDEBAR_MUTED)
        elif self.export_format == "png":
            desc = small_font.render("Export your animation as a PNG spritesheet.", True, SIDEBAR_MUTED)
        else:
            desc = small_font.render("Export all frames as separate PNG files.", True, SIDEBAR_MUTED)
        surface.blit(desc, (self.dialog_rect.left + 20, desc_y))
        
        # Options checkboxes
        if self.export_format == "gif":
            # Loop checkbox
            pg.draw.rect(surface, STATUS_BG, self.loop_checkbox_rect, border_radius=4)
            pg.draw.rect(surface, SIDEBAR_ACCENT, self.loop_checkbox_rect, width=2, border_radius=4)
            if self.loop_gif:
                # Draw checkmark
                pg.draw.line(surface, SIDEBAR_ACCENT, 
                           (self.loop_checkbox_rect.left + 4, self.loop_checkbox_rect.centery),
                           (self.loop_checkbox_rect.centerx, self.loop_checkbox_rect.bottom - 6), 3)
                pg.draw.line(surface, SIDEBAR_ACCENT,
                           (self.loop_checkbox_rect.centerx, self.loop_checkbox_rect.bottom - 6),
                           (self.loop_checkbox_rect.right - 4, self.loop_checkbox_rect.top + 4), 3)
            
            loop_text = label_font.render("Loop repeatedly", True, SIDEBAR_TEXT)
            surface.blit(loop_text, (self.loop_checkbox_rect.right + 10, self.loop_checkbox_rect.centery - loop_text.get_height() // 2))
        
        elif self.export_format == "png":
            # Spritesheet checkbox
            pg.draw.rect(surface, STATUS_BG, self.spritesheet_checkbox_rect, border_radius=4)
            pg.draw.rect(surface, SIDEBAR_ACCENT, self.spritesheet_checkbox_rect, width=2, border_radius=4)
            if self.spritesheet_mode:
                # Draw checkmark
                pg.draw.line(surface, SIDEBAR_ACCENT,
                           (self.spritesheet_checkbox_rect.left + 4, self.spritesheet_checkbox_rect.centery),
                           (self.spritesheet_checkbox_rect.centerx, self.spritesheet_checkbox_rect.bottom - 6), 3)
                pg.draw.line(surface, SIDEBAR_ACCENT,
                           (self.spritesheet_checkbox_rect.centerx, self.spritesheet_checkbox_rect.bottom - 6),
                           (self.spritesheet_checkbox_rect.right - 4, self.spritesheet_checkbox_rect.top + 4), 3)
            
            sprite_text = label_font.render("Spritesheet (all frames)", True, SIDEBAR_TEXT)
            surface.blit(sprite_text, (self.spritesheet_checkbox_rect.right + 10, self.spritesheet_checkbox_rect.centery - sprite_text.get_height() // 2))
            
            if self.spritesheet_mode:
                info_text = small_font.render("1 row, all frames", True, SIDEBAR_MUTED)
                surface.blit(info_text, (self.spritesheet_checkbox_rect.right + 10, self.spritesheet_checkbox_rect.bottom + 5))
        
        # Bottom buttons
        pg.draw.rect(surface, (255, 200, 0), self.Save_button_rect, border_radius=6)
        Save_text = label_font.render("Save", True, (0, 0, 0))
        surface.blit(Save_text, Save_text.get_rect(center=self.Save_button_rect.center))
        
        pg.draw.rect(surface, CANVAS_BORDER, self.cancel_button_rect, border_radius=6)
        cancel_text = label_font.render("Cancel", True, SIDEBAR_TEXT)
        surface.blit(cancel_text, cancel_text.get_rect(center=self.cancel_button_rect.center))
