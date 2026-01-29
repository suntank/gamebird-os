"""
Palette browser UI for loading saved palettes.
"""
from __future__ import annotations
from pathlib import Path
from typing import List, Tuple, Optional, TYPE_CHECKING
import pygame as pg

if TYPE_CHECKING:
    from palette_system import Palette, PaletteManager

# Colors (matching main app)
SIDEBAR_BG = (40, 43, 48)
SIDEBAR_TEXT = (220, 220, 220)
SIDEBAR_ACCENT = (100, 149, 237)
STATUS_BG = (30, 33, 38)
CANVAS_BORDER = (60, 63, 68)


class PaletteBrowserUI:
    """Modal dialog for browsing and loading saved palette files."""
    
    def __init__(self) -> None:
        self.active = False
        self.dialog_rect = pg.Rect(0, 0, 500, 600)
        self.palette_files: List[Tuple[Path, str]] = []  # (filepath, display_name)
        self.palette_rects: List[Tuple[pg.Rect, int]] = []  # (rect, file_index)
        self.selected_index: Optional[int] = None
        self.scroll_offset = 0
        self.max_scroll = 0
        
        # Scrollbar
        self.scrollbar_rect = pg.Rect(0, 0, 0, 0)
        self.scrollbar_handle_rect = pg.Rect(0, 0, 0, 0)
        self.dragging_scrollbar = False
        self.scrollbar_drag_start_y = 0
        self.scrollbar_drag_start_offset = 0
        
        # Buttons
        self.load_button_rect = pg.Rect(0, 0, 0, 0)
        self.cancel_button_rect = pg.Rect(0, 0, 0, 0)
        self.delete_button_rect = pg.Rect(0, 0, 0, 0)
    
    def open(self, window_size: Tuple[int, int]) -> None:
        """Open the palette browser and load available palette files."""
        self.active = True
        self.selected_index = None
        self.scroll_offset = 0
        
        # Center dialog
        self.dialog_rect.center = (window_size[0] // 2, window_size[1] // 2)
        
        # Load palette files
        self._load_palette_files()
        self._layout_elements()
    
    def close(self) -> None:
        """Close the palette browser."""
        self.active = False
        self.palette_files = []
        self.palette_rects = []
        self.selected_index = None
    
    def _load_palette_files(self) -> None:
        """Load all palette files from the exports/palettes directory."""
        palette_dir = Path("exports/palettes")
        self.palette_files = []
        
        if palette_dir.exists():
            for filepath in sorted(palette_dir.glob("*.json")):
                # Get display name from filename
                display_name = filepath.stem.replace('_', ' ')
                self.palette_files.append((filepath, display_name))
    
    def _layout_elements(self) -> None:
        """Layout all UI elements."""
        margin = 20
        
        # Content area for palette list
        list_top = self.dialog_rect.top + 60
        list_bottom = self.dialog_rect.bottom - 80
        list_height = list_bottom - list_top
        
        # Calculate palette item rects
        item_height = 60
        item_gap = 8
        item_width = self.dialog_rect.width - 60
        
        self.palette_rects = []
        y = list_top - self.scroll_offset
        
        for idx in range(len(self.palette_files)):
            rect = pg.Rect(
                self.dialog_rect.left + margin,
                y,
                item_width,
                item_height
            )
            self.palette_rects.append((rect, idx))
            y += item_height + item_gap
        
        # Calculate max scroll
        total_height = len(self.palette_files) * (item_height + item_gap)
        self.max_scroll = max(0, total_height - list_height)
        
        # Scrollbar
        scrollbar_width = 12
        self.scrollbar_rect = pg.Rect(
            self.dialog_rect.right - margin - scrollbar_width,
            list_top,
            scrollbar_width,
            list_height
        )
        
        if self.max_scroll > 0:
            handle_height = max(30, int(list_height * (list_height / total_height)))
            handle_y = list_top + int((self.scroll_offset / self.max_scroll) * (list_height - handle_height))
            self.scrollbar_handle_rect = pg.Rect(
                self.scrollbar_rect.left,
                handle_y,
                scrollbar_width,
                handle_height
            )
        else:
            self.scrollbar_handle_rect = pg.Rect(0, 0, 0, 0)
        
        # Bottom buttons
        button_width = 120
        button_height = 40
        button_y = self.dialog_rect.bottom - margin - button_height
        button_gap = 10
        
        self.cancel_button_rect = pg.Rect(
            self.dialog_rect.left + margin,
            button_y,
            button_width,
            button_height
        )
        
        self.delete_button_rect = pg.Rect(
            self.cancel_button_rect.right + button_gap,
            button_y,
            button_width,
            button_height
        )
        
        self.load_button_rect = pg.Rect(
            self.dialog_rect.right - margin - button_width,
            button_y,
            button_width,
            button_height
        )
    
    def render(self, surface: pg.Surface, fonts: dict) -> None:
        """Render the palette browser."""
        if not self.active:
            return
        
        # Semi-transparent overlay
        overlay = pg.Surface(surface.get_size(), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))
        
        # Dialog background
        pg.draw.rect(surface, (45, 48, 54), self.dialog_rect, border_radius=10)
        pg.draw.rect(surface, SIDEBAR_ACCENT, self.dialog_rect, width=2, border_radius=10)
        
        # Title
        title_font = fonts.get("title", fonts["label"])
        label_font = fonts["label"]
        small_font = fonts["small"]
        
        title = title_font.render("Load Palette", True, SIDEBAR_TEXT)
        surface.blit(title, (self.dialog_rect.left + 20, self.dialog_rect.top + 10))
        
        # Show count
        count_text = small_font.render(f"{len(self.palette_files)} palette(s) found", True, SIDEBAR_TEXT)
        surface.blit(count_text, (self.dialog_rect.left + 20, self.dialog_rect.top + 35))
        
        # Render palette list items
        list_top = self.dialog_rect.top + 60
        list_bottom = self.dialog_rect.bottom - 80
        
        for rect, file_idx in self.palette_rects:
            # Skip if outside visible area
            if rect.bottom < list_top or rect.top > list_bottom:
                continue
            
            filepath, display_name = self.palette_files[file_idx]
            
            # Item background
            is_selected = file_idx == self.selected_index
            bg_color = SIDEBAR_ACCENT if is_selected else STATUS_BG
            border_color = SIDEBAR_ACCENT if is_selected else CANVAS_BORDER
            
            pg.draw.rect(surface, bg_color if is_selected else STATUS_BG, rect, border_radius=6)
            pg.draw.rect(surface, border_color, rect, width=2, border_radius=6)
            
            # Palette name
            name_text = label_font.render(display_name, True, (255, 255, 255) if is_selected else SIDEBAR_TEXT)
            surface.blit(name_text, (rect.left + 15, rect.top + 12))
            
            # File info (size, date, etc.)
            try:
                file_size = filepath.stat().st_size
                size_kb = file_size / 1024
                info_text = small_font.render(f"{size_kb:.1f} KB", True, (200, 200, 200) if is_selected else (150, 150, 150))
                surface.blit(info_text, (rect.left + 15, rect.top + 35))
            except:
                pass
        
        # Scrollbar
        if self.max_scroll > 0:
            pg.draw.rect(surface, (60, 60, 60), self.scrollbar_rect, border_radius=6)
            pg.draw.rect(surface, SIDEBAR_ACCENT, self.scrollbar_handle_rect, border_radius=6)
        
        # Bottom buttons
        # Cancel button
        pg.draw.rect(surface, (100, 100, 100), self.cancel_button_rect, border_radius=6)
        cancel_text = label_font.render("Cancel", True, SIDEBAR_TEXT)
        surface.blit(cancel_text, cancel_text.get_rect(center=self.cancel_button_rect.center))
        
        # Delete button (only enabled if something is selected)
        delete_enabled = self.selected_index is not None
        delete_color = (180, 50, 50) if delete_enabled else (80, 80, 80)
        pg.draw.rect(surface, delete_color, self.delete_button_rect, border_radius=6)
        delete_text = label_font.render("Delete", True, SIDEBAR_TEXT if delete_enabled else (120, 120, 120))
        surface.blit(delete_text, delete_text.get_rect(center=self.delete_button_rect.center))
        
        # Load button (only enabled if something is selected)
        load_enabled = self.selected_index is not None
        load_color = (80, 180, 80) if load_enabled else (80, 80, 80)
        pg.draw.rect(surface, load_color, self.load_button_rect, border_radius=6)
        load_text = label_font.render("Load", True, SIDEBAR_TEXT if load_enabled else (120, 120, 120))
        surface.blit(load_text, load_text.get_rect(center=self.load_button_rect.center))
    
    def handle_mouse_down(self, pos: Tuple[int, int], palette_manager: 'PaletteManager') -> Optional[str]:
        """
        Handle mouse click events.
        Returns: 'load' if a palette was loaded, 'delete' if deleted, 'close' if cancelled, None otherwise
        """
        if not self.active:
            return None
        
        # Check if clicking outside dialog (close)
        if not self.dialog_rect.collidepoint(pos):
            self.close()
            return 'close'
        
        # Check scrollbar
        if self.scrollbar_handle_rect.collidepoint(pos):
            self.dragging_scrollbar = True
            self.scrollbar_drag_start_y = pos[1]
            self.scrollbar_drag_start_offset = self.scroll_offset
            return None
        
        # Check palette items
        for rect, file_idx in self.palette_rects:
            if rect.collidepoint(pos):
                self.selected_index = file_idx
                return None
        
        # Check buttons
        if self.cancel_button_rect.collidepoint(pos):
            self.close()
            return 'close'
        
        if self.delete_button_rect.collidepoint(pos) and self.selected_index is not None:
            # Delete the selected palette file
            filepath, _ = self.palette_files[self.selected_index]
            try:
                filepath.unlink()
                self._load_palette_files()
                self._layout_elements()
                self.selected_index = None
                return 'delete'
            except Exception as e:
                print(f"Error deleting palette: {e}")
            return None
        
        if self.load_button_rect.collidepoint(pos) and self.selected_index is not None:
            # Load the selected palette
            filepath, _ = self.palette_files[self.selected_index]
            try:
                loaded_palette = palette_manager.load_palette(filepath)
                palette_manager.add_palette(loaded_palette)
                self.close()
                return 'load'
            except Exception as e:
                print(f"Error loading palette: {e}")
            return None
        
        return None
    
    def handle_mouse_up(self, pos: Tuple[int, int]) -> None:
        """Handle mouse button release."""
        self.dragging_scrollbar = False
    
    def handle_mouse_move(self, pos: Tuple[int, int]) -> None:
        """Handle mouse movement for scrollbar dragging."""
        if self.dragging_scrollbar and self.max_scroll > 0:
            delta_y = pos[1] - self.scrollbar_drag_start_y
            scroll_range = self.scrollbar_rect.height - self.scrollbar_handle_rect.height
            if scroll_range > 0:
                scroll_delta = (delta_y / scroll_range) * self.max_scroll
                self.scroll_offset = max(0, min(self.max_scroll, int(self.scrollbar_drag_start_offset + scroll_delta)))
                self._layout_elements()
    
    def handle_scroll(self, y: int) -> None:
        """Handle mouse wheel scrolling."""
        if not self.active:
            return
        
        scroll_amount = 30
        self.scroll_offset = max(0, min(self.max_scroll, self.scroll_offset - y * scroll_amount))
        self._layout_elements()
