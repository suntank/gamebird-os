import pygame
from typing import List, Optional, Tuple
from pathlib import Path

# Colors
BG_COLOR = (20, 24, 40)
ACCENT_COLOR = (80, 180, 255)
TEXT_COLOR = (220, 220, 220)
SELECTED_TEXT_COLOR = (255, 255, 0)
HIGHLIGHT_COLOR = (60, 60, 80)
MATURE_RED = (180, 40, 40)
STAR_YELLOW = (255, 215, 0)
TAG_BG = (60, 60, 80)
TAG_BORDER = (100, 100, 120)

# Star image cache (loaded lazily)
_star_image_cache: dict = {}  # size -> pygame.Surface

def _get_star_image(size: int) -> Optional[pygame.Surface]:
    """Get a cached star image scaled to the given size."""
    if size in _star_image_cache:
        return _star_image_cache[size]
    
    # Load star image from same directory as this file
    star_path = Path(__file__).parent / "star.png.png"
    if not star_path.exists():
        return None
    
    try:
        original = pygame.image.load(str(star_path)).convert_alpha()
        scaled = pygame.transform.smoothscale(original, (size, size))
        _star_image_cache[size] = scaled
        return scaled
    except Exception:
        return None


def draw_text(surface, font, text, x, y, color=TEXT_COLOR, center=False, right=False):
    surf = font.render(text, True, color)
    if center:
        rect = surf.get_rect(center=(x, y))
        surface.blit(surf, rect)
    elif right:
        rect = surf.get_rect(topright=(x, y))
        surface.blit(surf, rect)
    else:
        surface.blit(surf, (x, y))
    return surf.get_width()


