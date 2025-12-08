import pygame
import threading
import logging
import subprocess
import time
import requests
from typing import List, Optional
from pathlib import Path
from .widgets import (
    draw_text, draw_list_item, draw_progress_bar, draw_button_hint,
    draw_browse_list_item, draw_tags_row, draw_star_rating,
    draw_mature_banner, draw_nav_arrow, draw_page_indicator, draw_heart,
    draw_rating_stars, _get_star_image, BG_COLOR, ACCENT_COLOR, STAR_YELLOW
)
from .image_cache import ImageCache
from ..models import CatalogEntry, GameManifest, InstalledGame, UpdateInfo
from ..cdn_api import CatalogPage

class Screen:
    def __init__(self, app):
        self.app = app

    def on_enter(self):
        pass

    def update(self, actions: List[str]):
        pass

    def draw(self, surface):
        pass

class MainMenu(Screen):
    def __init__(self, app):
        super().__init__(app)
        self.items = ["Browse Catalog", "Installed Games", "Check for Updates", "Parental Controls", "Developer Code", "Exit"]
        self.selected_index = 0

    def update(self, actions: List[str]):
        if "UP" in actions:
            self.selected_index = (self.selected_index - 1) % len(self.items)
        elif "DOWN" in actions:
            self.selected_index = (self.selected_index + 1) % len(self.items)
        elif "A" in actions:
            selection = self.items[self.selected_index]
            if selection == "Browse Catalog":
                self.app.change_screen("CatalogList")
            elif selection == "Installed Games":
                self.app.change_screen("InstalledList")
            elif selection == "Check for Updates":
                self.app.change_screen("UpdateCheck")
            elif selection == "Parental Controls":
                self.app.change_screen("ParentalControls")
            elif selection == "Developer Code":
                self.app.change_screen("DeveloperCode")
            elif selection == "Exit":
                self.app.change_screen("RebootScreen")

    def draw(self, surface):
        surface.fill(BG_COLOR)
        draw_text(surface, self.app.font, "GAME BIRD NEST", 120, 30, center=True)
        pygame.draw.line(surface, ACCENT_COLOR, (0, 50), (240, 50), 2)
        
        start_y = 80
        gap = 25
        for i, item in enumerate(self.items):
            draw_list_item(surface, self.app.font, item, start_y + i * gap, 180, i == self.selected_index)
            
        draw_text(surface, self.app.font, "A: Select         B: Back", 120, 230, (200, 200, 200), center=True)


