"""Commentary trigger detection system.

Identifies exciting moments in chess games that warrant commentary:
- Blunders and brilliant moves
- Tactical patterns (forks, pins, sacrifices)
- Critical position changes
- Checkmate threats and game endings
"""

from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import structlog

logger = structlog.get_logger()


class CommentaryTrigger(Enum):
    """Types of events that trigger commentary."""
    
    # High priority - always generate commentary
    BLUNDER = "blunder"                    # >300cp loss
    BRILLIANT = "brilliant"                # Best move with large advantage gain
    CHECKMATE = "checkmate"                # Game ending in checkmate
    CRITICAL_MISTAKE = "critical_mistake"  # Move that loses winning position
    
    # Medium-high priority - strategic overview
    STRATEGIC_OVERVIEW = "strategic_overview"  # Broad positional analysis (not move-specific)
    
    # Medium priority - generate if conditions met
    TACTICAL = "tactical"                  # Fork, pin, skewer detected
    SACRIFICE = "sacrifice"                # Material sacrifice for position
    MISSED_WIN = "missed_win"              # Failed to capitalize on winning move
    DEFENSIVE_BRILLIANCE = "defensive"     # Excellent defensive move under pressure
    
    # Low priority - selective commentary
    OPENING_NOVELTY = "opening_novelty"    # Unusual opening move
    ENDGAME_TECHNIQUE = "endgame"          # Clean endgame execution
    POSITIONAL_MASTERCLASS = "positional"  # Superior positional play
    
    # Special triggers
    NONE = "none"                          # No commentary needed
    
    # Game state triggers
    GAME_START = "game_start"              # Game beginning
    GAME_END = "game_end"                  # Game conclusion
    PHASE_TRANSITION = "phase_transition"  # Opening → middlegame → endgame


@dataclass
class TriggerContext:
    """Context information for commentary generation."""
    
    trigger: CommentaryTrigger
    priority: int  # 1-10, higher = more important
    
    # Move information
    player: str
    move: str
    san_move: str
    move_number: int
    
    # Evaluation data
    eval_before: Optional[int]
    eval_after: Optional[int]
    eval_swing: Optional[int]
    centipawn_loss: float
    quality: str
    is_best_move: bool
    best_move_alternative: Optional[str]
    
    # Game context
    game_phase: str
    material_balance: int
    position_type: str
    is_check: bool
    is_checkmate: bool
    
    # Tactical information
    tactical_motif: Optional[str] = None
    threat_detected: Optional[str] = None
    historical_reference: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "trigger": self.trigger.value,
            "priority": self.priority,
            "player": self.player,
            "move": self.move,
            "san_move": self.san_move,
            "move_number": self.move_number,
            "eval_before": self.eval_before,
            "eval_after": self.eval_after,
            "eval_swing": self.eval_swing,
            "centipawn_loss": self.centipawn_loss,
            "quality": self.quality,
            "is_best_move": self.is_best_move,
            "best_move_alternative": self.best_move_alternative,
            "game_phase": self.game_phase,
            "material_balance": self.material_balance,
            "position_type": self.position_type,
            "is_check": self.is_check,
            "is_checkmate": self.is_checkmate,
            "tactical_motif": self.tactical_motif,
            "threat_detected": self.threat_detected,
            "historical_reference": self.historical_reference,
        }


