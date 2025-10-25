# Phase 1: Data Model Specification

**Feature**: OpenEnv Multi-Agent Chess Demo  
**Date**: 2025-10-25  
**Status**: Complete

## Overview

This document defines the data entities, their relationships, state transitions, and validation rules for the Chess OpenEnv Multi-Agent System. All entities are designed for in-memory storage with focus on simplicity and educational value.

---

## 1. Core Entities

### 1.1 Game

**Purpose**: Represents a single chess match between two agents from start to completion.

**Attributes**:
| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `game_id` | `str` (UUID) | Yes | Unique identifier for the game | Must be valid UUID4 |
| `board_state` | `BoardState` | Yes | Current chess position | See BoardState entity |
| `move_history` | `List[Move]` | Yes | Chronological list of all moves | Initially empty list |
| `current_turn` | `str` | Yes | Which player's turn | Must be "white" or "black" |
| `status` | `str` | Yes | Current game status | Must be one of: "in_progress", "checkmate", "stalemate", "draw", "resigned", "timeout" |
| `result` | `Optional[str]` | No | Final game outcome | Only set when status != "in_progress". Values: "white_wins", "black_wins", "draw" |
| `started_at` | `datetime` | Yes | Game creation timestamp | ISO 8601 format |
| `ended_at` | `Optional[datetime]` | No | Game completion timestamp | Only set when game ends |
| `last_updated` | `datetime` | Yes | Most recent activity | Updated on every move |

**State Transitions**:
```
[Created] → in_progress (on reset)
    ↓
in_progress → checkmate (when king captured)
in_progress → stalemate (no legal moves, not in check)
in_progress → draw (50-move rule, threefold repetition, insufficient material)
in_progress → resigned (agent error/timeout fallback)
    ↓
[Terminal States: checkmate, stalemate, draw, resigned]
```

**Validation Rules**:
- `game_id` must be unique across all active games
- `current_turn` alternates between "white" and "black"
- `move_history` length must match turn number
- `ended_at` must be after `started_at` when set
- Terminal states cannot transition back to "in_progress"

**Example**:
```python
{
    "game_id": "550e8400-e29b-41d4-a716-446655440000",
    "board_state": { /* BoardState object */ },
    "move_history": [
        {"from_square": "e2", "to_square": "e4", "player": "white", "timestamp": "2025-10-25T10:00:00Z"},
        {"from_square": "e7", "to_square": "e5", "player": "black", "timestamp": "2025-10-25T10:00:35Z"}
    ],
    "current_turn": "white",
    "status": "in_progress",
    "result": null,
    "started_at": "2025-10-25T10:00:00Z",
    "ended_at": null,
    "last_updated": "2025-10-25T10:00:35Z"
}
```

---

### 1.2 BoardState

**Purpose**: Represents the current chess position including piece locations, castling rights, and move counts.

**Attributes**:
| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `fen` | `str` | Yes | Forsyth-Edwards Notation | Must be valid FEN string |
| `board_tensor` | `np.ndarray` | Yes | 8×8×12 tensor representation | Shape (8, 8, 12), dtype uint8, values 0-12 |
| `legal_moves` | `List[str]` | Yes | All valid moves in UCI notation | Each move matches pattern `[a-h][1-8][a-h][1-8][qrbn]?` |
| `is_check` | `bool` | Yes | King under attack | Computed from position |
| `is_checkmate` | `bool` | Yes | Game-ending check | True only if check + no legal moves |
| `is_stalemate` | `bool` | Yes | Game-ending draw | True only if !check + no legal moves |
| `castling_rights` | `str` | Yes | Available castling options | Subset of "KQkq" (K=white kingside, Q=white queenside, k=black kingside, q=black queenside) |
| `en_passant_square` | `Optional[str]` | No | Square where en passant is legal | Must be rank 3 or 6, format `[a-h][36]` |
| `halfmove_clock` | `int` | Yes | Moves since pawn/capture | For 50-move rule, 0-100 |
| `fullmove_number` | `int` | Yes | Full move count | Starts at 1, increments after black's turn |

