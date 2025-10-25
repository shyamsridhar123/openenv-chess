"""Unit tests for StateManager."""

import pytest
from src.state_manager import StateManager
from src.models.game import Game, GameStatus, GameResult
from src.models.board_state import BoardState
import chess


class TestStateManager:
    """Test suite for StateManager class."""
    
    def create_test_game(self, game_id: str = "test-game") -> Game:
        """Helper to create a test game."""
        board_state = BoardState.from_board(chess.Board())
        return Game(
            game_id=game_id,
            board_state=board_state,
            white_agent_id="white",
            black_agent_id="black"
        )
    
    def test_initialization(self):
        """Test state manager initialization."""
        manager = StateManager(max_games=100)
        assert len(manager.games) == 0
        assert manager.max_games == 100
    
    def test_create_game(self):
        """Test creating a new game."""
        manager = StateManager()
        game = self.create_test_game("game1")
        
        created = manager.create_game(game)
        assert created.game_id == "game1"
        assert len(manager.games) == 1
    
    def test_create_duplicate_game(self):
        """Test creating game with duplicate ID raises error."""
        manager = StateManager()
        game = self.create_test_game("game1")
        
        manager.create_game(game)
        
        with pytest.raises(ValueError, match="already exists"):
            manager.create_game(game)
    
    def test_get_game_exists(self):
        """Test retrieving existing game."""
        manager = StateManager()
        game = self.create_test_game("game1")
        manager.create_game(game)
        
        retrieved = manager.get_game("game1")
        assert retrieved is not None
        assert retrieved.game_id == "game1"
    
    def test_get_game_not_exists(self):
        """Test retrieving non-existent game returns None."""
        manager = StateManager()
        retrieved = manager.get_game("nonexistent")
        assert retrieved is None
    
    def test_update_game(self):
        """Test updating existing game."""
        manager = StateManager()
        game = self.create_test_game("game1")
        manager.create_game(game)
        
        # Modify game
        game.status = GameStatus.CHECKMATE
        game.result = GameResult.WHITE_WINS
        
        updated = manager.update_game(game)
        assert updated.status == GameStatus.CHECKMATE
        
        # Verify persistence
        retrieved = manager.get_game("game1")
        assert retrieved.status == GameStatus.CHECKMATE
    
    def test_update_nonexistent_game(self):
        """Test updating non-existent game raises error."""
        manager = StateManager()
        game = self.create_test_game("nonexistent")
        
        with pytest.raises(ValueError, match="not found"):
            manager.update_game(game)
    
    def test_delete_game(self):
        """Test deleting a game."""
        manager = StateManager()
        game = self.create_test_game("game1")
        manager.create_game(game)
        
        assert manager.delete_game("game1") is True
        assert len(manager.games) == 0
        assert manager.get_game("game1") is None
    
    def test_delete_nonexistent_game(self):
        """Test deleting non-existent game returns False."""
        manager = StateManager()
        assert manager.delete_game("nonexistent") is False
    
    def test_cleanup_completed_game(self):
        """Test cleaning up completed game."""
        manager = StateManager()
        game = self.create_test_game("game1")
        game.status = GameStatus.CHECKMATE
        manager.create_game(game)
        
        assert manager.cleanup_game("game1") is True
        assert len(manager.games) == 0
    
    def test_cleanup_active_game(self):
        """Test cleaning up active game returns False."""
        manager = StateManager()
        game = self.create_test_game("game1")
        game.status = GameStatus.ACTIVE
        manager.create_game(game)
        
        assert manager.cleanup_game("game1") is False
        assert len(manager.games) == 1  # Not cleaned up
    
    def test_list_games_empty(self):
        """Test listing games when empty."""
        manager = StateManager()
        games = manager.list_games()
        assert games == []
    
    def test_list_games_multiple(self):
        """Test listing multiple games."""
        manager = StateManager()
        
        for i in range(3):
            game = self.create_test_game(f"game{i}")
            manager.create_game(game)
        
        games = manager.list_games()
        assert len(games) == 3
        # Most recent first
        assert games[0].game_id == "game2"
        assert games[2].game_id == "game0"
    
    def test_list_games_with_limit(self):
        """Test listing games with limit."""
        manager = StateManager()
        
        for i in range(5):
            game = self.create_test_game(f"game{i}")
            manager.create_game(game)
        
        games = manager.list_games(limit=2)
        assert len(games) == 2
    
    def test_get_stats_empty(self):
        """Test stats for empty manager."""
        manager = StateManager(max_games=100)
        stats = manager.get_stats()
        
        assert stats["total_games"] == 0
        assert stats["active_games"] == 0
        assert stats["completed_games"] == 0
        assert stats["capacity"] == 100
        assert stats["capacity_used_percent"] == 0.0
    
    def test_get_stats_mixed(self):
        """Test stats with active and completed games."""
        manager = StateManager(max_games=10)
        
        # Create 3 active games
        for i in range(3):
            game = self.create_test_game(f"active{i}")
            game.status = GameStatus.ACTIVE
            manager.create_game(game)
        
        # Create 2 completed games
        for i in range(2):
            game = self.create_test_game(f"completed{i}")
            game.status = GameStatus.CHECKMATE
            manager.create_game(game)
        
        stats = manager.get_stats()
        assert stats["total_games"] == 5
        assert stats["active_games"] == 3
        assert stats["completed_games"] == 2
        assert stats["capacity_used_percent"] == 50.0
    
    def test_lru_cleanup(self):
        """Test LRU cleanup when capacity reached."""
        manager = StateManager(max_games=3)
        
        # Add 3 games (at capacity)
        for i in range(3):
            game = self.create_test_game(f"game{i}")
            manager.create_game(game)
        
        # Add 4th game, should trigger LRU cleanup
        game4 = self.create_test_game("game3")
        manager.create_game(game4)
        
        # Should have 3 games (oldest removed)
        assert len(manager.games) == 3
        assert manager.get_game("game0") is None  # Oldest removed
        assert manager.get_game("game1") is not None
        assert manager.get_game("game2") is not None
        assert manager.get_game("game3") is not None
    
    def test_lru_with_access(self):
        """Test LRU considers recent access."""
        manager = StateManager(max_games=3)
        
        # Add 3 games
        for i in range(3):
            game = self.create_test_game(f"game{i}")
            manager.create_game(game)
        
        # Access game0 (marks it as recently used)
        manager.get_game("game0")
        
        # Add 4th game
        game4 = self.create_test_game("game3")
        manager.create_game(game4)
        
        # game1 should be removed (least recently used)
        assert len(manager.games) == 3
        assert manager.get_game("game0") is not None  # Kept (accessed)
        assert manager.get_game("game1") is None  # Removed (LRU)
        assert manager.get_game("game2") is not None
        assert manager.get_game("game3") is not None
    
    def test_cleanup_completed_games_all(self):
        """Test bulk cleanup of completed games."""
        manager = StateManager()
        
        # Create mix of active and completed
        for i in range(3):
            game = self.create_test_game(f"active{i}")
            game.status = GameStatus.ACTIVE
            manager.create_game(game)
        
        for i in range(2):
            game = self.create_test_game(f"completed{i}")
            game.status = GameStatus.CHECKMATE
            manager.create_game(game)
        
        cleaned = manager.cleanup_completed_games()
        
        assert cleaned == 2
        assert len(manager.games) == 3  # Only active games remain
    
    def test_clear_all(self):
        """Test clearing all games."""
        manager = StateManager()
        
        for i in range(5):
            game = self.create_test_game(f"game{i}")
            manager.create_game(game)
        
        cleared = manager.clear_all()
        
        assert cleared == 5
        assert len(manager.games) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
