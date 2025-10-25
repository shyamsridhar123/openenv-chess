"""Move model representing a single chess move."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import chess


@dataclass
class Move:
    """Represents a single chess move with metadata.
    
    Attributes:
        uci: Move in UCI notation (e.g., 'e2e4', 'e7e8q')
        san: Move in Standard Algebraic Notation (e.g., 'e4', 'Nf3', 'O-O')
        piece: Piece that was moved (e.g., 'pawn', 'knight', 'king')
        player: Player who made the move ('white' or 'black')
        timestamp: When the move was made
        captured_piece: Piece that was captured, if any
        is_check: Whether the move puts opponent in check
        is_checkmate: Whether the move is checkmate
        is_castling: Whether the move is castling
        is_en_passant: Whether the move is en passant capture
        is_promotion: Whether the move is a pawn promotion
        promoted_to: Piece type promoted to (if promotion)
        thinking_time: Time taken to decide this move (seconds)
        reasoning: Agent's reasoning for this move (optional)
        confidence: Agent's confidence score 0-1 (optional)
    """
    
    uci: str
    san: str
    piece: str
    player: str
    timestamp: datetime = field(default_factory=datetime.now)
    captured_piece: Optional[str] = None
    is_check: bool = False
    is_checkmate: bool = False
    is_castling: bool = False
    is_en_passant: bool = False
    is_promotion: bool = False
    promoted_to: Optional[str] = None
    thinking_time: float = 0.0
    reasoning: Optional[str] = None
    confidence: Optional[float] = None
    
    @classmethod
    def from_chess_move(
        cls,
        board: chess.Board,
        chess_move: chess.Move,
        player: str,
        thinking_time: float = 0.0,
        reasoning: Optional[str] = None,
        confidence: Optional[float] = None,
    ) -> "Move":
        """Create Move from python-chess Move object.
        
        Args:
            board: Current board state before the move
            chess_move: python-chess Move instance
            player: Player making the move ('white' or 'black')
            thinking_time: Time taken to decide this move
            reasoning: Agent's reasoning (optional)
            confidence: Agent's confidence score (optional)
            
        Returns:
            Move instance with all metadata
        """
        piece = board.piece_at(chess_move.from_square)
        piece_name = chess.piece_name(piece.piece_type) if piece else "unknown"
        
        # Check for captures
        captured = board.piece_at(chess_move.to_square)
        captured_name = chess.piece_name(captured.piece_type) if captured else None
        
        # Apply move temporarily to check results
        board_copy = board.copy()
        san = board_copy.san(chess_move)
        board_copy.push(chess_move)
        
        return cls(
            uci=chess_move.uci(),
            san=san,
            piece=piece_name,
            player=player,
            captured_piece=captured_name,
            is_check=board_copy.is_check(),
            is_checkmate=board_copy.is_checkmate(),
            is_castling=board.is_castling(chess_move),
            is_en_passant=board.is_en_passant(chess_move),
            is_promotion=chess_move.promotion is not None,
            promoted_to=chess.piece_name(chess_move.promotion) if chess_move.promotion else None,
            thinking_time=thinking_time,
            reasoning=reasoning,
            confidence=confidence,
        )
    
    def to_dict(self) -> dict:
        """Convert Move to dictionary for JSON serialization."""
        return {
            "uci": self.uci,
            "san": self.san,
            "piece": self.piece,
            "player": self.player,
            "timestamp": self.timestamp.isoformat(),
            "captured_piece": self.captured_piece,
            "is_check": self.is_check,
            "is_checkmate": self.is_checkmate,
            "is_castling": self.is_castling,
            "is_en_passant": self.is_en_passant,
            "is_promotion": self.is_promotion,
            "promoted_to": self.promoted_to,
            "thinking_time": self.thinking_time,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
        }