**FEN Format**:
```
rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1
│                                           │ │    │ │ │
│                                           │ │    │ │ └─ Fullmove number
│                                           │ │    │ └─── Halfmove clock
│                                           │ │    └───── En passant square
│                                           │ └────────── Castling rights
│                                           └──────────── Active player (w/b)
└────────────────────────────────────────────────────── Piece positions
```

**Board Tensor Encoding**:
- **Dimensions**: (8 rows, 8 cols, 12 channels)
- **Channels**: [White: Pawn, Knight, Bishop, Rook, Queen, King | Black: Pawn, Knight, Bishop, Rook, Queen, King]
- **Values**: 1 if piece present, 0 otherwise
- **Example**: White pawn on e2 → tensor[6, 4, 0] = 1

**Validation Rules**:
- FEN must be parseable by python-chess library
- Board tensor must match FEN representation
- `legal_moves` must be non-empty unless game is over
- Exactly one king per color must exist
- `is_checkmate` requires `is_check == True`
- `is_stalemate` requires `is_check == False`
- `halfmove_clock` ≥ 0 and ≤ 100 (enforces 50-move rule)

**Example**:
```python
{
    "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
    "board_tensor": np.array([...]),  # Shape (8, 8, 12)
    "legal_moves": ["a7a6", "a7a5", "b7b6", "b7b5", ...],  # 20 opening moves
    "is_check": false,
    "is_checkmate": false,
    "is_stalemate": false,
    "castling_rights": "KQkq",
    "en_passant_square": "e3",
    "halfmove_clock": 0,
    "fullmove_number": 1
}
```

---

### 1.3 Move

**Purpose**: Represents a single chess action by an agent.

**Attributes**:
| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `from_square` | `str` | Yes | Starting square | Format `[a-h][1-8]` |
| `to_square` | `str` | Yes | Destination square | Format `[a-h][1-8]` |
| `piece` | `str` | Yes | Piece that moved | One of: "pawn", "knight", "bishop", "rook", "queen", "king" |
| `player` | `str` | Yes | Which agent made the move | Must be "white" or "black" |
| `uci_notation` | `str` | Yes | Standard move notation | Format `[a-h][1-8][a-h][1-8][qrbn]?` |
| `san_notation` | `str` | Yes | Algebraic notation | Examples: "e4", "Nf3", "O-O", "exd5" |
| `is_capture` | `bool` | Yes | Whether move captured a piece | Includes en passant captures |
| `is_castling` | `bool` | Yes | Whether move was castling | True for O-O or O-O-O |
| `is_promotion` | `bool` | Yes | Whether pawn promoted | True if pawn reached rank 1/8 |
| `promotion_piece` | `Optional[str]` | No | Piece promoted to | Required if is_promotion=True. One of: "queen", "rook", "bishop", "knight" |
| `timestamp` | `datetime` | Yes | When move was made | ISO 8601 format |
| `thinking_time` | `float` | Yes | Agent decision time (seconds) | Must be ≥ 0, typically < 30 |

**Validation Rules**:
- `from_square` and `to_square` must be different
- `from_square` must contain a piece of the moving `player`
- `to_square` must not contain a piece of the same color (unless castling)
- `uci_notation` format: `{from_square}{to_square}{promotion?}`
- `promotion_piece` required if and only if `is_promotion == True`
- `is_castling` only valid for king moves (e1g1, e1c1, e8g8, e8c8)

**Example**:
```python
{
    "from_square": "e2",
    "to_square": "e4",
    "piece": "pawn",
    "player": "white",
    "uci_notation": "e2e4",
    "san_notation": "e4",
    "is_capture": false,
    "is_castling": false,
    "is_promotion": false,
    "promotion_piece": null,
    "timestamp": "2025-10-25T10:00:00Z",
    "thinking_time": 2.34
}
```

---

### 1.4 Agent

**Purpose**: Represents an AI player with configuration and performance tracking.

