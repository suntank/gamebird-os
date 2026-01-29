"""
Export utilities for saving artwork as PNG, GIF, and ZIP files.
"""
from typing import List, Tuple
from pathlib import Path
import pygame as pg
from PIL import Image
import io
import zipfile


def pygame_surface_to_pil(surface: pg.Surface) -> Image.Image:
    """Convert a pygame surface to a PIL Image."""
    # Get the raw string buffer from the surface
    size = surface.get_size()
    mode = "RGBA"
    raw_str = pg.image.tostring(surface, mode)
    
    # Create PIL image from the raw data
    pil_image = Image.frombytes(mode, size, raw_str)
    return pil_image


def scale_surface(surface: pg.Surface, scale: float) -> pg.Surface:
    """Scale a pygame surface by the given factor."""
    if scale == 1.0:
        return surface
    
    new_width = int(surface.get_width() * scale)
    new_height = int(surface.get_height() * scale)
    
    # Use nearest neighbor scaling for pixel art
    return pg.transform.scale(surface, (new_width, new_height))


def export_single_png(surface: pg.Surface, filepath: Path, scale: float = 1.0) -> None:
    """Export a single frame as PNG."""
    # Scale if needed
    if scale != 1.0:
        surface = scale_surface(surface, scale)
    
    # Save using pygame
    pg.image.save(surface, str(filepath))


def export_spritesheet(frames: List[pg.Surface], filepath: Path, scale: float = 1.0, cols: int = 0) -> None:
    """Export frames as a horizontal spritesheet PNG."""
    if not frames:
        return
    
    # Scale frames if needed
    if scale != 1.0:
        frames = [scale_surface(frame, scale) for frame in frames]
    
    frame_width = frames[0].get_width()
    frame_height = frames[0].get_height()
    num_frames = len(frames)
    
    # Calculate layout
    if cols == 0:
        # Single row
        cols = num_frames
        rows = 1
    else:
        rows = (num_frames + cols - 1) // cols
    
    # Create spritesheet surface
    sheet_width = frame_width * cols
    sheet_height = frame_height * rows
    spritesheet = pg.Surface((sheet_width, sheet_height), pg.SRCALPHA)
    spritesheet.fill((0, 0, 0, 0))
    
    # Blit all frames onto the spritesheet
    for idx, frame in enumerate(frames):
        col = idx % cols
        row = idx // cols
        x = col * frame_width
        y = row * frame_height
        spritesheet.blit(frame, (x, y))
    
    # Save
    pg.image.save(spritesheet, str(filepath))


def export_gif(frames: List[pg.Surface], filepath: Path, scale: float = 1.0, 
               duration: int = 100, loop: bool = True) -> None:
    """Export frames as an animated GIF."""
    if not frames:
        return
    
    # Scale frames if needed
    if scale != 1.0:
        frames = [scale_surface(frame, scale) for frame in frames]
    
    # Convert pygame surfaces to PIL images
    pil_images = [pygame_surface_to_pil(frame) for frame in frames]
    
    # Save as animated GIF
    loop_count = 0 if loop else 1
    pil_images[0].save(
        filepath,
        save_all=True,
        append_images=pil_images[1:],
        duration=duration,
        loop=loop_count,
        optimize=False
    )


def export_zip(frames: List[pg.Surface], filepath: Path, scale: float = 1.0, 
               base_name: str = "frame") -> None:
    """Export frames as separate PNG files in a ZIP archive."""
    if not frames:
        return
    
    # Scale frames if needed
    if scale != 1.0:
        frames = [scale_surface(frame, scale) for frame in frames]
    
    # Create ZIP file
    with zipfile.ZipFile(filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for idx, frame in enumerate(frames):
            # Save frame to bytes
            frame_bytes = io.BytesIO()
            pg.image.save(frame, frame_bytes, "frame.png")
            frame_bytes.seek(0)
            
            # Add to ZIP
            frame_name = f"{base_name}_{idx:03d}.png"
            zipf.writestr(frame_name, frame_bytes.read())


def get_export_filename(base_name: str, export_format: str, spritesheet: bool = False) -> str:
    """Generate an appropriate filename for the export."""
    if export_format == "gif":
        return f"{base_name}.gif"
    elif export_format == "zip":
        return f"{base_name}_frames.zip"
    elif export_format == "png":
        if spritesheet:
            return f"{base_name}_spritesheet.png"
        else:
            return f"{base_name}.png"
    return f"{base_name}.png"
