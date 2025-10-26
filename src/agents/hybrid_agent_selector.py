"""Hybrid agent move selector combining Stockfish and LLM decision-making.

Ensures tactical soundness by constraining LLM selection to Stockfish's top candidates
while preserving agent personality differentiation. Includes opening book integration
for fast, grandmaster-level opening play.
"""

from typing import Optional, List, Tuple
import structlog
import chess

from src.utils.stockfish_evaluator import StockfishEvaluator
from src.utils.opening_book_client import OpeningBookClient
from src.utils.tablebase_client import TablebaseClient
from src.agents.agent_manager import ChessAgentManager
from src.models.board_state import BoardState

logger = structlog.get_logger()


class HybridAgentMoveSelector:
    """Hybrid move selector combining Stockfish evaluation with LLM personality."""
    
    def __init__(
        self,
        stockfish_evaluator: StockfishEvaluator,
        agent_manager: ChessAgentManager,
        num_candidates: int = 10,
        opening_book_client: Optional[OpeningBookClient] = None,
        tablebase_client: Optional[TablebaseClient] = None,
    ):
        """Initialize hybrid selector.
        
        Args:
            stockfish_evaluator: Stockfish evaluator instance
            agent_manager: Agent manager for LLM decision-making
            num_candidates: Number of top moves to get from Stockfish (default 5)
            opening_book_client: Optional opening book client for opening phase
            tablebase_client: Optional tablebase client for perfect endgame play
        """
        self.evaluator = stockfish_evaluator
        self.agent_manager = agent_manager
        self.num_candidates = num_candidates
        self.opening_book = opening_book_client
        self.tablebase = tablebase_client
        
        logger.info(
            "hybrid_selector_initialized",
            num_candidates=num_candidates,
            opening_book_enabled=opening_book_client is not None,
            tablebase_enabled=tablebase_client is not None,
        )
    
    def get_move(
        self,
        agent_id: str,
        board: chess.Board,
        board_state: BoardState,
        game_history: Optional[List[str]] = None,
        game_id: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Get move using hybrid Stockfish + LLM approach.
        
        Priority order:
        1. Opening book (if move <= 15 and opening book available)
        2. Syzygy tablebase (if ≤7 pieces and tablebase available)
        3. Stockfish candidates + LLM selection
        4. Pure LLM fallback (if Stockfish unavailable)
        
        Args:
            agent_id: Agent identifier
            board: Chess board instance
            board_state: Board state for agent context
            game_history: Optional game history
            game_id: Optional game ID for caching
            
        Returns:
            Tuple of (move_uci, move_source) where move_source is:
            - "opening_book": Move from Lichess Masters database
            - "tablebase": Perfect move from Syzygy endgame tablebase
            - "hybrid": Stockfish candidates + LLM selection
            - "llm-fallback": Pure LLM when Stockfish unavailable
        """
        # Calculate move number (history length / 2 + 1 for white's move, + 0.5 for black's)
        move_number = len(game_history or []) + 1
        
        # Try opening book first (if in opening phase)
        if self.opening_book and self.opening_book.should_use_opening_book(move_number):
            try:
                fen = board.fen()
                opening_moves = self.opening_book.query_opening_book(fen)
                
                if opening_moves:
                    # Get agent personality
                    agent_config = self.agent_manager.configs.get(agent_id)
                    personality = agent_config.personality if agent_config else "balanced"
                    is_white = board.turn == chess.WHITE
                    
                    move_uci = self.opening_book.select_opening_move(
                        opening_moves=opening_moves,
                        personality=personality,
                        is_white=is_white,
                    )
                    
                    if move_uci:
                        # Validate move is legal
                        try:
                            move = chess.Move.from_uci(move_uci)
                            if move in board.legal_moves:
                                logger.info(
                                    "opening_book_move_selected",
                                    agent_id=agent_id,
                                    move=move_uci,
                                    move_number=move_number,
                                    personality=personality,
                                )
                                return move_uci, "opening_book"
                            else:
                                logger.warning(
                                    "opening_book_illegal_move",
                                    agent_id=agent_id,
                                    move=move_uci,
                                )
                        except ValueError as e:
                            logger.warning(
                                "opening_book_invalid_uci",
                                agent_id=agent_id,
                                move=move_uci,
                                error=str(e),
                            )
                else:
                    logger.debug(
                        "opening_book_no_moves",
                        agent_id=agent_id,
                        move_number=move_number,
                    )
                    
            except Exception as e:
                logger.warning(
                    "opening_book_query_failed",
                    agent_id=agent_id,
                    error=str(e),
                )
        
        # Try tablebase for endgame positions (7 or fewer pieces)
        if self.tablebase:
            try:
                fen = board.fen()
                tablebase_result = self.tablebase.query_position(fen)
                
                if tablebase_result:
                    move_uci = tablebase_result["uci"]
                    wdl = tablebase_result.get("wdl")
                    category = tablebase_result.get("category")
                    
                    # Validate move is legal
                    try:
                        move = chess.Move.from_uci(move_uci)
                        if move in board.legal_moves:
                            # Use tablebase move if it's winning or drawing
                            # For losing positions, fall through to hybrid agent for best practical try
                            if self.tablebase.is_winning(wdl) or self.tablebase.is_drawing(wdl):
                                logger.info(
                                    "tablebase_move_selected",
                                    agent_id=agent_id,
                                    move=move_uci,
                                    wdl=wdl,
                                    category=category,
                                    move_number=move_number,
                                )
                                return move_uci, "tablebase"
                            else:
                                logger.debug(
                                    "tablebase_losing_fallback_to_hybrid",
                                    agent_id=agent_id,
                                    move=move_uci,
                                    wdl=wdl,
                                )
                        else:
                            logger.warning(
                                "tablebase_illegal_move",
                                agent_id=agent_id,
                                move=move_uci,
                            )
                    except ValueError as e:
                        logger.warning(
                            "tablebase_invalid_uci",
                            agent_id=agent_id,
                            move=move_uci,
                            error=str(e),
                        )
                        
            except Exception as e:
                logger.warning(
                    "tablebase_query_failed",
                    agent_id=agent_id,
                    error=str(e),
                )
        
        # Check if Stockfish is available
        if not self.evaluator.is_available():
            logger.warning(
                "stockfish_unavailable_using_llm_fallback",
                agent_id=agent_id,
            )
            return self._get_llm_fallback_move(agent_id, board, board_state, game_history), "llm-fallback"
        
        # Get top candidates from Stockfish
        try:
            candidates = self.evaluator.get_top_moves(
                board=board,
                num_moves=self.num_candidates,
                game_id=game_id,
            )
            
            if not candidates:
                logger.warning(
                    "stockfish_returned_no_candidates_using_fallback",
                    agent_id=agent_id,
                )
                return self._get_llm_fallback_move(agent_id, board, board_state, game_history), "llm-fallback"
            
            # Get move from agent constrained to candidates
            move_uci = self._get_hybrid_agent_move(
                agent_id=agent_id,
                board_state=board_state,
                candidates=candidates,
                game_history=game_history,
            )
            
            logger.info(
                "hybrid_move_selected",
                agent_id=agent_id,
                move=move_uci,
                num_candidates=len(candidates),
            )
            
            return move_uci, "hybrid"
            
        except Exception as e:
            logger.error(
                "hybrid_selection_failed_using_fallback",
                agent_id=agent_id,
                error=str(e),
            )
            return self._get_llm_fallback_move(agent_id, board, board_state, game_history), "llm-fallback"
    
    def _get_hybrid_agent_move(
        self,
        agent_id: str,
        board_state: BoardState,
        candidates: List[Tuple[chess.Move, int, List[chess.Move]]],
        game_history: Optional[List[str]],
    ) -> str:
        """Get move from agent constrained to Stockfish candidates.
        
        Args:
            agent_id: Agent identifier
            board_state: Board state for context
            candidates: List of (move, score, pv_line) from Stockfish
            game_history: Optional game history
            
        Returns:
            Move in UCI notation
        """
        # Build enhanced prompt with candidates
        enhanced_prompt = self._build_hybrid_agent_prompt(
            board_state=board_state,
            candidates=candidates,
            game_history=game_history,
            agent_id=agent_id,
        )
        
        # Get agent from manager
        agent = self.agent_manager.agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        config = self.agent_manager.configs.get(agent_id)
        candidate_moves = [move.uci() for move, _, _ in candidates]
        
        # Try to get valid move from agent with retries
        for attempt in range(config.max_retries):
            try:
                result = agent.run(enhanced_prompt)
                
                # Extract move and validate it's from candidates
                selected_move = self.agent_manager._extract_move(result, candidate_moves)
                
                if selected_move and selected_move in candidate_moves:
                    logger.debug(
                        "agent_selected_valid_candidate",
                        agent_id=agent_id,
                        move=selected_move,
                        attempt=attempt + 1,
                    )
                    return selected_move
                
                logger.warning(
                    "agent_selected_non_candidate_move",
                    agent_id=agent_id,
                    attempt=attempt + 1,
                    selected=selected_move,
                )
                
            except Exception as e:
                logger.warning(
                    "hybrid_agent_move_attempt_failed",
                    agent_id=agent_id,
                    attempt=attempt + 1,
                    error=str(e),
                )
        
        # All retries failed - use top Stockfish candidate as fallback
        top_candidate = candidates[0][0].uci()
        logger.warning(
            "agent_failed_all_retries_using_top_candidate",
            agent_id=agent_id,
            fallback_move=top_candidate,
        )
        return top_candidate
    
    def _build_hybrid_agent_prompt(
        self,
        board_state: BoardState,
        candidates: List[Tuple[chess.Move, int, List[chess.Move]]],
        game_history: Optional[List[str]],
        agent_id: str,
    ) -> str:
        """Build enhanced prompt including Stockfish candidates with scores and PV lines.
        
        Args:
            board_state: Current board state
            candidates: List of (move, score, pv_line) from Stockfish
            game_history: Optional game history
            agent_id: Agent identifier for personality
            
        Returns:
            Enhanced prompt string
        """
        config = self.agent_manager.configs.get(agent_id)
        personality = config.personality if config else "balanced"
        system_prompt = self.agent_manager.SYSTEM_PROMPTS.get(personality, self.agent_manager.SYSTEM_PROMPTS["balanced"])
        
        prompt = f"""{system_prompt}

=== HYBRID MOVE SELECTION ===

You are using a hybrid approach: Stockfish provides tactically sound candidate moves,
and you select the one that best matches your {personality} playing style.

**IMPORTANT**: You MUST select one of the candidate moves listed below.
Do NOT suggest any other moves - they may be tactically unsound.

=== STOCKFISH TOP CANDIDATES ===

"""
        
        # Check if any candidates are forcing (captures/checks)
        forcing_moves = []
        quiet_moves = []
        
        # Add candidates with scores and continuations
        for i, (move, score, pv_line) in enumerate(candidates, 1):
            move_san = board_state.fen  # We'll format this better with actual SAN
            
            # Format score
            if abs(score) >= 10000:
                score_str = f"Mate in {abs(score) // 10000}" if score > 0 else f"Mated in {abs(score) // 10000}"
            else:
                score_str = f"{score:+d} centipawns"
            
            # Format PV line
            pv_str = " ".join([m.uci() for m in pv_line[:5]]) if pv_line else "N/A"
            
            # Check if move is forcing (capture/check)
            move_obj = chess.Move.from_uci(move.uci())
            board_obj = chess.Board(board_state.fen)
            is_capture = board_obj.is_capture(move_obj)
            board_obj.push(move_obj)
            gives_check = board_obj.is_check()
            forcing_tag = "" 
            is_forcing = False
            
            if is_capture and gives_check:
                forcing_tag = " ⚡ [CAPTURE+CHECK]"
                is_forcing = True
            elif is_capture:
                forcing_tag = " 🎯 [CAPTURE]"
                is_forcing = True
            elif gives_check:
                forcing_tag = " ⚠️ [CHECK]"
                is_forcing = True
            
            move_info = {
                "index": i,
                "move": move.uci(),
                "tag": forcing_tag,
                "score": score_str,
                "pv": pv_str,
                "is_forcing": is_forcing
            }
            
            if is_forcing:
                forcing_moves.append(move_info)
            else:
                quiet_moves.append(move_info)
        
        # If there are forcing moves and personality is aggressive/tactical, show those FIRST with emphasis
        if forcing_moves and personality in ["aggressive", "tactical"]:
            prompt += "**FORCING MOVES (CAPTURES/CHECKS) - PRIORITIZE THESE:**\n\n"
            for info in forcing_moves:
                prompt += f"**Candidate {info['index']}**: {info['move']}{info['tag']}\n"
                prompt += f"  - Evaluation: {info['score']}\n"
                prompt += f"  - Continuation: {info['pv']}\n"
                prompt += f"  - 🔥 THIS IS A FORCING MOVE - CREATE THREATS!\n\n"
            
            if quiet_moves:
                prompt += "\n**QUIET MOVES (Less Interesting):**\n\n"
                for info in quiet_moves:
                    prompt += f"**Candidate {info['index']}**: {info['move']}\n"
                    prompt += f"  - Evaluation: {info['score']}\n"
                    prompt += f"  - Continuation: {info['pv']}\n\n"
        else:
            # Standard presentation for all moves
            all_moves = forcing_moves + quiet_moves
            for info in all_moves:
                prompt += f"**Candidate {info['index']}**: {info['move']}{info['tag']}\n"
                prompt += f"  - Evaluation: {info['score']}\n"
                prompt += f"  - Continuation: {info['pv']}\n"
                
                # Add personality-specific annotations
                if info['is_forcing'] and personality in ["aggressive", "tactical"]:
                    prompt += f"  - � Forcing move - creates threats!\n"
                elif personality == "defensive" and not info['is_forcing']:
                    prompt += f"  - 🛡️ Safe and solid choice\n"
                
                prompt += "\n"
        
        # Add selection guidance
        prompt += f"""
=== YOUR TASK ===

Current position: {board_state.fen}
You are playing as: {board_state.current_player.upper()}
"""
        
        if game_history:
            recent = game_history[-6:] if len(game_history) > 6 else game_history
            prompt += f"Recent moves: {' '.join(recent)}\n"
        
        if board_state.is_check:
            prompt += "\n⚠️ YOU ARE IN CHECK!\n"
        
        prompt += f"""
Select the BEST move from the candidates above that matches your {personality} style:
"""
        
        if personality == "aggressive":
            if forcing_moves:
                prompt += f"**CRITICAL: There are {len(forcing_moves)} forcing moves available!**\n"
                prompt += "- You MUST choose one of the FORCING MOVES (captures/checks) unless it's clearly losing\n"
                prompt += "- Quiet moves are BORING - only pick them if all forcing moves are terrible\n"
            else:
                prompt += "- Look for the most aggressive, initiative-seizing move\n"
            prompt += "- Actively look for ways to trade pieces and create imbalances\n"
        elif personality == "defensive":
            prompt += "- Prefer safe, solid moves that maintain piece security\n"
            prompt += "- Choose prophylactic moves that prevent opponent threats\n"
        elif personality == "tactical":
            if forcing_moves:
                prompt += f"**CRITICAL: There are {len(forcing_moves)} forcing moves available!**\n"
                prompt += "- You MUST choose one of the FORCING MOVES (captures/checks) - this is what tactics means!\n"
                prompt += "- Quiet moves avoid tactics - only pick them if all forcing moves fail tactically\n"
            else:
                prompt += "- Look for the most forcing, concrete move available\n"
            prompt += "- Look for piece exchanges that lead to tactical opportunities\n"
        elif personality == "positional":
            prompt += "- Prefer moves that improve long-term position\n"
            prompt += "- Choose moves that enhance pawn structure and piece placement\n"
        else:  # balanced
            prompt += "- Evaluate both tactical and positional factors\n"
            prompt += "- Choose the move that offers the best practical chances\n"
            prompt += "- Don't avoid exchanges - trading pieces is a normal part of chess\n"
        
        prompt += """
Respond with ONLY the move in UCI notation (e.g., 'e2e4').
Do not include explanations or additional text.

Your selected move:"""
        
        return prompt
    
    def _get_llm_fallback_move(
        self,
        agent_id: str,
        board: chess.Board,
        board_state: BoardState,
        game_history: Optional[List[str]],
    ) -> str:
        """Get move using pure LLM when Stockfish unavailable.
        
        Args:
            agent_id: Agent identifier
            board: Chess board
            board_state: Board state
            game_history: Optional game history
            
        Returns:
            Move in UCI notation
        """
        legal_moves = [move.uci() for move in board.legal_moves]
        
        logger.info(
            "using_llm_fallback",
            agent_id=agent_id,
            legal_moves_count=len(legal_moves),
        )
        
        return self.agent_manager.get_agent_move(
            agent_id=agent_id,
            board_state=board_state,
            legal_moves=legal_moves,
            game_history=game_history,
        )
