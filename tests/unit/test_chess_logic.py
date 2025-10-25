"""Unit tests for chess logic wrapper."""

import pytest
import chess
from src.chess_logic import ChessLogic
from src.models.board_state import BoardState


class TestChessLogic:
    """Test suite for ChessLogic class."""
    
    def test_initialization_default(self):
        """Test default initialization with standard starting position."""
        logic = ChessLogic()
        assert logic.get_fen() == chess.STARTING_FEN
    
    def test_initialization_custom_fen(self):
        """Test initialization with custom FEN."""
        custom_fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
        logic = ChessLogic(fen=custom_fen)
        assert logic.get_fen() == custom_fen
    
    def test_is_legal_move_valid(self):
        """Test legal move validation for valid moves."""
        logic = ChessLogic()
        assert logic.is_legal_move("e2e4") is True
        assert logic.is_legal_move("g1f3") is True
    
    def test_is_legal_move_invalid(self):
        """Test legal move validation for invalid moves."""
        logic = ChessLogic()
        assert logic.is_legal_move("e2e5") is False  # Pawn can't move 3 squares
        assert logic.is_legal_move("invalid") is False  # Invalid UCI format
    
    def test_apply_move_legal(self):
        """Test applying a legal move."""
        logic = ChessLogic()
        board_state = logic.apply_move("e2e4")
        
        assert isinstance(board_state, BoardState)
        assert "e2e4" not in board_state.legal_moves  # Can't repeat same move
        assert board_state.current_player == "black"  # Turn switched
    
    def test_apply_move_illegal(self):
        """Test applying an illegal move raises error."""
        logic = ChessLogic()
        
        with pytest.raises(ValueError, match="Illegal move"):
            logic.apply_move("e2e5")
    
    def test_get_legal_moves(self):
        """Test getting all legal moves."""
        logic = ChessLogic()
        moves = logic.get_legal_moves()
        
        assert len(moves) == 20  # 20 legal moves in starting position
        assert "e2e4" in moves
        assert "g1f3" in moves
    
    def test_get_board_state(self):
        """Test getting current board state."""
        logic = ChessLogic()
        board_state = logic.get_board_state()
        
        assert isinstance(board_state, BoardState)
        assert board_state.fen == chess.STARTING_FEN
        assert len(board_state.legal_moves) == 20
        assert board_state.current_player == "white"
    
    def test_render_svg(self):
        """Test SVG rendering."""
        logic = ChessLogic()
        svg = logic.render_svg(size=400)
        
        assert isinstance(svg, str)
        assert "<svg" in svg
        assert "400" in svg  # Check size is included
    
    def test_is_terminal_ongoing_game(self):
        """Test terminal detection for ongoing game."""
        logic = ChessLogic()
        is_terminal, reason = logic.is_terminal()
        
        assert is_terminal is False
        assert reason is None
    
    def test_is_terminal_checkmate(self):
        """Test terminal detection for checkmate."""
        # Scholar's mate position
        fen = "r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4"
        logic = ChessLogic(fen=fen)
        is_terminal, reason = logic.is_terminal()
        
        assert is_terminal is True
        assert reason == "checkmate"
    
    def test_is_terminal_stalemate(self):
        """Test terminal detection for stalemate."""
        # Stalemate position
        fen = "k7/8/1K6/8/8/8/8/1Q6 b - - 0 1"
        logic = ChessLogic(fen=fen)
        is_terminal, reason = logic.is_terminal()
        
        assert is_terminal is True
        assert reason == "stalemate"
    
    def test_get_result_ongoing(self):
        """Test result for ongoing game."""
        logic = ChessLogic()
        assert logic.get_result() == "*"
    
    def test_get_result_white_wins(self):
        """Test result when white wins."""
        # Scholar's mate
        fen = "r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4"
        logic = ChessLogic(fen=fen)
        assert logic.get_result() == "1-0"
    
    def test_get_result_draw(self):
        """Test result for stalemate (draw)."""
        fen = "k7/8/1K6/8/8/8/8/1Q6 b - - 0 1"
        logic = ChessLogic(fen=fen)
        assert logic.get_result() == "1/2-1/2"
    
    def test_reset_default(self):
        """Test reset to starting position."""
        logic = ChessLogic()
        logic.apply_move("e2e4")  # Make a move
        
        board_state = logic.reset()
        assert board_state.fen == chess.STARTING_FEN
        assert len(board_state.legal_moves) == 20
    
    def test_reset_custom_fen(self):
        """Test reset to custom position."""
        logic = ChessLogic()
        custom_fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
        
        board_state = logic.reset(fen=custom_fen)
        assert board_state.fen == custom_fen
    
    def test_get_san(self):
        """Test UCI to SAN conversion."""
        logic = ChessLogic()
        
        assert logic.get_san("e2e4") == "e4"
        assert logic.get_san("g1f3") == "Nf3"
    
    def test_get_san_invalid_move(self):
        """Test SAN conversion for invalid move."""
        logic = ChessLogic()
        
        with pytest.raises(ValueError):
            logic.get_san("e2e5")  # Illegal move
    
    def test_move_sequence(self):
        """Test a sequence of moves."""
        logic = ChessLogic()
        
        # Play a few moves
        logic.apply_move("e2e4")
        logic.apply_move("e7e5")
        logic.apply_move("g1f3")
        
        board_state = logic.get_board_state()
        assert board_state.move_count == 3
        assert board_state.current_player == "black"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