**Attributes**:
| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `agent_id` | `str` | Yes | Unique identifier | Typically "white" or "black" |
| `name` | `str` | Yes | Display name | Max 50 characters |
| `personality` | `str` | Yes | Playing style description | Examples: "aggressive", "defensive", "balanced" |
| `model_name` | `str` | Yes | LLM model identifier | HuggingFace model ID |
| `system_prompt` | `str` | Yes | Agent instructions | Plain text, describes chess strategy |
| `temperature` | `float` | Yes | LLM sampling temperature | Range 0.0-2.0, typically 0.7 |
| `max_tokens` | `int` | Yes | Max response length | Typically 2048 |
| `timeout_seconds` | `int` | Yes | Move decision timeout | Typically 30 |
| `stats` | `AgentStats` | Yes | Performance metrics | See AgentStats entity |

**Validation Rules**:
- `agent_id` must be unique per game
- `temperature` must be ≥ 0.0 and ≤ 2.0
- `max_tokens` must be > 0
- `timeout_seconds` must be > 0
- `model_name` should be a valid HuggingFace model ID

**Example**:
```python
{
    "agent_id": "white",
    "name": "Aggressive Alpha",
    "personality": "aggressive",
    "model_name": "Qwen/Qwen2.5-32B-Instruct",
    "system_prompt": "You are an aggressive chess player. Prioritize attacking moves, control the center, develop pieces quickly. Always look for tactical opportunities.",
    "temperature": 0.7,
    "max_tokens": 2048,
    "timeout_seconds": 30,
    "stats": { /* AgentStats object */ }
}
```

---

### 1.5 AgentStats

**Purpose**: Tracks agent performance metrics across games.

**Attributes**:
| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `games_played` | `int` | Yes | Total games | Must be ≥ 0 |
| `games_won` | `int` | Yes | Games with victory | Must be ≤ games_played |
| `games_lost` | `int` | Yes | Games with defeat | Must be ≤ games_played |
| `games_drawn` | `int` | Yes | Games with draw | Must be ≤ games_played |
| `total_moves` | `int` | Yes | Sum of all moves made | Must be ≥ 0 |
| `average_thinking_time` | `float` | Yes | Mean decision time (seconds) | Must be ≥ 0 |
| `illegal_moves_attempted` | `int` | Yes | Count of invalid moves | Must be ≥ 0 |
| `timeouts` | `int` | Yes | Count of timeout failures | Must be ≥ 0 |

**Validation Rules**:
- `games_won + games_lost + games_drawn` must equal `games_played`
- All counts must be non-negative integers
- `average_thinking_time` computed as `total_thinking_time / total_moves`

**Example**:
```python
{
    "games_played": 10,
    "games_won": 6,
    "games_lost": 3,
    "games_drawn": 1,
    "total_moves": 245,
    "average_thinking_time": 3.42,
    "illegal_moves_attempted": 2,
    "timeouts": 0
}
```

---

### 1.6 GameSession

**Purpose**: Represents the runtime context for an active game including WebSocket connections.

**Attributes**:
| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `session_id` | `str` (UUID) | Yes | Unique session identifier | Must be valid UUID4 |
| `game_id` | `str` (UUID) | Yes | Associated game | Must reference valid Game |
| `websocket_connections` | `List[WebSocket]` | Yes | Active client connections | FastAPI WebSocket objects |
| `agent_white` | `Agent` | Yes | White player agent | See Agent entity |
| `agent_black` | `Agent` | Yes | Black player agent | See Agent entity |
| `created_at` | `datetime` | Yes | Session start time | ISO 8601 format |
| `is_active` | `bool` | Yes | Whether session is live | False after game ends or cleanup |

**Validation Rules**:
- `session_id` must be unique across all sessions
- `game_id` must reference an existing Game entity
- `websocket_connections` can be empty (polling clients)
- `agent_white` and `agent_black` must have different `agent_id` values
- `is_active` set to False triggers cleanup

**Example**:
```python
{
    "session_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "game_id": "550e8400-e29b-41d4-a716-446655440000",
    "websocket_connections": [<WebSocket object>, <WebSocket object>],
    "agent_white": { /* Agent object */ },
    "agent_black": { /* Agent object */ },
    "created_at": "2025-10-25T10:00:00Z",
    "is_active": true
}
```

