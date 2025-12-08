Game Bird Store Client

Python Application Design Document

1. Purpose and Scope

Game Bird Nest is a Python application that runs directly on the Game Bird device. Its responsibilities:

Discover available games and their latest versions from the CDN worker.

Install games chosen by the user.

Detect and apply updates for installed games.

Verify integrity of downloaded game archives using SHA-256 and size checks.

Present a simple controller-driven UI so users never need to type on a keyboard.

All games are free. The client focuses on correctness, resilience, and bandwidth protection rather than access control.

Games can be filtered and rated giving users a high quality experience

2. Assumptions and Constraints
2.1 Platform

Hardware: Raspberry Pi Zero 2 W inside Game Bird.

OS: Linux (RetroPie-based environment).

Python: CPython 3.x.

Display: 240×240 primary screen (or HDMI), rendered via pygame or similar.

Input: SNES-style controller (D-pad, A/B/X/Y, Start, Select, L, R).

2.2 Networking

Device connects to Wi-Fi via an external configuration menu (outside this app).

HTTP client: standard requests library or httpx (blocking is acceptable; downloads are not huge).

CDN endpoints are public GET only, with Cloudflare WAF and rate limiting in front.

2.3 Security / Abuse Concerns

No user accounts or passwords.

Basic IP-based rate limiting already enforced at Cloudflare and Worker levels.

Client must behave politely toward the CDN:

Retry with exponential backoff on transient errors.

Respect 429 responses and back off appropriately.

3. External Interfaces
3.1 CDN Worker API

All URLs are relative to the configured CDN base, for example:

