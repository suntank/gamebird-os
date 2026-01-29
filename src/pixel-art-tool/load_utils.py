"""
Image loading utilities for pixel art app.
"""
from pathlib import Path
from typing import Optional, Tuple
import json
import subprocess
import sys
import pygame as pg

def _run_zenity_dialog(payload: dict) -> Optional[str]:
    """Run a file dialog using zenity (native GTK, works better on Linux)."""
    kind = payload.get('kind')
    
    try:
        if kind == 'open_image':
            cmd = [
                'zenity', '--file-selection',
                '--title=Load Image',
                '--file-filter=Image files | *.png *.jpg *.jpeg *.bmp *.gif *.tga',
                '--file-filter=All files | *',
            ]
        elif kind == 'save_image':
            default_name = payload.get('default_name', 'pixel_art.png')
            cmd = [
                'zenity', '--file-selection', '--save',
                '--title=Save Image',
                f'--filename={default_name}',
                '--file-filter=PNG files | *.png',
                '--file-filter=All files | *',
                '--confirm-overwrite',
            ]
        elif kind == 'save_export':
            default_name = payload.get('default_name', 'pixel_art.png')
            export_format = payload.get('export_format', 'png')
            
            if export_format == 'gif':
                file_filter = '--file-filter=GIF files | *.gif'
            elif export_format == 'zip':
                file_filter = '--file-filter=ZIP files | *.zip'
            else:
                file_filter = '--file-filter=PNG files | *.png'
            
            cmd = [
                'zenity', '--file-selection', '--save',
                '--title=Export As',
                f'--filename={default_name}',
                file_filter,
                '--file-filter=All files | *',
                '--confirm-overwrite',
            ]
        else:
            return None
        
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        
        # zenity returns 0 on success, 1 on cancel
        if completed.returncode == 0:
            out = (completed.stdout or "").strip()
            return out if out else None
        return None
        
    except Exception as e:
        print(f"Error opening file dialog: {e}")
        return None


