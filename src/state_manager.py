"""StateManager: In-memory state management for chess games.

Manages game state with LRU cleanup when max concurrent games reached.
"""

from typing import Dict, Optional, List
from collections import OrderedDict
import structlog

from src.models.game import Game

logger = structlog.get_logger()


class StateManager:
    """In-memory state manager with LRU cleanup.
    
    Manages chess game state with automatic cleanup when capacity is reached.
    Uses OrderedDict for O(1) LRU operations.
    
    Attributes:
        games: Ordered dict of game_id -> Game
        max_games: Maximum number of concurrent games
    """
    
    def __init__(self, max_games: int = 100):
        """Initialize state manager.
        
        Args:
            max_games: Maximum concurrent games before LRU cleanup
        """
        self.games: OrderedDict[str, Game] = OrderedDict()
        self.max_games = max_games
        logger.info("state_manager_initialized", max_games=max_games)
    
    def create_game(self, game: Game) -> Game:
        """Create a new game.
        
        Args:
            game: Game object to store
            
        Returns:
            The stored game object
            
        Raises:
            ValueError: If game_id already exists
        """
        if game.game_id in self.games:
            raise ValueError(f"Game {game.game_id} already exists")
        
        # Check capacity and cleanup if needed
        if len(self.games) >= self.max_games:
            self._cleanup_oldest()
        
        self.games[game.game_id] = game
        self.games.move_to_end(game.game_id)  # Mark as most recently used
        
        logger.info(
            "game_created",
            game_id=game.game_id,
            total_games=len(self.games)
        )
        
        return game
    
    def get_game(self, game_id: str) -> Optional[Game]:
        """Retrieve a game by ID.
        
        Args:
            game_id: Game identifier
            
        Returns:
            Game object if found, None otherwise
        """
        game = self.games.get(game_id)
        
        if game:
            # Move to end (mark as recently accessed)
            self.games.move_to_end(game_id)
            logger.debug("game_accessed", game_id=game_id)
        else:
            logger.warning("game_not_found", game_id=game_id)
        
        return game
    
    def update_game(self, game: Game) -> Game:
        """Update an existing game.
        
        Args:
            game: Updated game object
            
        Returns:
            The updated game object
            
        Raises:
            ValueError: If game doesn't exist
        """
        if game.game_id not in self.games:
            raise ValueError(f"Game {game.game_id} not found")
        
        self.games[game.game_id] = game
        self.games.move_to_end(game.game_id)  # Mark as recently used
        
        logger.debug("game_updated", game_id=game.game_id)
        
        return game
    
    def delete_game(self, game_id: str) -> bool:
        """Delete a game.
        
        Args:
            game_id: Game identifier
            
        Returns:
            True if game was deleted, False if not found
        """
        if game_id in self.games:
            del self.games[game_id]
            logger.info("game_deleted", game_id=game_id, total_games=len(self.games))
            return True
        
        logger.warning("game_delete_failed", game_id=game_id, reason="not_found")
        return False
    
    def cleanup_game(self, game_id: str) -> bool:
        """Clean up a completed game.
        
        Alias for delete_game with additional logging for completed games.
        
        Args:
            game_id: Game identifier
            
        Returns:
            True if game was cleaned up, False if not found
        """
        game = self.get_game(game_id)
        if game and game.is_terminal():
            logger.info(
                "game_cleanup",
                game_id=game_id,
                status=game.status.value,
                moves=game.total_moves
            )
            return self.delete_game(game_id)
        return False
    
    def list_games(self, limit: Optional[int] = None) -> List[Game]:
        """List all games (most recent first).
        
        Args:
            limit: Maximum number of games to return
            
        Returns:
            List of Game objects, most recent first
        """
        games_list = list(reversed(self.games.values()))
        return games_list[:limit] if limit else games_list
    
    def get_stats(self) -> Dict[str, int]:
        """Get state manager statistics.
        
        Returns:
            Dict with total_games, active_games, completed_games
        """
        active = sum(1 for game in self.games.values() if not game.is_terminal())
        completed = sum(1 for game in self.games.values() if game.is_terminal())
        
        return {
            "total_games": len(self.games),
            "active_games": active,
            "completed_games": completed,
            "capacity": self.max_games,
            "capacity_used_percent": round(len(self.games) / self.max_games * 100, 1),
        }
    
    def _cleanup_oldest(self) -> None:
        """Remove oldest (least recently used) game.
        
        Called automatically when max capacity is reached.
        """
        if not self.games:
            return
        
        # Get oldest game (first item in OrderedDict)
        oldest_id = next(iter(self.games))
        oldest_game = self.games[oldest_id]
        
        logger.info(
            "lru_cleanup",
            game_id=oldest_id,
            status=oldest_game.status.value,
            moves=oldest_game.total_moves,
            age_minutes=round(
                (oldest_game.updated_at - oldest_game.created_at).total_seconds() / 60,
                1
            )
        )
        
        del self.games[oldest_id]
    
    def cleanup_completed_games(self, max_age_minutes: Optional[int] = None) -> int:
        """Clean up completed games, optionally filtering by age.
        
        Args:
            max_age_minutes: Only clean up games older than this (optional)
            
        Returns:
            Number of games cleaned up
        """
        from datetime import datetime, timedelta
        
        cleaned = 0
        games_to_delete = []
        
        for game_id, game in self.games.items():
            if not game.is_terminal():
                continue
            
            if max_age_minutes:
                age = (datetime.now() - game.updated_at).total_seconds() / 60
                if age < max_age_minutes:
                    continue
            
            games_to_delete.append(game_id)
        
        for game_id in games_to_delete:
            if self.delete_game(game_id):
                cleaned += 1
        
        logger.info("bulk_cleanup", games_cleaned=cleaned)
        return cleaned
    
    def clear_all(self) -> int:
        """Clear all games from state.
        
        Warning: This removes all games including active ones.
        
        Returns:
            Number of games cleared
        """
        count = len(self.games)
        self.games.clear()
        logger.warning("state_cleared", games_removed=count)
        return count
