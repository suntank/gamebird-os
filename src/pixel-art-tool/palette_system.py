"""
Palette management system for pixel art editor.
Implements Piskel-style palette features.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

Color = Tuple[int, int, int, int]


@dataclass
class Palette:
    """A color palette with a name and list of colors."""
    name: str
    colors: List[Color] = field(default_factory=list)
    
    def add_color(self, color: Color) -> None:
        """Add a color to the palette if it's not already present."""
        if color not in self.colors:
            self.colors.append(color)
    
    def remove_color(self, index: int) -> bool:
        """Remove a color by index."""
        if 0 <= index < len(self.colors):
            self.colors.pop(index)
            return True
        return False
    
    def to_dict(self) -> dict:
        """Convert palette to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "colors": [[r, g, b, a] for r, g, b, a in self.colors]
        }
    
    @staticmethod
    def from_dict(data: dict) -> Palette:
        """Create palette from dictionary."""
        colors = [tuple(c) for c in data.get("colors", [])]
        return Palette(name=data.get("name", "Unnamed"), colors=colors)
    
    def clone(self) -> Palette:
        """Create a deep copy of this palette."""
        return Palette(name=f"{self.name} clone", colors=self.colors.copy())


class PaletteManager:
    """Manages multiple palettes."""
    
    def __init__(self):
        self.palettes: List[Palette] = []
        self.active_index: int = 0
        self._create_default_palettes()
    
    def _create_default_palettes(self) -> None:
        """Create default palettes with common colors."""
        # Default comprehensive palette
        default_palette = Palette(name="Default colors")
        default_colors = [
            # Grayscale
            (0, 0, 0, 255), (32, 32, 32, 255), (64, 64, 64, 255), (96, 96, 96, 255),
            (128, 128, 128, 255), (160, 160, 160, 255), (192, 192, 192, 255), (255, 255, 255, 255),
            # Reds
            (128, 0, 0, 255), (192, 0, 0, 255), (255, 0, 0, 255), (255, 64, 64, 255),
            (255, 128, 128, 255), (255, 192, 192, 255),
            # Oranges
            (255, 128, 0, 255), (255, 160, 64, 255), (255, 192, 128, 255),
            # Yellows
            (255, 255, 0, 255), (255, 255, 128, 255), (255, 255, 192, 255),
            # Greens
            (0, 128, 0, 255), (0, 192, 0, 255), (64, 255, 64, 255), (128, 255, 128, 255),
            # Cyans
            (0, 192, 192, 255), (0, 255, 255, 255), (128, 255, 255, 255),
            # Blues
            (0, 0, 192, 255), (0, 0, 255, 255), (64, 64, 255, 255), (128, 128, 255, 255),
            # Purples
            (128, 0, 128, 255), (192, 0, 192, 255), (255, 0, 255, 255), (255, 128, 255, 255),
        ]
        default_palette.colors = default_colors
        self.palettes.append(default_palette)
        
        # Simple palette
        simple_palette = Palette(name="Simple", colors=[
            (0, 0, 0, 255),       # Black
            (255, 255, 255, 255), # White
            (255, 0, 0, 255),     # Red
            (0, 255, 0, 255),     # Green
            (0, 0, 255, 255),     # Blue
            (255, 255, 0, 255),   # Yellow
        ])
        self.palettes.append(simple_palette)
    
    @property
    def active_palette(self) -> Palette:
        """Get the currently active palette."""
        if not self.palettes:
            self._create_default_palettes()
        return self.palettes[self.active_index]
    
    def add_palette(self, palette: Palette) -> None:
        """Add a new palette."""
        self.palettes.append(palette)
        self.active_index = len(self.palettes) - 1
    
    def remove_palette(self, index: int) -> bool:
        """Remove a palette by index."""
        if len(self.palettes) <= 1:
            return False  # Keep at least one palette
        if 0 <= index < len(self.palettes):
            self.palettes.pop(index)
            self.active_index = min(self.active_index, len(self.palettes) - 1)
            return True
        return False
    
    def clone_active(self) -> None:
        """Clone the active palette."""
        cloned = self.active_palette.clone()
        self.add_palette(cloned)
    
    def save_palette(self, palette: Palette, filepath: Path) -> None:
        """Save palette to JSON file."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(palette.to_dict(), f, indent=2)
    
    def load_palette(self, filepath: Path) -> Palette:
        """Load palette from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return Palette.from_dict(data)
    
    def save_all(self, directory: Path) -> None:
        """Save all palettes to a directory."""
        directory.mkdir(parents=True, exist_ok=True)
        config = {
            "active_index": self.active_index,
            "palettes": [p.to_dict() for p in self.palettes]
        }
        with open(directory / "palettes.json", 'w') as f:
            json.dump(config, f, indent=2)
    
    def load_all(self, directory: Path) -> None:
        """Load all palettes from a directory."""
        config_file = directory / "palettes.json"
        if not config_file.exists():
            return
        
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        self.palettes = [Palette.from_dict(p) for p in config.get("palettes", [])]
        self.active_index = config.get("active_index", 0)
        
        if not self.palettes:
            self._create_default_palettes()