CDN_BASE = "https://cdn.gamebird.games/api"
(For development: https://nestworker.suntank.workers.dev)

Endpoints:

GET /api/catalog

GET /api/game/{slug}

GET /download/{slug}

GET /images/... and other static files as needed.

Details are in section 5.

3.2 Local File System

Suggested layout on the Game Bird:

/home/gamebird/
  store/
    config.json
    installed_games.json
    cache/
      catalog.json
      manifests/
        hungry-hatchling.json
        frog-boss-raid.json
    downloads/
      hungry-hatchling/
        game.zip
      frog-boss-raid/
        game.zip
  games/
    hungry-hatchling/
      game/
        ...unzipped game content...
    frog-boss-raid/
      game/
        ...unzipped...

3.3 User Interface

UI built in Python (likely pygame) using controller input only.

Basic views:

Catalog list view

Game detail view

Installed games view

Update notifications

Download progress and error dialogs

4. Data Contracts
4.1 Catalog JSON (GET /api/catalog)

Example:

{
  "games": [
    {
      "id": "hungry-hatchling",
      "title": "Hungry Hatchling",
      "short_description": "Puzzle platformer about a hungry bird-snake.",
      "current_version": "1.1.0",
      "icon_url": "https://cdn.gamebird.games/api/images/hungry-hatchling-icon.png"
    },
    {
      "id": "frog-boss-raid",
      "title": "Frog Boss Raid",
      "short_description": "Boss rush with giant frogs.",
      "current_version": "0.9.0",
      "icon_url": "https://cdn.gamebird.games/api/images/frog-boss-raid-icon.png"
    }
  ]
}

4.2 Game Manifest JSON (GET /api/game/{slug})

Example hungry-hatchling:

{
  "id": "hungry-hatchling",
  "title": "Hungry Hatchling",
  "description": "Guide a young bird-snake through tight tunnels and puzzles.",
  "author": "Game Bird Studios",
  "current_version": "1.1.0",
  "engine_version": "1.0.0",
  "min_firmware_version": "1.0.0",
  "release_date": "2025-11-25",
  "tags": ["platformer", "puzzle", "singleplayer"],
  "icon_url": "https://cdn.gamebird.games/api/images/hungry-hatchling-icon.png",
  "screenshot_urls": [
    "https://cdn.gamebird.games/api/images/hungry-hatchling-screen1.png"
  ],
  "download": {
    "version": "1.1.0",
    "size_bytes": 2457600,
    "sha256": "aa...bb",
    "path": "games/hungry-hatchling/1.1.0/game.zip"
  },
  "changelog": [
    {
      "version": "1.1.0",
      "date": "2025-11-25",
      "notes": [
        "Added world 2",
        "Improved hit detection"
      ]
    },
    {
      "version": "1.0.0",
      "date": "2025-11-10",
      "notes": [
        "Initial release"
      ]
    }
  ]
}

4.3 Download Endpoint (GET /download/{slug})

Redirects to or streams the latest download.path zip for that slug.

Content type: application/zip (or application/octet-stream).

Client saves response directly as downloads/{slug}/game.zip.

5. Application Architecture
5.1 Layered Overview

UI Layer
Renders screens, responds to controller input, calls service layer.

Service Layer
Orchestrates catalog refresh, install, update, uninstall, and integrity checks.

Repository Layer
Handles reading and writing local metadata (installed_games.json and cached manifests).

Network Layer
Wraps HTTP requests to the CDN worker and applies backoff and basic metrics.

System Layer
File system operations, unpacking ZIP archives, launching installed games.

5.2 Module Breakdown

Planned Python packages:

store_client/
  __init__.py
  config.py
  models.py
  http_client.py
  cdn_api.py
  repository.py
  integrity.py
  installer.py
  updater.py
  ui/
    __init__.py
    screens.py
    widgets.py
    controller_input.py
  main.py

6. Module Responsibilities
6.1 config.py

Responsibility:

Load and store configuration such as:

CDN base URL

Paths for data and games

Timeouts and retry limits

Key ideas:

@dataclass
class StoreConfig:
    cdn_base_url: str
    data_dir: Path
    games_dir: Path
    http_timeout: float
    max_retries: int

def load_config() -> StoreConfig:
    ...

6.2 models.py

Data models representing catalog entries, manifest data, and installed games.

Key classes:

CatalogEntry

GameManifest

InstalledGame

@dataclass
class CatalogEntry:
    id: str
    title: str
    short_description: str
    current_version: str
    icon_url: str

@dataclass
class GameManifest:
    id: str
    title: str
    description: str
    current_version: str
    download_path: str
    download_version: str
    download_size_bytes: int
    download_sha256: str
    # other fields as needed

@dataclass
class InstalledGame:
    id: str
    title: str
    installed_version: str
    install_path: Path

6.3 http_client.py

Thin wrapper around requests or httpx:

Responsibilities:

GET requests with timeout.

Automatic JSON parsing.

Simple exponential backoff on network errors and 5xx.

Respect 429 (Too Many Requests) by backing off longer.

API outline:

class HttpClient:
    def __init__(self, base_url: str, timeout: float = 10.0):
        ...

    def get_json(self, path: str) -> dict:
        ...

    def get_stream(self, path: str) -> Iterable[bytes]:
        ...

6.4 cdn_api.py

Higher-level functions that use HttpClient and know about the CDN schema.

Responsibilities:

Fetch catalog and parse into CatalogEntry list.

Fetch game manifest by slug and parse into GameManifest.

Download latest zip for a game and save to a specified file path.

API outline:

class CdnApi:
    def __init__(self, http_client: HttpClient):
        ...

    def fetch_catalog(self) -> List[CatalogEntry]:
        ...

    def fetch_manifest(self, slug: str) -> GameManifest:
        ...

    def download_game_zip(self, slug: str, destination: Path) -> None:
        ...

6.5 repository.py

Handles local metadata:

installed_games.json structure:

{
  "games": [
    {
      "id": "hungry-hatchling",
      "title": "Hungry Hatchling",
      "installed_version": "1.0.0",
      "install_path": "/home/gamebird/games/hungry-hatchling"
    }
  ]
}


Repo operations:

load_installed_games() -> Dict[str, InstalledGame]

save_installed_games(games: Dict[str, InstalledGame])

cache_catalog(catalog)

load_cached_catalog()

6.6 integrity.py

Responsible for integrity checking:

Compute SHA-256 of a file.

Compare to value in manifest.

Optionally verify size.

Functions:

def sha256_file(path: Path, chunk_size: int = 65536) -> str:
    ...

def validate_download(path: Path, expected_hash: str, expected_size: int) -> bool:
    ...

6.7 installer.py

Orchestrates installation:

Steps:

Download zip for slug into downloads/{slug}/game.zip.

Run integrity validation.

Unzip into games/{slug}/game/.

Register or update entry in installed_games.json.

API:

class Installer:
    def __init__(self, cdn_api: CdnApi, repo: Repository):
        ...

    def install_or_update(self, manifest: GameManifest) -> None:
        ...

6.8 updater.py

Utility that compares catalog data with installed games and produces update suggestions.

Steps:

Load catalog.

Load installed games.

For each installed game, check if catalog current_version > installed version (simple semantic version compare).

API:

@dataclass
class UpdateInfo:
    game_id: str
    title: str
    installed_version: str
    latest_version: str

class Updater:
    def __init__(self, repo: Repository, cdn_api: CdnApi):
        ...

    def get_update_list(self) -> List[UpdateInfo]:
        ...

    def update_game(self, slug: str) -> None:
        ...

6.9 ui/ package

Configurable for your existing UI framework, but conceptually:

screens.py: higher-level screen controllers.

widgets.py: reusable UI elements (list, text, progress bar).

controller_input.py: maps SNES buttons to high-level actions.

Core screens:

Main Store Screen

Shows:

“Browse Catalog”

“Installed Games”

“Check for Updates”

“Exit”

Navigation controlled by D-pad and A/B.

Catalog Screen

List of games from catalog.

Each item: title, short description, installed status, update icon if needed.

A: open game detail.

Game Detail Screen

Shows:

Title, full description, tags, current version.

Buttons:

“Install” or “Update” or “Play” depending on state.

On Install/Update:

Show download progress screen.

Download Progress Screen

Displays bytes downloaded and a simple progress bar.

Shows messages on verification, extraction, completion, or errors.

Installed Games Screen

Lists installed games with status and “Play” / “Uninstall” actions.

7. Primary Workflows
7.1 Browse Catalog

User opens Store Client.

Client attempts to fetch /api/catalog.

If online and successful, update cached catalog.

If offline, fall back to cached catalog (if any).

Display catalog list.

User selects a game, opens Game Detail screen.

7.2 Install Game

From Game Detail, user presses A on “Install”.

Client fetches manifest for slug via /api/game/{slug}.

Installer:

Downloads latest zip via /download/{slug} to downloads/{slug}/game.zip.

Uses integrity.validate_download.

Extracts zip into games/{slug}/game/.

Marks entry in installed_games.json with installed_version = manifest.download.version.

UI shows success and offers “Play”.

7.3 Check for Updates

From main menu, user selects “Check for Updates”.

Client fetches catalog.

Updater compares versions for each installed game.

If updates exist, present an “Updates Available” screen with games that can be updated.

User chooses one or more games to update.

For each, call Installer.install_or_update(manifest).

7.4 Handling Rate Limiting and Errors

If the CDN returns HTTP 429:

Show “Server busy, please try again later”.

Apply backoff (for example, wait 30 seconds before next attempt).

If integrity check fails:

Delete the downloaded zip.

Show “Download corrupted, please retry”.

If network is unavailable:

Show “Offline” indicator and fall back to cached catalog.

8. Configuration and Persistence

config.json should allow overriding:

CDN base (for staging vs production).

Download directory.

Whether to do automatic catalog refresh on startup.

installed_games.json must be updated atomically:

Write to temp file, then rename to avoid corruption during power loss.

9. Future Extensions

While v1 needs only free downloads and simple updates, the design keeps room for:

Device registration and pairing with a website.

Game categories, featured lists, or ratings.

Telemetry (opt-in) for knowing which games are popular.

Background update checks triggered at boot or on a schedule.

10. Summary

This design defines a clear boundary between:

CDN Worker: hosts catalog, manifests, and game archives.

Game Bird Store Client: pulls those resources, safely installs and updates games, and presents a controller-friendly UI.

The client requires no user typing, operates within tight resource constraints, and protects you from accidental or intentional overuse of the CDN through polite network behavior and Cloudflare-side limits.