def draw_list_item(surface, font, text, y, width, selected=False, x_offset=0):
    rect_height = 24
    x = (surface.get_width() - width) // 2 + x_offset
    
    if selected:
        rect = pygame.Rect(x, y - rect_height//2, width, rect_height)
        pygame.draw.rect(surface, ACCENT_COLOR, rect, border_radius=5)
        pygame.draw.rect(surface, (255, 255, 255), rect, width=2, border_radius=5)
        color = SELECTED_TEXT_COLOR
    else:
        color = TEXT_COLOR
        
    draw_text(surface, font, text, x + width // 2, y, color, center=True)


def draw_browse_list_item(surface, font, text: str, y: int, selected: bool = False):
    """
    Draw a game title in the browse list at the bottom.
    Selected item gets white background with black text.
    """
    rect_height = 18
    padding = 8
    
    # Measure text
    text_surf = font.render(text, True, (0, 0, 0) if selected else TEXT_COLOR)
    text_width = min(text_surf.get_width(), surface.get_width() - 20)
    
    # Center horizontally
    x = (surface.get_width() - text_width - padding * 2) // 2
    
    if selected:
        # White rounded rectangle background
        rect = pygame.Rect(x, y, text_width + padding * 2, rect_height)
        pygame.draw.rect(surface, (255, 255, 255), rect, border_radius=4)
        # Black text
        text_surf = font.render(text, True, (0, 0, 0))
    
    # Blit text centered in the rect
    text_x = x + padding
    text_y = y + (rect_height - text_surf.get_height()) // 2
    surface.blit(text_surf, (text_x, text_y))


def draw_tag_pill(surface, font, tag: str, x: int, y: int) -> int:
    """
    Draw a tag pill and return its width.
    """
    padding_x = 6
    padding_y = 2
    
    text_surf = font.render(tag, True, TEXT_COLOR)
    width = text_surf.get_width() + padding_x * 2
    height = text_surf.get_height() + padding_y * 2
    
    # Draw pill background
    rect = pygame.Rect(x, y, width, height)
    pygame.draw.rect(surface, TAG_BG, rect, border_radius=3)
    pygame.draw.rect(surface, TAG_BORDER, rect, width=1, border_radius=3)
    
    # Draw text
    surface.blit(text_surf, (x + padding_x, y + padding_y))
    
    return width


def draw_tags_row(surface, font, tags: List[str], x: int, y: int, max_width: int) -> None:
    """
    Draw as many tags as fit in the given width.
    """
    current_x = x
    gap = 4
    
    for tag in tags:
        # Measure tag width
        text_surf = font.render(tag, True, TEXT_COLOR)
        pill_width = text_surf.get_width() + 12  # padding
        
        if current_x + pill_width > x + max_width:
            break  # No more room
        
        draw_tag_pill(surface, font, tag, current_x, y)
        current_x += pill_width + gap


def draw_star_rating(surface, font, rating: Optional[float], x: int, y: int) -> None:
    """
    Draw a star icon with rating number (e.g., star + "4.3").
    """
    if rating is None:
        return
    
    star_size = 16
    star_img = _get_star_image(star_size)
    
    if star_img:
        # Draw star image centered at position
        surface.blit(star_img, (x - star_size // 2, y))
        # Draw rating number next to star
        rating_text = f"{rating:.1f}"
        draw_text(surface, font, rating_text, x + star_size // 2 + 2, y + 2, STAR_YELLOW)
    else:
        # Fallback to polygon if image not available
        import math
        star_x = x
        star_y = y + 6
        points = []
        for i in range(5):
            angle = math.radians(-90 + i * 72)
            points.append((star_x + star_size * 0.5 * math.cos(angle), 
                           star_y + star_size * 0.5 * math.sin(angle)))
            angle = math.radians(-90 + i * 72 + 36)
            points.append((star_x + star_size * 0.2 * math.cos(angle),
                           star_y + star_size * 0.2 * math.sin(angle)))
        pygame.draw.polygon(surface, STAR_YELLOW, points)
        rating_text = f"{rating:.1f}"
        draw_text(surface, font, rating_text, x + star_size // 2 + 4, y, STAR_YELLOW)


def draw_mature_banner(surface, font, x: int, y: int, width: int) -> None:
    """
    Draw a red "Mature" banner across the bottom of an image.
    """
    banner_height = 18
    rect = pygame.Rect(x, y, width, banner_height)
    pygame.draw.rect(surface, MATURE_RED, rect)
    
    # Center text
    text_surf = font.render("Mature", True, (255, 255, 255))
    text_x = x + (width - text_surf.get_width()) // 2
    text_y = y + (banner_height - text_surf.get_height()) // 2
    surface.blit(text_surf, (text_x, text_y))


def draw_nav_arrow(surface, x: int, y: int, direction: str, size: int = 12) -> None:
    """
    Draw a navigation arrow (left or right).
    """
    if direction == "right":
        points = [
            (x, y - size),
            (x + size, y),
            (x, y + size)
        ]
    else:  # left
        points = [
            (x, y - size),
            (x - size, y),
            (x, y + size)
        ]
    
    pygame.draw.polygon(surface, (255, 255, 0), points)


def draw_page_indicator(surface, font, page: int, total_pages: int, y: int) -> None:
    """
    Draw page indicator at the bottom (e.g., "Page 1/5").
    """
    text = f"Page {page}/{total_pages}"
    draw_text(surface, font, text, surface.get_width() // 2, y, (150, 150, 150), center=True)


def draw_rating_stars(surface, x: int, y: int, rating: int, max_stars: int = 5, size: int = 12, filled_color: Tuple[int, int, int] = STAR_YELLOW, empty_color: Tuple[int, int, int] = (80, 80, 80)) -> int:
    """
    Draw star rating display (filled and empty stars).
    Returns the total width of the drawn stars.
    
    Args:
        surface: Pygame surface
        x: X position (left edge)
        y: Y position (center vertically)
        rating: Number of filled stars (0-5)
        max_stars: Total number of stars to draw
        size: Size of each star
        filled_color: Color for filled stars
        empty_color: Color for empty stars
    """
    gap = 2
    total_width = 0
    star_img = _get_star_image(size)
    
    for i in range(max_stars):
        star_x = x + i * (size + gap)
        star_y = y - size // 2
        is_filled = i < rating
        
        if star_img:
            if is_filled:
                # Draw filled star (normal image)
                surface.blit(star_img, (star_x, star_y))
            else:
                # Draw empty star (darkened version)
                dark_star = star_img.copy()
                dark_star.fill((60, 60, 60, 255), special_flags=pygame.BLEND_RGBA_MULT)
                surface.blit(dark_star, (star_x, star_y))
        else:
            # Fallback to polygon
            import math
            cx = star_x + size // 2
            cy = y
            color = filled_color if is_filled else empty_color
            points = []
            for j in range(5):
                angle = math.radians(-90 + j * 72)
                points.append((cx + (size // 2) * math.cos(angle), 
                               cy + (size // 2) * math.sin(angle)))
                angle = math.radians(-90 + j * 72 + 36)
                points.append((cx + (size // 2) * 0.4 * math.cos(angle),
                               cy + (size // 2) * 0.4 * math.sin(angle)))
            pygame.draw.polygon(surface, color, points)
        
        total_width = (i + 1) * (size + gap)
    
    return total_width


def draw_heart(surface, x: int, y: int, size: int = 12, color: Tuple[int, int, int] = (255, 100, 100), filled: bool = True) -> None:
    """
    Draw a heart shape at the given position.
    The heart is centered at (x, y).
    """
    import math
    
    # Heart shape using parametric equations
    points = []
    for i in range(30):
        t = i * 2 * math.pi / 30
        # Parametric heart curve
        hx = 16 * (math.sin(t) ** 3)
        hy = -(13 * math.cos(t) - 5 * math.cos(2*t) - 2 * math.cos(3*t) - math.cos(4*t))
        # Scale and translate
        scale = size / 32
        points.append((x + hx * scale, y + hy * scale))
    
    if filled:
        pygame.draw.polygon(surface, color, points)
    else:
        pygame.draw.polygon(surface, color, points, width=2)


def draw_progress_bar(surface, x, y, width, height, progress):
    # Background
    pygame.draw.rect(surface, (50, 50, 50), (x, y, width, height), border_radius=3)
    # Fill
    fill_width = int(width * progress)
    if fill_width > 0:
        pygame.draw.rect(surface, ACCENT_COLOR, (x, y, fill_width, height), border_radius=3)


def draw_button_hint(surface, font, label, x, y, color):
    pygame.draw.circle(surface, color, (x, y), 8)
    draw_text(surface, font, label, x + 12, y - 6, (150, 150, 150))
