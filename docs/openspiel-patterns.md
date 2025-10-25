# OpenSpiel Environment Pattern Study

**Date**: 2025-10-25  
**Purpose**: Study `openenv/openspiel_env` patterns before implementing ChessOpenEnv  
**Repository**: https://github.com/facebookresearch/OpenEnv (openspiel examples)

## Key Patterns Identified

### 1. Game State Representation

**Pattern**: OpenSpiel environments use observation dictionaries with:
- `state`: Current game state (typically a tensor or string representation)
- `legal_actions`: List of legal moves available
- `current_player`: Which player's turn it is
- `is_terminal`: Boolean indicating game end

**Application to Chess**:
```python
observation = {
    "board_state": {
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "board_tensor": np.array([8, 8, 12]),  # 8x8 board, 12 piece types
    },
    "legal_moves": ["e2e4", "d2d4", "g1f3", ...],  # UCI notation
    "current_player": "white",
    "is_terminal": False
}
```

### 2. Reward Function Design for Turn-Based Games

**Pattern**: OpenSpiel uses:
- **Zero-sum rewards**: Winner gets +1, loser gets -1, draw is 0
- **Sparse rewards**: Only at terminal states, not intermediate moves
- **Per-player perspective**: Rewards flipped based on player

**Application to Chess**:
```python
def _get_reward(self, game_result):
    """Return reward from current player's perspective"""
    if game_result == "1-0":  # White wins
        return 1.0 if self.current_player == "white" else -1.0
    elif game_result == "0-1":  # Black wins
        return 1.0 if self.current_player == "black" else -1.0
    elif game_result in ["1/2-1/2", "draw"]:
        return 0.0
    else:
        return 0.0  # Game not finished
```

### 3. Multi-Player Coordination Patterns

**Pattern**: OpenSpiel handles turn-taking with:
- `current_player` property tracking whose turn it is
- `step()` method validates action is from correct player
- Agent manager alternates between players
- No simultaneous actions (sequential turn-based)

**Application to Chess**:
```python
def step(self, action: str):
    """Execute one move"""
    # Validate it's the correct player's turn
    if not self._is_current_players_turn():
        raise ValueError(f"Not {self.current_player}'s turn")
    
    # Apply move
    self.board.push_uci(action)
    
    # Toggle player
    self.current_player = "black" if self.current_player == "white" else "white"
    
    # Return observation
    return self._get_observation(), reward, terminated, truncated, info
```

### 4. Terminal State Detection

**Pattern**: OpenSpiel checks for:
- **Win conditions**: Checkmate, resignation
- **Draw conditions**: Stalemate, insufficient material, 50-move rule, threefold repetition
- **Truncation conditions**: Move limit (optional)

**Application to Chess**:
```python
def _is_terminal(self):
    """Check if game has ended"""
    # Checkmate or stalemate
    if self.board.is_checkmate():
        return True, "checkmate"
    if self.board.is_stalemate():
        return True, "stalemate"
    
    # Draw conditions
    if self.board.is_insufficient_material():
        return True, "insufficient_material"
    if self.board.is_seventyfive_moves():  # 50-move rule
        return True, "fifty_move_rule"
    if self.board.is_fivefold_repetition():  # Threefold repetition
        return True, "threefold_repetition"
    
    # Game ongoing
    return False, None
```

### 5. Action Space Specification

**Pattern**: OpenSpiel uses:
- **Discrete action spaces**: Integer indices mapping to moves
- **String actions**: For human-readable formats (e.g., "e2e4")
- **Validation**: Check action is in legal_actions before applying

**Application to Chess**:
```python
# Use UCI notation (Universal Chess Interface) for actions
# Examples: "e2e4", "e7e5", "e1g1" (castling), "e7e8q" (promotion)

def step(self, action: str):
    # Validate action format
    if not self._is_valid_uci(action):
        raise ValueError(f"Invalid UCI format: {action}")
    
    # Validate action is legal
    if action not in self._get_legal_moves():
        raise ValueError(f"Illegal move: {action}")
    
    # Apply move
    self.board.push_uci(action)
```

### 6. Error Handling and Recovery

**Pattern**: OpenSpiel environments handle:
- **Invalid actions**: Raise clear errors, don't silently fail
- **Illegal moves**: Return error immediately
- **Timeouts**: Not handled at environment level (agent responsibility)

**Application to Chess**:
- Environment validates moves but doesn't implement retry logic
- Agent manager handles retries (3 attempts) and timeout fallback
- Clear error messages with context for debugging

## Key Takeaways for ChessOpenEnv Implementation

1. **Use dictionary observations** with FEN, tensor, legal moves
2. **Sparse rewards** only at terminal states (+1/-1/0)
3. **Track current player** and validate turn order
4. **Comprehensive terminal detection** for all chess end conditions
5. **UCI notation** for actions (standard in chess programming)
6. **Raise errors for invalid moves** (don't silently fail)
7. **Keep environment pure** (no retry logic, agent manager handles that)

## References

- OpenEnv OpenSpiel examples: https://github.com/facebookresearch/OpenEnv
- OpenSpiel documentation: https://github.com/deepmind/open_spiel
- python-chess library: https://python-chess.readthedocs.io/
- UCI protocol: https://www.chessprogramming.org/UCI

## Next Steps

- Implement `ChessOpenEnv` class following these patterns (Task T023)
- Use `python-chess` library for move validation and board state
- Test with smolagents to ensure agent compatibility
- Document deviations from OpenSpiel patterns (if any)
