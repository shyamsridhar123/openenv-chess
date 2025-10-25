# Stockfish Evaluation & Dynamic Prompting Features

## Overview

Two major enhancements have been added to improve agent chess play quality:

1. **Stockfish Integration** - Move quality evaluation using the Stockfish chess engine
2. **Dynamic Prompting** - Context-aware prompts that adapt to game phase and position type

---

## 1. Stockfish Move Evaluation

### Features

- **Centipawn Loss Tracking**: Measures how much each move deviates from optimal play
- **Move Quality Classification**: 
  - Excellent (< 10cp loss)
  - Good (10-50cp loss)
  - Inaccuracy (50-100cp loss)
  - Mistake (100-300cp loss)
  - Blunder (> 300cp loss)
- **Best Move Comparison**: Identifies if agent's move matches Stockfish recommendation
- **Tactical Accuracy**: Percentage of moves that are not mistakes or blunders

### Installation

```bash
# Ubuntu/Debian
sudo apt-get install stockfish

# macOS with Homebrew
brew install stockfish

# Or download from https://stockfishchess.org/download/
```

### Usage

#### Programmatic

```python
from src.utils.stockfish_evaluator import get_evaluator
import chess

# Get evaluator instance
evaluator = get_evaluator()

# Check if available
if evaluator.is_available():
    # Evaluate position
    board = chess.Board()
    eval_score = evaluator.evaluate_position(board)  # Returns centipawns
    
    # Get best move
    best_move = evaluator.get_best_move(board)
    
    # Evaluate move quality
    move = chess.Move.from_uci("e2e4")
    evaluation = evaluator.evaluate_move(board, move)
    # Returns: {
    #     "centipawn_loss": 0.0,
    #     "is_best_move": True,
    #     "best_move_uci": "e2e4",
    #     "eval_before": 25,
    #     "eval_after": -25,
    #     "quality": "excellent"
    # }
```

#### API Endpoints

**Check Status:**
```bash
GET /api/v1/evaluate/status

Response:
{
  "available": true,
  "stockfish_path": "/usr/bin/stockfish",
  "depth": 15,
  "time_limit": 0.1
}
```

**Evaluate Position:**
```bash
POST /api/v1/evaluate/position
Content-Type: application/json

{
  "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
  "depth": 15
}

Response:
{
  "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
  "evaluation": 25,  // centipawns
  "best_move": "e2e4",
  "available": true
}
```

**Evaluate Move:**
```bash
POST /api/v1/evaluate/move
Content-Type: application/json

{
  "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
  "move": "e2e4"
}

Response:
{
  "move": "e2e4",
  "evaluation": {
    "centipawn_loss": 0.0,
    "is_best_move": true,
    "best_move_uci": "e2e4",
    "eval_before": 25,
    "eval_after": -25,
    "quality": "excellent"
  },
  "available": true
}
```

### AgentStats Enhancement

Agent statistics now track move quality:

```python
from src.models.agent import AgentStats

stats = AgentStats(agent_id="white_tactical")

# Record move evaluation
stats.record_move_evaluation(
    centipawn_loss=15.0,
    is_best_move=False
)

# Get comprehensive stats
stats_dict = stats.to_dict()
# Includes:
# - average_centipawn_loss: 15.0
# - blunders: 0
# - mistakes: 0
# - inaccuracies: 0
# - excellent_moves: 1
# - blunder_rate: 0.0
# - tactical_accuracy: 100.0
# - best_move_rate: 0.0
```

### Game Orchestrator Integration

Evaluation is automatically integrated when running games:

```python
from src.game_manager.game_orchestrator import GameOrchestrator

orchestrator = GameOrchestrator(
    agent_manager=agent_mgr,
    enable_evaluation=True  # Enable Stockfish evaluation
)

# Run game - evaluations logged automatically
result = await orchestrator.run_game(env, white_id, black_id)

# Or step-by-step with evaluation in response
step_result = await orchestrator.run_game_step(env, agent_id)
# Returns evaluation data if available:
# {
#     "move": "e2e4",
#     "evaluation": {...},  // Stockfish analysis
#     ...
# }
```

---

## 2. Dynamic Prompting System

### Features

Prompts automatically adapt based on:

1. **Game Phase Detection**
   - Opening (< 20 moves): Focus on development, center control, castling
   - Middlegame (20-60 moves): Tactical opportunities, attacks, piece improvement
   - Endgame (60+ moves or reduced material): King activation, passed pawns, simplification

2. **Position Type Analysis**
   - Tactical: Checks, many captures available → tactical examples
   - Development: Early game, many empty squares → development examples
   - Positional: Default → positional play examples

3. **Situation-Specific Guidance**
   - Check warnings
   - Checkmate threats
   - Material imbalances

### Prompt Structure