---

## 2. Entity Relationships

```
GameSession (1) ──────> (1) Game
                              │
                              ├──> (1) BoardState
                              │
                              └──> (0..*) Move
                              
GameSession (1) ──────> (1) Agent (white)
                              └──> (1) AgentStats
                              
GameSession (1) ──────> (1) Agent (black)
                              └──> (1) AgentStats
```

**Relationship Rules**:
- Each `GameSession` has exactly one `Game`
- Each `Game` has exactly one `BoardState` (current position)
- Each `Game` has zero or more `Move` records (history)
- Each `GameSession` has exactly two `Agent` instances (white and black)
- Each `Agent` has exactly one `AgentStats` instance
- Multiple `WebSocket` connections can observe one `GameSession`

---

## 3. State Management Implementation

### 3.1 In-Memory Storage Schema

```python
from typing import Dict
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class StateManager:
    """In-memory storage for game state"""
    
    # Primary storage
    games: Dict[str, Game] = field(default_factory=dict)  # game_id -> Game
    sessions: Dict[str, GameSession] = field(default_factory=dict)  # session_id -> GameSession
    agents: Dict[str, Agent] = field(default_factory=dict)  # agent_id -> Agent
    
    # Configuration
    max_concurrent_games: int = 100
    cleanup_after_hours: int = 24
    
    # Metrics
    total_games_created: int = 0
    total_games_completed: int = 0
    memory_usage_bytes: int = 0
```

### 3.2 CRUD Operations

**Create Game**:
```python
def create_game(self, session_id: str) -> Game:
    """Initialize new game with starting position"""
    if len(self.games) >= self.max_concurrent_games:
        self._cleanup_oldest_game()
    
    game_id = str(uuid.uuid4())
    game = Game(
        game_id=game_id,
        board_state=BoardState.from_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"),
        move_history=[],
        current_turn="white",
        status="in_progress",
        started_at=datetime.utcnow(),
        last_updated=datetime.utcnow()
    )
    
    self.games[game_id] = game
    self.total_games_created += 1
    return game
```

**Read Game**:
```python
def get_game(self, game_id: str) -> Optional[Game]:
    """Retrieve game by ID"""
    return self.games.get(game_id)
```

**Update Game**:
```python
def update_game_state(self, game_id: str, new_board_state: BoardState, move: Move):
    """Apply move to game"""
    game = self.games.get(game_id)
    if not game:
        raise ValueError(f"Game {game_id} not found")
    
    game.board_state = new_board_state
    game.move_history.append(move)
    game.current_turn = "black" if game.current_turn == "white" else "white"
    game.last_updated = datetime.utcnow()
    
    # Check for terminal states
    if new_board_state.is_checkmate:
        game.status = "checkmate"
        game.result = f"{move.player}_wins"
        game.ended_at = datetime.utcnow()
        self.total_games_completed += 1
```

**Delete Game (Cleanup)**:
```python
def cleanup_game(self, game_id: str):
    """Remove game from memory"""
    if game_id in self.games:
        del self.games[game_id]
    
    # Also cleanup associated session
    session_id = self._find_session_by_game(game_id)
    if session_id and session_id in self.sessions:
        del self.sessions[session_id]
```

### 3.3 Cleanup Strategy

**Automatic Cleanup Triggers**:
1. **Game Limit Reached**: When creating game #101, evict oldest completed game
2. **Game Completed**: Mark for cleanup after 1 hour of inactivity
3. **Session Timeout**: Close WebSocket connections after 30 min idle
4. **Memory Threshold**: If total memory > 1.8GB, evict oldest 10%

**LRU Eviction**:
```python
def _cleanup_oldest_game(self):
    """Remove least recently updated game"""
    if not self.games:
        return
    
    oldest_game_id = min(
        self.games.keys(),
        key=lambda gid: self.games[gid].last_updated
    )
    
    self.cleanup_game(oldest_game_id)
    logger.info("cleaned_up_oldest_game", game_id=oldest_game_id)
```

---

## 4. Validation & Constraints

### 4.1 Business Rules

