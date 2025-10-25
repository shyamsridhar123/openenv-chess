"""Game model representing a complete chess game."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from enum import Enum

from .board_state import BoardState
from .move import Move


class GameStatus(str, Enum):
    """Game status enumeration."""
    ACTIVE = "active"
    CHECKMATE = "checkmate"
    STALEMATE = "stalemate"
    DRAW = "draw"
    RESIGNED = "resigned"
    TIMEOUT = "timeout"
    ERROR = "error"


class GameResult(str, Enum):
    """Game result enumeration."""
    WHITE_WINS = "1-0"
    BLACK_WINS = "0-1"
    DRAW = "1/2-1/2"
    ONGOING = "*"


@dataclass
class Game:
    """Represents a complete chess game.
    
    Attributes:
        game_id: Unique identifier for the game
        board_state: Current board state
        move_history: List of all moves made
        status: Current game status
        result: Game result (1-0, 0-1, 1/2-1/2, or *)
        white_agent_id: ID of white agent
        black_agent_id: ID of black agent
        created_at: When the game was created
        updated_at: When the game was last updated
        completed_at: When the game finished (if completed)
        total_moves: Total number of moves made
        time_control: Time control settings (optional)
        metadata: Additional game metadata
    """
    
    game_id: str
    board_state: BoardState
    move_history: List[Move] = field(default_factory=list)
    status: GameStatus = GameStatus.ACTIVE
    result: GameResult = GameResult.ONGOING
    white_agent_id: str = "white"
    black_agent_id: str = "black"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    total_moves: int = 0
    time_control: Optional[dict] = None
    metadata: dict = field(default_factory=dict)
    
    def add_move(self, move: Move) -> None:
        """Add a move to the game history.
        
        Args:
            move: Move to add
        """
        self.move_history.append(move)
        self.total_moves += 1
        self.updated_at = datetime.now()
    
    def update_status(self, status: GameStatus, result: Optional[GameResult] = None) -> None:
        """Update game status and result.
        
        Args:
            status: New game status
            result: Game result (if terminal)
        """
        self.status = status
        if result:
            self.result = result
        self.updated_at = datetime.now()
        
        # Mark completion time for terminal states
        if status in [GameStatus.CHECKMATE, GameStatus.STALEMATE, 
                      GameStatus.DRAW, GameStatus.RESIGNED, GameStatus.TIMEOUT]:
            self.completed_at = datetime.now()
    
    def is_terminal(self) -> bool:
        """Check if game has ended.
        
        Returns:
            True if game is finished, False otherwise
        """
        return self.status != GameStatus.ACTIVE
    
    def get_pgn_moves(self) -> str:
        """Get moves in PGN format.
        
        Returns:
            String of moves in SAN notation
        """
        moves = []
        for i, move in enumerate(self.move_history):
            if i % 2 == 0:
                moves.append(f"{i // 2 + 1}. {move.san}")
            else:
                moves.append(move.san)
        return " ".join(moves)
    
    def to_dict(self) -> dict:
        """Convert Game to dictionary for JSON serialization."""
        return {
            "game_id": self.game_id,
            "board_state": self.board_state.to_dict(),
            "move_history": [move.to_dict() for move in self.move_history],
            "status": self.status.value,
            "result": self.result.value,
            "white_agent_id": self.white_agent_id,
            "black_agent_id": self.black_agent_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_moves": self.total_moves,
            "time_control": self.time_control,
            "metadata": self.metadata,
        }