Enhanced prompts include (200-300 words):

1. **Chess Evaluation Framework**
   - 6 Fundamental Principles (material, center control, development, king safety, pawn structure, piece activity)
   - 8 Tactical Patterns (forks, pins, skewers, discovered attacks, etc.)

2. **Phase-Specific Strategy**
   - Opening: "Prioritize development over material gains..."
   - Middlegame: "Look for tactical opportunities..."
   - Endgame: "Activate your king..."

3. **Few-Shot Examples** (3 per position type)
   - Knight fork example
   - Discovered attack example
   - Back rank mate threat
   - (Conditional based on position type)

4. **Current Position Analysis**
   - FEN notation
   - Player color
   - Move number and game phase
   - Recent move history
   - Check/checkmate warnings

5. **Decision Framework**
   - 5-point checklist for move selection
   - Personality-aligned guidance

### Example Usage

```python
from src.agents.agent_manager import ChessAgentManager

agent_mgr = ChessAgentManager()

# Prompt automatically adapts
prompt = agent_mgr._build_move_prompt(
    board_state=board_state,
    legal_moves=legal_moves,
    game_history=game_history,
    personality="aggressive"  # Affects emphasis and examples
)

# Prompt includes:
# - Phase-specific advice (automatically detected)
# - Relevant few-shot examples (conditionally added)
# - Check warnings (if applicable)
# - Personality-tuned guidance
```

### Prompt Length

- **Before**: ~50 words (basic move request)
- **After**: ~280 words (comprehensive chess guidance)
- Includes concrete examples and strategic frameworks

### Personalities

Each personality gets tailored emphasis:

- **Aggressive**: "Prioritize forcing moves, attacks, and initiative-seizing moves..."
- **Defensive**: "Learn from these examples but ensure king safety first..."
- **Tactical**: "These tactical patterns are your bread and butter..."
- **Positional**: Standard strategic emphasis
- **Balanced**: Adaptive based on position

---

## Testing

Run comprehensive test suite:

```bash
python test_evaluation.py
```

Tests cover:
- ✅ Stockfish evaluator initialization
- ✅ Position evaluation
- ✅ Move quality assessment
- ✅ Dynamic prompt generation
- ✅ Game phase detection
- ✅ Position type analysis
- ✅ API endpoints

---

## Performance Considerations

### Stockfish Evaluation

- **CPU Impact**: Minimal with default settings (depth=15, time=0.1s)
- **Optional**: Evaluation gracefully degrades if Stockfish unavailable
- **Configurable**: Adjust depth/time limit for accuracy vs. speed tradeoff

```python
evaluator = StockfishEvaluator(
    depth=20,         # Deeper = more accurate, slower
    time_limit=0.5,   # Longer = more thorough, slower
)
```

### Prompt Size

- Prompt length increased from ~50 to ~280 words
- LLM processing time impact: negligible with modern models
- Token cost: ~350 tokens per move (vs ~70 before)
- **Value**: Significantly improved move quality justifies cost

---

## Configuration

Disable evaluation if Stockfish unavailable:

```python
orchestrator = GameOrchestrator(
    agent_manager=agent_mgr,
    enable_evaluation=False  # Disable Stockfish integration
)
```

Adjust evaluation parameters:

```python
from src.utils.stockfish_evaluator import StockfishEvaluator

evaluator = StockfishEvaluator(
    stockfish_path="/custom/path/to/stockfish",
    depth=20,           # Default: 15
    time_limit=0.5,     # Default: 0.1
)
```

---

## Future Enhancements

Potential additions:

1. **Move Suggestion**: Include Stockfish's top 3 moves in prompt when agent struggles
2. **Adaptive Depth**: Increase depth for critical positions (checks, low material)
3. **Opening Book**: Integrate ECO opening database for opening phase
4. **Position Evaluation in Prompt**: Include current eval score to guide decision-making
5. **Historical Analysis**: Track agent improvement over time via eval metrics
6. **Multi-PV Analysis**: Show multiple good continuations for learning

---

## Troubleshooting

**Stockfish not found:**
```bash
# Install stockfish first
sudo apt-get install stockfish  # or brew install stockfish

# Verify installation
which stockfish
stockfish --help
```

**Evaluation too slow:**
```python
# Reduce depth or time limit
evaluator = StockfishEvaluator(depth=10, time_limit=0.05)
```

**Memory issues:**
```python
# Close evaluator when done
evaluator.close()

# Or use context manager
with StockfishEvaluator() as eval:
    result = eval.evaluate_position(board)
```

---

## References

- [Stockfish Chess Engine](https://stockfishchess.org/)
- [python-chess Documentation](https://python-chess.readthedocs.io/)
- [Centipawn Explanation](https://en.wikipedia.org/wiki/Chess_piece_relative_value)
