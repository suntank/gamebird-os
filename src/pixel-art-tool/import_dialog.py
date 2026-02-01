"""
Import dialog for pixel art app - supports importing images as single image or spritesheet.
Two-stage dialog: first select mode/settings, then preview frames with Combine/Replace options.
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
YELLOW = (255, 200, 0)


class ImportDialog:
    """Dialog for importing images as single image or spritesheet."""
    
    def __init__(self) -> None:
        self.active = False
        self.dialog_rect = pg.Rect(0, 0, 520, 400)
        
        # Dialog stage: "settings" or "preview"
        self.dialog_stage = "settings"
        
        # Import settings
        self.import_mode = "single"  # "single" or "spritesheet"
        self.smooth_resize = True
        self.import_action = "replace"  # "combine" or "replace"
        
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
        
        # Extracted frames (for GIF or spritesheet)
        self.frames: List[Image.Image] = []
        self.current_frame_index = 0
        self.frame_preview_surface: Optional[pg.Surface] = None
        
        # UI elements - Stage 1 (settings)
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
        
        # UI elements - Stage 2 (preview)
        self.combine_button_rect = pg.Rect(0, 0, 0, 0)
        self.replace_button_rect = pg.Rect(0, 0, 0, 0)
        self.back_button_rect = pg.Rect(0, 0, 0, 0)
        self.prev_frame_rect = pg.Rect(0, 0, 0, 0)
        self.next_frame_rect = pg.Rect(0, 0, 0, 0)
        self.first_frame_rect = pg.Rect(0, 0, 0, 0)
        self.last_frame_rect = pg.Rect(0, 0, 0, 0)
        
        # Text input state
        self.editing_field: Optional[str] = None
        self.input_text = ""
        self.cursor_blink_time = 0
        
        # Preview rect
        self.preview_rect = pg.Rect(0, 0, 0, 0)
        
    def open(self, window_size: Tuple[int, int], image_path: Path) -> bool:
        """Open the import dialog with the specified image. Returns False if image couldn't be loaded."""
        try:
            self.image_path = image_path
            self.image_name = image_path.name
            self.dialog_stage = "settings"
            self.frames = []
            self.current_frame_index = 0
            
            # Check if it's a GIF with multiple frames
            img = Image.open(image_path)
            is_animated_gif = hasattr(img, 'n_frames') and img.n_frames > 1
            
            if is_animated_gif:
                # Extract all frames from GIF
                self._extract_gif_frames(img)
                self.original_image = self.frames[0] if self.frames else img.convert("RGBA")
            else:
                self.original_image = img.convert("RGBA")
            
            self.original_width, self.original_height = self.original_image.size
            
            # Set default resize to original dimensions
            self.resize_width = self.original_width
            self.resize_height = self.original_height
            
            # Set default frame size for spritesheet
            self.frame_width = self.original_width
            self.frame_height = self.original_height
            
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
    
    def _extract_gif_frames(self, gif_image: Image.Image) -> None:
        """Extract all frames from an animated GIF."""
        self.frames = []
        try:
            for frame_idx in range(gif_image.n_frames):
                gif_image.seek(frame_idx)
                # Convert frame to RGBA
                frame = gif_image.convert("RGBA")
                self.frames.append(frame.copy())
        except Exception as e:
            print(f"Error extracting GIF frames: {e}")
    
    def _slice_spritesheet(self) -> None:
        """Slice the original image into frames based on frame size and offset."""
        self.frames = []
        if self.original_image is None:
            return
        
        img_width, img_height = self.original_image.size
        frame_w = max(1, self.frame_width)
        frame_h = max(1, self.frame_height)
        offset_x = max(0, self.offset_x)
        offset_y = max(0, self.offset_y)
        
        y = offset_y
        while y + frame_h <= img_height:
            x = offset_x
            while x + frame_w <= img_width:
                # Crop frame from image
                frame = self.original_image.crop((x, y, x + frame_w, y + frame_h))
                self.frames.append(frame)
                x += frame_w
            y += frame_h
        
        # If no frames were extracted, use the whole image
        if not self.frames:
            self.frames = [self.original_image.copy()]
        
        self.current_frame_index = 0
        self._update_frame_preview()
    
    def close(self) -> None:
        """Close the import dialog."""
        self.active = False
        self.editing_field = None
        self.original_image = None
        self.preview_surface = None
        self.frames = []
        self.frame_preview_surface = None
        self.dialog_stage = "settings"
    
    def _update_frame_preview(self) -> None:
        """Update the frame preview surface for the current frame."""
        if not self.frames or self.current_frame_index >= len(self.frames):
            return
        
        frame = self.frames[self.current_frame_index]
        
        # Scale to fit preview area (max 120x120)
        max_size = 120
        frame_w, frame_h = frame.size
        scale = min(max_size / frame_w, max_size / frame_h, 1.0)
        preview_w = max(1, int(frame_w * scale))
        preview_h = max(1, int(frame_h * scale))
        
        preview_img = frame.resize((preview_w, preview_h), Image.Resampling.NEAREST)
        
        # Convert PIL image to pygame surface
        mode = preview_img.mode
        size = preview_img.size
        data = preview_img.tobytes()
        self.frame_preview_surface = pg.image.fromstring(data, size, mode)
    
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
        
        if self.dialog_stage == "settings":
            self._layout_settings_stage(margin, left)
        else:
            self._layout_preview_stage(margin, left)
    
    def _layout_settings_stage(self, margin: int, left: int) -> None:
        """Layout UI elements for the settings stage."""
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
    
    def _layout_preview_stage(self, margin: int, left: int) -> None:
        """Layout UI elements for the preview stage (Piskel-style)."""
        # Preview area with frame navigation (left side)
        self.preview_rect = pg.Rect(
            left,
            self.dialog_rect.top + 60,
            160, 160
        )
        
        # Frame navigation buttons below preview
        nav_y = self.preview_rect.bottom + 5
        btn_w = 30
        btn_h = 24
        nav_x = self.preview_rect.left
        
        self.first_frame_rect = pg.Rect(nav_x, nav_y, btn_w, btn_h)
        self.prev_frame_rect = pg.Rect(nav_x + btn_w + 4, nav_y, btn_w, btn_h)
        # Frame counter goes in middle
        self.next_frame_rect = pg.Rect(nav_x + 100, nav_y, btn_w, btn_h)
        self.last_frame_rect = pg.Rect(nav_x + 100 + btn_w + 4, nav_y, btn_w, btn_h)
        
        # Right side content area
        right_x = self.preview_rect.right + 20
        content_y = self.dialog_rect.top + 60
        
        # "How do you want to import the new content?" text at top
        
        # Combine option box
        combine_box_y = content_y + 30
        self.combine_button_rect = pg.Rect(
            self.dialog_rect.right - margin - 90,
            combine_box_y + 10,
            80, 32
        )
        
        # Replace option box
        replace_box_y = combine_box_y + 60
        self.replace_button_rect = pg.Rect(
            self.dialog_rect.right - margin - 90,
            replace_box_y + 10,
            80, 32
        )
        
        # Back button (bottom right)
        self.back_button_rect = pg.Rect(
            self.dialog_rect.right - margin - 60,
            self.dialog_rect.bottom - margin - 35,
            50, 28
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
            
            if self.dialog_stage == "settings":
                return self._handle_settings_click(pos)
            else:
                return self._handle_preview_click(pos)
        
        return False
    
    def _handle_settings_click(self, pos: Tuple[int, int]) -> bool:
        """Handle mouse clicks in settings stage."""
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
        
        # Check import button - transition to preview stage
        if self.import_button_rect.collidepoint(pos):
            self._prepare_frames()
            self.dialog_stage = "preview"
            self._layout_elements()
            self._update_frame_preview()
            return True
        
        return False
    
    def _handle_preview_click(self, pos: Tuple[int, int]) -> bool:
        """Handle mouse clicks in preview stage."""
        # Frame navigation
        if self.first_frame_rect.collidepoint(pos):
            self.current_frame_index = 0
            self._update_frame_preview()
            return True
        if self.prev_frame_rect.collidepoint(pos):
            if self.current_frame_index > 0:
                self.current_frame_index -= 1
                self._update_frame_preview()
            return True
        if self.next_frame_rect.collidepoint(pos):
            if self.current_frame_index < len(self.frames) - 1:
                self.current_frame_index += 1
                self._update_frame_preview()
            return True
        if self.last_frame_rect.collidepoint(pos):
            self.current_frame_index = max(0, len(self.frames) - 1)
            self._update_frame_preview()
            return True
        
        # Combine button
        if self.combine_button_rect.collidepoint(pos):
            self.import_action = "combine"
            return True  # Will be handled by caller
        
        # Replace button
        if self.replace_button_rect.collidepoint(pos):
            self.import_action = "replace"
            return True  # Will be handled by caller
        
        # Back button
        if self.back_button_rect.collidepoint(pos):
            self.dialog_stage = "settings"
            self._layout_elements()
            return True
        
        return False
    
    def _prepare_frames(self) -> None:
        """Prepare frames based on import mode."""
        if self.import_mode == "single":
            # Single image mode - resize and use as single frame
            if self.original_image:
                resample = Image.Resampling.LANCZOS if self.smooth_resize else Image.Resampling.NEAREST
                resized = self.original_image.resize(
                    (self.resize_width, self.resize_height), resample
                )
                self.frames = [resized]
        else:
            # Spritesheet mode
            # Check if we already have GIF frames
            if self.frames and len(self.frames) > 1:
                # Already have GIF frames, no need to slice
                pass
            else:
                # Slice the spritesheet
                self._slice_spritesheet()
        
        self.current_frame_index = 0
    
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
        if not self.frames:
            return None
        
        return {
            "mode": self.import_mode,
            "action": self.import_action,
            "frames": self.frames,
            "image_path": self.image_path,
            "smooth_resize": self.smooth_resize,
            "resize_width": self.resize_width,
            "resize_height": self.resize_height,
            "frame_width": self.frame_width,
            "frame_height": self.frame_height,
        }
    
    def is_action_clicked(self, pos: Tuple[int, int]) -> bool:
        """Check if Combine or Replace button was clicked."""
        if self.dialog_stage != "preview":
            return False
        return (self.combine_button_rect.collidepoint(pos) or 
                self.replace_button_rect.collidepoint(pos))
    
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
        pg.draw.rect(surface, YELLOW, self.dialog_rect, width=3, border_radius=0)
        
        # Title bar
        title_bar = pg.Rect(self.dialog_rect.left, self.dialog_rect.top, self.dialog_rect.width, 50)
        pg.draw.rect(surface, YELLOW, title_bar)
        
        # Title text
        title = title_font.render("Import and Merge", True, (0, 0, 0))
        surface.blit(title, (self.dialog_rect.left + 20, self.dialog_rect.top + 12))
        
        # Close button (X)
        x_text = title_font.render("X", True, (0, 0, 0))
        surface.blit(x_text, x_text.get_rect(center=self.close_button_rect.center))
        
        if self.dialog_stage == "settings":
            self._render_settings_stage(surface, fonts)
        else:
            self._render_preview_stage(surface, fonts)
    
    def _render_settings_stage(self, surface: pg.Surface, fonts: Dict[str, pg.font.Font]) -> None:
        """Render the settings stage UI."""
        label_font = fonts["label"]
        margin = 20
        left = self.dialog_rect.left + margin
        
        # File name
        name_y = self.dialog_rect.top + 60
        name_label = label_font.render("Name : ", True, SIDEBAR_TEXT)
        surface.blit(name_label, (self.dialog_rect.left + 20, name_y))
        name_value = label_font.render(self.image_name, True, YELLOW)
        surface.blit(name_value, (self.dialog_rect.left + 20 + name_label.get_width(), name_y))
        
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
        
        # Show frame count preview for spritesheet mode
        if self.import_mode == "spritesheet" and self.original_image:
            img_w, img_h = self.original_image.size
            frame_w = max(1, self.frame_width)
            frame_h = max(1, self.frame_height)
            cols = max(1, (img_w - self.offset_x) // frame_w)
            rows = max(1, (img_h - self.offset_y) // frame_h)
            frame_count = cols * rows
            count_y = self.offset_y_rect.bottom + 15
            count_text = label_font.render(f"Will extract {frame_count} frame{'s' if frame_count != 1 else ''} ({cols}x{rows})", True, YELLOW)
            surface.blit(count_text, (left + 20, count_y))
        
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
    
    def _render_preview_stage(self, surface: pg.Surface, fonts: Dict[str, pg.font.Font]) -> None:
        """Render the preview stage UI (Piskel-style)."""
        label_font = fonts["label"]
        small_font = fonts["small"]
        margin = 20
        left = self.dialog_rect.left + margin
        
        # Draw checkered background in preview area
        self._draw_checkered_bg(surface, self.preview_rect)
        pg.draw.rect(surface, CANVAS_BORDER, self.preview_rect, width=2)
        
        # Draw current frame preview
        if self.frame_preview_surface:
            preview_pos = self.frame_preview_surface.get_rect(center=self.preview_rect.center)
            surface.blit(self.frame_preview_surface, preview_pos)
        
        # Frame navigation buttons
        btn_color = (60, 64, 70)
        btn_text_color = SIDEBAR_TEXT
        
        # << button
        pg.draw.rect(surface, btn_color, self.first_frame_rect, border_radius=2)
        first_text = small_font.render("<<", True, btn_text_color)
        surface.blit(first_text, first_text.get_rect(center=self.first_frame_rect.center))
        
        # < button
        pg.draw.rect(surface, btn_color, self.prev_frame_rect, border_radius=2)
        prev_text = small_font.render("<", True, btn_text_color)
        surface.blit(prev_text, prev_text.get_rect(center=self.prev_frame_rect.center))
        
        # Frame counter
        frame_counter = f"{self.current_frame_index + 1}"
        counter_text = label_font.render(frame_counter, True, SIDEBAR_TEXT)
        counter_x = self.prev_frame_rect.right + (self.next_frame_rect.left - self.prev_frame_rect.right) // 2
        surface.blit(counter_text, counter_text.get_rect(center=(counter_x, self.prev_frame_rect.centery)))
        
        # > button
        pg.draw.rect(surface, btn_color, self.next_frame_rect, border_radius=2)
        next_text = small_font.render(">", True, btn_text_color)
        surface.blit(next_text, next_text.get_rect(center=self.next_frame_rect.center))
        
        # >> button
        pg.draw.rect(surface, btn_color, self.last_frame_rect, border_radius=2)
        last_text = small_font.render(">>", True, btn_text_color)
        surface.blit(last_text, last_text.get_rect(center=self.last_frame_rect.center))
        
        # Info section below navigation
        info_y = self.last_frame_rect.bottom + 15
        
        # Name
        name_label = small_font.render("Name", True, YELLOW)
        surface.blit(name_label, (left, info_y))
        name_value = small_font.render(self.image_name, True, SIDEBAR_TEXT)
        surface.blit(name_value, (left + 5, info_y + 18))
        
        # Dimensions
        dim_y = info_y + 45
        dim_label = small_font.render("Dimensions", True, YELLOW)
        surface.blit(dim_label, (left, dim_y))
        if self.frames:
            frame_w, frame_h = self.frames[0].size
            dim_value = small_font.render(f"{frame_w}x{frame_h}", True, SIDEBAR_TEXT)
        else:
            dim_value = small_font.render(f"{self.original_width}x{self.original_height}", True, SIDEBAR_TEXT)
        surface.blit(dim_value, (left + 5, dim_y + 18))
        
        # Frames count
        frames_y = dim_y + 45
        frames_label = small_font.render("Frames", True, YELLOW)
        surface.blit(frames_label, (left, frames_y))
        frames_value = small_font.render(str(len(self.frames)), True, SIDEBAR_TEXT)
        surface.blit(frames_value, (left + 5, frames_y + 18))
        
        # Right side - Import options
        right_x = self.preview_rect.right + 20
        
        # Question text
        question_y = self.dialog_rect.top + 60
        question = label_font.render("How do you want to import the new content?", True, SIDEBAR_TEXT)
        surface.blit(question, (right_x, question_y))
        
        # Combine option box
        combine_box = pg.Rect(right_x, question_y + 30, 280, 50)
        pg.draw.rect(surface, (50, 54, 60), combine_box, border_radius=4)
        pg.draw.rect(surface, CANVAS_BORDER, combine_box, width=1, border_radius=4)
        
        combine_label = label_font.render("Combine with your sprite", True, SIDEBAR_TEXT)
        surface.blit(combine_label, (combine_box.left + 10, combine_box.centery - combine_label.get_height() // 2))
        
        # Combine button
        pg.draw.rect(surface, YELLOW, self.combine_button_rect, border_radius=4)
        combine_btn_text = label_font.render("Combine", True, (0, 0, 0))
        surface.blit(combine_btn_text, combine_btn_text.get_rect(center=self.combine_button_rect.center))
        
        # Replace option box
        replace_box = pg.Rect(right_x, question_y + 90, 280, 50)
        pg.draw.rect(surface, (50, 54, 60), replace_box, border_radius=4)
        pg.draw.rect(surface, CANVAS_BORDER, replace_box, width=1, border_radius=4)
        
        replace_label = label_font.render("Replace your sprite", True, SIDEBAR_TEXT)
        surface.blit(replace_label, (replace_box.left + 10, replace_box.centery - replace_label.get_height() // 2))
        
        # Replace button
        pg.draw.rect(surface, YELLOW, self.replace_button_rect, border_radius=4)
        replace_btn_text = label_font.render("Replace", True, (0, 0, 0))
        surface.blit(replace_btn_text, replace_btn_text.get_rect(center=self.replace_button_rect.center))
        
        # Back button
        pg.draw.rect(surface, (50, 54, 60), self.back_button_rect, border_radius=4)
        pg.draw.rect(surface, CANVAS_BORDER, self.back_button_rect, width=1, border_radius=4)
        back_text = small_font.render("back", True, SIDEBAR_TEXT)
        surface.blit(back_text, back_text.get_rect(center=self.back_button_rect.center))
    
    def _draw_checkered_bg(self, surface: pg.Surface, rect: pg.Rect) -> None:
        """Draw a checkered background for transparency."""
        check_size = 8
        colors = [(80, 80, 80), (60, 60, 60)]
        for y in range(rect.top, rect.bottom, check_size):
            for x in range(rect.left, rect.right, check_size):
                color_idx = ((x - rect.left) // check_size + (y - rect.top) // check_size) % 2
                check_rect = pg.Rect(x, y, min(check_size, rect.right - x), min(check_size, rect.bottom - y))
                pg.draw.rect(surface, colors[color_idx], check_rect)
    
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
