import time
import logging
import requests
from typing import Optional, Dict, Any, Iterable

class HttpClient:
    def __init__(self, base_url: str, timeout: float = 10.0, max_retries: int = 3):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()

    def get_json(self, path: str) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.get(url, timeout=self.timeout)
                
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 30))
                    logging.warning(f"Rate limited. Waiting {retry_after} seconds.")
                    time.sleep(retry_after)
                    continue
                
                response.raise_for_status()
                return response.json()
            
            except requests.RequestException as e:
                logging.warning(f"Request failed (attempt {attempt + 1}/{self.max_retries + 1}): {e}")
                if attempt < self.max_retries:
                    sleep_time = 2 ** attempt # Exponential backoff
                    time.sleep(sleep_time)
                else:
                    logging.error(f"Max retries reached for {url}")
                    return None
        return None

    def get_stream(self, path: str) -> Optional[requests.Response]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            response = self.session.get(url, stream=True, timeout=self.timeout)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logging.error(f"Stream request failed: {e}")
            return None

    def post_json(self, path: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """POST JSON data and return JSON response."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            response = self.session.post(url, json=data, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logging.error(f"POST request failed: {e}")
            return None

    def delete_json(self, path: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """DELETE with JSON body and return JSON response."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            response = self.session.delete(url, json=data, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logging.error(f"DELETE request failed: {e}")
            return None
