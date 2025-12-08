import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional
from .models import InstalledGame, CatalogEntry
from .config import StoreConfig

class Repository:
    def __init__(self, config: StoreConfig):
        self.config = config
        self.installed_games_path = self.config.data_dir / "installed_games.json"
        self.catalog_cache_path = self.config.data_dir / "cache" / "catalog.json"
        self.ratings_path = self.config.data_dir / "ratings.json"
        
        # Ensure directories exist
        self.config.data_dir.mkdir(parents=True, exist_ok=True)
        (self.config.data_dir / "cache").mkdir(parents=True, exist_ok=True)

    def load_installed_games(self) -> Dict[str, InstalledGame]:
        if not self.installed_games_path.exists():
            return {}
        
        try:
            with open(self.installed_games_path, 'r') as f:
                data = json.load(f)
                games = {}
                for item in data.get("games", []):
                    games[item["id"]] = InstalledGame(
                        id=item["id"],
                        title=item["title"],
                        installed_version=item["installed_version"],
                        install_path=Path(item["install_path"]),
                        installed_files=item.get("installed_files", [])
                    )
                return games
        except json.JSONDecodeError:
            logging.error("Failed to parse installed_games.json")
            return {}

    def save_installed_games(self, games: Dict[str, InstalledGame]):
        data = {
            "games": [
                {
                    "id": g.id,
                    "title": g.title,
                    "installed_version": g.installed_version,
                    "install_path": str(g.install_path),
                    "installed_files": g.installed_files or []
                }
                for g in games.values()
            ]
        }
        
        # Atomic write
        temp_path = self.installed_games_path.with_suffix(".tmp")
        try:
            with open(temp_path, 'w') as f:
                json.dump(data, f, indent=2)
            os.replace(temp_path, self.installed_games_path)
        except Exception as e:
            logging.error(f"Failed to save installed games: {e}")

    def cache_catalog(self, catalog: List[CatalogEntry]):
        data = {
            "games": [
                {
                    "id": e.id,
                    "slug": e.slug,
                    "title": e.title,
                    "description": e.description,
                    "version": e.version,
                    "icon_url": e.icon_url,
                    "screenshot_urls": e.screenshot_urls,
                    "tags": e.tags,
                    "rating": e.rating,
                    "mature_content": e.mature_content,
                    "size_bytes": e.size_bytes,
                    "sha256": e.sha256,
                    "download_path": e.download_path
                }
                for e in catalog
            ]
        }
        try:
            with open(self.catalog_cache_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to cache catalog: {e}")

    def load_cached_catalog(self) -> List[CatalogEntry]:
        if not self.catalog_cache_path.exists():
            return []
        
        try:
            with open(self.catalog_cache_path, 'r') as f:
                data = json.load(f)
                entries = []
                for item in data.get("games", []):
                    entries.append(CatalogEntry(
                        id=item["id"],
                        slug=item.get("slug", item["id"]),
                        title=item["title"],
                        description=item.get("description", ""),
                        version=item.get("version", ""),
                        icon_url=item.get("icon_url", ""),
                        screenshot_urls=item.get("screenshot_urls", []),
                        tags=item.get("tags", []),
                        rating=item.get("rating"),
                        mature_content=item.get("mature_content", False),
                        size_bytes=item.get("size_bytes", 0),
                        sha256=item.get("sha256", ""),
                        download_path=item.get("download_path", "")
                    ))
                return entries
        except json.JSONDecodeError:
            logging.error("Failed to parse cached catalog")
            return []

    def load_ratings(self) -> Dict[str, int]:
        """Load dict of game ratings {game_slug: rating} from local storage."""
        if not self.ratings_path.exists():
            return {}
        
        try:
            with open(self.ratings_path, 'r') as f:
                data = json.load(f)
                return data.get("ratings", {})
        except json.JSONDecodeError:
            logging.error("Failed to parse ratings.json")
            return {}

    def save_ratings(self, ratings: Dict[str, int]):
        """Save dict of game ratings to local storage."""
        data = {"ratings": ratings}
        
        temp_path = self.ratings_path.with_suffix(".tmp")
        try:
            with open(temp_path, 'w') as f:
                json.dump(data, f, indent=2)
            os.replace(temp_path, self.ratings_path)
        except Exception as e:
            logging.error(f"Failed to save ratings: {e}")

    def set_rating(self, game_slug: str, rating: int) -> None:
        """Set a rating (1-5) for a game."""
        ratings = self.load_ratings()
        ratings[game_slug] = rating
        self.save_ratings(ratings)

    def remove_rating(self, game_slug: str) -> bool:
        """Remove a rating for a game. Returns True if was removed."""
        ratings = self.load_ratings()
        if game_slug in ratings:
            del ratings[game_slug]
            self.save_ratings(ratings)
            return True
        return False

    def get_rating(self, game_slug: str) -> Optional[int]:
        """Get the rating for a game, or None if not rated."""
        return self.load_ratings().get(game_slug)
