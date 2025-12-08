import logging
from typing import List, Dict
from .repository import Repository
from .cdn_api import CdnApi
from .models import UpdateInfo, CatalogEntry

class Updater:
    def __init__(self, repo: Repository, cdn_api: CdnApi):
        self.repo = repo
        self.cdn_api = cdn_api

    def get_update_list(self, catalog: List[CatalogEntry]) -> List[UpdateInfo]:
        installed_games = self.repo.load_installed_games()
        updates = []
        
        logging.info(f"Checking updates for {len(installed_games)} installed games against {len(catalog)} catalog entries")
        
        # Map by both id and slug for compatibility
        catalog_by_id = {entry.id: entry for entry in catalog}
        catalog_by_slug = {entry.slug: entry for entry in catalog}
        
        for game_id, installed_game in installed_games.items():
            # Try to find by id first, then by slug
            catalog_entry = catalog_by_id.get(game_id) or catalog_by_slug.get(game_id)
            
            if not catalog_entry:
                logging.debug(f"Game '{game_id}' not found in catalog")
                continue
                
            latest_version = catalog_entry.version or ""
            installed_version = installed_game.installed_version or ""
            
            logging.info(f"Checking '{game_id}': installed={installed_version}, latest={latest_version}")
            
            if self._is_newer(latest_version, installed_version):
                logging.info(f"Update available for '{game_id}': {installed_version} -> {latest_version}")
                updates.append(UpdateInfo(
                    game_id=catalog_entry.slug,  # Use slug for navigation
                    title=installed_game.title,
                    installed_version=installed_version,
                    latest_version=latest_version
                ))
        
        logging.info(f"Found {len(updates)} updates")
        return updates

    def _is_newer(self, latest: str, current: str) -> bool:
        """
        Compare semantic versions. Returns True if latest > current.
        Handles formats like x.y.z, x.y, or x
        """
        if not latest or not current:
            return False
        
        # Strip any leading 'v' prefix
        latest = latest.lstrip('v')
        current = current.lstrip('v')
        
        try:
            # Split and pad with zeros for comparison
            l_parts = [int(x) for x in latest.split('.')]
            c_parts = [int(x) for x in current.split('.')]
            
            # Pad shorter list with zeros
            max_len = max(len(l_parts), len(c_parts))
            l_parts.extend([0] * (max_len - len(l_parts)))
            c_parts.extend([0] * (max_len - len(c_parts)))
            
            return l_parts > c_parts
        except ValueError as e:
            logging.warning(f"Version comparison failed for '{latest}' vs '{current}': {e}")
            # Fallback: string comparison
            return latest != current and latest > current
