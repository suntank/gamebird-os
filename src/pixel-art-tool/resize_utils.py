"""
Canvas resize utilities for pixel art app.
"""
from typing import Tuple
import pygame as pg


def resize_canvas(
    old_surface: pg.Surface,
    new_width: int,
    new_height: int,
    anchor: str = "center"
) -> pg.Surface:
    """
    Resize a canvas surface, anchoring the existing content at the specified position.
    
    Args:
        old_surface: The original surface to resize
        new_width: New width in pixels
        new_height: New height in pixels
        anchor: Where to anchor the existing content
                ("center", "top-left", "top-center", "top-right",
                 "center-left", "center-right",
                 "bottom-left", "bottom-center", "bottom-right")
    
    Returns:
        New surface with the specified dimensions
    """
    old_width = old_surface.get_width()
    old_height = old_surface.get_height()
    
    # Create new surface with transparency
    new_surface = pg.Surface((new_width, new_height), pg.SRCALPHA)
    new_surface.fill((0, 0, 0, 0))
    
    # Calculate offset based on anchor position
    if anchor == "top-left":
        offset_x, offset_y = 0, 0
    elif anchor == "top-center":
        offset_x = (new_width - old_width) // 2
        offset_y = 0
    elif anchor == "top-right":
        offset_x = new_width - old_width
        offset_y = 0
    elif anchor == "center-left":
        offset_x = 0
        offset_y = (new_height - old_height) // 2
    elif anchor == "center":
        offset_x = (new_width - old_width) // 2
        offset_y = (new_height - old_height) // 2
    elif anchor == "center-right":
        offset_x = new_width - old_width
        offset_y = (new_height - old_height) // 2
    elif anchor == "bottom-left":
        offset_x = 0
        offset_y = new_height - old_height
    elif anchor == "bottom-center":
        offset_x = (new_width - old_width) // 2
        offset_y = new_height - old_height
    elif anchor == "bottom-right":
        offset_x = new_width - old_width
        offset_y = new_height - old_height
    else:
        # Default to center
        offset_x = (new_width - old_width) // 2
        offset_y = (new_height - old_height) // 2
    
    # Blit old content onto new surface at the calculated offset
    new_surface.blit(old_surface, (offset_x, offset_y))
    
    return new_surface


def resize_frame_stack(frame_stack, new_width: int, new_height: int, anchor: str = "center"):
    """
    Resize all frames and layers in a frame stack.
    
    Args:
        frame_stack: The FrameStack object to resize
        new_width: New width in pixels
        new_height: New height in pixels
        anchor: Where to anchor the existing content
    
    Returns:
        A new FrameStack with resized frames
    """
    import importlib.util
    import sys
    from pathlib import Path
    
    # Import from 'pixel art.py' using importlib
    spec = importlib.util.spec_from_file_location("pixel_art", Path(__file__).parent / "pixel art.py")
    pixel_art = importlib.util.module_from_spec(spec)
    sys.modules["pixel_art"] = pixel_art
    spec.loader.exec_module(pixel_art)
    
    FrameStack = pixel_art.FrameStack
    Frame = pixel_art.Frame
    Canvas = pixel_art.PixelCanvas
    Layer = pixel_art.Layer
    
    new_stack = FrameStack(new_width, new_height)
    new_stack.frames = []
    
    for old_frame in frame_stack.frames:
        # Create new canvas with new dimensions
        new_canvas = Canvas(new_width, new_height)
        new_canvas.layers = []
        
        # Resize each layer
        for old_layer in old_frame.canvas.layers:
            # Resize the layer surface
            new_surface = resize_canvas(old_layer.surface, new_width, new_height, anchor)
            
            # Create new layer with resized surface (name, surface)
            new_layer = Layer(name=old_layer.name, surface=new_surface)
            new_layer.visible = old_layer.visible
            new_layer.opacity = old_layer.opacity
            new_canvas.layers.append(new_layer)
        
        new_canvas.active_index = old_frame.canvas.active_index
        new_canvas._mark_dirty()
        
        # Create new frame with the same name as the old frame
        new_frame = Frame(name=old_frame.name, canvas=new_canvas)
        new_stack.frames.append(new_frame)
    
    new_stack.active_index = frame_stack.active_index
    return new_stack