def _run_tk_dialog(payload: dict) -> Optional[str]:
    """Fallback to tkinter if zenity is not available."""
    code = (
        "import json, sys\n"
        "data = json.loads(sys.argv[1])\n"
        "kind = data.get('kind')\n"
        "import tkinter as tk\n"
        "from tkinter import filedialog\n"
        "root = tk.Tk()\n"
        "root.withdraw()\n"
        "try:\n"
        "    root.attributes('-topmost', True)\n"
        "except Exception:\n"
        "    pass\n"
        "root.update_idletasks()\n"
        "root.update()\n"
        "root.focus_force()\n"
        "result = ''\n"
        "if kind == 'open_image':\n"
        "    result = filedialog.askopenfilename(\n"
        "        parent=root,\n"
        "        title='Load Image',\n"
        "        filetypes=[\n"
        "            ('Image files', '*.png *.jpg *.jpeg *.bmp *.gif *.tga'),\n"
        "            ('PNG files', '*.png'),\n"
        "            ('JPEG files', '*.jpg *.jpeg'),\n"
        "            ('All files', '*.*'),\n"
        "        ],\n"
        "    )\n"
        "elif kind == 'save_image':\n"
        "    result = filedialog.asksaveasfilename(\n"
        "        parent=root,\n"
        "        title='Save Image',\n"
        "        initialfile=data.get('default_name', 'pixel_art.png'),\n"
        "        filetypes=[\n"
        "            ('PNG files', '*.png'),\n"
        "            ('JPEG files', '*.jpg'),\n"
        "            ('Bitmap files', '*.bmp'),\n"
        "            ('All files', '*.*'),\n"
        "        ],\n"
        "        defaultextension='.png',\n"
        "    )\n"
        "elif kind == 'save_export':\n"
        "    export_format = data.get('export_format', 'png')\n"
        "    if export_format == 'gif':\n"
        "        filetypes = [('GIF files', '*.gif'), ('All files', '*.*')]\n"
        "        default_ext = '.gif'\n"
        "    elif export_format == 'zip':\n"
        "        filetypes = [('ZIP files', '*.zip'), ('All files', '*.*')]\n"
        "        default_ext = '.zip'\n"
        "    else:\n"
        "        filetypes = [('PNG files', '*.png'), ('All files', '*.*')]\n"
        "        default_ext = '.png'\n"
        "    result = filedialog.asksaveasfilename(\n"
        "        parent=root,\n"
        "        title='Export As',\n"
        "        initialfile=data.get('default_name', 'pixel_art.png'),\n"
        "        filetypes=filetypes,\n"
        "        defaultextension=default_ext,\n"
        "    )\n"
        "root.destroy()\n"
        "sys.stdout.write(result or '')\n"
    )

    try:
        completed = subprocess.run(
            [sys.executable, "-c", code, json.dumps(payload)],
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as e:
        print(f"Error opening file dialog: {e}")
        return None

    if completed.returncode != 0:
        err = (completed.stderr or "").strip()
        if err:
            print(f"Error opening file dialog: {err}")
        return None

    out = (completed.stdout or "").strip()
    return out if out else None


def _run_file_dialog(payload: dict) -> Optional[str]:
    """Run a file dialog, preferring zenity on Linux."""
    import shutil
    # Prefer zenity on Linux as it integrates better with the desktop
    if shutil.which('zenity'):
        return _run_zenity_dialog(payload)
    # Fall back to tkinter
    return _run_tk_dialog(payload)

def load_image_to_canvas(image_path: str, max_width: int = 512, max_height: int = 512) -> Optional[Tuple[pg.Surface, int, int]]:
    """
    Load an image from a file and prepare it for the canvas.
    
    Args:
        image_path: Path to the image file
        max_width: Maximum canvas width (default 512)
        max_height: Maximum canvas height (default 512)
    
    Returns:
        Tuple of (surface, width, height) or None if loading failed
    """
    try:
        # Load the image
        image = pg.image.load(image_path)
        
        # Get dimensions
        width = image.get_width()
        height = image.get_height()
        
        # Clamp to maximum dimensions
        if width > max_width or height > max_height:
            # Calculate scale to fit within max dimensions
            scale = min(max_width / width, max_height / height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            
            # Scale the image
            image = pg.transform.scale(image, (new_width, new_height))
            width = new_width
            height = new_height
        
        # Convert to RGBA format with per-pixel alpha
        surface = pg.Surface((width, height), pg.SRCALPHA)
        surface.blit(image, (0, 0))
        
        return (surface, width, height)
        
    except Exception as e:
        print(f"Error loading image: {e}")
        return None


def open_image_file_dialog() -> Optional[str]:
    """
    Open a file dialog to select an image file.
    
    Returns:
        Path to selected file or None if cancelled
    """
    try:
        # Aggressively release pygame's input grab before showing tkinter dialog
        try:
            pg.event.set_grab(False)
        except Exception:
            pass
        try:
            pg.mouse.set_visible(True)
        except Exception:
            pass
        # Pump and clear all pygame events to fully release input
        pg.event.pump()
        pg.event.clear()
        # Small delay to ensure pygame releases input
        pg.time.wait(50)
        
        file_path = _run_file_dialog({"kind": "open_image"})
        # Clear any remaining pygame events after dialog closes
        pg.event.pump()
        pg.event.clear()

        return file_path
        
    except Exception as e:
        print(f"Error opening file dialog: {e}")
        return None


def save_image_file_dialog(default_name: str = "pixel_art.png") -> Optional[str]:
    """
    Open a file dialog to save an image file.
    
    Args:
        default_name: Default filename for the save dialog
        
    Returns:
        Path to save file or None if cancelled
    """
    try:
        # Aggressively release pygame's input grab before showing tkinter dialog
        try:
            pg.event.set_grab(False)
        except Exception:
            pass
        try:
            pg.mouse.set_visible(True)
        except Exception:
            pass
        # Pump and clear all pygame events to fully release input
        pg.event.pump()
        pg.event.clear()
        # Small delay to ensure pygame releases input
        pg.time.wait(50)
        
        file_path = _run_file_dialog({"kind": "save_image", "default_name": default_name})
        # Clear any remaining pygame events after dialog closes
        pg.event.pump()
        pg.event.clear()

        return file_path
        
    except Exception as e:
        print(f"Error opening save dialog: {e}")
        return None


def save_export_file_dialog(default_name: str, export_format: str = "png") -> Optional[str]:
    """
    Open a file dialog to save an export file (supports GIF, PNG, ZIP).
    
    Args:
        default_name: Default filename for the save dialog
        export_format: Export format ("gif", "png", "zip")
        
    Returns:
        Path to save file or None if cancelled
    """
    try:
        # Aggressively release pygame's input grab before showing tkinter dialog
        try:
            pg.event.set_grab(False)
        except Exception:
            pass
        try:
            pg.mouse.set_visible(True)
        except Exception:
            pass
        # Pump and clear all pygame events to fully release input
        pg.event.pump()
        pg.event.clear()
        # Small delay to ensure pygame releases input
        pg.time.wait(50)
        
        file_path = _run_file_dialog(
            {"kind": "save_export", "default_name": default_name, "export_format": export_format}
        )
        # Clear any remaining pygame events after dialog closes
        pg.event.pump()
        pg.event.clear()

        return file_path
        
    except Exception as e:
        print(f"Error opening export dialog: {e}")
        return None


def create_frame_stack_from_image(surface: pg.Surface, width: int, height: int):
    """
    Create a new FrameStack from a loaded image surface.
    
    Args:
        surface: The image surface to convert
        width: Canvas width
        height: Canvas height
    
    Returns:
        A new FrameStack with the image as a layer
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
    
    # Create new canvas
    canvas = Canvas(width, height)
    canvas.layers = []
    
    # Create layer with the loaded image
    layer = Layer(name="Loaded Image", surface=surface)
    canvas.layers.append(layer)
    canvas.active_index = 0
    canvas._mark_dirty()
    
    # Create frame
    frame = Frame(name="Frame 1", canvas=canvas)
    
    # Create frame stack
    frame_stack = FrameStack(width, height)
    frame_stack.frames = [frame]
    frame_stack.active_index = 0
    
    return frame_stack
