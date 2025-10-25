"""Stockfish-based move evaluation for chess agents.

Provides move quality analysis using Stockfish engine to measure:
- Centipawn loss per move
- Blunder detection
- Tactical accuracy
- Best move comparison
"""

from typing import Optional, Dict, Any, List, Tuple
import chess
import chess.engine
import structlog
from pathlib import Path
import subprocess
import os

logger = structlog.get_logger()


class StockfishEvaluator:
    """Evaluates chess moves using Stockfish engine."""
    
    def __init__(
        self,
        stockfish_path: Optional[str] = None,
        depth: int = 15,
        time_limit: float = 0.1,
    ):
        """Initialize Stockfish evaluator.
        
        Args:
            stockfish_path: Path to Stockfish binary. If None, tries to find it.
            depth: Search depth for evaluation (default 15)
            time_limit: Time limit per evaluation in seconds (default 0.1)
        """
        self.stockfish_path = stockfish_path or self._find_stockfish()
        self.depth = depth
        self.time_limit = time_limit
        self.engine: Optional[chess.engine.SimpleEngine] = None
        
        if self.stockfish_path:
            try:
                self.engine = chess.engine.SimpleEngine.popen_uci(self.stockfish_path)
                logger.info(
                    "stockfish_initialized",
                    path=self.stockfish_path,
                    depth=depth,
                    time_limit=time_limit,
                )
            except Exception as e:
                logger.warning(
                    "stockfish_init_failed",
                    error=str(e),
                    path=self.stockfish_path,
                )
                self.engine = None
        else:
            logger.warning("stockfish_not_found")
    
    def _find_stockfish(self) -> Optional[str]:
        """Try to find Stockfish binary in common locations."""
        # Common Stockfish locations
        possible_paths = [
            "stockfish",  # In PATH
            "/usr/bin/stockfish",
            "/usr/local/bin/stockfish",
            "/opt/homebrew/bin/stockfish",  # macOS Homebrew
            str(Path.home() / ".local" / "bin" / "stockfish"),
        ]
        
        for path in possible_paths:
            try:
                # Test if executable works
                result = subprocess.run(
                    [path, "--help"],
                    capture_output=True,
                    timeout=2,
                )
                if result.returncode == 0:
                    return path
            except (FileNotFoundError, subprocess.TimeoutExpired, PermissionError):
                continue
        
        return None
    
    def is_available(self) -> bool:
        """Check if Stockfish engine is available."""
        return self.engine is not None
    
    def evaluate_position(self, board: chess.Board) -> Optional[int]:
        """Evaluate a chess position.
        
        Args:
            board: Chess board to evaluate
            
        Returns:
            Evaluation in centipawns from white's perspective, or None if unavailable
        """
        if not self.is_available():
            return None
        
        try:
            info = self.engine.analyse(
                board,
                chess.engine.Limit(depth=self.depth, time=self.time_limit)
            )
            
            # Get score from white's perspective
            score = info.get("score")
            if score:
                cp_score = score.white()
                if cp_score.is_mate():
                    # Convert mate scores to large centipawn values
                    mate_in = cp_score.mate()
                    return 10000 if mate_in > 0 else -10000
                else:
                    return cp_score.score()
            
            return None
            
        except Exception as e:
            logger.error("evaluation_failed", error=str(e))
            return None
    
    def get_best_move(self, board: chess.Board) -> Optional[chess.Move]:
        """Get Stockfish's best move for the position.
        
        Args:
            board: Chess board position
            
        Returns:
            Best move according to Stockfish, or None if unavailable
        """
        if not self.is_available():
            return None
        
        try:
            result = self.engine.play(
                board,
                chess.engine.Limit(depth=self.depth, time=self.time_limit)
            )
            return result.move
            
        except Exception as e:
            logger.error("best_move_failed", error=str(e))
            return None
    
    def evaluate_move(
        self,
        board: chess.Board,
        move: chess.Move,
    ) -> Dict[str, Any]:
        """Evaluate quality of a move.
        
        Args:
            board: Board position before the move
            move: Move to evaluate
            
        Returns:
            Dictionary with evaluation metrics:
            - centipawn_loss: CP loss from best move (0 = perfect)
            - is_best_move: Whether this is Stockfish's top choice
            - best_move_uci: Stockfish's recommended move
            - eval_before: Position eval before move
            - eval_after: Position eval after move
            - quality: Move quality category
        """
        if not self.is_available():
            return {
                "centipawn_loss": 0.0,
                "is_best_move": False,
                "best_move_uci": None,
                "eval_before": None,
                "eval_after": None,
                "quality": "unknown",
                "error": "Stockfish not available"
            }
        
        try:
            # Evaluate position before move
            eval_before = self.evaluate_position(board)
            
            # Get Stockfish's best move
            best_move = self.get_best_move(board)
            is_best = (best_move == move) if best_move else False
            
            # Make the move and evaluate after
            board_copy = board.copy()
            board_copy.push(move)
            eval_after = self.evaluate_position(board_copy)
            
            # Calculate centipawn loss
            centipawn_loss = 0.0
            if eval_before is not None and eval_after is not None:
                # Flip eval_after since it's from opponent's perspective after move
                expected_eval = eval_before
                actual_eval = -eval_after
                centipawn_loss = abs(expected_eval - actual_eval)
            
            # Categorize move quality
            if centipawn_loss > 300:
                quality = "blunder"
            elif centipawn_loss > 100:
                quality = "mistake"
            elif centipawn_loss > 50:
                quality = "inaccuracy"
            elif centipawn_loss < 10:
                quality = "excellent"
            else:
                quality = "good"
            
            return {
                "centipawn_loss": round(centipawn_loss, 2),
                "is_best_move": is_best,
                "best_move_uci": best_move.uci() if best_move else None,
                "eval_before": eval_before,
                "eval_after": eval_after,
                "quality": quality,
            }
            
        except Exception as e:
            logger.error("move_evaluation_failed", error=str(e), move=move.uci())
            return {
                "centipawn_loss": 0.0,
                "is_best_move": False,
                "best_move_uci": None,
                "eval_before": None,
                "eval_after": None,
                "quality": "error",
                "error": str(e)
            }
    
    def get_top_moves(
        self,
        board: chess.Board,
        num_moves: int = 3,
    ) -> List[Tuple[chess.Move, int]]:
        """Get top N moves with evaluations.
        
        Args:
            board: Chess board position
            num_moves: Number of top moves to return
            
        Returns:
            List of (move, centipawn_eval) tuples
        """
        if not self.is_available():
            return []
        
        try:
            info = self.engine.analyse(
                board,
                chess.engine.Limit(depth=self.depth, time=self.time_limit),
                multipv=num_moves
            )
            
            # Extract moves and scores
            top_moves = []
            if isinstance(info, list):
                for pv_info in info:
                    pv = pv_info.get("pv", [])
                    if pv:
                        move = pv[0]
                        score = pv_info.get("score")
                        if score:
                            cp = score.white().score() or 0
                            top_moves.append((move, cp))
            
            return top_moves
            
        except Exception as e:
            logger.error("top_moves_failed", error=str(e))
            return []
    
    def close(self):
        """Close the Stockfish engine."""
        if self.engine:
            try:
                self.engine.quit()
                logger.info("stockfish_closed")
            except Exception as e:
                logger.warning("stockfish_close_error", error=str(e))
            finally:
                self.engine = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def __del__(self):
        """Cleanup on deletion."""
        self.close()


# Global evaluator instance (lazy initialized)
_global_evaluator: Optional[StockfishEvaluator] = None


def get_evaluator() -> StockfishEvaluator:
    """Get or create global Stockfish evaluator instance."""
    global _global_evaluator
    if _global_evaluator is None:
        _global_evaluator = StockfishEvaluator()
    return _global_evaluator
