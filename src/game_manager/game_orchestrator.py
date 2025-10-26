"""Game Orchestrator for managing chess games between agents.

Coordinates turn-based gameplay, move validation, and game completion.
Integrates Stockfish evaluation, opening book, and live commentary.
"""

from typing import Optional, Dict, Any, List
import structlog
import time
import chess
import os

from src.chess_env import ChessOpenEnv
from src.agents.agent_manager import ChessAgentManager
from src.agents.hybrid_agent_selector import HybridAgentMoveSelector
from src.models.game import GameStatus, GameResult
from src.utils.stockfish_evaluator import get_evaluator
from src.utils.opening_book_client import OpeningBookClient
from src.utils.tablebase_client import TablebaseClient
from src.commentary.triggers import TriggerDetector, CommentaryTrigger
from src.commentary.commentary_generator import CommentaryGenerator
from src.commentary.commentary_strategist import CommentaryStrategist, CommentaryDecision
from src.utils.strategic_analyzer import analyze_position, format_themes_for_commentary

logger = structlog.get_logger()


class GameOrchestrator:
    """Orchestrates chess games between two agents."""
    
    def __init__(
        self,
        agent_manager: ChessAgentManager,
        enable_evaluation: bool = True,
        enable_commentary: bool = True,
    ):
        """Initialize the orchestrator.
        
        Args:
            agent_manager: Agent manager instance
            enable_evaluation: Whether to enable Stockfish move evaluation
            enable_commentary: Whether to enable live commentary generation
        """
        self.agent_manager = agent_manager
        self.enable_evaluation = enable_evaluation
        self.enable_commentary = enable_commentary and os.getenv("COMMENTARY_ENABLED", "true").lower() == "true"
        
        self.evaluator = get_evaluator() if enable_evaluation else None
        
        if self.enable_evaluation and self.evaluator and not self.evaluator.is_available():
            logger.warning("stockfish_not_available_disabling_evaluation")
            self.enable_evaluation = False
        
        # Initialize opening book client
        self.opening_book = None
        opening_book_env_var = os.getenv("OPENING_BOOK_ENABLED", "true")
        logger.debug(
            "opening_book_check",
            env_var=opening_book_env_var,
            enabled=opening_book_env_var.lower() == "true"
        )
        if opening_book_env_var.lower() == "true":
            try:
                api_url = os.getenv("OPENING_BOOK_API_URL", "https://explorer.lichess.ovh/masters")
                timeout = float(os.getenv("OPENING_BOOK_TIMEOUT", "1.0"))
                cache_size = int(os.getenv("OPENING_BOOK_CACHE_SIZE", "1000"))
                
                logger.debug(
                    "opening_book_attempting_init",
                    api_url=api_url,
                    timeout=timeout,
                    cache_size=cache_size
                )
                
                self.opening_book = OpeningBookClient(
                    api_url=api_url,
                    timeout=timeout,
                    cache_size=cache_size,
                )
                logger.info(
                    "opening_book_initialized",
                    api_url=api_url,
                    timeout=timeout,
                )
            except Exception as e:
                logger.warning("opening_book_initialization_failed", error=str(e), error_type=type(e).__name__)
                self.opening_book = None
        
        # Initialize tablebase client
        self.tablebase = None
        tablebase_env_var = os.getenv("TABLEBASE_ENABLED", "true")
        if tablebase_env_var.lower() == "true":
            try:
                api_url = os.getenv("TABLEBASE_API_URL", "https://tablebase.lichess.ovh/standard")
                timeout = float(os.getenv("TABLEBASE_TIMEOUT", "1.0"))
                
                self.tablebase = TablebaseClient(
                    api_url=api_url,
                    timeout=timeout,
                )
                logger.info(
                    "tablebase_initialized",
                    api_url=api_url,
                    timeout=timeout,
                )
            except Exception as e:
                logger.warning("tablebase_initialization_failed", error=str(e))
                self.tablebase = None
        
        # Initialize hybrid agent selector
        self.hybrid_selector = None
        if self.enable_evaluation and self.evaluator and self.evaluator.is_available():
            self.hybrid_selector = HybridAgentMoveSelector(
                stockfish_evaluator=self.evaluator,
                agent_manager=agent_manager,
                num_candidates=10,
                opening_book_client=self.opening_book,
                tablebase_client=self.tablebase,
            )
            logger.info("hybrid_agent_selector_initialized")
        
        # Initialize commentary system
        self.trigger_detector = None
        self.commentary_generator = None
        self.commentary_strategist = None
        
        # Commentary state tracking
        self.last_commentary_move_number = 0
        self.evaluation_history: List[Dict[str, Any]] = []
        
        if self.enable_commentary:
            try:
                threshold = int(os.getenv("COMMENTARY_TRIGGER_THRESHOLD", "50"))
                self.trigger_detector = TriggerDetector(threshold=threshold)
                self.commentary_generator = CommentaryGenerator()
                self.commentary_strategist = CommentaryStrategist()
                logger.info(
                    "commentary_enabled",
                    threshold=threshold,
                    mode=os.getenv("COMMENTARY_MODE", "text"),
                    dynamic_strategist=True,
                )
            except Exception as e:
                logger.warning("commentary_initialization_failed", error=str(e))
                self.enable_commentary = False
        
        logger.info(
            "game_orchestrator_initialized",
            evaluation_enabled=self.enable_evaluation,
            commentary_enabled=self.enable_commentary,
        )
    
    async def run_game(
        self,
        env: ChessOpenEnv,
        white_agent_id: str,
        black_agent_id: str,
        max_moves: int = 200,
        move_delay: float = 0.0,
    ) -> Dict[str, Any]:
        """Run a complete game between two agents.
        
        Args:
            env: Chess environment instance
            white_agent_id: White agent identifier
            black_agent_id: Black agent identifier
            max_moves: Maximum number of moves before draw
            move_delay: Delay between moves in seconds
            
        Returns:
            Game summary with result and statistics
        """
        game_id = env.game.game_id
        move_history: List[str] = []
        
        logger.info(
            "game_started",
            game_id=game_id,
            white_agent=white_agent_id,
            black_agent=black_agent_id,
        )
        
        start_time = time.time()
        move_count = 0
        
        try:
            while not env.game.is_terminal() and move_count < max_moves:
                # Determine current agent
                current_player = env.game.board_state.current_player
                agent_id = white_agent_id if current_player == "white" else black_agent_id
                
                # Get legal moves
                legal_moves = env.chess.get_legal_moves()
                
                if not legal_moves:
                    # No legal moves available
                    break
                
                # Get agent move using hybrid selector or fallback to direct agent
                if self.hybrid_selector:
                    move, move_source = self.hybrid_selector.get_move(
                        agent_id=agent_id,
                        board=env.chess.board,
                        board_state=env.game.board_state,
                        game_history=move_history,
                        game_id=game_id,
                    )
                    logger.debug(
                        "move_selected",
                        game_id=game_id,
                        agent=agent_id,
                        move=move,
                        source=move_source,
                    )
                else:
                    # Fallback to direct agent call
                    move = self.agent_manager.get_agent_move(
                        agent_id=agent_id,
                        board_state=env.game.board_state,
                        legal_moves=legal_moves,
                        game_history=move_history,
                    )
                
                # Evaluate move quality with Stockfish (if enabled)
                move_eval = None
                if self.enable_evaluation and self.evaluator:
                    try:
                        # Convert move string to chess.Move
                        chess_move = chess.Move.from_uci(move)
                        move_eval = self.evaluator.evaluate_move(
                            env.chess.board,
                            chess_move
                        )
                        logger.debug(
                            "move_evaluated",
                            game_id=game_id,
                            move=move,
                            quality=move_eval.get("quality"),
                            cp_loss=move_eval.get("centipawn_loss"),
                        )
                    except Exception as e:
                        logger.warning("move_evaluation_error", error=str(e))
                
                # Execute move
                try:
                    observation, reward, terminated, truncated, info = env.step(move)
                    
                    move_history.append(info["san_move"])
                    move_count += 1
                    
                    logger.debug(
                        "move_executed",
                        game_id=game_id,
                        move_num=move_count,
                        agent=agent_id,
                        move=move,
                        san=info["san_move"],
                    )
                    
                    # Add delay if specified
                    if move_delay > 0:
                        time.sleep(move_delay)
                    
                    # Check if game ended
                    if terminated or truncated:
                        break
                        
                except ValueError as e:
                    logger.error(
                        "invalid_move_attempted",
                        game_id=game_id,
                        agent=agent_id,
                        move=move,
                        error=str(e),
                    )
                    # This shouldn't happen if agent returns legal move
                    # But if it does, fallback to random legal move
                    import random
                    fallback_move = random.choice(legal_moves)
                    observation, reward, terminated, truncated, info = env.step(fallback_move)
                    move_history.append(info["san_move"])
                    move_count += 1
            
            # Game ended
            elapsed = time.time() - start_time
            
            # Determine winner
            winner = None
            if env.game.result == GameResult.WHITE_WINS:
                winner = white_agent_id
            elif env.game.result == GameResult.BLACK_WINS:
                winner = black_agent_id
            
            summary = {
                "game_id": game_id,
                "white_agent": white_agent_id,
                "black_agent": black_agent_id,
                "result": env.game.result.value,
                "winner": winner,
                "total_moves": move_count,
                "move_history": move_history,
                "elapsed_time": elapsed,
                "avg_move_time": elapsed / move_count if move_count > 0 else 0,
                "final_fen": env.game.board_state.fen,
            }
            
            logger.info(
                "game_completed",
                game_id=game_id,
                result=env.game.result.value,
                winner=winner,
                moves=move_count,
                elapsed=elapsed,
            )
            
            return summary
            
        except Exception as e:
            logger.error(
                "game_execution_error",
                game_id=game_id,
                error=str(e),
            )
            raise
    
    async def run_game_step(
        self,
        env: ChessOpenEnv,
        agent_id: str,
        move_history: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Execute a single move in a game with Stockfish evaluation.
        
        Useful for interactive games or step-by-step execution.
        
        Args:
            env: Chess environment instance
            agent_id: Current agent identifier
            move_history: Optional game history
            
        Returns:
            Step result with move, observation, and evaluation
        """
        try:
            # Check if game is already over
            if env.game.is_terminal():
                return {
                    "terminated": True,
                    "result": env.game.result.value,
                    "message": "Game already completed",
                }
            
            # Get legal moves
            legal_moves = env.chess.get_legal_moves()
            
            if not legal_moves:
                return {
                    "terminated": True,
                    "result": "no_legal_moves",
                    "message": "No legal moves available",
                }
            
            # Get agent move using hybrid selector or fallback to direct agent
            move_source = None
            if self.hybrid_selector:
                move, move_source = self.hybrid_selector.get_move(
                    agent_id=agent_id,
                    board=env.chess.board,
                    board_state=env.game.board_state,
                    game_history=move_history or [],
                    game_id=env.game.game_id,
                )
                logger.debug(
                    "move_selected",
                    game_id=env.game.game_id,
                    agent=agent_id,
                    move=move,
                    source=move_source,
                )
            else:
                # Fallback to direct agent call
                move = self.agent_manager.get_agent_move(
                    agent_id=agent_id,
                    board_state=env.game.board_state,
                    legal_moves=legal_moves,
                    game_history=move_history or [],
                )
            
            # Evaluate move quality with Stockfish (if enabled)
            move_evaluation = None
            if self.enable_evaluation and self.evaluator:
                try:
                    chess_move = chess.Move.from_uci(move)
                    move_evaluation = self.evaluator.evaluate_move(
                        env.chess.board,
                        chess_move
                    )
                except Exception as e:
                    logger.warning("move_evaluation_error", error=str(e))
            
            # Execute move
            observation, reward, terminated, truncated, info = env.step(move)
            
            result = {
                "move": move,
                "san_move": info["san_move"],
                "observation": observation,
                "reward": reward,
                "terminated": terminated,
                "truncated": truncated,
                "info": info,
            }
            
            # Add evaluation if available
            if move_evaluation:
                result["evaluation"] = move_evaluation
                
                # Track evaluation history for volatility analysis
                if self.enable_commentary:
                    self.evaluation_history.append({
                        "move_number": len(move_history or []) + 1,
                        "centipawns": move_evaluation.get("centipawns", 0),
                    })
                    # Keep last 10 evaluations for trend analysis
                    if len(self.evaluation_history) > 10:
                        self.evaluation_history.pop(0)
            
            # Generate commentary if enabled using dynamic strategist
            if self.enable_commentary and self.commentary_strategist and self.commentary_generator and move_evaluation:
                try:
                    current_move_number = len(move_history or []) + 1
                    moves_since_last = current_move_number - self.last_commentary_move_number
                    
                    logger.info(
                        "🎙️ COMMENTARY_CHECK_START",
                        game_id=env.game.game_id,
                        move_number=current_move_number,
                        move=move,
                        san_move=info.get("san_move", "?"),
                        player="white" if env.game.board_state.current_player == "black" else "black",
                        last_commentary_move=self.last_commentary_move_number,
                        moves_since_last=moves_since_last,
                    )
                    
                    # Calculate position interest
                    board = env.game.board_state.board
                    interest_score = self.commentary_strategist.calculate_position_interest(
                        board=board,
                        evaluation=move_evaluation,
                        recent_history=self.evaluation_history,
                    )
                    
                    # Determine if position is quiet (just after tactical)
                    just_after_tactical = False
                    eval_swing = 0
                    if self.evaluation_history and len(self.evaluation_history) >= 2:
                        prev_eval = self.evaluation_history[-2]["centipawns"]
                        curr_eval = self.evaluation_history[-1]["centipawns"]
                        eval_swing = abs(curr_eval - prev_eval)
                        just_after_tactical = eval_swing > 100  # Position was tactical recently
                    
                    logger.info(
                        "📊 POSITION_ANALYSIS",
                        game_id=env.game.game_id,
                        move_number=current_move_number,
                        interest_score=interest_score,
                        centipawns=move_evaluation.get("centipawns", 0),
                        eval_swing=eval_swing,
                        just_after_tactical=just_after_tactical,
                        eval_history_length=len(self.evaluation_history),
                    )
                    
                    # Get decision from strategist
                    decision, reason = self.commentary_strategist.should_generate_commentary(
                        interest_score=interest_score,
                        moves_since_last=moves_since_last,
                        evaluation=move_evaluation,
                        position_type="opening" if current_move_number < 20 else "middlegame",
                        just_after_tactical=just_after_tactical,
                    )
                    
                    logger.info(
                        "🎯 COMMENTARY_DECISION",
                        game_id=env.game.game_id,
                        move_number=current_move_number,
                        decision=decision.value,
                        reason=reason,
                        interest_score=interest_score,
                        moves_since_last=moves_since_last,
                        will_generate=decision != CommentaryDecision.SKIP,
                    )
                    
                    # Handle SKIP decision - no commentary
                    if decision == CommentaryDecision.SKIP:
                        logger.info(
                            "⏭️ COMMENTARY_SKIPPED",
                            game_id=env.game.game_id,
                            move_number=current_move_number,
                            move=move,
                            san_move=info.get("san_move", "?"),
                            reason=reason,
                            interest_score=interest_score,
                            moves_since_last=moves_since_last,
                        )
                        # Don't update last_commentary_move_number for skips
                        
                    # Handle STRATEGIC_OVERVIEW - analyze position holistically
                    elif decision == CommentaryDecision.STRATEGIC_OVERVIEW:
                        logger.info(
                            "🌐 STRATEGIC_OVERVIEW_START",
                            game_id=env.game.game_id,
                            move_number=current_move_number,
                            reason=reason,
                            interest_score=interest_score,
                            moves_since_last=moves_since_last,
                        )
                        
                        # Build strategic overview context
                        overview_context = self._build_strategic_overview_context(
                            board=board,
                            evaluation=move_evaluation,
                            move_history=move_history or [],
                            current_move_number=current_move_number,
                        )
                        
                        # Create TriggerContext for STRATEGIC_OVERVIEW
                        from src.commentary.triggers import TriggerContext
                        trigger_result = TriggerContext(
                            trigger=CommentaryTrigger.STRATEGIC_OVERVIEW,
                            move=move,
                            san_move=info["san_move"],
                            player="white" if env.game.board_state.current_player == "black" else "black",
                            priority=60,  # Medium-high priority
                            move_number=current_move_number,
                            evaluation=move_evaluation,
                        )
                        
                        commentary_result = await self.commentary_generator.generate_commentary(
                            trigger_context=trigger_result,
                            game_context=overview_context,
                        )
                        
                        result["commentary"] = {
                            "text": commentary_result["text"],
                            "trigger": CommentaryTrigger.STRATEGIC_OVERVIEW.value,
                            "priority": 60,
                            "type": "strategic_overview",
                        }
                        
                        if "audio" in commentary_result:
                            result["commentary"]["audio"] = commentary_result["audio"]
                        
                        self.last_commentary_move_number = current_move_number
                        
                        logger.info(
                            "✅ STRATEGIC_OVERVIEW_COMPLETE",
                            game_id=env.game.game_id,
                            move_number=current_move_number,
                            text_length=len(commentary_result["text"]),
                            text_preview=commentary_result["text"][:100] + "..." if len(commentary_result["text"]) > 100 else commentary_result["text"],
                        )
                    
                    # Handle MOVE_COMMENT and CRITICAL_MOMENT - standard commentary
                    elif decision in [CommentaryDecision.MOVE_COMMENT, CommentaryDecision.CRITICAL_MOMENT]:
                        logger.info(
                            "💬 MOVE_COMMENTARY_START",
                            game_id=env.game.game_id,
                            move_number=current_move_number,
                            decision_type=decision.value,
                            interest_score=interest_score,
                        )
                        
                        # Use trigger detector for specific trigger type
                        move_data = {
                            "move": move,
                            "san_move": info["san_move"],
                            "player": "white" if env.game.board_state.current_player == "black" else "black",
                            "move_number": current_move_number,
                        }
                        game_context = {
                            "fen": env.game.board_state.fen,
                            "game_phase": "opening" if current_move_number < 20 else "middlegame",
                            "history": move_history or []
                        }
                        trigger_result = self.trigger_detector.should_generate_commentary(
                            move_data=move_data,
                            evaluation=move_evaluation,
                            game_context=game_context
                        )
                        
                        logger.info(
                            "🔍 TRIGGER_DETECTOR_RESULT",
                            game_id=env.game.game_id,
                            move_number=current_move_number,
                            trigger_found=trigger_result is not None and trigger_result.trigger != CommentaryTrigger.NONE,
                            trigger_type=trigger_result.trigger.value if trigger_result else "NONE",
                        )
                        
                        if trigger_result and trigger_result.trigger != CommentaryTrigger.NONE:
                            logger.info(
                                "📝 GENERATING_MOVE_COMMENTARY",
                                game_id=env.game.game_id,
                                trigger=trigger_result.trigger.value,
                                decision=decision.value,
                                move=move,
                                san_move=info.get("san_move", "?"),
                            )
                            
                            commentary_result = await self.commentary_generator.generate_commentary(
                                trigger_context=trigger_result,
                                game_context={
                                    "fen": env.game.board_state.fen,
                                    "game_phase": "opening" if current_move_number < 20 else "middlegame",
                                    "history": move_history or [],
                                    "evaluation": move_evaluation,
                                }
                            )
                            
                            result["commentary"] = {
                                "text": commentary_result["text"],
                                "trigger": trigger_result.trigger.value,
                                "priority": trigger_result.priority,
                                "type": "critical" if decision == CommentaryDecision.CRITICAL_MOMENT else "move",
                            }
                            
                            if "audio" in commentary_result:
                                result["commentary"]["audio"] = commentary_result["audio"]
                            
                            self.last_commentary_move_number = current_move_number
                            
                            logger.info(
                                "✅ MOVE_COMMENTARY_COMPLETE",
                                game_id=env.game.game_id,
                                move=move,
                                trigger=trigger_result.trigger.value,
                                text_length=len(commentary_result["text"]),
                                text_preview=commentary_result["text"][:100] + "..." if len(commentary_result["text"]) > 100 else commentary_result["text"],
                            )
                        else:
                            logger.info(
                                "⚠️ NO_TRIGGER_DESPITE_DECISION",
                                game_id=env.game.game_id,
                                move_number=current_move_number,
                                decision=decision.value,
                                reason="TriggerDetector returned NONE despite strategist recommending commentary",
                            )
                        
                except Exception as e:
                    logger.error(
                        "❌ COMMENTARY_GENERATION_FAILED",
                        game_id=env.game.game_id,
                        move_number=current_move_number,
                        error=str(e),
                        move=move,
                        error_type=type(e).__name__,
                    )
            
            return result
            
        except Exception as e:
            logger.error(
                "step_execution_error",
                game_id=env.game.game_id,
                agent=agent_id,
                error=str(e),
            )
            raise
    
    def _build_strategic_overview_context(
        self,
        board: chess.Board,
        evaluation: Dict[str, Any],
        move_history: List[str],
        current_move_number: int,
    ) -> Dict[str, Any]:
        """Build context for strategic overview commentary.
        
        Args:
            board: Current chess board position
            evaluation: Current evaluation with centipawns
            move_history: List of moves played
            current_move_number: Current move number
            
        Returns:
            Dictionary with strategic overview context
        """
        try:
            # Analyze position for both sides
            themes_dict = analyze_position(board)
            
            # Format themes for both players
            white_themes = format_themes_for_commentary(themes_dict, "white")
            black_themes = format_themes_for_commentary(themes_dict, "black")
            
            # Calculate evaluation trend (last 3 moves)
            eval_trend = "stable"
            if len(self.evaluation_history) >= 3:
                recent_evals = [h["centipawns"] for h in self.evaluation_history[-3:]]
                if recent_evals[-1] > recent_evals[0] + 50:
                    eval_trend = "improving for White"
                elif recent_evals[-1] < recent_evals[0] - 50:
                    eval_trend = "improving for Black"
                elif max(recent_evals) - min(recent_evals) > 100:
                    eval_trend = "volatile"
            
            # Determine opening context if applicable
            opening_context = ""
            if current_move_number < 20 and self.opening_book:
                try:
                    opening_info = self.opening_book.get_opening_name(board)
                    if opening_info and opening_info.get("opening"):
                        opening_context = f"Opening: {opening_info['opening']}"
                except Exception as e:
                    logger.debug("opening_lookup_failed_for_overview", error=str(e))
            
            # Build context
            context = {
                "fen": board.fen(),
                "game_phase": "opening" if current_move_number < 20 else "middlegame" if board.fullmove_number < 40 else "endgame",
                "history": move_history,
                "evaluation": evaluation,
                "eval_current": f"{evaluation.get('centipawns', 0) / 100:.2f}",
                "eval_trend": eval_trend,
                "white_themes": white_themes,
                "black_themes": black_themes,
                "strategic_themes": themes_dict.get("general_themes", []),
                "opening_context": opening_context,
            }
            
            logger.debug(
                "strategic_overview_context_built",
                white_themes_count=len(themes_dict.get("white_themes", [])),
                black_themes_count=len(themes_dict.get("black_themes", [])),
                eval_trend=eval_trend,
            )
            
            return context
            
        except Exception as e:
            logger.error("strategic_overview_context_failed", error=str(e))
            # Return minimal context
            return {
                "fen": board.fen(),
                "game_phase": "middlegame",
                "history": move_history,
                "evaluation": evaluation,
                "eval_current": "0.00",
                "eval_trend": "unknown",
                "white_themes": "Balanced position",
                "black_themes": "Balanced position",
                "strategic_themes": [],
                "opening_context": "",
            }
