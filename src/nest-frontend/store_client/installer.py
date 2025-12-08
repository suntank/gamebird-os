import zipfile
import shutil
import logging
import subprocess
from pathlib import Path
from .cdn_api import CdnApi
from .repository import Repository
from .integrity import validate_download
from .models import GameManifest, InstalledGame

class Installer:
    def __init__(self, cdn_api: CdnApi, repo: Repository):
        self.cdn_api = cdn_api
        self.repo = repo
    
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
        
        # 5. Make shell script executable
        shell_script = install_dir / f"{manifest.title}.sh"
        if shell_script.exists():
            try:
                shell_script.chmod(shell_script.stat().st_mode | 0o755)
                logging.info(f"Made executable: {shell_script}")
            except Exception as e:
                logging.warning(f"Failed to chmod shell script: {e}")
            
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
