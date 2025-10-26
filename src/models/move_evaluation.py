"""Move evaluation data structures for hybrid agent architecture.

Provides structured move evaluation results from Stockfish for agent decision-making.
"""

from dataclasses import dataclass
from typing import List, Optional
import chess


@dataclass
class MoveEvaluation:
    """Structured evaluation of a chess move with Stockfish analysis.
    
    Attributes:
        move: The chess move being evaluated
        score: Centipawn evaluation from white's perspective
        pv_line: Principal variation (continuation after this move)
        quality: Move quality classification (excellent/good/inaccuracy/mistake/blunder)
        best_alternative: Best move according to Stockfish (if different)
        best_alternative_score: Score of the best alternative move
        best_alternative_pv: PV line for best alternative
        centipawn_loss: Centipawns lost compared to best move
    """
    
    move: chess.Move
    score: int
    pv_line: List[chess.Move]
    quality: str = "unknown"
    best_alternative: Optional[chess.Move] = None
    best_alternative_score: Optional[int] = None
    best_alternative_pv: Optional[List[chess.Move]] = None
    centipawn_loss: float = 0.0
    
    def is_best_move(self) -> bool:
        """Check if this is the best move available."""
        return self.best_alternative is None or self.move == self.best_alternative
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            "move": self.move.uci(),
            "score": self.score,
            "pv_line": [m.uci() for m in self.pv_line],
            "quality": self.quality,
            "best_alternative": self.best_alternative.uci() if self.best_alternative else None,
            "best_alternative_score": self.best_alternative_score,
            "best_alternative_pv": [m.uci() for m in self.best_alternative_pv] if self.best_alternative_pv else None,
            "centipawn_loss": self.centipawn_loss,
            "is_best_move": self.is_best_move(),
        }
