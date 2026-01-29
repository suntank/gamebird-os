"""
History system for undo/redo functionality.
"""
from __future__ import annotations
from typing import List, Optional
import copy


class History:
    """Manages undo/redo history with a maximum capacity."""
    
    def __init__(self, max_size: int = 50):
        """
        Initialize the history system.
        
        Args:
            max_size: Maximum number of states to store
        """
        self.max_size = max_size
        self.states: List[any] = []
        self.current_index: int = -1
    
    def push(self, state: any) -> None:
        """
        Push a new state onto the history stack.
        This will clear any redo history after the current position.
        
        Args:
            state: The state to save (will be deep copied or cloned if possible)
        """
        # Remove any states after current position (they become invalid after a new action)
        if self.current_index < len(self.states) - 1:
            self.states = self.states[:self.current_index + 1]
        
        # Try to use clone method if available, otherwise fall back to deepcopy
        if hasattr(state, 'clone') and callable(getattr(state, 'clone')):
            state_copy = state.clone()
        else:
            state_copy = copy.deepcopy(state)
        self.states.append(state_copy)
        
        # Maintain max size by removing oldest states
        if len(self.states) > self.max_size:
            self.states.pop(0)
        else:
            self.current_index += 1
    
    def can_undo(self) -> bool:
        """Check if undo is available."""
        return self.current_index > 0
    
    def can_redo(self) -> bool:
        """Check if redo is available."""
        return self.current_index < len(self.states) - 1
    
    def undo(self) -> Optional[any]:
        """
        Move back one state in history.
        
        Returns:
            The previous state, or None if can't undo
        """
        if not self.can_undo():
            return None
        
        self.current_index -= 1
        state = self.states[self.current_index]
        # Try to use clone method if available, otherwise fall back to deepcopy
        if hasattr(state, 'clone') and callable(getattr(state, 'clone')):
            return state.clone()
        else:
            return copy.deepcopy(state)
    
    def redo(self) -> Optional[any]:
        """
        Move forward one state in history.
        
        Returns:
            The next state, or None if can't redo
        """
        if not self.can_redo():
            return None
        
        self.current_index += 1
        state = self.states[self.current_index]
        # Try to use clone method if available, otherwise fall back to deepcopy
        if hasattr(state, 'clone') and callable(getattr(state, 'clone')):
            return state.clone()
        else:
            return copy.deepcopy(state)
    
    def current_state(self) -> Optional[any]:
        """Get the current state without modifying history."""
        if 0 <= self.current_index < len(self.states):
            state = self.states[self.current_index]
            # Try to use clone method if available, otherwise fall back to deepcopy
            if hasattr(state, 'clone') and callable(getattr(state, 'clone')):
                return state.clone()
            else:
                return copy.deepcopy(state)
        return None
    
    def clear(self) -> None:
        """Clear all history."""
        self.states.clear()
        self.current_index = -1
    
    def get_info(self) -> str:
        """Get information about the current history state."""
        return f"History: {self.current_index + 1}/{len(self.states)} (Undo: {self.can_undo()}, Redo: {self.can_redo()})"
