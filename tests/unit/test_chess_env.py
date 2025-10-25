"""Unit tests for ChessOpenEnv environment."""

import pytest
from src.chess_env import ChessOpenEnv
from src.models.game import GameStatus, GameResult


class TestChessOpenEnv:
    """Test suite for ChessOpenEnv class."""
    
    def test_initialization(self):
        """Test environment initialization."""
        env = ChessOpenEnv()
        assert env.game_id is not None
        assert env.game is None  # Not initialized until reset()
    
    def test_reset_default(self):
        """Test reset with default starting position."""
        env = ChessOpenEnv()
        observation, info = env.reset()
        
        # Check observation structure
        assert "board_state" in observation
        assert "legal_moves" in observation
        assert "current_player" in observation
        assert observation["current_player"] == "white"
        
        # Check info structure
        assert "game_id" in info
        assert "move_count" in info
        assert info["move_count"] == 0
    
    def test_reset_custom_fen(self):
        """Test reset with custom FEN position."""
        env = ChessOpenEnv()
        custom_fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
        observation, info = env.reset(fen=custom_fen)
        
        assert observation["board_state"]["fen"] == custom_fen
        assert observation["current_player"] == "black"
    
    def test_step_legal_move(self):
        """Test stepping with legal move."""
        env = ChessOpenEnv()
        env.reset()
        
        observation, reward, terminated, truncated, info = env.step("e2e4")
        
        # Check return values
        assert observation["current_player"] == "black"  # Turn switched
        assert reward == 0.0  # No reward for non-terminal move
        assert terminated is False
        assert truncated is False
        assert info["last_move"] == "e2e4"
        assert info["move_count"] == 1
    
    def test_step_illegal_move(self):
        """Test stepping with illegal move raises error."""
        env = ChessOpenEnv()
        env.reset()
        
        with pytest.raises(ValueError, match="Illegal move"):
            env.step("e2e5")  # Illegal move
    
    def test_step_without_reset(self):
        """Test stepping without calling reset first."""
        env = ChessOpenEnv()
        
        with pytest.raises(ValueError, match="not initialized"):
            env.step("e2e4")
    
    def test_step_after_game_finished(self):
        """Test stepping after game ended raises error."""
        env = ChessOpenEnv()
        # Scholar's mate position (checkmate)
        fen = "r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4"
        env.reset(fen=fen)
        
        with pytest.raises(ValueError, match="already finished"):
            env.step("a7a6")
    
    def test_game_to_checkmate(self):
        """Test game ending in checkmate."""
        env = ChessOpenEnv()
        # Position before checkmate
        fen = "r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4"
        env.reset(fen=fen)
        
        # Deliver checkmate
        observation, reward, terminated, truncated, info = env.step("h5f7")
        
        assert terminated is True
        assert info["terminal_reason"] == "checkmate"
        assert info["result"] == "1-0"  # White wins
        assert reward != 0.0  # Terminal reward
    
    def test_game_to_stalemate(self):
        """Test game ending in stalemate."""
        env = ChessOpenEnv()
        # Position before stalemate
        fen = "k7/8/1K6/8/8/8/8/7Q w - - 0 1"
        env.reset(fen=fen)
        
        # Create stalemate
        observation, reward, terminated, truncated, info = env.step("h1b1")
        
        assert terminated is True
        assert info["terminal_reason"] == "stalemate"
        assert info["result"] == "1/2-1/2"  # Draw
        assert reward == 0.0  # Draw reward
    
    def test_state_uninitialized(self):
        """Test state() on uninitialized environment."""
        env = ChessOpenEnv()
        state = env.state()
        
        assert state["status"] == "not_initialized"
        assert "message" in state
    
    def test_state_active_game(self):
        """Test state() on active game."""
        env = ChessOpenEnv()
        env.reset()
        env.step("e2e4")
        
        state = env.state()
        assert state["status"] == "active"
        assert state["move_count"] == 1
        assert state["current_player"] == "black"
        assert state["is_terminal"] is False
    
    def test_state_finished_game(self):
        """Test state() on finished game."""
        env = ChessOpenEnv()
        fen = "r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4"
        env.reset(fen=fen)
        
        state = env.state()
        assert state["status"] == "checkmate"
        assert state["is_terminal"] is True
    
    def test_render_svg(self):
        """Test SVG rendering."""
        env = ChessOpenEnv()
        env.reset()
        
        svg = env.render(mode="svg", size=400)
        assert isinstance(svg, str)
        assert "<svg" in svg
    
    def test_render_ascii(self):
        """Test ASCII rendering."""
        env = ChessOpenEnv()
        env.reset()
        
        ascii_board = env.render(mode="ascii")
        assert isinstance(ascii_board, str)
        assert "r" in ascii_board  # Black rook
        assert "P" in ascii_board  # White pawn
    
    def test_render_invalid_mode(self):
        """Test rendering with invalid mode."""
        env = ChessOpenEnv()
        env.reset()
        
        with pytest.raises(ValueError, match="Unknown render mode"):
            env.render(mode="invalid")
    
    def test_get_legal_moves(self):
        """Test getting legal moves."""
        env = ChessOpenEnv()
        env.reset()
        
        moves = env.get_legal_moves()
        assert len(moves) == 20  # 20 legal moves in starting position
        assert "e2e4" in moves
    
    def test_close(self):
        """Test environment cleanup."""
        env = ChessOpenEnv()
        env.reset()
        env.close()
        
        assert env.game is None
        assert env.chess is None
    
    def test_multiple_games_same_env(self):
        """Test playing multiple games with same environment."""
        env = ChessOpenEnv()
        
        # First game
        env.reset()
        env.step("e2e4")
        env.step("e7e5")
        
        # Reset for second game
        observation, info = env.reset()
        assert info["move_count"] == 0
        assert observation["current_player"] == "white"
        
        # Second game
        env.step("d2d4")
        state = env.state()
        assert state["move_count"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
