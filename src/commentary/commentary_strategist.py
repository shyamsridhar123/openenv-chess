"""Commentary Strategist - Intelligent decision engine for when and what type of commentary to generate.

This module implements grandmaster-level intuition about when positions are "interesting enough"
to comment on, using a custom heuristic that combines tactical density, evaluation volatility,
structural changes, and narrative flow.
"""

from typing import Dict, List, Optional, Tuple
from enum import Enum
import chess
import structlog

logger = structlog.get_logger(__name__)


class CommentaryDecision(Enum):
    """Decision on whether and how to generate commentary."""
    SKIP = "skip"  # Position not interesting enough
    MOVE_COMMENT = "move_comment"  # Comment on the specific move
    STRATEGIC_OVERVIEW = "strategic_overview"  # Broad positional overview
    CRITICAL_MOMENT = "critical_moment"  # Major tactical/strategic moment


class CommentaryStrategist:
    """Decides when and what type of commentary to generate based on position analysis."""
    
    def __init__(self):
        """Initialize the commentary strategist."""
        logger.info("commentary_strategist_initialized")
    
    def calculate_position_interest(
        self,
        board: chess.Board,
        evaluation: Optional[Dict] = None,
        recent_history: Optional[List[str]] = None,
    ) -> int:
        """Calculate position interest score (0-100) using custom chess heuristic.
        
        Higher scores indicate more interesting positions worthy of commentary.
        
        Args:
            board: Current chess board position
            evaluation: Optional Stockfish evaluation dict with centipawn score
            recent_history: Optional list of recent moves in UCI format
            
        Returns:
            Interest score (0-100)
        """
        score = 0
        
        # 1. Tactical Density (0-30 points)
        # Checks, captures, piece attacks indicate tactical richness
        tactical_score = self._calculate_tactical_density(board)
        score += tactical_score
        
        # 2. Evaluation Volatility (0-25 points)
        # Recent evaluation swings indicate dynamic position
        if evaluation and recent_history:
            volatility_score = self._calculate_evaluation_volatility(evaluation, recent_history)
            score += volatility_score
        
        # 3. Structural Changes (0-20 points)
        # Pawn moves, trades, king moves change position character
        if recent_history:
            structural_score = self._calculate_structural_changes(board, recent_history)
            score += structural_score
        
        # 4. Material Imbalance (0-15 points)
        # Unequal material creates tension
        material_score = self._calculate_material_imbalance(board)
        score += material_score
        
        # 5. Phase Transitions (0-10 points)
        # Opening→middlegame, middlegame→endgame are interesting
        if recent_history:
            phase_score = self._detect_phase_transition(board, recent_history)
            score += phase_score
        
        logger.debug(
            "position_interest_calculated",
            total_score=score,
            tactical=tactical_score,
            volatility=volatility_score if evaluation else 0,
            structural=structural_score if recent_history else 0,
            material=material_score,
            phase=phase_score if recent_history else 0,
        )
        
        return min(score, 100)  # Cap at 100
    
    def _calculate_tactical_density(self, board: chess.Board) -> int:
        """Calculate tactical density score (0-30 points).
        
        Measures: checks, captures available, pieces under attack, piece coordination.
        """
        score = 0
        
        # Check: +10 points
        if board.is_check():
            score += 10
        
        # Count captures available (max +10)
        captures = [move for move in board.legal_moves if board.is_capture(move)]
        score += min(len(captures) * 2, 10)
        
        # Count pieces attacking enemy pieces (max +10)
        # Simplified: count attacks on all squares
        attacks = 0
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece and piece.color != board.turn:
                if board.is_attacked_by(board.turn, square):
                    attacks += 1
        score += min(attacks, 10)
        
        return score
    
    def _calculate_evaluation_volatility(
        self,
        evaluation: Dict,
        recent_history: List[str]
    ) -> int:
        """Calculate evaluation volatility score (0-25 points).
        
        Measures evaluation swings over recent moves.
        """
        # TODO: Track evaluation history over moves to detect swings
        # For now, use evaluation change if available
        score = 0
        
        if "cp" in evaluation:
            cp = abs(evaluation["cp"])
            # Large evaluation swings are interesting
            if cp > 200:
                score = 25
            elif cp > 100:
                score = 15
            elif cp > 50:
                score = 10
        
        return score
    
    def _calculate_structural_changes(
        self,
        board: chess.Board,
        recent_history: List[str]
    ) -> int:
        """Calculate structural change score (0-20 points).
        
        Measures pawn moves, trades, castling in recent moves.
        """
        score = 0
        
        if not recent_history or len(recent_history) < 2:
            return 0
        
        # Analyze last 2 moves
        recent_moves = recent_history[-2:]
        
        try:
            # Create temporary board to replay moves
            temp_board = board.copy()
            for _ in range(len(recent_moves)):
                temp_board.pop()
            
            for uci_move in recent_moves:
                move = chess.Move.from_uci(uci_move)
                
                # Pawn move: +5 points (changes structure)
                if temp_board.piece_at(move.from_square).piece_type == chess.PAWN:
                    score += 5
                
                # Capture: +8 points (material change)
                if temp_board.is_capture(move):
                    score += 8
                
                # Castling: +7 points (major positional change)
                if temp_board.is_castling(move):
                    score += 7
                
                # King move: +5 points (safety concern)
                if temp_board.piece_at(move.from_square).piece_type == chess.KING:
                    score += 5
                
                temp_board.push(move)
        except Exception as e:
            logger.warning("structural_change_analysis_failed", error=str(e))
        
        return min(score, 20)
    
    def _calculate_material_imbalance(self, board: chess.Board) -> int:
        """Calculate material imbalance score (0-15 points).
        
        Deviation from equal material creates tension.
        """
        piece_values = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9,
        }
        
        white_material = 0
        black_material = 0
        
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece and piece.piece_type != chess.KING:
                value = piece_values.get(piece.piece_type, 0)
                if piece.color == chess.WHITE:
                    white_material += value
                else:
                    black_material += value
        
        imbalance = abs(white_material - black_material)
        
        # More imbalance = more interesting
        # 1 point = 15 points, 2 points = 12, 3+ points = 10
        if imbalance >= 3:
            return 15
        elif imbalance == 2:
            return 12
        elif imbalance == 1:
            return 8
        else:
            return 0
    
    def _detect_phase_transition(
        self,
        board: chess.Board,
        recent_history: List[str]
    ) -> int:
        """Detect phase transitions (0-10 points).
        
        Opening→middlegame, middlegame→endgame are notable moments.
        """
        move_count = len(recent_history)
        
        # Count pieces on board (excluding pawns and kings)
        pieces = 0
        queens = 0
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece and piece.piece_type not in [chess.PAWN, chess.KING]:
                pieces += 1
                if piece.piece_type == chess.QUEEN:
                    queens += 1
        
        # Opening→middlegame transition (moves 12-18, pieces developed)
        if 12 <= move_count <= 18:
            return 10
        
        # Middlegame→endgame (few pieces left or queens traded)
        if move_count > 20 and (pieces <= 8 or queens == 0):
            return 10
        
        return 0
    
    def should_generate_commentary(
        self,
        interest_score: int,
        moves_since_last_commentary: int,
        evaluation: Optional[Dict] = None,
        position_type: str = "middlegame",
        just_after_tactical: bool = False,
    ) -> Tuple[CommentaryDecision, str]:
        """Decide whether and what type of commentary to generate.
        
        Args:
            interest_score: Position interest score (0-100)
            moves_since_last_commentary: Number of moves since last commentary
            evaluation: Optional Stockfish evaluation
            position_type: Game phase (opening/middlegame/endgame)
            just_after_tactical: Whether position just stabilized after tactics
            
        Returns:
            Tuple of (decision, reason)
        """
        # Critical moment: High interest or large evaluation swing
        if interest_score >= 75:
            return CommentaryDecision.CRITICAL_MOMENT, "high_interest_score"
        
        if evaluation and "cp" in evaluation:
            eval_swing = abs(evaluation.get("cp", 0))
            if eval_swing > 150:
                return CommentaryDecision.CRITICAL_MOMENT, "large_evaluation_swing"
        
        # Strategic overview: Been quiet for a while OR just after tactical sequence
        if moves_since_last_commentary >= 8:
            return CommentaryDecision.STRATEGIC_OVERVIEW, "many_moves_without_commentary"
        
        if just_after_tactical and moves_since_last_commentary >= 4:
            return CommentaryDecision.STRATEGIC_OVERVIEW, "position_stabilized_after_tactics"
        
        if moves_since_last_commentary >= 5 and interest_score < 40:
            return CommentaryDecision.STRATEGIC_OVERVIEW, "quiet_position_needs_overview"
        
        # Move comment: Moderately interesting position
        if interest_score >= 60:
            return CommentaryDecision.MOVE_COMMENT, "moderate_interest"
        
        if evaluation and "cp" in evaluation:
            eval_swing = abs(evaluation.get("cp", 0))
            if eval_swing > 75 and moves_since_last_commentary >= 2:
                return CommentaryDecision.MOVE_COMMENT, "evaluation_change"
        
        # Skip: Not interesting enough
        if interest_score < 30 and moves_since_last_commentary < 5:
            return CommentaryDecision.SKIP, "low_interest_and_recent_commentary"
        
        # Default: Comment if been at least 3 moves
        if moves_since_last_commentary >= 3:
            return CommentaryDecision.MOVE_COMMENT, "minimum_move_threshold"
        
        return CommentaryDecision.SKIP, "default_skip"
