"""BoardState model representing the current state of a chess board."""

from dataclasses import dataclass, field
from typing import List, Optional
import numpy as np
import chess


@dataclass
class BoardState:
    """Represents the current state of a chess board.
    
    Attributes:
        fen: Forsyth-Edwards Notation string representing the board position
        board_tensor: 8x8x12 numpy array encoding piece positions
                     (6 piece types × 2 colors = 12 channels)
        legal_moves: List of legal moves in UCI notation (e.g., ['e2e4', 'g1f3'])
        current_player: 'white' or 'black'
        is_check: Whether the current player is in check
        is_checkmate: Whether the current player is checkmated
        is_stalemate: Whether the position is a stalemate
        move_count: Number of half-moves (plies) made
        fullmove_number: Current move number in the game
    """
    
    fen: str
    board_tensor: np.ndarray  # Shape: (8, 8, 12)
    legal_moves: List[str] = field(default_factory=list)
    current_player: str = "white"
    is_check: bool = False
    is_checkmate: bool = False
    is_stalemate: bool = False
    move_count: int = 0
    fullmove_number: int = 1
    
    @classmethod
    def from_board(cls, board: chess.Board) -> "BoardState":
        """Create BoardState from python-chess Board object.
        
        Args:
            board: python-chess Board instance
            
        Returns:
            BoardState instance with current board state
        """
        return cls(
            fen=board.fen(),
            board_tensor=cls._board_to_tensor(board),
            legal_moves=[move.uci() for move in board.legal_moves],
            current_player="white" if board.turn == chess.WHITE else "black",
            is_check=board.is_check(),
            is_checkmate=board.is_checkmate(),
            is_stalemate=board.is_stalemate(),
            move_count=board.halfmove_clock,
            fullmove_number=board.fullmove_number,
        )
    
    @staticmethod
    def _board_to_tensor(board: chess.Board) -> np.ndarray:
        """Convert chess board to 8x8x12 tensor.
        
        Encoding:
        - Channels 0-5: White pieces (Pawn, Knight, Bishop, Rook, Queen, King)
        - Channels 6-11: Black pieces (Pawn, Knight, Bishop, Rook, Queen, King)
        - Each channel is 8x8 binary matrix (1 if piece present, 0 otherwise)
        
        Args:
            board: python-chess Board instance
            
        Returns:
            numpy array of shape (8, 8, 12)
        """
        tensor = np.zeros((8, 8, 12), dtype=np.float32)
        
        # Map piece types to channel indices
        piece_to_channel = {
            chess.PAWN: 0,
            chess.KNIGHT: 1,
            chess.BISHOP: 2,
            chess.ROOK: 3,
            chess.QUEEN: 4,
            chess.KING: 5,
        }
        
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece is not None:
                # Get row and column (0-7)
                row = 7 - (square // 8)  # Flip row for numpy indexing
                col = square % 8
                
                # Get channel index (0-11)
                channel = piece_to_channel[piece.piece_type]
                if piece.color == chess.BLACK:
                    channel += 6  # Offset for black pieces
                
                tensor[row, col, channel] = 1.0
        
        return tensor
    
    def to_dict(self) -> dict:
        """Convert BoardState to dictionary for JSON serialization."""
        return {
            "fen": self.fen,
            "board_tensor": self.board_tensor.tolist(),
            "legal_moves": self.legal_moves,
            "current_player": self.current_player,
            "is_check": self.is_check,
            "is_checkmate": self.is_checkmate,
            "is_stalemate": self.is_stalemate,
            "move_count": self.move_count,
            "fullmove_number": self.fullmove_number,
        }
