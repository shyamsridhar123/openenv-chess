"""Agent Manager for chess agents using smolagents.

Manages agent creation, move generation with retry logic, and fallback behavior.
"""

from typing import Optional, Dict, Any, List
import structlog
import random
import time
from dataclasses import dataclass

from smolagents import CodeAgent, InferenceClientModel
from src.models.board_state import BoardState

logger = structlog.get_logger()


@dataclass
class AgentConfig:
    """Configuration for a chess agent."""
    agent_id: str
    model_name: str = "Qwen/Qwen2.5-Coder-32B-Instruct"
    personality: str = "balanced"
    temperature: float = 0.7
    max_tokens: int = 512
    timeout: float = 30.0
    max_retries: int = 3


class ChessAgentManager:
    """Manages chess agents and move generation."""
    
    SYSTEM_PROMPTS = {
        "aggressive": """You are an aggressive chess player. You prioritize attacking moves, 
        sacrifices for initiative, and putting pressure on your opponent. You prefer tactical 
        complications over quiet positional play.""",
        
        "defensive": """You are a defensive chess player. You focus on solid positions, 
        preventing opponent threats, and maintaining piece safety. You prefer prophylactic 
        moves and only attack when your position is secure.""",
        
        "balanced": """You are a balanced chess player. You evaluate both tactical and 
        positional factors, adapting your style to the position. You balance attacking 
        chances with defensive needs.""",
        
        "tactical": """You are a tactical chess player. You excel at calculating concrete 
        variations, finding combinations, and exploiting tactical weaknesses. You love 
        sharp, complicated positions.""",
        
        "positional": """You are a positional chess player. You focus on long-term advantages 
        like pawn structure, piece placement, and control of key squares. You prefer strategic 
        maneuvering over tactical complications.""",
    }
    
    def __init__(self):
        """Initialize the agent manager."""
        self.agents: Dict[str, CodeAgent] = {}
        self.configs: Dict[str, AgentConfig] = {}
        logger.info("agent_manager_initialized")
    
    def create_agent(
        self,
        agent_id: str,
        model_name: str = "Qwen/Qwen2.5-Coder-32B-Instruct",
        personality: str = "balanced",
        temperature: float = 0.7,
        max_tokens: int = 512,
        timeout: float = 30.0,
    ) -> CodeAgent:
        """Create a new chess agent.
        
        Args:
            agent_id: Unique identifier for the agent
            model_name: HuggingFace model to use
            personality: Agent personality (aggressive, defensive, balanced, tactical, positional)
            temperature: Sampling temperature
            max_tokens: Maximum tokens for response
            timeout: Timeout in seconds
            
        Returns:
            Configured CodeAgent instance
        """
        try:
            # Store configuration
            config = AgentConfig(
                agent_id=agent_id,
                model_name=model_name,
                personality=personality,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            self.configs[agent_id] = config
            
            # Create model
            model = InferenceClientModel(model_id=model_name)
            
            # Get system prompt
            system_prompt = self.SYSTEM_PROMPTS.get(personality, self.SYSTEM_PROMPTS["balanced"])
            
            # Create agent
            agent = CodeAgent(
                tools=[],
                model=model,
                additional_authorized_imports=["chess"],
            )
            
            self.agents[agent_id] = agent
            
            logger.info(
                "agent_created",
                agent_id=agent_id,
                model=model_name,
                personality=personality,
            )
            
            return agent
            
        except Exception as e:
            logger.error("agent_creation_failed", agent_id=agent_id, error=str(e))
            raise
    
    def get_agent_move(
        self,
        agent_id: str,
        board_state: BoardState,
        legal_moves: List[str],
        game_history: Optional[List[str]] = None,
    ) -> str:
        """Get move from agent with retry logic.
        
        Implements 3-retry pattern validated against openenv/coding patterns.
        Falls back to random legal move on failure.
        
        Args:
            agent_id: Agent identifier
            board_state: Current board state
            legal_moves: List of legal moves in UCI notation
            game_history: Optional game history for context
            
        Returns:
            Move in UCI notation
        """
        agent = self.agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found. Agent must be created before requesting moves.")
        
        config = self.configs[agent_id]
        
        # Build prompt
        prompt = self._build_move_prompt(
            board_state=board_state,
            legal_moves=legal_moves,
            game_history=game_history,
            personality=config.personality,
        )
        
        # Try with retries
        for attempt in range(config.max_retries):
            try:
                start_time = time.time()
                
                # Run agent
                result = agent.run(prompt)
                
                elapsed = time.time() - start_time
                
                # Extract move from result
                move = self._extract_move(result, legal_moves)
                
                if move:
                    logger.info(
                        "agent_move_success",
                        agent_id=agent_id,
                        move=move,
                        attempt=attempt + 1,
                        elapsed=elapsed,
                    )
                    return move
                
                logger.warning(
                    "agent_move_invalid",
                    agent_id=agent_id,
                    attempt=attempt + 1,
                    result=str(result)[:100],
                )
                
            except Exception as e:
                logger.warning(
                    "agent_move_error",
                    agent_id=agent_id,
                    attempt=attempt + 1,
                    error=str(e),
                )
        
        # All retries failed - raise error instead of fallback
        logger.error(
            "agent_move_failed_all_retries",
            agent_id=agent_id,
            max_retries=config.max_retries,
        )
        raise ValueError(f"Agent {agent_id} failed to generate valid move after {config.max_retries} attempts")
    
    def _build_move_prompt(
        self,
        board_state: BoardState,
        legal_moves: List[str],
        game_history: Optional[List[str]],
        personality: str,
    ) -> str:
        """Build comprehensive prompt for agent move generation with chess principles and examples."""
        system_prompt = self.SYSTEM_PROMPTS.get(personality, self.SYSTEM_PROMPTS["balanced"])
        
        # Determine game phase for phase-specific guidance
        move_count = len(game_history) if game_history else 0
        game_phase = self._determine_game_phase(move_count, board_state.fen)
        
        # Detect position type for conditional few-shot examples
        position_type = self._analyze_position_type(board_state, legal_moves)
        
        prompt = f"""{system_prompt}

=== CHESS EVALUATION FRAMEWORK ===

**Fundamental Principles:**
1. **Material**: Value pieces appropriately (Pawn=1, Knight/Bishop=3, Rook=5, Queen=9). Avoid unnecessary losses.
2. **Center Control**: Dominate central squares (e4, e5, d4, d5) with pawns and pieces. The center is the key battleground.
3. **Development**: Activate pieces early - knights before bishops, castle within first 10 moves, connect rooks.
4. **King Safety**: Castle early, maintain pawn shield, avoid weaknesses around king. Never expose your king unnecessarily.
5. **Pawn Structure**: Avoid doubled/isolated pawns, create passed pawns, control key squares with pawn chains.
6. **Piece Activity**: Place pieces on active squares - knights on outposts, bishops on open diagonals, rooks on open files.

**Tactical Patterns to Recognize:**
- **Forks**: One piece attacks two or more enemy pieces simultaneously (especially knight forks)
- **Pins**: Piece cannot move without exposing higher-value piece behind it (absolute pin if king is behind)
- **Skewers**: Reverse pin - valuable piece forced to move, exposing lesser piece behind
- **Discovered Attacks**: Moving one piece reveals attack from another piece behind it
- **Double Attacks**: Simultaneously threatening two targets with different pieces
- **Removal of Defender**: Eliminate or deflect piece protecting key square/piece
- **Overloading**: Force opponent's piece to defend too many things at once
- **Back Rank Threats**: Exploit weak back rank with rook/queen invasions

**Phase-Specific Strategy ({game_phase.upper()}):**
"""
        
        # Add phase-specific guidance
        if game_phase == "opening":
            prompt += """- Prioritize development over material gains unless clearly winning
- Fight for the center with pawns (e4, d4 or e5, d5)
- Castle early (within 10 moves) to ensure king safety
- Develop knights before bishops (knights to f3/c3 or f6/c6)
- Avoid moving same piece twice unless necessary
- Don't bring queen out too early - she can be attacked
"""
        elif game_phase == "middlegame":
            prompt += """- Look for tactical opportunities (forks, pins, skewers)
- Create threats and attacks on opponent's weaknesses
- Improve worst-placed piece or reposition for better coordination
- Control open files with rooks, place them on 7th rank if possible
- Target weak pawns and squares in opponent's camp
- Calculate forcing moves (checks, captures, threats) carefully
"""
        else:  # endgame
            prompt += """- Activate your king - he becomes a strong piece in endgame
- Create passed pawns and push them toward promotion
- Cut off opponent's king from stopping your pawns
- Rook behind passed pawns (yours or opponent's)
- Simplify when ahead in material, complicate when behind
- Know basic checkmate patterns (K+Q vs K, K+R vs K)
"""
        
        # Add few-shot examples based on position type
        prompt += "\n**EXAMPLES OF STRONG MOVE SELECTION:**\n"
        prompt += self._get_few_shot_examples(position_type, personality)
        
        # Add current position information
        prompt += f"""

=== CURRENT POSITION ===
FEN: {board_state.fen}
You are playing as: {board_state.current_player.upper()}
Move number: {move_count // 2 + 1}
Game phase: {game_phase.upper()}
"""
        
        if game_history:
            recent_moves = game_history[-10:] if len(game_history) > 10 else game_history
            prompt += f"Recent moves: {' '.join(recent_moves)}\n"
        
        if board_state.is_check:
            prompt += "\n⚠️ **YOU ARE IN CHECK!** You must move out of check immediately.\n"
        
        prompt += f"""
Legal moves available: {', '.join(legal_moves)}

=== YOUR TASK ===
Analyze the position using the framework above. Consider:
1. Are there immediate tactical opportunities (checks, captures, threats)?
2. What is the most important piece to develop or improve?
3. Can you control key central squares or open files?
4. Is your king safe? Should you castle or improve king safety?
5. What is your opponent's biggest threat? Should you defend or counterattack?

Choose the BEST move from the legal moves list that aligns with your {personality} style.
Respond with ONLY the move in UCI notation (e.g., 'e2e4' or 'e7e8q' for promotion).
Do not include any explanation, reasoning, or additional text.

Your move:"""
        
        return prompt
    
    def _determine_game_phase(self, move_count: int, fen: str) -> str:
        """Determine game phase based on move count and position."""
        if move_count < 20:
            return "opening"
        
        # Count major pieces to detect endgame
        piece_counts = fen.split()[0].replace('/', '')
        queens = piece_counts.count('Q') + piece_counts.count('q')
        rooks = piece_counts.count('R') + piece_counts.count('r')
        minor_pieces = (piece_counts.count('N') + piece_counts.count('n') + 
                       piece_counts.count('B') + piece_counts.count('b'))
        
        # Endgame if queens off and few pieces
        if queens == 0 and (rooks + minor_pieces) <= 4:
            return "endgame"
        # Endgame if both sides reduced material significantly
        if queens <= 1 and (rooks + minor_pieces) <= 6:
            return "endgame"
        
        return "middlegame"
    
    def _analyze_position_type(self, board_state: BoardState, legal_moves: List[str]) -> str:
        """Analyze position to determine type for conditional examples."""
        # Check for checks (tactical)
        if board_state.is_check:
            return "tactical"
        
        # Check for many captures available (tactical position)
        capture_moves = [m for m in legal_moves if 'x' in m or 
                        any(m.endswith(p) for p in ['q', 'r', 'n', 'b'])]
        if len(capture_moves) > 3:
            return "tactical"
        
        # Early game (positional development)
        fen_parts = board_state.fen.split()
        if fen_parts[0].count('.') + fen_parts[0].count('/') > 40:  # Many empty squares
            return "development"
        
        # Default to positional
        return "positional"
    
    def _get_few_shot_examples(self, position_type: str, personality: str) -> str:
        """Return few-shot examples based on position type and personality."""
        examples = ""
        
        if position_type == "tactical":
            examples += """
**Example 1 - Knight Fork:**
Position: White knight on e5, Black king on e7, Black rook on c7
Legal moves include: e5c6, e5d7, e5f7, ...
Best move: e5d7 (knight fork - attacks both king and rook, wins the rook after king moves)

**Example 2 - Discovered Attack:**
Position: White bishop on b2 pinning Black queen on e5 to king on h8, White knight on d4
Legal moves include: d4f5, d4e6, d4c6, ...
Best move: d4f5 (knight moves with check, and bishop still attacks pinned queen - wins queen)

**Example 3 - Back Rank Mate Threat:**
Position: White rook on d1, Black king on g8 trapped by own pawns on f7, g7, h7
Legal moves include: d1d8, d1d7, a2a3, ...
Best move: d1d8 (rook to 8th rank delivers checkmate - king has no escape)
"""
        
        elif position_type == "development":
            examples += """
**Example 1 - Central Pawn Development:**
Position: Opening, White to move, e2 pawn can advance
Legal moves include: e2e4, e2e3, d2d4, g1f3, ...
Best move: e2e4 (controls center squares d5 and f5, opens diagonals for bishop and queen)

**Example 2 - Knight Development:**
Position: Early opening, center pawns placed, knights still on starting squares
Legal moves include: g1f3, g1h3, b1c3, b1a3, ...
Best move: g1f3 (develops knight to natural square, controls center, prepares castling)

**Example 3 - Castling for King Safety:**
Position: Middlegame, king still on e1, pieces developed, path clear to castle
Legal moves include: e1g1, f1e2, h1g1, d2d4, ...
Best move: e1g1 (castles kingside - improves king safety and connects rooks)
"""
        
        else:  # positional
            examples += """
**Example 1 - Rook to Open File:**
Position: Open d-file, White rook on a1, no pieces blocking d-file
Legal moves include: a1d1, a1b1, a1c1, f3d4, ...
Best move: a1d1 (places rook on open file, controls key central file, pressures d7 pawn)

**Example 2 - Improving Worst Piece:**
Position: White knight passively placed on a3, excellent outpost on e5 available
Legal moves include: a3b5, a3c4, a3c2, a3b1, ...
Best move: a3c4 (improves knight toward center, prepares to reach e5 outpost next move)

**Example 3 - Creating Passed Pawn:**
Position: White pawns on a4 and b5, Black pawn on a5, move b5b6 available
Legal moves include: b5b6, b5a6, a4b5, f3e5, ...
Best move: b5b6 (creates dangerous passed pawn, forces opponent to deal with promotion threat)
"""
        
        # Add personality-specific emphasis
        if personality == "aggressive":
            examples += "\n*Prioritize forcing moves, attacks, and initiative-seizing moves like these examples.*"
        elif personality == "defensive":
            examples += "\n*Learn from these examples but ensure king safety and piece security first.*"
        elif personality == "tactical":
            examples += "\n*These tactical patterns are your bread and butter - spot them relentlessly.*"
        
        return examples
    
    def _extract_move(self, result: Any, legal_moves: List[str]) -> Optional[str]:
        """Extract and validate move from agent result.
        
        Args:
            result: Agent result (can be string or complex object)
            legal_moves: List of legal moves for validation
            
        Returns:
            Valid move in UCI notation or None
        """
        # Convert result to string
        result_str = str(result).strip().lower()
        
        # Clean up code blocks and XML-like tags
        import re
        # Remove <code> tags and </code> tags
        result_str = re.sub(r'</?code>', '', result_str)
        # Remove markdown code blocks
        result_str = re.sub(r'```\w*\n?', '', result_str)
        # Remove "thoughts:" prefix if present
        result_str = re.sub(r'thoughts:.*?(?=\n|$)', '', result_str, flags=re.IGNORECASE)
        
        # Try to find a legal move in the result (exact match)
        for move in legal_moves:
            # Check if the move appears as a standalone word
            if re.search(r'\b' + re.escape(move.lower()) + r'\b', result_str):
                return move
        
        # Try extracting just the move notation
        # Look for patterns like e2e4, e7e8q, etc.
        move_pattern = r'\b([a-h][1-8][a-h][1-8][qrbn]?)\b'
        matches = re.findall(move_pattern, result_str)
        
        for match in matches:
            if match in legal_moves:
                return match
        
        return None
    
    def remove_agent(self, agent_id: str) -> bool:
        """Remove an agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            True if agent was removed, False if not found
        """
        if agent_id in self.agents:
            del self.agents[agent_id]
            del self.configs[agent_id]
            logger.info("agent_removed", agent_id=agent_id)
            return True
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent manager statistics.
        
        Returns:
            Dictionary with statistics
        """
        return {
            "total_agents": len(self.agents),
            "agents": [
                {
                    "agent_id": config.agent_id,
                    "model": config.model_name,
                    "personality": config.personality,
                }
                for config in self.configs.values()
            ],
        }
