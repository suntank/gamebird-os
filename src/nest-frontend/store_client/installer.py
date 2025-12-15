import zipfile
import shutil
import logging
import subprocess
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from .cdn_api import CdnApi
from .repository import Repository
from .integrity import validate_download
from .models import GameManifest, InstalledGame

# EmulationStation paths for gamebird
ES_IMAGES_DIR = Path("/opt/retropie/configs/all/emulationstation/downloaded_images/gamebird")
ES_GAMELIST_PATH = Path("/opt/retropie/configs/all/emulationstation/gamelists/gamebird/gamelist.xml")

class Installer:
    def __init__(self, cdn_api: CdnApi, repo: Repository):
        self.cdn_api = cdn_api
        self.repo = repo
    
    def _remount_rw(self) -> bool:
        """Remount the root filesystem as read-write."""
        try:
            result = subprocess.run(
                ['sudo', 'mount', '-o', 'remount,rw', '/'],
                capture_output=True,
                timeout=10
            )
            if result.returncode == 0:
                logging.info("Filesystem remounted as read-write")
                return True
            logging.warning(f"Failed to remount filesystem: {result.stderr.decode()}")
            return False
        except Exception as e:
            logging.error(f"Error remounting filesystem: {e}")
            return False

    def _copy_icon_to_es(self, manifest: GameManifest, extracted_files: list, install_dir: Path) -> str:
        """
        Copy the game icon to EmulationStation's downloaded_images directory.
        Returns the image path for gamelist.xml or empty string on failure.
        """
        slug = manifest.slug or manifest.id
        icon_filename = f"{slug}-icon.png"
        
        # First, try to find icon in extracted files
        icon_source = None
        for f in extracted_files:
            if f.endswith('-icon.png') or f.endswith('_icon.png') or f == 'icon.png':
                icon_source = install_dir / f
                break
        
        # If not found in extracted files, download from icon_url
        if (not icon_source or not icon_source.exists()) and manifest.icon_url:
            try:
                logging.info(f"Downloading icon from {manifest.icon_url}...")
                temp_icon = self.repo.config.data_dir / "downloads" / icon_filename
                temp_icon.parent.mkdir(parents=True, exist_ok=True)
                
                # Download icon using cdn_api
                if self.cdn_api.cdn_client:
                    # Extract path from full URL if needed
                    icon_path = manifest.icon_url
                    if manifest.icon_url.startswith('http'):
                        # Use requests to download directly
                        import requests
                        response = requests.get(manifest.icon_url, timeout=30)
                        if response.status_code == 200:
                            with open(temp_icon, 'wb') as f:
                                f.write(response.content)
                            icon_source = temp_icon
                            logging.info(f"Downloaded icon to {temp_icon}")
                        else:
                            logging.warning(f"Failed to download icon: HTTP {response.status_code}")
                    else:
                        response = self.cdn_api.cdn_client.get_stream(icon_path)
                        if response:
                            with open(temp_icon, 'wb') as f:
                                for chunk in response.iter_content(chunk_size=8192):
                                    if chunk:
                                        f.write(chunk)
                            icon_source = temp_icon
            except Exception as e:
                logging.warning(f"Failed to download icon: {e}")
        
        if not icon_source or not icon_source.exists():
            logging.warning("No icon found for game")
            return ""
        
        # Remount filesystem as read-write
        if not self._remount_rw():
            logging.warning("Could not remount filesystem, skipping ES icon copy")
            return ""
        
        # Ensure ES images directory exists
        try:
            ES_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logging.warning(f"Failed to create ES images directory: {e}")
            return ""
        
        # Copy icon to ES directory
        dest_path = ES_IMAGES_DIR / icon_filename
        try:
            shutil.copy2(icon_source, dest_path)
            logging.info(f"Copied icon to {dest_path}")
            # Return the path format that ES expects
            return f"~/.emulationstation/downloaded_images/gamebird/{icon_filename}"
        except Exception as e:
            logging.warning(f"Failed to copy icon to ES directory: {e}")
            return ""

    def _update_gamelist_xml(self, manifest: GameManifest, image_path: str, shell_script_name: str):
        """
        Update the gamelist.xml to add or update the game entry with the image tag.
        """
        if not self._remount_rw():
            logging.warning("Could not remount filesystem, skipping gamelist.xml update")
            return
        
        try:
            # Ensure gamelist directory exists
            ES_GAMELIST_PATH.parent.mkdir(parents=True, exist_ok=True)
            
            # Load or create gamelist.xml
            if ES_GAMELIST_PATH.exists():
                tree = ET.parse(ES_GAMELIST_PATH)
                root = tree.getroot()
            else:
                root = ET.Element("gameList")
                tree = ET.ElementTree(root)
            
            # Find existing game entry by path
            game_path = f"./{shell_script_name}"
            existing_game = None
            for game in root.findall("game"):
                path_elem = game.find("path")
                if path_elem is not None and path_elem.text == game_path:
                    existing_game = game
                    break
            
            if existing_game is not None:
                # Update existing entry - add or update image tag
                image_elem = existing_game.find("image")
                if image_elem is None:
                    image_elem = ET.SubElement(existing_game, "image")
                image_elem.text = image_path
                logging.info(f"Updated existing game entry with image: {manifest.title}")
            else:
                # Create new game entry
                game_elem = ET.SubElement(root, "game")
                
                path_elem = ET.SubElement(game_elem, "path")
                path_elem.text = game_path
                
                name_elem = ET.SubElement(game_elem, "name")
                name_elem.text = manifest.title
                
                playcount_elem = ET.SubElement(game_elem, "playcount")
                playcount_elem.text = "0"
                
                if image_path:
                    image_elem = ET.SubElement(game_elem, "image")
                    image_elem.text = image_path
                
                logging.info(f"Added new game entry to gamelist.xml: {manifest.title}")
            
            # Write back with proper formatting
            self._indent_xml(root)
            tree.write(ES_GAMELIST_PATH, encoding="unicode", xml_declaration=True)
            logging.info(f"Updated gamelist.xml at {ES_GAMELIST_PATH}")
            
        except Exception as e:
            logging.error(f"Failed to update gamelist.xml: {e}")

    def _indent_xml(self, elem, level=0):
        """Add indentation to XML elements for readability."""
        indent = "\n" + "\t" * level
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = indent + "\t"
            if not elem.tail or not elem.tail.strip():
                elem.tail = indent
            for child in elem:
                self._indent_xml(child, level + 1)
            if not child.tail or not child.tail.strip():
                child.tail = indent
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = indent

    def restart_emulationstation(self) -> bool:
        """Restart EmulationStation to refresh the game list."""
        try:
            # Try systemctl restart first (common on RetroPie/Raspberry Pi)
            result = subprocess.run(
                ['sudo', 'systemctl', 'restart', 'emulationstation'],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                logging.info("EmulationStation restarted via systemctl")
                return True
            
            # Fallback: try pkill and let it auto-restart
            result = subprocess.run(
                ['pkill', '-f', 'emulationstation'],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                logging.info("EmulationStation killed (should auto-restart)")
                return True
            
            logging.warning("Could not restart EmulationStation")
            return False
        except subprocess.TimeoutExpired:
            logging.error("EmulationStation restart timed out")
            return False
        except Exception as e:
            logging.error(f"Error restarting EmulationStation: {e}")
            return False

    def install_or_update(self, manifest: GameManifest, progress_callback=None) -> bool:
        # 1. Prepare paths
        slug = manifest.slug or manifest.id
        download_dir = self.repo.config.data_dir / "downloads"
        download_dir.mkdir(parents=True, exist_ok=True)
        download_path = download_dir / f"{slug}.zip"
        
        # 2. Download
        logging.info(f"Downloading {slug}...")
        remote_path = manifest.download.path if manifest.download else None
        if not self.cdn_api.download_game_zip(slug, download_path, remote_path, progress_callback):
            logging.error("Download failed.")
            return False
            
        # 3. Validate
        logging.info("Validating download...")
        if not validate_download(
            download_path, 
            manifest.download.sha256, 
            manifest.download.size_bytes
        ):
            logging.error("Validation failed. Deleting corrupted file.")
            if download_path.exists():
                download_path.unlink()
            return False
            
        # 4. Extract
        install_dir = self.repo.config.games_dir
        logging.info(f"Extracting to {install_dir}...")
        
        # Ensure games directory exists
        install_dir.mkdir(parents=True, exist_ok=True)
        
        # Track extracted files for uninstall
        extracted_files = []
        try:
            with zipfile.ZipFile(download_path, 'r') as zip_ref:
                # Get list of files in zip (excluding directories)
                extracted_files = [name for name in zip_ref.namelist() if not name.endswith('/')]
                zip_ref.extractall(install_dir)
        except zipfile.BadZipFile:
            logging.error("Failed to extract zip file.")
            return False
        
        # 4.5. Flatten if zip contains a 'game' wrapper folder
        game_subfolder = install_dir / "game"
        if game_subfolder.exists() and game_subfolder.is_dir():
            logging.info("Flattening 'game' folder structure...")
            # Update tracked files to remove 'game/' prefix
            extracted_files = [f[5:] if f.startswith('game/') else f for f in extracted_files]
            # Move all contents of game subfolder to install_dir
            for item in game_subfolder.iterdir():
                dest = install_dir / item.name
                # Remove existing item if present
                if dest.exists():
                    if dest.is_dir():
                        shutil.rmtree(dest)
                    else:
                        dest.unlink()
                shutil.move(str(item), str(dest))
            # Remove empty game folder
            game_subfolder.rmdir()
        
        # 5. Make shell script executable and determine actual script name
        shell_script = install_dir / f"{manifest.title}.sh"
        shell_script_name = f"{manifest.title}.sh"
        
        # Check if the expected shell script exists, otherwise look for any .sh file
        if not shell_script.exists():
            # Look for .sh file in extracted files
            for f in extracted_files:
                if f.endswith('.sh') and '/' not in f:
                    shell_script = install_dir / f
                    shell_script_name = f
                    logging.info(f"Found shell script: {shell_script_name}")
                    break
        
        if shell_script.exists():
            try:
                shell_script.chmod(shell_script.stat().st_mode | 0o755)
                logging.info(f"Made executable: {shell_script}")
            except Exception as e:
                logging.warning(f"Failed to chmod shell script: {e}")
        
        # 5.5. Copy icon to EmulationStation and update gamelist.xml
        image_path = self._copy_icon_to_es(manifest, extracted_files, install_dir)
        self._update_gamelist_xml(manifest, image_path, shell_script_name)
            
        # 6. Register
        logging.info("Registering installation...")
        installed_games = self.repo.load_installed_games()
        version = manifest.download.version if manifest.download else manifest.version
        installed_games[slug] = InstalledGame(
            id=slug,
            title=manifest.title,
            installed_version=version,
            install_path=install_dir,
            installed_files=extracted_files
        )
        self.repo.save_installed_games(installed_games)
        
        # Cleanup download
        if download_path.exists():
            download_path.unlink()
        
        logging.info(f"Successfully installed {manifest.title} v{version}")
        
        # Note: ES will be restarted automatically when user exits Nest
        # Don't restart here - Nest is still using the display
        
        return True

    def uninstall(self, game_id: str) -> bool:
        installed_games = self.repo.load_installed_games()
        if game_id not in installed_games:
            return False
            
        game = installed_games[game_id]
        install_dir = game.install_path
        
        # Delete game folder (named after game id)
        game_folder = install_dir / game_id
        if game_folder.exists() and game_folder.is_dir():
            try:
                shutil.rmtree(game_folder)
                logging.info(f"Deleted game folder: {game_folder}")
            except Exception as e:
                logging.warning(f"Failed to delete game folder {game_folder}: {e}")
        
        # Delete shell script (named after game title)
        shell_script = install_dir / f"{game.title}.sh"
        if shell_script.exists():
            try:
                shell_script.unlink()
                logging.info(f"Deleted shell script: {shell_script}")
            except Exception as e:
                logging.warning(f"Failed to delete shell script {shell_script}: {e}")
            
        # Remove from registry
        del installed_games[game_id]
        self.repo.save_installed_games(installed_games)
        
        logging.info(f"Uninstalled {game.title}")
        return True