1. **Game Integrity**:
   - Games cannot be modified after reaching terminal state
   - Move history must be append-only (no deletions)
   - Agents must alternate turns (white → black → white → ...)

2. **Chess Rules** (enforced by python-chess):
   - All moves must be legal according to FIDE rules
   - Castling only when conditions met (king/rook unmoved, no check, path clear)
   - En passant only valid for one move after opponent's double pawn push
   - Pawn promotion required when reaching opposite end

3. **Performance Constraints**:
   - Maximum 100 concurrent games
   - Maximum 30-second agent thinking time
   - Board state updates must complete in <10ms
   - WebSocket messages must be < 64KB

4. **Security Constraints**:
   - UCI notation must match regex `^[a-h][1-8][a-h][1-8][qrbn]?$`
   - FEN strings must be validated before parsing
   - Agent prompts must not contain code execution instructions
   - Rate limiting: 100 API requests per minute per IP

### 4.2 Data Integrity Checks

```python
def validate_game_state(game: Game) -> List[str]:
    """Return list of validation errors"""
    errors = []
    
    # Check turn consistency
    if len(game.move_history) % 2 == 0 and game.current_turn != "white":
        errors.append("Turn mismatch: even moves should be white's turn")
    
    # Check move history matches board
    board = chess.Board()
    for move in game.move_history:
        if move.uci_notation not in [m.uci() for m in board.legal_moves]:
            errors.append(f"Illegal move in history: {move.uci_notation}")
        board.push_uci(move.uci_notation)
    
    if board.fen() != game.board_state.fen:
        errors.append("Board state doesn't match move history")
    
    # Check terminal state consistency
    if game.status in ["checkmate", "stalemate", "draw"]:
        if game.result is None:
            errors.append("Terminal game must have result")
        if game.ended_at is None:
            errors.append("Terminal game must have end timestamp")
    
    return errors
```

---

## 5. Example Data Flows

### 5.1 Game Initialization Flow

```
1. Client → POST /reset
2. StateManager.create_game()
   └─> Generate game_id
   └─> Create Game with initial BoardState
   └─> Create GameSession with two Agents
   └─> Store in memory: games[game_id] = game
3. Return observation with FEN, legal_moves, board_tensor
```

### 5.2 Move Execution Flow

```
1. Agent decides move via smolagents
2. Client → POST /step with move="e2e4"
3. Validate UCI format
4. ChessEnv.step(move)
   └─> ChessLogic.is_legal(move)? → Yes
   └─> Apply move to board
   └─> Generate new BoardState
   └─> Create Move record
   └─> StateManager.update_game_state()
5. Broadcast via WebSocket: "move_made" event
6. Return new observation
```

### 5.3 Game Completion Flow

```
1. Agent makes move resulting in checkmate
2. ChessLogic.is_checkmate()? → True
3. Game.status = "checkmate"
4. Game.result = "{player}_wins"
5. Game.ended_at = now()
6. AgentStats updated (winner: +1 win, loser: +1 loss)
7. WebSocket: "game_ended" event
8. Schedule cleanup after 1 hour
```

---

## Data Model Summary

### Entities Defined

1. **Game**: Chess match state and metadata
2. **BoardState**: Current position with FEN, tensor, legal moves
3. **Move**: Individual chess action with notation and timing
4. **Agent**: AI player configuration and personality
5. **AgentStats**: Performance tracking metrics
6. **GameSession**: Runtime context with WebSocket connections

### Storage Strategy

- **Type**: In-memory (Python dictionaries)
- **Capacity**: 100 concurrent games maximum
- **Cleanup**: LRU eviction when limit reached
- **Persistence**: None (ephemeral, lost on restart)

### Validation Approach

- **Format Validation**: Regex for UCI, FEN parsing
- **Business Rules**: python-chess for move legality
- **State Consistency**: Validation checks on state transitions
- **Performance**: <10ms validation overhead per move

---

**Document Status**: Complete  
**Ready for Phase 1 Contracts**: Yes  
**Constitution Compliance**: Simple in-memory model aligns with Principle II (Simplicity First)