class CatalogList(Screen):
    """
    Browse catalog screen with visual game preview.
    
    Layout (240x240):
    - Top bar: Active filter tags
    - Center: Game icon/screenshot (160x160)
    - Rating at bottom-right of icon
    - Mature banner overlay if applicable
    - Nav arrows on sides when viewing screenshots
    - Bottom: Scrolling game list (3 visible titles)
    - Page indicator at very bottom
    """
    
    GAMES_PER_PAGE = 25
    
    def __init__(self, app):
        super().__init__(app)
        self.games: List[CatalogEntry] = []
        self.selected_index = 0
        self.loading = False
        self.error = None
        
        # Pagination
        self.current_page = 1
        self.total_pages = 1
        self.total_games = 0
        
        # Active tag filters
        self.filter_tags: List[str] = []
        
        # Screenshot viewing
        self.viewing_screenshot = False
        self.screenshot_index = 0  # 0 = icon, 1-3 = screenshots
        
        # Image cache
        cache_dir = Path.home() / "gamebird" / "cache" / "images"
        self.image_cache = ImageCache(cache_dir, target_size=(160, 160))
        
        # Current displayed image (icon or screenshot)
        self.current_image: Optional[pygame.Surface] = None
        self.image_loading = False

    def on_enter(self):
        self.loading = True
        self.error = None
        self.games = []
        self.selected_index = 0
        self.current_page = 1
        self.viewing_screenshot = False
        self.screenshot_index = 0
        # Keep filter_tags across re-entries unless explicitly cleared
        threading.Thread(target=self._fetch_catalog, daemon=True).start()

    def _fetch_catalog(self):
        try:
            include_mature = not self.app.parental_controls.should_filter_mature()
            
            result: CatalogPage = self.app.cdn_api.fetch_catalog(
                page=self.current_page,
                per_page=self.GAMES_PER_PAGE,
                include_mature=include_mature,
                tags=self.filter_tags if self.filter_tags else None
            )
            
            self.games = result.games
            self.total_pages = result.total_pages
            self.total_games = result.total
            
            # Preload icons for visible games
            if self.games:
                for game in self.games[:5]:
                    if game.icon_url:
                        self.image_cache.preload([game.icon_url])
                # Load first game's icon
                self._load_current_image()
                
        except Exception as e:
            logging.error(f"Catalog fetch error: {e}")
            self.error = str(e)
        finally:
            self.loading = False

    def _load_current_image(self):
        """Load the current game's icon or screenshot."""
        if not self.games:
            self.current_image = None
            return
        
        game = self.games[self.selected_index]
        
        if self.screenshot_index == 0:
            url = game.icon_url
        else:
            # Screenshot index 1-3 maps to screenshot_urls[0-2]
            idx = self.screenshot_index - 1
            if idx < len(game.screenshot_urls):
                url = game.screenshot_urls[idx]
            else:
                url = None
        
        if url:
            self.image_loading = True
            # Try to get from cache, with callback for async load
            cached = self.image_cache.get(url, callback=self._on_image_loaded)
            if cached:
                self.current_image = cached
                self.image_loading = False
        else:
            self.current_image = None
            self.image_loading = False
    
    def _on_image_loaded(self, surface: Optional[pygame.Surface]):
        """Callback when async image load completes."""
        self.current_image = surface
        self.image_loading = False

    def _load_page(self, page: int):
        """Load a specific page."""
        if page < 1 or page > self.total_pages:
            return
        self.current_page = page
        self.selected_index = 0
        self.viewing_screenshot = False
        self.screenshot_index = 0
        self.loading = True
        threading.Thread(target=self._fetch_catalog, daemon=True).start()

    def set_filters(self, tags: List[str] = None):
        """Set filter tags and reload catalog."""
        self.filter_tags = tags or []
        self.current_page = 1
        self.selected_index = 0
        self.loading = True
        threading.Thread(target=self._fetch_catalog, daemon=True).start()

    def clear_filters(self):
        """Clear all filters and reload catalog."""
        self.set_filters([])

    def add_filter_tag(self, tag: str):
        """Add a tag to the filter list."""
        if tag not in self.filter_tags:
            self.filter_tags.append(tag)
            self.set_filters(self.filter_tags)

    def remove_filter_tag(self, tag: str):
        """Remove a tag from the filter list."""
        if tag in self.filter_tags:
            self.filter_tags.remove(tag)
            self.set_filters(self.filter_tags)

    def update(self, actions: List[str]):
        if self.loading:
            if "B" in actions:
                self.app.change_screen("MainMenu")
            return

        if not self.games:
            if "START" in actions:
                self.app.change_screen("FilterScreen")
            elif "B" in actions:
                self.app.change_screen("MainMenu")
            return

        game = self.games[self.selected_index]
        
        # Navigation
        if "UP" in actions:
            if self.viewing_screenshot:
                # Exit screenshot mode, go back to icon
                self.viewing_screenshot = False
                self.screenshot_index = 0
                self._load_current_image()
            else:
                # Move up in list
                if self.selected_index > 0:
                    self.selected_index -= 1
                    self.screenshot_index = 0
                    self._load_current_image()
                    
        elif "DOWN" in actions:
            if self.viewing_screenshot:
                # Exit screenshot mode
                self.viewing_screenshot = False
                self.screenshot_index = 0
                self._load_current_image()
            else:
                # Move down in list
                if self.selected_index < len(self.games) - 1:
                    self.selected_index += 1
                    self.screenshot_index = 0
                    self._load_current_image()
                    
        elif "RIGHT" in actions:
            # View screenshots
            max_screenshots = len(game.screenshot_urls)
            if self.screenshot_index < max_screenshots:
                self.screenshot_index += 1
                self.viewing_screenshot = True
                self._load_current_image()
                
        elif "LEFT" in actions:
            if self.screenshot_index > 0:
                self.screenshot_index -= 1
                if self.screenshot_index == 0:
                    self.viewing_screenshot = False
                self._load_current_image()
                
        elif "L" in actions:
            # Previous page
            if self.current_page > 1:
                self._load_page(self.current_page - 1)
                
        elif "R" in actions:
            # Next page
            if self.current_page < self.total_pages:
                self._load_page(self.current_page + 1)
                
        elif "A" in actions:
            # Select game - go to detail
            self.app.show_game_detail(game.slug)
            
        elif "START" in actions:
            # Open filter screen
            self.app.change_screen("FilterScreen")
            
        elif "B" in actions:
            if self.viewing_screenshot:
                # Exit screenshot mode
                self.viewing_screenshot = False
                self.screenshot_index = 0
                self._load_current_image()
            else:
                self.app.change_screen("MainMenu")

    def draw(self, surface):
        surface.fill(BG_COLOR)
        
        if self.loading:
            draw_text(surface, self.app.font, "Loading...", 120, 120, center=True)
            return
            
        if self.error:
            draw_text(surface, self.app.font, "Error loading catalog", 120, 100, center=True)
            draw_text(surface, self.app.font, "Press B to go back", 120, 130, center=True)
            return

        if not self.games:
            draw_text(surface, self.app.font, "No games found", 120, 100, center=True)
            if self.filter_tags:
                draw_text(surface, self.app.font, "START: Change Filters", 120, 130, (120, 120, 140), center=True)
            else:
                draw_text(surface, self.app.font, "START: Apply Filters", 120, 130, (120, 120, 140), center=True)
            draw_text(surface, self.app.font, "B: Back", 120, 230, (200, 200, 200), center=True)
            return

        game = self.games[self.selected_index]
        
        # === TOP BAR: Filter count / hint, Games count, Page info ===
        top_y = 6
        
        if self.filter_tags:
            # Show filter count
            draw_text(surface, self.app.font, f"Filters: {len(self.filter_tags)}", 2, top_y)
            # Games count (center)
            draw_text(surface, self.app.font, f"Games: {self.total_games}", 83, top_y)
            # Page count (right)
            draw_text(surface, self.app.font, f"P.{self.current_page}/{self.total_pages}", 194, top_y)
        
        else:
            # Show hint to apply filters
            draw_text(surface, self.app.font, "Press Start to Filter", 45, top_y, (255, 255, 255))
        
        
        # Show page navigation hints only when at last item on page
        if self.selected_index == len(self.games) - 1 and self.total_pages > 1:
            if self.current_page > 1 and self.current_page < self.total_pages:
                draw_text(surface, self.app.font, "L: Prev                             R: Next", 120, 231, (255, 255, 255), center=True)
            elif self.current_page > 1:
                draw_text(surface, self.app.font, "L: Prev                                           ", 120, 231, (255, 255, 255), center=True)
            elif self.current_page < self.total_pages:
                draw_text(surface, self.app.font, "                                           R: Next", 120, 231, (255, 255, 255), center=True)
        # === CENTER: Game image (icon or screenshot) ===
        img_size = 160
        img_x = (240 - img_size) // 2  # Center horizontally
        img_y = 22  # Fixed position below top bar
        
        # Draw image background
        pygame.draw.rect(surface, (30, 30, 50), (img_x, img_y, img_size, img_size))
        
        if self.current_image:
            surface.blit(self.current_image, (img_x, img_y))
        elif self.image_loading:
            draw_text(surface, self.app.font, "Loading...", 120, img_y + img_size // 2, center=True)
        
        # === TOP RIGHT: Rating (overlayed on icon) ===
        if game.rating is not None:
            draw_star_rating(surface, self.app.font, game.rating, img_x + img_size - 38, img_y + 2)
        
        # === BOTTOM OF ICON: Mature banner (full width) ===
        if game.mature_content:
            banner_y = img_y + img_size - 18
            draw_mature_banner(surface, self.app.font, img_x, banner_y, img_size)
        
        # === NAV ARROWS ===
        arrow_y = img_y + img_size // 2
        
        # Left arrow (if viewing screenshots)
        if self.screenshot_index > 0:
            draw_nav_arrow(surface, img_x - 8, arrow_y, "left", size=10)
        
        # Right arrow (if more screenshots available)
        max_screenshots = len(game.screenshot_urls)
        if self.screenshot_index < max_screenshots:
            draw_nav_arrow(surface, img_x + img_size + 8, arrow_y, "right", size=10)
        
        # === BOTTOM: Game list ===
        list_y = 186
        list_gap = 18
        visible_count = 3
        
        # Calculate which games to show (selected in middle when possible)
        # When last item is selected, keep it in the middle for page hint visibility
        if self.selected_index == len(self.games) - 1:
            start_idx = max(0, self.selected_index - 1)
        else:
            start_idx = max(0, min(self.selected_index - 1, len(self.games) - visible_count))
        end_idx = min(start_idx + visible_count, len(self.games))
        
        for i in range(start_idx, end_idx):
            g = self.games[i]
            y = list_y + (i - start_idx) * list_gap
            # Calculate global game number: (page-1) * per_page + index + 1
            game_num = (self.current_page - 1) * self.GAMES_PER_PAGE + i + 1
            numbered_title = f"{game_num}.{g.title}"
            draw_browse_list_item(surface, self.app.font, numbered_title, y, selected=(i == self.selected_index))

class GameDetail(Screen):
    """
    Game detail screen with scrollable content.
    
    Layout:
    - Header: Title (left) | Version (right)
    - Icon (left) | Rating, release date, mature warning (right)
    - Tags (full width, wrapping)
    - Description (full width, scrollable)
    - Screenshots (after description)
    - Footer: Controls hint
    """
    
    ICON_SIZE = 100
    SCROLL_SPEED = 20
    LINE_HEIGHT = 18
    
    def __init__(self, app):
        super().__init__(app)
        self.game_slug = None
        self.manifest: Optional[GameManifest] = None
        self.loading = False
        self.error = None
        self.installed_game: Optional[InstalledGame] = None
        
        # Scrolling
        self.scroll_y = 0
        self.max_scroll = 0
        self.content_height = 0
        
        # Image cache for icon and screenshots
        cache_dir = Path.home() / "gamebird" / "cache" / "images"
        self.image_cache = ImageCache(cache_dir, target_size=(self.ICON_SIZE, self.ICON_SIZE))
        self.icon_surface: Optional[pygame.Surface] = None
        self.screenshot_surfaces: List[Optional[pygame.Surface]] = []
        
    def on_enter(self):
        if self.game_slug:
            self.installed_game = self.app.repo.load_installed_games().get(self.game_slug)

    def set_game(self, slug: str):
        """Set the game to display by slug."""
        self.game_slug = slug
        self.manifest = None
        self.loading = True
        self.error = None
        self.scroll_y = 0
        self.icon_surface = None
        self.screenshot_surfaces = []
        self.installed_game = self.app.repo.load_installed_games().get(slug)
        threading.Thread(target=self._fetch_manifest, daemon=True).start()

    def _fetch_manifest(self):
        try:
            self.manifest = self.app.cdn_api.fetch_manifest(self.game_slug)
            if not self.manifest:
                self.error = "Failed to load game details"
            else:
                # Load icon
                if self.manifest.icon_url:
                    self.image_cache.get(self.manifest.icon_url, callback=self._on_icon_loaded)
                # Preload screenshots
                for url in self.manifest.screenshot_urls:
                    self.screenshot_surfaces.append(None)
                    idx = len(self.screenshot_surfaces) - 1
                    self.image_cache.get(url, callback=lambda s, i=idx: self._on_screenshot_loaded(s, i))
        except Exception as e:
            self.error = str(e)
        finally:
            self.loading = False
    
    def _on_icon_loaded(self, surface: Optional[pygame.Surface]):
        self.icon_surface = surface
    
    def _on_screenshot_loaded(self, surface: Optional[pygame.Surface], idx: int):
        if idx < len(self.screenshot_surfaces):
            self.screenshot_surfaces[idx] = surface

    def _wrap_text(self, text: str, max_chars: int = 30) -> List[str]:
        """Wrap text to fit within max characters per line."""
        words = text.split()
        lines = []
        current_line = []
        for word in words:
            current_line.append(word)
            if len(" ".join(current_line)) > max_chars:
                if len(current_line) > 1:
                    lines.append(" ".join(current_line[:-1]))
                    current_line = [word]
                else:
                    lines.append(word)
                    current_line = []
        if current_line:
            lines.append(" ".join(current_line))
        return lines

    def update(self, actions: List[str]):
        if "B" in actions:
            self.app.go_back()
            return
            
        if self.loading or not self.manifest:
            return
        
        # Scrolling
        if "UP" in actions:
            self.scroll_y = max(0, self.scroll_y - self.SCROLL_SPEED)
        elif "DOWN" in actions:
            visible_height = 195
            self.max_scroll = max(0, self.content_height - visible_height)
            self.scroll_y = min(self.max_scroll, self.scroll_y + self.SCROLL_SPEED)

        if "A" in actions:
            version = self.manifest.version or self.manifest.current_version
            if self.installed_game:
                if version != self.installed_game.installed_version:
                    self.app.start_download(self.manifest)
            else:
                self.app.start_download(self.manifest)
        elif "X" in actions and self.installed_game:
            self.app.installer.uninstall(self.game_slug)
            self.installed_game = None
            self.app.go_back()

    def draw(self, surface):
        surface.fill(BG_COLOR)
        
        if self.loading:
            draw_text(surface, self.app.font, "Loading details...", 120, 120, center=True)
            return
            
        if self.error:
            draw_text(surface, self.app.font, "Error:", 120, 100, center=True)
            draw_text(surface, self.app.font, self.error, 120, 130, center=True)
            return

        if not self.manifest:
            return
        
        version = self.manifest.version or self.manifest.current_version
        is_installed = self.installed_game and version == self.installed_game.installed_version
        
        # Calculate starting y position with scroll offset
        y = 5 - self.scroll_y
        
        # === HEADER: Title (left) | Version (right) ===
        if y > -20 and y < 200:
            draw_text(surface, self.app.font, self.manifest.title, 5, y)
            draw_text(surface, self.app.font, f"v{version}", 235, y, right=True)
        y += 20
        
        # === ICON ROW: Icon (left) | Metadata (right) ===
        icon_x = 5
        icon_y = y
        meta_x = icon_x + self.ICON_SIZE + 5
        
        # Draw icon
        if icon_y > -self.ICON_SIZE and icon_y < 200:
            pygame.draw.rect(surface, (30, 30, 50), (icon_x, icon_y, self.ICON_SIZE, self.ICON_SIZE))
            if self.icon_surface:
                surface.blit(self.icon_surface, (icon_x, icon_y))
            # Installed banner at bottom of icon
            if is_installed:
                banner_h = 18
                banner_y = icon_y + self.ICON_SIZE - banner_h
                pygame.draw.rect(surface, (0, 100, 0), (icon_x, banner_y, self.ICON_SIZE, banner_h))
                draw_text(surface, self.app.font, "INSTALLED", icon_x + self.ICON_SIZE // 2, banner_y + 10, (255, 255, 255), center=True)
        
        # Metadata on right side
        meta_y = icon_y
        
        # Rating with star
        if self.manifest.rating is not None and meta_y > -20 and meta_y < 200:
            star_img = _get_star_image(18)
            if star_img:
                surface.blit(star_img, (meta_x, meta_y))
            draw_text(surface, self.app.font, f"{self.manifest.rating:.1f}", meta_x + 22, meta_y + 3)
            meta_y += 24
            # Rating count
            if self.manifest.rating_count > 0:
                draw_text(surface, self.app.font, f"({self.manifest.rating_count} ratings)", meta_x, meta_y, (150, 150, 150))
                meta_y += 22
        
        # Release date
        draw_text(surface, self.app.font, "Released:", meta_x, meta_y, (180, 180, 180))
        meta_y += 18
        if self.manifest.release_date and meta_y > -20 and meta_y < 200:
            # Format date to MM/DD/YYYY
            date_str = self.manifest.release_date.split("T")[0] if "T" in self.manifest.release_date else self.manifest.release_date
            try:
                parts = date_str.split("-")
                if len(parts) == 3:
                    release_str = f"{parts[1]}/{parts[2]}/{parts[0]}"
                else:
                    release_str = date_str
            except:
                release_str = date_str
            draw_text(surface, self.app.font, release_str, meta_x, meta_y, (180, 180, 180))
            meta_y += 24
        
        # Mature content warning
        if self.manifest.mature_content and meta_y > -20 and meta_y < 200:
            draw_text(surface, self.app.font, "Mature Content", meta_x, meta_y, (255, 100, 100))
            meta_y += 24
        
        y += self.ICON_SIZE + 10
        
        # === TAGS ===
        if self.manifest.tags and y > -50 and y < 200:
            tag_text = "Tags: " + ", ".join(self.manifest.tags)
            tag_lines = self._wrap_text(tag_text, 28)
            for line in tag_lines:
                if y > -self.LINE_HEIGHT and y < 200:
                    draw_text(surface, self.app.font, line, 5, y, (200, 200, 200))
                y += self.LINE_HEIGHT
            y += 8
        
        # === DESCRIPTION ===
        if y > -20 and y < 200:
            draw_text(surface, self.app.font, "Description:", 5, y, (180, 180, 180))
        y += self.LINE_HEIGHT + 2
        
        desc_lines = self._wrap_text(self.manifest.description, 28)
        for line in desc_lines:
            if y > -self.LINE_HEIGHT and y < 200:
                draw_text(surface, self.app.font, line, 5, y)
            y += self.LINE_HEIGHT
        y += 10
        
        # === SCREENSHOTS ===
        if self.manifest.screenshot_urls:
            if y > -20 and y < 200:
                draw_text(surface, self.app.font, "Screenshots:", 5, y, (180, 180, 180))
            y += 20
            
            for i, ss_surface in enumerate(self.screenshot_surfaces):
                if y > -self.ICON_SIZE and y < 200:
                    ss_x = (240 - self.ICON_SIZE) // 2
                    pygame.draw.rect(surface, (30, 30, 50), (ss_x, y, self.ICON_SIZE, self.ICON_SIZE))
                    if ss_surface:
                        surface.blit(ss_surface, (ss_x, y))
                y += self.ICON_SIZE + 10
        
        # Store content height for scroll calculations
        self.content_height = y + self.scroll_y
        
        # === FOOTER (fixed at bottom) ===
        footer_y = 200
        pygame.draw.rect(surface, BG_COLOR, (0, footer_y, 240, 40))
        pygame.draw.line(surface, (60, 60, 80), (0, footer_y), (240, footer_y), 1)
        
        draw_text(surface, self.app.font, "Up/Down: Scroll to view more", 5, footer_y + 5, (255, 255, 255))
        
        if is_installed:
            draw_text(surface, self.app.font, "X: Uninstall", 5, footer_y + 22, (200, 200, 200))
        else:
            action = "A: Update" if self.installed_game else "A: Install"
            draw_text(surface, self.app.font, action, 5, footer_y + 22, (200, 200, 200))
        
        draw_text(surface, self.app.font, "B: Back", 235, footer_y + 22, (200, 200, 200), right=True)


class DownloadScreen(Screen):
    def __init__(self, app):
        super().__init__(app)
        self.manifest = None
        self.progress = 0.0
        self.status = "Initializing..."
        self.finished = False
        self.success = False
        self.showing_cta = False  # Show rating CTA after install

    def start_download(self, manifest: GameManifest):
        self.manifest = manifest
        self.progress = 0.0
        self.status = "Starting..."
        self.finished = False
        self.success = False
        self.showing_cta = False
        threading.Thread(target=self._download_task, daemon=True).start()

    def _download_task(self):
        def progress_cb(downloaded, total):
            if total > 0:
                self.progress = downloaded / total
                self.status = f"{int(self.progress * 100)}%"

        self.status = "Downloading..."
        success = self.app.installer.install_or_update(self.manifest, progress_callback=progress_cb)
        
        self.finished = True
        self.success = success
        if success:
            self.status = "Installation Complete!"
        else:
            self.status = "Installation Failed."

    def update(self, actions: List[str]):
        if self.finished:
            if self.success and not self.showing_cta:
                # Show CTA after successful install
                if "A" in actions:
                    self.showing_cta = True
            elif self.showing_cta:
                # Dismiss CTA
                if "A" in actions:
                    self.app.go_back()
            else:
                # Failed install - just go back
                if "A" in actions or "B" in actions:
                    self.app.go_back()

    def draw(self, surface):
        surface.fill(BG_COLOR)
        
        if self.showing_cta:
            # Rating CTA screen
            draw_text(surface, self.app.font, "Game Installed!", 120, 40, ACCENT_COLOR, center=True)
            
            # Wrap the message text
            msg_lines = [
                "Love it or hate it,",
                "go to Installed Games",
                "to rate it!",
                "",
                "Rating games helps",
                "other users find",
                "great content."
            ]
            y = 75
            for line in msg_lines:
                draw_text(surface, self.app.font, line, 120, y, center=True)
                y += 22
            
            draw_text(surface, self.app.font, "A: Continue", 120, 230, (200, 200, 200), center=True)
        else:
            # Download progress screen
            draw_text(surface, self.app.font, "Downloading...", 120, 40, center=True)
            if self.manifest:
                draw_text(surface, self.app.font, self.manifest.title, 120, 70, center=True)
                
            draw_progress_bar(surface, 20, 110, 200, 20, self.progress)
            draw_text(surface, self.app.font, self.status, 120, 140, center=True)
            
            if self.finished:
                draw_text(surface, self.app.font, "A: Continue", 120, 230, (200, 200, 200), center=True)

class UpdateCheck(Screen):
    def __init__(self, app):
        super().__init__(app)
        self.updates: List[UpdateInfo] = []
        self.loading = False
        self.message = ""

    def on_enter(self):
        self.loading = True
        self.updates = []
        self.message = "Checking..."
        threading.Thread(target=self._check_updates, daemon=True).start()

    def _check_updates(self):
        try:
            # Refresh catalog first (fetch ALL games for update check)
            all_games = []
            page = 1
            while True:
                catalog_page = self.app.cdn_api.fetch_catalog(page=page, per_page=100)
                all_games.extend(catalog_page.games)
                logging.info(f"Fetched page {page}/{catalog_page.total_pages}, got {len(catalog_page.games)} games")
                if page >= catalog_page.total_pages:
                    break
                page += 1
            
            if all_games:
                self.app.repo.cache_catalog(all_games)
                catalog = all_games
            else:
                catalog = self.app.repo.load_cached_catalog()
            
            logging.info(f"Total catalog: {len(catalog)} games")
            self.updates = self.app.updater.get_update_list(catalog)
            if not self.updates:
                self.message = "No updates available."
            else:
                self.message = f"Found {len(self.updates)} updates."
        except Exception as e:
            logging.error(f"Update check failed: {e}", exc_info=True)
            self.message = f"Error: {e}"
        finally:
            self.loading = False

    def update(self, actions: List[str]):
        if self.loading:
            return

        if "B" in actions:
            self.app.change_screen("MainMenu")
        elif "A" in actions and self.updates:
            # Update all (simple version)
            # Or go to a list. For simplicity, let's just pick the first one and go to details
            # In a real app, we'd show a list of updates.
            # Let's just go to the first one's detail page
            self.app.show_game_detail(self.updates[0].game_id)

    def draw(self, surface):
        surface.fill(BG_COLOR)
        draw_text(surface, self.app.font, "UPDATES", 120, 20, center=True)
        
        draw_text(surface, self.app.font, self.message, 120, 120, center=True)
        
        if not self.loading:

            draw_text(surface, self.app.font, "A: View First         B: Back", 120, 230, (200, 200, 200), center=True)

def get_device_id() -> Optional[str]:
    """Get the device ID (Pi serial number). Returns None if not available."""
    try:
        with open('/sys/firmware/devicetree/base/serial-number', 'r') as f:
            return f.read().replace('\x00', '').strip().lower()
    except FileNotFoundError:
        return None


class InstalledList(Screen):
    # Layout constants
    LIST_START_Y = 50
    ITEM_HEIGHT = 30
    VISIBLE_AREA_HEIGHT = 155  # From LIST_START_Y to footer background
    FOOTER_BG_Y = 205  # Where footer background starts
    
    def __init__(self, app):
        super().__init__(app)
        self.games: List[InstalledGame] = []
        self.selected_index = 0
        self.scroll_offset = 0  # How many items scrolled from top
        self.game_ratings: dict = {}  # Dict of game_slug -> rating (1-5)
        self.device_id: Optional[str] = None
        
        # Rating mode
        self.rating_mode = False
        self.pending_rating = 0  # Rating being selected (1-5)

    def on_enter(self):
        self.games = list(self.app.repo.load_installed_games().values())
        self.selected_index = 0
        self.scroll_offset = 0
        self.device_id = get_device_id()
        self.rating_mode = False
        # Load ratings from local storage
        self.game_ratings = self.app.repo.load_ratings()
        # Sync ratings from server in background
        if self.device_id:
            threading.Thread(target=self._sync_ratings, daemon=True).start()

    def _sync_ratings(self):
        """Sync ratings with server."""
        try:
            server_ratings = self.app.cdn_api.fetch_device_ratings(self.device_id)
            if server_ratings:
                self.game_ratings = server_ratings
                self.app.repo.save_ratings(self.game_ratings)
        except Exception as e:
            logging.warning(f"Failed to sync ratings from server: {e}")

    def _submit_rating(self, game_slug: str, rating: int):
        """Submit a rating for a game."""
        self.game_ratings[game_slug] = rating
        self.app.repo.set_rating(game_slug, rating)
        if self.device_id:
            threading.Thread(
                target=lambda: self.app.cdn_api.rate_game(self.device_id, game_slug, rating),
                daemon=True
            ).start()

    def _adjust_scroll(self):
        """Adjust scroll offset to keep selected item visible."""
        max_visible = self.VISIBLE_AREA_HEIGHT // self.ITEM_HEIGHT
        
        # Scroll down if selected is below visible area
        if self.selected_index >= self.scroll_offset + max_visible:
            self.scroll_offset = self.selected_index - max_visible + 1
        # Scroll up if selected is above visible area
        elif self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index

    def update(self, actions: List[str]):
        if not self.games:
            if "B" in actions:
                self.app.change_screen("MainMenu")
            return

        game = self.games[self.selected_index]
        
        if self.rating_mode:
            # Rating mode: LEFT/RIGHT to adjust, A to confirm, B to cancel
            if "LEFT" in actions:
                self.pending_rating = max(1, self.pending_rating - 1)
            elif "RIGHT" in actions:
                self.pending_rating = min(5, self.pending_rating + 1)
            elif "A" in actions:
                # Confirm rating
                self._submit_rating(game.id, self.pending_rating)
                self.rating_mode = False
            elif "B" in actions:
                # Cancel rating mode
                self.rating_mode = False
        else:
            # Normal mode
            if "B" in actions:
                self.app.change_screen("MainMenu")
                return
            
            if "UP" in actions:
                self.selected_index = (self.selected_index - 1) % len(self.games)
                self._adjust_scroll()
            elif "DOWN" in actions:
                self.selected_index = (self.selected_index + 1) % len(self.games)
                self._adjust_scroll()
            elif "A" in actions:
                # Go to details to allow uninstall
                self.app.show_game_detail(game.id)
            elif "Y" in actions:
                # Enter rating mode
                self.rating_mode = True
                # Start with current rating or 3 if unrated
                self.pending_rating = self.game_ratings.get(game.id, 3)

    def draw(self, surface):
        surface.fill(BG_COLOR)
        draw_text(surface, self.app.font, "INSTALLED GAMES", 120, 20, center=True)
        
        if not self.games:
            draw_text(surface, self.app.font, "No games installed", 120, 120, center=True)
            draw_text(surface, self.app.font, "B: Back", 120, 230, (200, 200, 200), center=True)
            return

        # Calculate visible range
        max_visible = self.VISIBLE_AREA_HEIGHT // self.ITEM_HEIGHT
        start_idx = self.scroll_offset
        end_idx = min(start_idx + max_visible, len(self.games))
        
        # Draw visible games
        for i in range(start_idx, end_idx):
            game = self.games[i]
            y = self.LIST_START_Y + (i - start_idx) * self.ITEM_HEIGHT
            rating = self.game_ratings.get(game.id, 0)
            is_selected = i == self.selected_index
            
            # In rating mode for this game, show pending rating
            if self.rating_mode and is_selected:
                # Draw stars for pending rating (larger)
                draw_rating_stars(surface, 8, y, self.pending_rating, size=14)
                draw_list_item(surface, self.app.font, game.title, y, 130, True, x_offset=50)
            elif rating > 0:
                # Draw stars for current rating
                draw_rating_stars(surface, 8, y, rating, size=12)
                draw_list_item(surface, self.app.font, game.title, y, 145, is_selected, x_offset=42)
            else:
                # No rating
                draw_list_item(surface, self.app.font, game.title, y, 200, is_selected)
        
        # Draw footer background to prevent text overlap
        pygame.draw.rect(surface, BG_COLOR, (0, self.FOOTER_BG_Y, 240, 35))
        
        # Footer hints
        if self.rating_mode:
            draw_text(surface, self.app.font, "LEFT/RIGHT: Adjust Stars", 120, 213, (200, 200, 200), center=True)
            draw_text(surface, self.app.font, "A: Confirm  B: Cancel", 120, 230, (200, 200, 200), center=True)
        else:
            draw_text(surface, self.app.font, "A: Select  Y: Rate  B: Back", 120, 230, (200, 200, 200), center=True)


class ParentalControlsScreen(Screen):
    """Screen for managing parental controls / child-safe mode."""
    
    # States
    STATE_MENU = "menu"
    STATE_ENTER_PIN = "enter_pin"
    STATE_CONFIRM_PIN = "confirm_pin"
    
    def __init__(self, app):
        super().__init__(app)
        self.state = self.STATE_MENU
        self.menu_items = []
        self.selected_index = 0
        self.pin_digits = ["0", "0", "0", "0"]
        self.pin_cursor = 0
        self.confirm_digits = ["0", "0", "0", "0"]
        self.pin_action = None  # "enable", "unlock", "remove"
        self.message = ""
        self.message_timer = 0

    def on_enter(self):
        self.state = self.STATE_MENU
        self._update_menu_items()
        self.selected_index = 0
        self.message = ""

    def _update_menu_items(self):
        pc = self.app.parental_controls
        self.menu_items = []
        
        if not pc.is_enabled():
            self.menu_items.append(("Enable Child Safe Mode", "enable"))
        else:
            if pc.is_locked():
                self.menu_items.append(("Unlock (Enter PIN)", "unlock"))
            else:
                self.menu_items.append(("Lock Now", "lock"))
                self.menu_items.append(("Remove PIN", "remove"))
        
        self.menu_items.append(("Back", "back"))

    def _reset_pin_entry(self):
        self.pin_digits = ["0", "0", "0", "0"]
        self.pin_cursor = 0
        self.confirm_digits = ["0", "0", "0", "0"]

    def _get_pin_string(self):
        return "".join(self.pin_digits)

    def update(self, actions: List[str]):
        # Handle temporary messages
        if self.message_timer > 0:
            self.message_timer -= 1
            if self.message_timer == 0:
                self.message = ""

        if self.state == self.STATE_MENU:
            self._update_menu(actions)
        elif self.state == self.STATE_ENTER_PIN:
            self._update_pin_entry(actions)
        elif self.state == self.STATE_CONFIRM_PIN:
            self._update_pin_confirm(actions)

    def _update_menu(self, actions):
        if "UP" in actions:
            self.selected_index = (self.selected_index - 1) % len(self.menu_items)
        elif "DOWN" in actions:
            self.selected_index = (self.selected_index + 1) % len(self.menu_items)
        elif "A" in actions:
            _, action = self.menu_items[self.selected_index]
            if action == "back":
                self.app.change_screen("MainMenu")
            elif action == "enable":
                self.pin_action = "enable"
                self._reset_pin_entry()
                self.state = self.STATE_ENTER_PIN
            elif action == "unlock":
                self.pin_action = "unlock"
                self._reset_pin_entry()
                self.state = self.STATE_ENTER_PIN
            elif action == "remove":
                self.pin_action = "remove"
                self._reset_pin_entry()
                self.state = self.STATE_ENTER_PIN
            elif action == "lock":
                self.app.parental_controls.lock()
                self._update_menu_items()
                self.message = "Locked!"
                self.message_timer = 60
        elif "B" in actions:
            self.app.change_screen("MainMenu")

    def _update_pin_entry(self, actions):
        if "UP" in actions:
            # Increment current digit
            current = int(self.pin_digits[self.pin_cursor])
            self.pin_digits[self.pin_cursor] = str((current + 1) % 10)
        elif "DOWN" in actions:
            # Decrement current digit
            current = int(self.pin_digits[self.pin_cursor])
            self.pin_digits[self.pin_cursor] = str((current - 1) % 10)
        elif "RIGHT" in actions:
            self.pin_cursor = min(3, self.pin_cursor + 1)
        elif "LEFT" in actions:
            self.pin_cursor = max(0, self.pin_cursor - 1)
        elif "A" in actions:
            # Confirm PIN entry
            if self.pin_action == "enable":
                # Need to confirm PIN
                self.confirm_digits = ["0", "0", "0", "0"]
                self.pin_cursor = 0
                self.state = self.STATE_CONFIRM_PIN
            elif self.pin_action == "unlock":
                if self.app.parental_controls.unlock(self._get_pin_string()):
                    self.message = "Unlocked!"
                    self.message_timer = 60
                    self.state = self.STATE_MENU
                    self._update_menu_items()
                else:
                    self.message = "Wrong PIN!"
                    self.message_timer = 60
                    self._reset_pin_entry()
            elif self.pin_action == "remove":
                if self.app.parental_controls.remove_pin(self._get_pin_string()):
                    self.message = "PIN Removed!"
                    self.message_timer = 60
                    self.state = self.STATE_MENU
                    self._update_menu_items()
                else:
                    self.message = "Wrong PIN!"
                    self.message_timer = 60
                    self._reset_pin_entry()
        elif "B" in actions:
            self.state = self.STATE_MENU
            self._reset_pin_entry()

    def _update_pin_confirm(self, actions):
        if "UP" in actions:
            current = int(self.confirm_digits[self.pin_cursor])
            self.confirm_digits[self.pin_cursor] = str((current + 1) % 10)
        elif "DOWN" in actions:
            current = int(self.confirm_digits[self.pin_cursor])
            self.confirm_digits[self.pin_cursor] = str((current - 1) % 10)
        elif "RIGHT" in actions:
            self.pin_cursor = min(3, self.pin_cursor + 1)
        elif "LEFT" in actions:
            self.pin_cursor = max(0, self.pin_cursor - 1)
        elif "A" in actions:
            # Check if PINs match
            if self.pin_digits == self.confirm_digits:
                if self.app.parental_controls.set_pin(self._get_pin_string()):
                    self.message = "PIN Set!"
                    self.message_timer = 60
                    self.state = self.STATE_MENU
                    self._update_menu_items()
                else:
                    self.message = "Error setting PIN"
                    self.message_timer = 60
            else:
                self.message = "PINs don't match!"
                self.message_timer = 60
                self._reset_pin_entry()
                self.state = self.STATE_ENTER_PIN
        elif "B" in actions:
            self.state = self.STATE_ENTER_PIN
            self.pin_cursor = 0

    def draw(self, surface):
        surface.fill(BG_COLOR)
        draw_text(surface, self.app.font, "PARENTAL CONTROLS", 120, 20, center=True)
        pygame.draw.line(surface, ACCENT_COLOR, (0, 40), (240, 40), 2)
        
        # Show current status
        if self.app.parental_controls.is_enabled():
            if self.app.parental_controls.is_locked():
                status = "Status: LOCKED"
                status_color = (255, 100, 100)
            else:
                status = "Status: Unlocked"
                status_color = (100, 255, 100)
        else:
            status = "Status: Disabled"
            status_color = (150, 150, 150)
        draw_text(surface, self.app.font, status, 120, 55, status_color, center=True)

        if self.state == self.STATE_MENU:
            self._draw_menu(surface)
        elif self.state == self.STATE_ENTER_PIN:
            self._draw_pin_entry(surface, "Enter PIN:")
        elif self.state == self.STATE_CONFIRM_PIN:
            self._draw_pin_entry(surface, "Confirm PIN:", confirm=True)
        
        # Show message if any
        if self.message:
            draw_text(surface, self.app.font, self.message, 120, 195, ACCENT_COLOR, center=True)

    def _draw_menu(self, surface):
        y = 80
        for i, (label, _) in enumerate(self.menu_items):
            draw_list_item(surface, self.app.font, label, y, 200, i == self.selected_index)
            y += 28
        
        draw_text(surface, self.app.font, "A: Select         B: Back", 120, 230, (200, 200, 200), center=True)

    def _draw_pin_entry(self, surface, title, confirm=False):
        draw_text(surface, self.app.font, title, 120, 80, center=True)
        
        digits = self.confirm_digits if confirm else self.pin_digits
        
        # Draw PIN digits with cursor highlight
        digit_width = 30
        start_x = 120 - (digit_width * 2)
        y = 110
        
        for i, digit in enumerate(digits):
            x = start_x + i * digit_width
            color = ACCENT_COLOR if i == self.pin_cursor else (255, 255, 255)
            draw_text(surface, self.app.font, digit, x + digit_width // 2, y, color, center=True)
            
            # Draw cursor indicator
            if i == self.pin_cursor:
                pygame.draw.line(surface, ACCENT_COLOR, (x + 5, y + 18), (x + digit_width - 5, y + 18), 2)
        
        draw_text(surface, self.app.font, "UP/DOWN: Change", 120, 145, center=True)
        draw_text(surface, self.app.font, "LEFT/RIGHT: Move", 120, 165, center=True)
        
        draw_text(surface, self.app.font, "A: Confirm         B: Cancel", 120, 230, (200, 200, 200), center=True)


class DeveloperCodeScreen(Screen):
    """Screen to display the developer code for account linking."""
    
    def __init__(self, app):
        super().__init__(app)
        self.code = None
        self.loading = False
        self.error = None

    def on_enter(self):
        self.loading = True
        self.code = None
        self.error = None
        threading.Thread(target=self._fetch_code, daemon=True).start()

    def _fetch_code(self):
        try:
            # Read Pi serial number as device ID (strip null bytes and whitespace)
            with open('/sys/firmware/devicetree/base/serial-number', 'r') as f:
                device_id = f.read().replace('\x00', '').strip().lower()
            
            response = requests.post(
                'https://dbworker.suntank.workers.dev/api/device/request-code',
                json={'device_id': device_id},
                timeout=10
            )
            
            if response.ok:
                self.code = response.json().get('code')
            else:
                self.error = response.json().get('error', 'Request failed')
        except FileNotFoundError:
            self.error = "Device ID not found"
        except requests.RequestException as e:
            self.error = "Network error"
        except Exception as e:
            self.error = str(e)
        finally:
            self.loading = False

    def update(self, actions: List[str]):
        if "B" in actions:
            self.app.change_screen("MainMenu")

    def draw(self, surface):
        surface.fill(BG_COLOR)
        draw_text(surface, self.app.font, "DEVELOPER CODE", 120, 20, center=True)
        pygame.draw.line(surface, ACCENT_COLOR, (0, 40), (240, 40), 2)
        
        if self.loading:
            draw_text(surface, self.app.font, "Fetching code...", 120, 120, center=True)
        elif self.error:
            draw_text(surface, self.app.font, "Error:", 120, 80, center=True)
            draw_text(surface, self.app.font, self.error, 120, 110, center=True)
        elif self.code:
            draw_text(surface, self.app.font, "Your code:", 120, 70, center=True)
            draw_text(surface, self.app.font, self.code, 120, 110, ACCENT_COLOR, center=True)
            draw_text(surface, self.app.font, "Enter this code on", 120, 150, center=True)
            draw_text(surface, self.app.font, "the website to link", 120, 170, center=True)
            draw_text(surface, self.app.font, "your account.", 120, 190, center=True)
        
        draw_text(surface, self.app.font, "B: Back", 120, 230, (200, 200, 200), center=True)


class RebootScreen(Screen):
    """Shows a reboot message and reboots the system after 2 seconds."""
    def __init__(self, app):
        super().__init__(app)
        self.start_time = None
    
    def on_enter(self):
        self.start_time = time.time()
        logging.info("Reboot screen entered, will reboot in 2 seconds...")
    
    def update(self, actions: List[str]):
        if self.start_time and (time.time() - self.start_time) >= 2.0:
            logging.info("Initiating system reboot...")
            pygame.quit()
            subprocess.run(['sudo', 'reboot'], check=False)
            self.app.running = False  # Fallback if reboot doesn't happen immediately
    
    def draw(self, surface):
        surface.fill(BG_COLOR)
        draw_text(surface, self.app.font, "Rebooting...", 120, 110, center=True)


class FilterScreen(Screen):
    """
    Screen for selecting tag filters.
    Tags are grouped by category (players, genre, style).
    User can toggle tags on/off and apply filters.
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.tags_by_category: dict = {}  # category -> [{id, name}, ...]
        self.categories: List[str] = []   # Ordered list of categories
        self.all_tags: List[dict] = []    # Flat list for navigation
        self.selected_index = 0
        self.selected_tags: set = set()   # Set of selected tag IDs
        self.loading = False
        self.error = None

    def on_enter(self):
        self.loading = True
        self.error = None
        # Pre-select any existing filters from CatalogList
        catalog_screen = self.app.screens.get("CatalogList")
        if catalog_screen and catalog_screen.filter_tags:
            self.selected_tags = set(catalog_screen.filter_tags)
        else:
            self.selected_tags = set()
        threading.Thread(target=self._fetch_tags, daemon=True).start()

    def _fetch_tags(self):
        try:
            self.tags_by_category = self.app.cdn_api.fetch_tags()
            
            # Define category order
            category_order = ["players", "genre", "style", "other"]
            self.categories = [c for c in category_order if c in self.tags_by_category]
            # Add any categories not in our predefined order
            for cat in self.tags_by_category:
                if cat not in self.categories:
                    self.categories.append(cat)
            
            # Build flat list for navigation
            self.all_tags = []
            for cat in self.categories:
                for tag in self.tags_by_category.get(cat, []):
                    self.all_tags.append({
                        "id": tag["id"],
                        "name": tag["name"],
                        "category": cat
                    })
            
            self.selected_index = 0
        except Exception as e:
            logging.error(f"Failed to fetch tags: {e}")
            self.error = str(e)
        finally:
            self.loading = False

    def update(self, actions: List[str]):
        if self.loading:
            if "B" in actions:
                self.app.go_back()
            return

        if not self.all_tags:
            if "B" in actions:
                self.app.go_back()
            return

        # Navigation
        if "UP" in actions:
            self.selected_index = (self.selected_index - 1) % len(self.all_tags)
        elif "DOWN" in actions:
            self.selected_index = (self.selected_index + 1) % len(self.all_tags)
        elif "A" in actions:
            # Toggle tag selection
            tag_id = self.all_tags[self.selected_index]["id"]
            if tag_id in self.selected_tags:
                self.selected_tags.discard(tag_id)
            else:
                self.selected_tags.add(tag_id)
        elif "START" in actions:
            # Apply filters and go back to catalog
            self._apply_filters()
        elif "B" in actions:
            # Cancel - go back without applying
            self.app.go_back()
        elif "X" in actions:
            # Clear all filters
            self.selected_tags.clear()

    def _apply_filters(self):
        """Apply selected filters to CatalogList and navigate back."""
        catalog_screen = self.app.screens.get("CatalogList")
        if catalog_screen:
            catalog_screen.set_filters(list(self.selected_tags))
        self.app.change_screen("CatalogList")

    def draw(self, surface):
        surface.fill(BG_COLOR)
        draw_text(surface, self.app.font, "SELECT FILTERS", 120, 12, center=True)
        pygame.draw.line(surface, ACCENT_COLOR, (0, 28), (240, 28), 2)
        
        if self.loading:
            draw_text(surface, self.app.font, "Loading tags...", 120, 120, center=True)
            return
            
        if self.error:
            draw_text(surface, self.app.font, "Error loading tags", 120, 100, center=True)
            draw_text(surface, self.app.font, "Press B to go back", 120, 130, center=True)
            return

        if not self.all_tags:
            draw_text(surface, self.app.font, "No tags available", 120, 120, center=True)
            return

        # Show selected count
        count = len(self.selected_tags)
        count_text = f"{count} filter{'s' if count != 1 else ''} selected"
        draw_text(surface, self.app.font, count_text, 102, 34, (150, 150, 150))

        # Draw scrolling tag list (simple approach - no inline category headers)
        max_visible = 8
        total_tags = len(self.all_tags)
        
        # Calculate start index to keep selected item visible
        if total_tags <= max_visible:
            start_idx = 0
        else:
            start_idx = self.selected_index - 3
            start_idx = max(0, min(start_idx, total_tags - max_visible))
        
        end_idx = min(start_idx + max_visible, total_tags)
        
        # Show category of selected tag at top-right
        if self.all_tags:
            selected_cat = self.all_tags[self.selected_index]["category"].upper()
            draw_text(surface, self.app.font, selected_cat, 15, 34, (200, 200, 200))
        
        y = 55
        for i in range(start_idx, end_idx):
            tag = self.all_tags[i]
            is_selected = i == self.selected_index
            is_checked = tag["id"] in self.selected_tags
            
            # Draw checkbox and tag name
            checkbox = "[X]" if is_checked else "[ ]"
            color = ACCENT_COLOR if is_selected else ((200, 200, 200) if is_checked else (150, 150, 150))
            
            # Highlight background for selected item
            if is_selected:
                rect = pygame.Rect(5, y - 2, 230, 18)
                pygame.draw.rect(surface, (40, 40, 60), rect, border_radius=3)
            
            draw_text(surface, self.app.font, f"{checkbox} {tag['name']}", 15, y, color)
            y += 18

        # Bottom hints
        draw_text(surface, self.app.font, "A: Toggle   X: Clear", 120, 213, (255, 255, 255), center=True)
        draw_text(surface, self.app.font, "B: Cancel   Start: Apply", 120, 230, (255, 255, 255), center=True)