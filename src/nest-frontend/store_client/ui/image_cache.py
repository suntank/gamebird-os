"""
Image loading and caching for the store client.
Handles downloading, caching, and scaling images for display.
"""
import pygame
import requests
import logging
import hashlib
import threading
from collections import OrderedDict
from pathlib import Path
from typing import Optional, Callable
from io import BytesIO


class ImageCache:
    """
    Async image loader with disk caching.
    Images are loaded in background threads and cached to disk.
    Uses LRU eviction to cap memory usage.
    """
    
    # Max surfaces in memory (~100KB each at 160x160 RGBA)
    # 100 surfaces ≈ 10MB memory cap
    MAX_CACHED_SURFACES = 100
    
    def __init__(self, cache_dir: Path, target_size: tuple = (160, 160)):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.target_size = target_size
        
        # In-memory LRU cache of loaded surfaces (OrderedDict for LRU)
        self._surfaces: OrderedDict[str, pygame.Surface] = OrderedDict()
        # URLs currently being loaded
        self._loading: set = set()
        # Callbacks for when images finish loading
        self._callbacks: dict[str, list] = {}
        # Lock for thread safety
        self._lock = threading.Lock()
    
    def _url_to_cache_path(self, url: str) -> Path:
        """Convert URL to a cache file path."""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        ext = url.split('.')[-1].lower()
        if ext not in ('png', 'jpg', 'jpeg'):
            ext = 'png'
        return self.cache_dir / f"{url_hash}.{ext}"
    
    def get(self, url: str, callback: Optional[Callable[[pygame.Surface], None]] = None) -> Optional[pygame.Surface]:
        """
        Get an image surface. Returns immediately if cached, otherwise starts async load.
        
        Args:
            url: Image URL to load
            callback: Optional callback when image is ready (for async loads)
            
        Returns:
            Surface if already cached, None if loading
        """
        if not url:
            return None
        
        with self._lock:
            # Check memory cache (move to end for LRU)
            if url in self._surfaces:
                self._surfaces.move_to_end(url)
                surface = self._surfaces[url]
                # Still call callback if provided (for code that relies on it)
                if callback:
                    callback(surface)
                return surface
            
            # Check if already loading
            if url in self._loading:
                if callback:
                    self._callbacks.setdefault(url, []).append(callback)
                return None
            
            # Start loading
            self._loading.add(url)
            if callback:
                self._callbacks[url] = [callback]
        
        # Load in background thread
        thread = threading.Thread(target=self._load_image, args=(url,), daemon=True)
        thread.start()
        return None
    
    def _load_image(self, url: str):
        """Load image from cache or network (runs in background thread)."""
        surface = None
        cache_path = self._url_to_cache_path(url)
        
        try:
            # Try disk cache first
            if cache_path.exists():
                surface = self._load_from_disk(cache_path)
            
            # Download if not cached
            if surface is None:
                surface = self._download_and_cache(url, cache_path)
            
            # Scale to target size
            if surface and surface.get_size() != self.target_size:
                surface = pygame.transform.smoothscale(surface, self.target_size)
        
        except Exception as e:
            logging.warning(f"Failed to load image {url}: {e}")
            surface = None
        
        # Update caches and call callbacks
        with self._lock:
            self._loading.discard(url)
            if surface:
                self._surfaces[url] = surface
                self._evict_if_needed()
            callbacks = self._callbacks.pop(url, [])
        
        # Call callbacks outside lock
        for cb in callbacks:
            try:
                cb(surface)
            except Exception as e:
                logging.warning(f"Image callback error: {e}")
    
    def _load_from_disk(self, path: Path) -> Optional[pygame.Surface]:
        """Load image from disk cache."""
        try:
            return pygame.image.load(str(path))
        except Exception as e:
            logging.warning(f"Failed to load cached image {path}: {e}")
            return None
    
    def _download_and_cache(self, url: str, cache_path: Path) -> Optional[pygame.Surface]:
        """Download image and save to cache."""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Save to disk
            cache_path.write_bytes(response.content)
            
            # Load as surface
            return pygame.image.load(BytesIO(response.content))
        
        except Exception as e:
            logging.warning(f"Failed to download image {url}: {e}")
            return None
    
    def preload(self, urls: list):
        """Preload a list of images in background."""
        for url in urls:
            if url and url not in self._surfaces and url not in self._loading:
                self.get(url)
    
    def clear_memory(self):
        """Clear in-memory cache (keeps disk cache)."""
        with self._lock:
            self._surfaces.clear()
    
    def _evict_if_needed(self):
        """Evict oldest entries if cache exceeds max size. Must hold lock."""
        while len(self._surfaces) > self.MAX_CACHED_SURFACES:
            # Pop oldest (first) item
            evicted_url, _ = self._surfaces.popitem(last=False)
            logging.debug(f"ImageCache: evicted {evicted_url}")
    
    def get_cache_stats(self) -> dict:
        """Get cache statistics for debugging."""
        with self._lock:
            return {
                "memory_count": len(self._surfaces),
                "memory_max": self.MAX_CACHED_SURFACES,
                "loading_count": len(self._loading),
            }
    
    def get_sync(self, url: str) -> Optional[pygame.Surface]:
        """
        Synchronously get an image (blocks until loaded).
        Use sparingly - prefer async get() with callback.
        """
        if not url:
            return None
        
        with self._lock:
            if url in self._surfaces:
                return self._surfaces[url]
        
        # Load synchronously
        cache_path = self._url_to_cache_path(url)
        surface = None
        
        try:
            if cache_path.exists():
                surface = self._load_from_disk(cache_path)
            
            if surface is None:
                surface = self._download_and_cache(url, cache_path)
            
            if surface and surface.get_size() != self.target_size:
                surface = pygame.transform.smoothscale(surface, self.target_size)
            
            if surface:
                with self._lock:
                    self._surfaces[url] = surface
        
        except Exception as e:
            logging.warning(f"Failed to load image sync {url}: {e}")
        
        return surface
