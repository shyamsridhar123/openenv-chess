"""Chess logic wrapper around python-chess library.

Provides high-level chess operations with validation and error handling.
"""

from typing import List, Optional, Tuple
import chess
import chess.svg
from src.models.board_state import BoardState


class ChessLogic:
    """Wrapper around python-chess for chess operations."""
    
    def __init__(self, fen: Optional[str] = None):
        """Initialize chess logic with optional starting position.
        
        Args:
            fen: FEN string for starting position (default: standard starting position)
        """
        self.board = chess.Board(fen) if fen else chess.Board()
    
    def is_legal_move(self, move_uci: str) -> bool:
        """Check if a move is legal in the current position.
        
        Args:
            move_uci: Move in UCI notation (e.g., 'e2e4', 'e7e8q')
            
        Returns:
            True if move is legal, False otherwise
        """
        try:
            move = chess.Move.from_uci(move_uci)
            return move in self.board.legal_moves
        except (ValueError, AssertionError):
            return False
    
    def apply_move(self, move_uci: str) -> BoardState:
        """Apply a move and return the new board state.
        
        Args:
            move_uci: Move in UCI notation
            
        Returns:
            New BoardState after the move
            
        Raises:
            ValueError: If move is illegal or invalid format
        """
        if not self.is_legal_move(move_uci):
            raise ValueError(f"Illegal move: {move_uci}")
        
        try:
            move = chess.Move.from_uci(move_uci)
            self.board.push(move)
            return BoardState.from_board(self.board)
        except (ValueError, AssertionError) as e:
            raise ValueError(f"Invalid move format '{move_uci}': {e}")
    
    def get_legal_moves(self) -> List[str]:
        """Get all legal moves in current position.
        
        Returns:
            List of moves in UCI notation
        """
        return [move.uci() for move in self.board.legal_moves]
    
    def get_board_state(self) -> BoardState:
        """Get current board state.
        
        Returns:
            BoardState object with current position
        """
        return BoardState.from_board(self.board)
    
    def render_svg(self, size: int = 400, lastmove: Optional[chess.Move] = None) -> str:
        """Render board as SVG for visualization.
        
        Args:
            size: Size of the board in pixels
            lastmove: Highlight the last move (optional)
            
        Returns:
            SVG string representation of the board
        """
        return chess.svg.board(
            self.board,
            size=size,
            lastmove=lastmove,
            coordinates=True,
        )
    
    def is_terminal(self) -> Tuple[bool, Optional[str]]:
        """Check if game has ended and return reason.
        
        Returns:
            Tuple of (is_terminal, reason)
            - is_terminal: True if game ended
            - reason: 'checkmate', 'stalemate', 'insufficient_material', 
                     'fifty_move_rule', 'threefold_repetition', or None
        """
        if self.board.is_checkmate():
            return True, "checkmate"
        if self.board.is_stalemate():
            return True, "stalemate"
        if self.board.is_insufficient_material():
            return True, "insufficient_material"
        if self.board.is_seventyfive_moves():  # 50-move rule
            return True, "fifty_move_rule"
        if self.board.is_fivefold_repetition():  # Threefold repetition
            return True, "threefold_repetition"
        return False, None
    
    def get_result(self) -> str:
        """Get game result in PGN format.
        
        Returns:
            '1-0' (white wins), '0-1' (black wins), '1/2-1/2' (draw), or '*' (ongoing)
        """
        if not self.is_terminal()[0]:
            return "*"
        
        if self.board.is_checkmate():
            # Winner is the opposite of current turn (who just got checkmated)
            return "1-0" if self.board.turn == chess.BLACK else "0-1"
        else:
            # All other terminal states are draws
            return "1/2-1/2"
    
    def get_fen(self) -> str:
        """Get FEN string of current position.
        
        Returns:
            FEN string
        """
        return self.board.fen()
    
    def reset(self, fen: Optional[str] = None) -> BoardState:
        """Reset board to starting position or given FEN.
        
        Args:
            fen: FEN string for starting position (default: standard starting position)
            
        Returns:
            BoardState of the new position
        """
        self.board = chess.Board(fen) if fen else chess.Board()
        return BoardState.from_board(self.board)
    
    def get_san(self, move_uci: str) -> str:
        """Convert UCI move to SAN notation.
        
        Args:
            move_uci: Move in UCI notation
            
        Returns:
            Move in SAN notation (e.g., 'Nf3', 'e4', 'O-O')
            
        Raises:
            ValueError: If move is invalid
        """
        try:
            move = chess.Move.from_uci(move_uci)
            if move not in self.board.legal_moves:
                raise ValueError(f"Illegal move: {move_uci}")
            return self.board.san(move)
        except (ValueError, AssertionError) as e:
            raise ValueError(f"Invalid move '{move_uci}': {e}")
