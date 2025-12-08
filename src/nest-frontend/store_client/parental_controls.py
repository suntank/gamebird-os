"""
Parental Controls Manager
Handles child-safe mode PIN storage and verification.
"""
import os
import hashlib
from pathlib import Path


class ParentalControls:
    """Manages child-safe mode with PIN protection."""
    
    def __init__(self, data_dir: Path):
        self.pin_file = data_dir / "parental_pin.txt"
        self._session_unlocked = False
    
    def is_enabled(self) -> bool:
        """Check if parental controls are enabled (PIN file exists)."""
        return self.pin_file.exists()
    
    def is_locked(self) -> bool:
        """Check if currently locked (enabled but not unlocked this session)."""
        return self.is_enabled() and not self._session_unlocked
    
    def should_filter_mature(self) -> bool:
        """Returns True if mature content should be hidden."""
        return self.is_locked()
    
    def set_pin(self, pin: str) -> bool:
        """Set a new PIN (4 digits). Returns True on success."""
        if len(pin) != 4 or not pin.isdigit():
            return False
        
        # Store hashed PIN
        pin_hash = hashlib.sha256(pin.encode()).hexdigest()
        self.pin_file.parent.mkdir(parents=True, exist_ok=True)
        self.pin_file.write_text(pin_hash)
        self._session_unlocked = False
        return True
    
    def verify_pin(self, pin: str) -> bool:
        """Verify PIN against stored hash."""
        if not self.is_enabled():
            return False
        
        stored_hash = self.pin_file.read_text().strip()
        pin_hash = hashlib.sha256(pin.encode()).hexdigest()
        return pin_hash == stored_hash
    
    def unlock(self, pin: str) -> bool:
        """Attempt to unlock with PIN. Returns True on success."""
        if self.verify_pin(pin):
            self._session_unlocked = True
            return True
        return False
    
    def lock(self):
        """Re-lock parental controls for this session."""
        self._session_unlocked = False
    
    def remove_pin(self, pin: str) -> bool:
        """Remove PIN (disable parental controls). Requires correct PIN."""
        if self.verify_pin(pin):
            try:
                self.pin_file.unlink()
                self._session_unlocked = False
                return True
            except OSError:
                return False
        return False
