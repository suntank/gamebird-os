from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path

@dataclass
class CatalogEntry:
    """Game entry from the catalog API (D1-backed)."""
    id: str
    slug: str
    title: str
    description: str
    version: str
    icon_url: str
    screenshot_urls: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    rating: Optional[float] = None  # 1-5 scale, None if no ratings
    mature_content: bool = False
    size_bytes: int = 0
    sha256: str = ""
    download_path: str = ""

@dataclass
class DownloadInfo:
    version: str
    size_bytes: int
    sha256: str
    path: str

@dataclass
class ChangelogEntry:
    version: str
    date: str
    notes: List[str]

@dataclass
class GameManifest:
    """Full game details from the API."""
    id: str
    slug: str
    title: str
    description: str
    version: str
    tags: List[str]
    icon_url: str
    screenshot_urls: List[str]
    download: DownloadInfo
    changelog: List[ChangelogEntry]
    rating: Optional[float] = None
    rating_count: int = 0
    mature_content: bool = False
    release_date: str = ""
    
    # Legacy fields for compatibility (may be empty)
    author: str = ""
    current_version: str = ""  # Alias for version
    engine_version: str = ""
    min_firmware_version: str = ""

@dataclass
class InstalledGame:
    id: str
    title: str
    installed_version: str
    install_path: Path
    installed_files: List[str] = None  # List of relative paths of installed files

@dataclass
class UpdateInfo:
    game_id: str
    title: str
    installed_version: str
    latest_version: str
