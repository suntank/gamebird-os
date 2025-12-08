import hashlib
from pathlib import Path
import logging

def sha256_file(path: Path, chunk_size: int = 65536) -> str:
    sha256 = hashlib.sha256()
    try:
        with open(path, 'rb') as f:
            while True:
                data = f.read(chunk_size)
                if not data:
                    break
                sha256.update(data)
        return sha256.hexdigest()
    except FileNotFoundError:
        logging.error(f"File not found for checksum: {path}")
        return ""

def validate_download(path: Path, expected_hash: str, expected_size: int) -> bool:
    if not path.exists():
        logging.error(f"Validation failed: File {path} does not exist.")
        return False
    
    file_size = path.stat().st_size
    if file_size != expected_size:
        logging.error(f"Size mismatch: expected {expected_size}, got {file_size}")
        return False
    
    file_hash = sha256_file(path)
    if file_hash != expected_hash:
        logging.error(f"Hash mismatch: expected {expected_hash}, got {file_hash}")
        return False
        
    return True
