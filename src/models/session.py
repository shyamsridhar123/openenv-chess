"""GameSession model for WebSocket session management."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Set, Optional


@dataclass
class GameSession:
    """Represents a WebSocket session for real-time game updates.
    
    Note: WebSocket is a demo enhancement, not part of core OpenEnv spec.
    Core OpenEnv only requires HTTP REST endpoints (/reset, /step, /state).
    
    Attributes:
        session_id: Unique session identifier
        game_id: Associated game ID
        websocket_ids: Set of connected WebSocket client IDs
        created_at: When session was created
        last_activity: Last activity timestamp
        is_active: Whether session is active
        metadata: Additional session metadata
    """
    
    session_id: str
    game_id: str
    websocket_ids: Set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    metadata: dict = field(default_factory=dict)
    
    def add_websocket(self, ws_id: str) -> None:
        """Add a WebSocket connection to this session.
        
        Args:
            ws_id: WebSocket client ID
        """
        self.websocket_ids.add(ws_id)
        self.last_activity = datetime.now()
    
    def remove_websocket(self, ws_id: str) -> None:
        """Remove a WebSocket connection from this session.
        
        Args:
            ws_id: WebSocket client ID
        """
        self.websocket_ids.discard(ws_id)
        self.last_activity = datetime.now()
        
        # Deactivate session if no connections remain
        if not self.websocket_ids:
            self.is_active = False
    
    def has_connections(self) -> bool:
        """Check if session has any active WebSocket connections.
        
        Returns:
            True if connections exist, False otherwise
        """
        return len(self.websocket_ids) > 0
    
    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now()
    
    def to_dict(self) -> dict:
        """Convert GameSession to dictionary."""
        return {
            "session_id": self.session_id,
            "game_id": self.game_id,
            "websocket_ids": list(self.websocket_ids),
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "is_active": self.is_active,
            "metadata": self.metadata,
        }
