"""Agent models for chess-playing AI agents."""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class AgentConfig:
    """Configuration for an AI agent.
    
    Attributes:
        agent_id: Unique identifier for the agent
        name: Human-readable name
        personality: Agent personality (e.g., 'aggressive', 'defensive', 'balanced')
        model_name: LLM model to use (e.g., 'Qwen/Qwen2.5-7B-Instruct')
        system_prompt: System prompt defining agent behavior
        temperature: Sampling temperature (0.0-1.0)
        max_tokens: Maximum tokens to generate
        timeout: Move decision timeout in seconds
        max_retries: Maximum retries for illegal moves
        color: 'white' or 'black'
        additional_params: Additional model parameters
    """
    
    agent_id: str
    name: str
    personality: str = "balanced"
    model_name: str = "Qwen/Qwen2.5-7B-Instruct"
    system_prompt: str = "You are a chess-playing AI agent."
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 30
    max_retries: int = 3
    color: str = "white"
    additional_params: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert AgentConfig to dictionary."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "personality": self.personality,
            "model_name": self.model_name,
            "system_prompt": self.system_prompt,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "color": self.color,
            "additional_params": self.additional_params,
        }


@dataclass
class AgentStats:
    """Statistics for an agent's performance.
    
    Attributes:
        agent_id: Agent identifier
        games_played: Total games played
        games_won: Total games won
        games_lost: Total games lost
        games_drawn: Total games drawn
        total_moves: Total moves made
        illegal_moves: Total illegal moves attempted
        timeouts: Number of move timeouts
        average_thinking_time: Average time per move (seconds)
        total_thinking_time: Total thinking time (seconds)
        win_rate: Win percentage (0-100)
        longest_game: Longest game in moves
        shortest_game: Shortest game in moves
        
        # Stockfish Evaluation Metrics
        total_centipawn_loss: Total centipawn loss across all moves
        average_centipawn_loss: Average centipawn loss per move
        blunders: Number of blunders (loss > 300cp)
        mistakes: Number of mistakes (loss 100-300cp)
        inaccuracies: Number of inaccuracies (loss 50-100cp)
        excellent_moves: Number of excellent moves (loss < 10cp)
        blunder_rate: Percentage of moves that are blunders
        tactical_accuracy: Percentage of tactically accurate moves
        best_move_rate: Percentage of moves matching Stockfish best move
        evaluation_history: List of evaluations per move
    """
    
    agent_id: str
    games_played: int = 0
    games_won: int = 0
    games_lost: int = 0
    games_drawn: int = 0
    total_moves: int = 0
    illegal_moves: int = 0
    timeouts: int = 0
    average_thinking_time: float = 0.0
    total_thinking_time: float = 0.0
    win_rate: float = 0.0
    longest_game: int = 0
    shortest_game: Optional[int] = None
    
    # Stockfish Evaluation Metrics
    total_centipawn_loss: float = 0.0
    average_centipawn_loss: float = 0.0
    blunders: int = 0
    mistakes: int = 0
    inaccuracies: int = 0
    excellent_moves: int = 0
    blunder_rate: float = 0.0
    tactical_accuracy: float = 0.0
    best_move_rate: float = 0.0
    best_moves_played: int = 0
    evaluation_history: list = field(default_factory=list)
    
    def update_after_game(self, won: bool, lost: bool, drawn: bool, moves: int, thinking_time: float) -> None:
        """Update stats after a game completes.
        
        Args:
            won: Whether agent won
            lost: Whether agent lost
            drawn: Whether game was drawn
            moves: Number of moves made in game
            thinking_time: Total thinking time for this game
        """
        self.games_played += 1
        if won:
            self.games_won += 1
        elif lost:
            self.games_lost += 1
        elif drawn:
            self.games_drawn += 1
        
        self.total_moves += moves
        self.total_thinking_time += thinking_time
        self.average_thinking_time = self.total_thinking_time / self.total_moves if self.total_moves > 0 else 0.0
        self.win_rate = (self.games_won / self.games_played * 100) if self.games_played > 0 else 0.0
        
        # Update longest/shortest game
        if moves > self.longest_game:
            self.longest_game = moves
        if self.shortest_game is None or moves < self.shortest_game:
            self.shortest_game = moves
    
    def record_move_evaluation(self, centipawn_loss: float, is_best_move: bool) -> None:
        """Record Stockfish evaluation for a move.
        
        Args:
            centipawn_loss: Centipawn loss for the move (0 = perfect)
            is_best_move: Whether this was Stockfish's top choice
        """
        self.total_centipawn_loss += centipawn_loss
        evaluated_moves = len(self.evaluation_history) + 1
        self.average_centipawn_loss = self.total_centipawn_loss / evaluated_moves
        
        # Categorize move quality
        if centipawn_loss > 300:
            self.blunders += 1
        elif centipawn_loss > 100:
            self.mistakes += 1
        elif centipawn_loss > 50:
            self.inaccuracies += 1
        elif centipawn_loss < 10:
            self.excellent_moves += 1
        
        if is_best_move:
            self.best_moves_played += 1
        
        # Calculate rates
        total_evaluated = evaluated_moves
        self.blunder_rate = (self.blunders / total_evaluated * 100) if total_evaluated > 0 else 0.0
        self.best_move_rate = (self.best_moves_played / total_evaluated * 100) if total_evaluated > 0 else 0.0
        
        # Tactical accuracy: % of moves that are not mistakes or blunders
        good_moves = total_evaluated - (self.mistakes + self.blunders)
        self.tactical_accuracy = (good_moves / total_evaluated * 100) if total_evaluated > 0 else 0.0
        
        # Store in history
        self.evaluation_history.append({
            "centipawn_loss": round(centipawn_loss, 2),
            "is_best_move": is_best_move
        })
    
    def record_illegal_move(self) -> None:
        """Record an illegal move attempt."""
        self.illegal_moves += 1
    
    def record_timeout(self) -> None:
        """Record a move timeout."""
        self.timeouts += 1
    
    def to_dict(self) -> dict:
        """Convert AgentStats to dictionary."""
        return {
            "agent_id": self.agent_id,
            "games_played": self.games_played,
            "games_won": self.games_won,
            "games_lost": self.games_lost,
            "games_drawn": self.games_drawn,
            "total_moves": self.total_moves,
            "illegal_moves": self.illegal_moves,
            "timeouts": self.timeouts,
            "average_thinking_time": round(self.average_thinking_time, 3),
            "total_thinking_time": round(self.total_thinking_time, 2),
            "win_rate": round(self.win_rate, 2),
            "longest_game": self.longest_game,
            "shortest_game": self.shortest_game,
            # Stockfish metrics
            "average_centipawn_loss": round(self.average_centipawn_loss, 2),
            "blunders": self.blunders,
            "mistakes": self.mistakes,
            "inaccuracies": self.inaccuracies,
            "excellent_moves": self.excellent_moves,
            "blunder_rate": round(self.blunder_rate, 2),
            "tactical_accuracy": round(self.tactical_accuracy, 2),
            "best_move_rate": round(self.best_move_rate, 2),
            "total_evaluated_moves": len(self.evaluation_history),
        }
