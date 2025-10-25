"""Game Orchestrator for managing chess games between agents.

Coordinates turn-based gameplay, move validation, and game completion.
Integrates Stockfish evaluation and live commentary.
"""

from typing import Optional, Dict, Any, List
import structlog
import time
import chess
import os

from src.chess_env import ChessOpenEnv
from src.agents.agent_manager import ChessAgentManager
from src.models.game import GameStatus, GameResult
from src.utils.stockfish_evaluator import get_evaluator
from src.commentary.triggers import TriggerDetector, CommentaryTrigger
from src.commentary.commentary_generator import CommentaryGenerator

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
        
        # Initialize commentary system
        self.trigger_detector = None
        self.commentary_generator = None
        
        if self.enable_commentary:
            try:
                threshold = int(os.getenv("COMMENTARY_TRIGGER_THRESHOLD", "50"))
                self.trigger_detector = TriggerDetector(threshold=threshold)
                self.commentary_generator = CommentaryGenerator()
                logger.info(
                    "commentary_enabled",
                    threshold=threshold,
                    mode=os.getenv("COMMENTARY_MODE", "text")
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
                
                # Get agent move
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
            
            # Get agent move
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
            
            # Generate commentary if enabled and triggers met
            if self.enable_commentary and self.trigger_detector and self.commentary_generator and move_evaluation:
                try:
                    # Check if commentary should be generated
                    trigger_result = self.trigger_detector.should_generate_commentary(
                        evaluation=move_evaluation,
                        board_state=env.game.board_state,
                        move_history=move_history or []
                    )
                    
                    if trigger_result.trigger != CommentaryTrigger.NONE:
                        # Generate commentary
                        commentary_result = await self.commentary_generator.generate_commentary(
                            trigger_ctx=trigger_result,
                            move_data={
                                "move": move,
                                "san_move": info["san_move"],
                                "player": env.game.board_state.current_player,
                                "move_number": len(move_history or []) + 1,
                            },
                            evaluation=move_evaluation,
                            game_context={
                                "fen": env.game.board_state.fen,
                                "game_phase": "opening" if len(move_history or []) < 20 else "middlegame",
                                "history": move_history or []
                            }
                        )
                        
                        # Add commentary to result
                        result["commentary"] = {
                            "text": commentary_result["text"],
                            "trigger": trigger_result.trigger.value,
                            "priority": trigger_result.priority,
                        }
                        
                        # Add audio if available
                        if "audio" in commentary_result:
                            result["commentary"]["audio"] = commentary_result["audio"]
                        
                        logger.info(
                            "commentary_generated_for_move",
                            game_id=env.game.game_id,
                            move=move,
                            trigger=trigger_result.trigger.value,
                            text_length=len(commentary_result["text"])
                        )
                        
                except Exception as e:
                    logger.error("commentary_generation_failed", error=str(e), move=move)
            
            return result
            
        except Exception as e:
            logger.error(
                "step_execution_error",
                game_id=env.game.game_id,
                agent=agent_id,
                error=str(e),
            )
            raise