class TriggerDetector:
    """Detects when commentary should be generated."""
    
    def __init__(self, threshold: int = 50):
        """Initialize trigger detector.
        
        Args:
            threshold: Minimum centipawn change for commentary (default 50)
        """
        self.threshold = threshold
        logger.info("trigger_detector_initialized", threshold=threshold)
    
    def should_generate_commentary(
        self,
        move_data: Dict[str, Any],
        evaluation: Optional[Dict[str, Any]],
        game_context: Dict[str, Any],
    ) -> Optional[TriggerContext]:
        """Determine if commentary should be generated for this move.
        
        Args:
            move_data: Move information (player, move, san, etc.)
            evaluation: Stockfish evaluation data
            game_context: Game state (phase, material, etc.)
            
        Returns:
            TriggerContext if commentary should be generated, None otherwise
        """
        if not evaluation:
            # No evaluation data - only comment on game start/end
            if game_context.get("is_game_start"):
                return self._create_context(
                    CommentaryTrigger.GAME_START,
                    priority=5,
                    move_data=move_data,
                    evaluation={},
                    game_context=game_context,
                )
            if game_context.get("is_checkmate"):
                return self._create_context(
                    CommentaryTrigger.CHECKMATE,
                    priority=10,
                    move_data=move_data,
                    evaluation={},
                    game_context=game_context,
                )
            return None
        
        cp_loss = evaluation.get("centipawn_loss", 0)
        quality = evaluation.get("quality", "unknown")
        eval_before = evaluation.get("eval_before")
        eval_after = evaluation.get("eval_after")
        
        # Calculate evaluation swing (absolute change)
        eval_swing = None
        if eval_before is not None and eval_after is not None:
            eval_swing = abs(eval_after - (-eval_before))  # Flip perspective
        
        # High priority triggers
        if quality == "blunder" or cp_loss > 300:
            return self._create_context(
                CommentaryTrigger.BLUNDER,
                priority=9,
                move_data=move_data,
                evaluation=evaluation,
                game_context=game_context,
            )
        
        if game_context.get("is_checkmate"):
            return self._create_context(
                CommentaryTrigger.CHECKMATE,
                priority=10,
                move_data=move_data,
                evaluation=evaluation,
                game_context=game_context,
            )
        
        # Brilliant move detection
        if evaluation.get("is_best_move") and eval_swing and eval_swing > 200:
            return self._create_context(
                CommentaryTrigger.BRILLIANT,
                priority=8,
                move_data=move_data,
                evaluation=evaluation,
                game_context=game_context,
            )
        
        # Critical position detection
        if eval_after and abs(eval_after) > 500:
            if eval_before and abs(eval_before) < 200:
                # Position swung from balanced to critical
                return self._create_context(
                    CommentaryTrigger.CRITICAL_MISTAKE,
                    priority=8,
                    move_data=move_data,
                    evaluation=evaluation,
                    game_context=game_context,
                )
        
        # Medium priority triggers
        if quality == "mistake" or (100 < cp_loss <= 300):
            if cp_loss > self.threshold:
                return self._create_context(
                    CommentaryTrigger.CRITICAL_MISTAKE,
                    priority=6,
                    move_data=move_data,
                    evaluation=evaluation,
                    game_context=game_context,
                )
        
        # Tactical pattern detection
        tactical_motif = self._detect_tactical_pattern(move_data, evaluation, game_context)
        if tactical_motif:
            return self._create_context(
                CommentaryTrigger.TACTICAL,
                priority=7,
                move_data=move_data,
                evaluation=evaluation,
                game_context=game_context,
                tactical_motif=tactical_motif,
            )
        
        # Excellent move under pressure
        if quality == "excellent" and game_context.get("is_check"):
            return self._create_context(
                CommentaryTrigger.DEFENSIVE_BRILLIANCE,
                priority=7,
                move_data=move_data,
                evaluation=evaluation,
                game_context=game_context,
            )
        
        # Sacrifice detection
        if self._is_sacrifice(move_data, evaluation, game_context):
            return self._create_context(
                CommentaryTrigger.SACRIFICE,
                priority=7,
                move_data=move_data,
                evaluation=evaluation,
                game_context=game_context,
            )
        
        # Low priority - only if significant
        if eval_swing and eval_swing > self.threshold * 2:
            return self._create_context(
                CommentaryTrigger.POSITIONAL_MASTERCLASS,
                priority=4,
                move_data=move_data,
                evaluation=evaluation,
                game_context=game_context,
            )
        
        # No commentary needed
        return None
    
    def _create_context(
        self,
        trigger: CommentaryTrigger,
        priority: int,
        move_data: Dict[str, Any],
        evaluation: Dict[str, Any],
        game_context: Dict[str, Any],
        tactical_motif: Optional[str] = None,
    ) -> TriggerContext:
        """Create TriggerContext from move data."""
        eval_before = evaluation.get("eval_before")
        eval_after = evaluation.get("eval_after")
        eval_swing = None
        if eval_before is not None and eval_after is not None:
            eval_swing = abs(eval_after - (-eval_before))
        
        return TriggerContext(
            trigger=trigger,
            priority=priority,
            player=move_data.get("player", "unknown"),
            move=move_data.get("move", ""),
            san_move=move_data.get("san_move", ""),
            move_number=move_data.get("move_number", 0),
            eval_before=eval_before,
            eval_after=eval_after,
            eval_swing=eval_swing,
            centipawn_loss=evaluation.get("centipawn_loss", 0),
            quality=evaluation.get("quality", "unknown"),
            is_best_move=evaluation.get("is_best_move", False),
            best_move_alternative=evaluation.get("best_move_uci"),
            game_phase=game_context.get("game_phase", "unknown"),
            material_balance=game_context.get("material_balance", 0),
            position_type=game_context.get("position_type", "unknown"),
            is_check=game_context.get("is_check", False),
            is_checkmate=game_context.get("is_checkmate", False),
            tactical_motif=tactical_motif,
        )
    
    def _detect_tactical_pattern(
        self,
        move_data: Dict[str, Any],
        evaluation: Dict[str, Any],
        game_context: Dict[str, Any],
    ) -> Optional[str]:
        """Detect tactical patterns in the move.
        
        Returns:
            Name of tactical pattern if detected, None otherwise
        """
        san_move = move_data.get("san_move", "")
        
        # Check notation patterns
        if "x" in san_move:
            # Capture - could be tactical
            if evaluation.get("quality") in ["excellent", "good"]:
                # Piece type indicators
                if san_move[0] == "N":
                    return "knight_fork"
                if san_move[0] == "B":
                    return "bishop_attack"
                if san_move[0] == "Q":
                    return "queen_domination"
                return "tactical_capture"
        
        # Check for discovered attack indicators
        if evaluation.get("eval_swing", 0) > 150 and not "x" in san_move:
            return "discovered_attack"
        
        # Check/checkmate indicators
        if "+" in san_move:
            return "check_attack"
        if "#" in san_move:
            return "checkmate_sequence"
        
        # Castling
        if san_move in ["O-O", "O-O-O"]:
            if game_context.get("move_number", 99) > 15:
                return "delayed_castling"
        
        return None
    
    def _is_sacrifice(
        self,
        move_data: Dict[str, Any],
        evaluation: Dict[str, Any],
        game_context: Dict[str, Any],
    ) -> bool:
        """Detect if move is a sacrifice.
        
        A sacrifice is defined as:
        - Material lost in capture
        - But position improved significantly (eval gain)
        """
        san_move = move_data.get("san_move", "")
        
        # Must be a capture
        if "x" not in san_move:
            return False
        
        # Check if position improved despite material loss
        eval_swing = evaluation.get("eval_swing", 0)
        if eval_swing > 150:  # Significant improvement
            # Check if quality is good despite high cp_loss
            # (sacrifice often shows high cp_loss but is actually good)
            return True
        
        return False
