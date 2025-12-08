from typing import List, Optional, Dict, Any
from pathlib import Path
from dataclasses import dataclass
import logging
from .http_client import HttpClient
from .models import CatalogEntry, GameManifest, DownloadInfo, ChangelogEntry


@dataclass
class CatalogPage:
    """Paginated catalog response."""
    games: List[CatalogEntry]
    page: int
    per_page: int
    total: int
    total_pages: int


class CdnApi:
    def __init__(self, api_client: HttpClient, cdn_client: Optional[HttpClient] = None):
        """Initialize with API client for metadata and optional CDN client for downloads."""
        self.api_client = api_client
        self.cdn_client = cdn_client or api_client

    def fetch_catalog(
        self,
        page: int = 1,
        per_page: int = 20,
        tags: Optional[List[str]] = None,
        min_rating: Optional[float] = None,
        include_mature: bool = True,
        sort_by: str = "title"  # title, rating, release_date
    ) -> CatalogPage:
        """
        Fetch paginated catalog from D1-backed API.
        
        Args:
            page: Page number (1-indexed)
            per_page: Games per page (default 20)
            tags: Filter by tags (any match)
            min_rating: Minimum rating filter (1-5)
            include_mature: Whether to include mature content
            sort_by: Sort field
        """
        # Build query params
        params = [f"page={page}", f"per_page={per_page}", f"sort={sort_by}"]
        
        if tags:
            for tag in tags:
                params.append(f"tag={tag}")
        
        if min_rating is not None:
            params.append(f"min_rating={min_rating}")
        
        if not include_mature:
            params.append("mature=false")
        
        query = "&".join(params)
        data = self.api_client.get_json(f"api/catalog?{query}")
        
        if data is None:
            raise Exception("Failed to connect to store")

        games = []
        for item in data.get("games", []):
            try:
                games.append(CatalogEntry(
                    id=item["id"],
                    slug=item["slug"],
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
            except KeyError as e:
                logging.warning(f"Skipping invalid catalog entry: {e}")
        
        return CatalogPage(
            games=games,
            page=data.get("page", page),
            per_page=data.get("per_page", per_page),
            total=data.get("total", len(games)),
            total_pages=data.get("total_pages", 1)
        )

    def fetch_catalog_all(self) -> List[CatalogEntry]:
        """Legacy method - fetch first page of catalog."""
        result = self.fetch_catalog(page=1, per_page=100)
        return result.games

    def fetch_tags(self) -> Dict[str, List[Dict[str, str]]]:
        """
        Fetch all available tags from D1, grouped by category.
        
        Returns:
            Dict mapping category -> list of {id, name} dicts
        """
        data = self.api_client.get_json("api/tags")
        
        if data is None:
            return {}
        
        return data.get("grouped", {})

    def fetch_manifest(self, slug: str) -> Optional[GameManifest]:
        data = self.api_client.get_json(f"api/game/{slug}")
        
        if data is None:
            raise Exception(f"Failed to fetch manifest for {slug}")
        
        try:
            download_data = data.get("download", {})
            download_info = DownloadInfo(
                version=download_data.get("version", data.get("version", "")),
                size_bytes=download_data.get("size_bytes", 0),
                sha256=download_data.get("sha256", ""),
                path=download_data.get("path", "")
            )
            
            changelog = []
            for cl in data.get("changelog", []):
                changelog.append(ChangelogEntry(
                    version=cl.get("version", ""),
                    date=cl.get("date", ""),
                    notes=cl.get("notes", [])
                ))

            version = data.get("version", data.get("current_version", ""))
            
            return GameManifest(
                id=data["id"],
                slug=data.get("slug", slug),
                title=data["title"],
                description=data.get("description", ""),
                version=version,
                current_version=version,  # Legacy alias
                tags=data.get("tags", []),
                icon_url=data.get("icon_url", ""),
                screenshot_urls=data.get("screenshot_urls", []),
                download=download_info,
                changelog=changelog,
                rating=data.get("rating"),
                rating_count=data.get("rating_count", 0),
                mature_content=data.get("mature_content", False),
                release_date=data.get("release_date", ""),
                # Legacy fields (may not exist in new API)
                author=data.get("author", ""),
                engine_version=data.get("engine_version", ""),
                min_firmware_version=data.get("min_firmware_version", "")
            )
        except KeyError as e:
            logging.error(f"Error parsing manifest for {slug}: {e}")
            return None

    def fetch_device_ratings(self, device_id: str) -> Dict[str, int]:
        """
        Fetch dict of game ratings for a device from the server.
        
        Args:
            device_id: The device's unique identifier (16 hex chars)
            
        Returns:
            Dict mapping game_slug -> rating (1-5)
        """
        data = self.api_client.get_json(f"api/device/ratings?device_id={device_id}")
        
        if data is None:
            return {}
        
        return data.get("ratings", {})

    def rate_game(self, device_id: str, game_slug: str, rating: int) -> bool:
        """
        Rate a game on the server (1-5 stars).
        
        Args:
            device_id: The device's unique identifier
            game_slug: The game's slug
            rating: Rating value (1-5)
            
        Returns:
            True if successful
        """
        try:
            response = self.api_client.post_json(
                "api/device/ratings",
                {"device_id": device_id, "game_slug": game_slug, "rating": rating}
            )
            return response is not None and response.get("ok", False)
        except Exception as e:
            logging.warning(f"Failed to rate game on server: {e}")
            return False

    def remove_rating(self, device_id: str, game_slug: str) -> bool:
        """
        Remove a rating for a game on the server.
        
        Args:
            device_id: The device's unique identifier
            game_slug: The game's slug
            
        Returns:
            True if successful
        """
        try:
            response = self.api_client.delete_json(
                "api/device/ratings",
                {"device_id": device_id, "game_slug": game_slug}
            )
            return response is not None and response.get("ok", False)
        except Exception as e:
            logging.warning(f"Failed to remove rating on server: {e}")
            return False

    def download_game_zip(self, slug: str, destination: Path, remote_path: str = None, progress_callback=None) -> bool:
        # Use the provided remote path (from manifest) or fallback to legacy /download/{slug}
        # Downloads go through CDN client
        url_path = remote_path if remote_path else f"download/{slug}"
        
        response = self.cdn_client.get_stream(url_path)
        if not response:
            return False
        
        destination.parent.mkdir(parents=True, exist_ok=True)
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded_size = 0
        
        try:
            with open(destination, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        if progress_callback:
                            progress_callback(downloaded_size, total_size)
            return True
        except Exception as e:
            logging.error(f"Error writing download file: {e}")
            return False
