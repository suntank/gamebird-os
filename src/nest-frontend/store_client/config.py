from dataclasses import dataclass
from pathlib import Path
import os

@dataclass
class StoreConfig:
    api_base_url: str      # Worker API for catalog, game details
    cdn_base_url: str      # CDN for downloads and images
    data_dir: Path
    games_dir: Path
    http_timeout: float
    max_retries: int

def load_config() -> StoreConfig:
    # Default configuration
    home = Path(os.path.expanduser("~"))
    base_dir = home / "gamebird" / "store"
    games_dir = home / "gamebird" / "games"
    
    return StoreConfig(
        api_base_url="https://dbworker.suntank.workers.dev",  # Worker API
        cdn_base_url="https://cdn.gamebird.games",            # CDN for downloads
        data_dir=base_dir,
        games_dir=games_dir,
        http_timeout=10.0,
        max_retries=3
    )
