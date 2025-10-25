"""ChessOpenEnv: OpenEnv 0.1 compliant chess environment.

This environment implements the OpenEnv specification for a chess game,
following patterns from openenv/openspiel_env.
"""

from typing import Dict, Any, Optional, Tuple
import uuid
import chess

from src.chess_logic import ChessLogic
from src.models.board_state import BoardState
from src.models.game import Game, GameStatus, GameResult


class ChessOpenEnv:
    """Chess environment implementing OpenEnv 0.1 specification.
    
    Follows OpenEnv patterns:
    - reset() -> observation, info
    - step(action) -> observation, reward, terminated, truncated, info
    - state() -> game metadata
    - close() -> cleanup
    
    Based on patterns from openenv/openspiel_env for turn-based games.
    """
    
    def __init__(self, game_id: Optional[str] = None):
        """Initialize chess environment.
        
        Args:
            game_id: Optional game identifier (generated if not provided)
        """
        self.game_id = game_id or str(uuid.uuid4())
        self.chess = ChessLogic()
        self.game: Optional[Game] = None
        self._move_count = 0
        
    def reset(self, fen: Optional[str] = None, **kwargs) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Reset environment to initial state.
        
        Args:
            fen: Optional FEN string for custom starting position
            **kwargs: Additional reset parameters
            
        Returns:
            Tuple of (observation, info)
            - observation: Dict with board_state, legal_moves, current_player
            - info: Dict with game_id, move_count, metadata
        """
        # Reset chess logic
        board_state = self.chess.reset(fen)
        
        # Create new game
        self.game = Game(
            game_id=self.game_id,
            board_state=board_state,
            white_agent_id=kwargs.get("white_agent_id", "white"),
            black_agent_id=kwargs.get("black_agent_id", "black"),
        )
        
        self._move_count = 0
        
        # Build observation
        observation = {
            "board_state": {
                "fen": board_state.fen,
                "board_tensor": board_state.board_tensor.tolist(),
            },
            "legal_moves": board_state.legal_moves,
            "current_player": board_state.current_player,
            "is_check": board_state.is_check,
        }
        
        # Build info
        info = {
            "game_id": self.game_id,
            "move_count": self._move_count,
            "white_agent": self.game.white_agent_id,
            "black_agent": self.game.black_agent_id,
        }
        
        return observation, info
    
    def step(self, action: str) -> Tuple[Dict[str, Any], float, bool, bool, Dict[str, Any]]:
        """Execute one move in the environment.
        
        Args:
            action: Move in UCI notation (e.g., 'e2e4', 'e7e8q')
            
        Returns:
            Tuple of (observation, reward, terminated, truncated, info)
            - observation: New board state
            - reward: Reward for this move (0 for ongoing, +1/-1 for terminal)
            - terminated: Whether game ended naturally
            - truncated: Whether game was truncated (not used for chess)
            - info: Additional information
            
        Raises:
            ValueError: If move is illegal or game is already finished
        """
        if self.game is None:
            raise ValueError("Environment not initialized. Call reset() first.")
        
        if self.game.is_terminal():
            raise ValueError(f"Game already finished with status: {self.game.status}")
        
        # Validate and apply move
        if not self.chess.is_legal_move(action):
            raise ValueError(
                f"Illegal move: {action}. "
                f"Legal moves: {', '.join(self.chess.get_legal_moves()[:5])}..."
            )
        
        # Get SAN before applying move
        san_move = self.chess.get_san(action)
        
        # Apply move and get new state
        board_state = self.chess.apply_move(action)
        self._move_count += 1
        
        # Update game state
        self.game.board_state = board_state
        
        # Check for terminal state
        is_terminal, terminal_reason = self.chess.is_terminal()
        terminated = is_terminal
        truncated = False  # Chess games end naturally, not truncated
        
        # Calculate reward (sparse rewards only at terminal states)
        reward = 0.0
        if terminated:
            result = self.chess.get_result()
            if result == "1-0":  # White wins
                self.game.update_status(GameStatus.CHECKMATE, GameResult.WHITE_WINS)
                reward = 1.0 if board_state.current_player == "black" else -1.0
            elif result == "0-1":  # Black wins
                self.game.update_status(GameStatus.CHECKMATE, GameResult.BLACK_WINS)
                reward = 1.0 if board_state.current_player == "white" else -1.0
            elif result == "1/2-1/2":  # Draw
                status_map = {
                    "stalemate": GameStatus.STALEMATE,
                    "insufficient_material": GameStatus.DRAW,
                    "fifty_move_rule": GameStatus.DRAW,
                    "threefold_repetition": GameStatus.DRAW,
                }
                self.game.update_status(
                    status_map.get(terminal_reason, GameStatus.DRAW),
                    GameResult.DRAW
                )
                reward = 0.0
        
        # Build observation
        observation = {
            "board_state": {
                "fen": board_state.fen,
                "board_tensor": board_state.board_tensor.tolist(),
            },
            "legal_moves": board_state.legal_moves,
            "current_player": board_state.current_player,
            "is_check": board_state.is_check,
            "is_checkmate": board_state.is_checkmate,
            "is_stalemate": board_state.is_stalemate,
        }
        
        # Build info
        info = {
            "game_id": self.game_id,
            "move_count": self._move_count,
            "last_move": action,
            "san_move": san_move,
            "terminated": terminated,
            "terminal_reason": terminal_reason,
            "result": self.game.result.value if terminated else None,
        }
        
        return observation, reward, terminated, truncated, info
    
    def state(self) -> Dict[str, Any]:
        """Get current game state metadata.
        
        Returns:
            Dict with game metadata (id, status, move_count, etc.)
        """
        if self.game is None:
            return {
                "game_id": self.game_id,
                "status": "not_initialized",
                "message": "Call reset() to initialize environment",
            }
        
        return {
            "game_id": self.game_id,
            "status": self.game.status.value,
            "result": self.game.result.value,
            "move_count": self._move_count,
            "current_player": self.game.board_state.current_player,
            "fen": self.game.board_state.fen,
            "is_terminal": self.game.is_terminal(),
            "white_agent": self.game.white_agent_id,
            "black_agent": self.game.black_agent_id,
            "created_at": self.game.created_at.isoformat(),
            "updated_at": self.game.updated_at.isoformat(),
        }
    
    def close(self) -> None:
        """Clean up environment resources.
        
        For chess environment, this is mostly a no-op as we use in-memory state.
        """
        self.game = None
        self.chess = None
    
    def render(self, mode: str = "svg", size: int = 400) -> str:
        """Render current board state.
        
        Args:
            mode: Rendering mode ('svg' or 'ascii')
            size: Size in pixels for SVG rendering
            
        Returns:
            Rendered board as string (SVG or ASCII)
        """
        if self.chess is None:
            return "Environment not initialized"
        
        if mode == "svg":
            return self.chess.render_svg(size=size)
        elif mode == "ascii":
            return str(self.chess.board)
        else:
            raise ValueError(f"Unknown render mode: {mode}")
    
    def get_legal_moves(self) -> list[str]:
        """Get list of legal moves in current position.
        
        Returns:
            List of moves in UCI notation
        """
        return self.chess.get_legal_moves() if self.chess else []
