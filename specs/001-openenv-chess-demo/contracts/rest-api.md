# REST API Specification

**Feature**: OpenEnv Multi-Agent Chess Demo  
**API Version**: 1.0.0  
**Date**: 2025-10-25  
**Protocol**: HTTP/1.1, JSON over REST

---

## Base URL

```
Development: http://localhost:8000
Production: TBD
```

---

## Authentication

**Type**: None (public demo)  
**Security**: Rate limiting only (100 requests/minute per IP)

---

## OpenAPI 3.0 Specification

### Metadata

```yaml
openapi: 3.0.3
info:
  title: Chess OpenEnv Multi-Agent API
  description: REST API for managing chess games between AI agents using OpenEnv specification
  version: 1.0.0
  contact:
    name: OpenEnv Chess Demo
    
servers:
  - url: http://localhost:8000
    description: Development server

tags:
  - name: game
    description: Game lifecycle operations
  - name: environment
    description: OpenEnv standard endpoints
  - name: monitoring
    description: Health and metrics
```

---

## Core Endpoints

### 1. POST /reset - Initialize New Game

**Purpose**: Create a new chess game and return initial observation

**Request**:
```http
POST /reset HTTP/1.1
Content-Type: application/json

{
  "white_agent": {
    "name": "Aggressive Alpha",
    "personality": "aggressive",
    "model_name": "Qwen/Qwen2.5-32B-Instruct",
    "temperature": 0.7
  },
  "black_agent": {
    "name": "Defensive Delta",
    "personality": "defensive",
    "model_name": "Qwen/Qwen2.5-32B-Instruct",
    "temperature": 0.5
  }
}
```

**Request Schema**:
```yaml
ResetRequest:
  type: object
  required:
    - white_agent
    - black_agent
  properties:
    white_agent:
      $ref: '#/components/schemas/AgentConfig'
    black_agent:
      $ref: '#/components/schemas/AgentConfig'

AgentConfig:
  type: object
  required:
    - name
    - personality
    - model_name
  properties:
    name:
      type: string
      maxLength: 50
      example: "Aggressive Alpha"
    personality:
      type: string
      enum: [aggressive, defensive, balanced, positional]
      example: "aggressive"
    model_name:
      type: string
      example: "Qwen/Qwen2.5-32B-Instruct"
    temperature:
      type: number
      minimum: 0.0
      maximum: 2.0
      default: 0.7
    max_tokens:
      type: integer
      minimum: 256
      maximum: 4096
      default: 2048
    timeout_seconds:
      type: integer
      minimum: 10
      maximum: 60
      default: 30
```

**Response (200 OK)**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "game_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "observation": {
    "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    "board_tensor": [[...]], // 8x8x12 array
    "legal_moves": ["a2a3", "a2a4", "b2b3", ...],
    "current_turn": "white",
    "is_check": false,
    "is_checkmate": false,
    "is_stalemate": false
  },
  "agents": {
    "white": {
      "agent_id": "white",
      "name": "Aggressive Alpha",
      "personality": "aggressive",
      "model_name": "Qwen/Qwen2.5-32B-Instruct"
    },
    "black": {
      "agent_id": "black",
      "name": "Defensive Delta",
      "personality": "defensive",
      "model_name": "Qwen/Qwen2.5-32B-Instruct"
    }
  },
  "metadata": {
    "started_at": "2025-10-25T10:00:00Z",
    "status": "in_progress"
  }
}
```

**Response Schema**:
```yaml
ResetResponse:
  type: object
  required:
    - game_id
    - session_id
    - observation
    - agents
    - metadata
  properties:
    game_id:
      type: string
      format: uuid
    session_id:
      type: string
      format: uuid
    observation:
      $ref: '#/components/schemas/Observation'
    agents:
      type: object
      properties:
        white:
          $ref: '#/components/schemas/Agent'
        black:
          $ref: '#/components/schemas/Agent'
    metadata:
      type: object
      properties:
        started_at:
          type: string
          format: date-time
        status:
          type: string
          enum: [in_progress, checkmate, stalemate, draw, resigned]

Observation:
  type: object
  required:
    - fen
    - board_tensor
    - legal_moves
    - current_turn
    - is_check
    - is_checkmate
    - is_stalemate
  properties:
    fen:
      type: string
      example: "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    board_tensor:
      type: array
      items:
        type: array
        items:
          type: array
          items:
            type: integer
      description: "8x8x12 tensor representing piece positions"
    legal_moves:
      type: array
      items:
        type: string
        pattern: "^[a-h][1-8][a-h][1-8][qrbn]?$"
      example: ["e2e4", "d2d4", "g1f3"]
    current_turn:
      type: string
      enum: [white, black]
    is_check:
      type: boolean
    is_checkmate:
      type: boolean
    is_stalemate:
      type: boolean
```

**Error Responses**:
- `400 Bad Request`: Invalid agent configuration
- `500 Internal Server Error`: Game creation failed
- `503 Service Unavailable`: Maximum concurrent games reached

---

### 2. POST /step - Execute Move

**Purpose**: Apply a move to the game and return updated observation

**Request**:
```http
POST /step HTTP/1.1
Content-Type: application/json

{
  "game_id": "550e8400-e29b-41d4-a716-446655440000",
  "move": "e2e4"
}
```

**Request Schema**:
```yaml
StepRequest:
  type: object
  required:
    - game_id
    - move
  properties:
    game_id:
      type: string
      format: uuid
    move:
      type: string
      pattern: "^[a-h][1-8][a-h][1-8][qrbn]?$"
      example: "e2e4"
      description: "Move in UCI notation"
```

**Response (200 OK)**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "observation": {
    "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
    "board_tensor": [[...]],
    "legal_moves": ["a7a6", "a7a5", "b7b6", ...],
    "current_turn": "black",
    "is_check": false,
    "is_checkmate": false,
    "is_stalemate": false
  },
  "move_result": {
    "from_square": "e2",
    "to_square": "e4",
    "piece": "pawn",
    "player": "white",
    "uci_notation": "e2e4",
    "san_notation": "e4",
    "is_capture": false,
    "is_castling": false,
    "is_promotion": false,
    "timestamp": "2025-10-25T10:00:00Z",
    "thinking_time": 2.34
  },
  "game_state": {
    "status": "in_progress",
    "result": null,
    "move_number": 1,
    "last_updated": "2025-10-25T10:00:00Z"
  },
  "reward": 0.0,
  "terminated": false,
  "truncated": false,
  "info": {
    "captured_piece": null,
    "check_given": false,
    "legal_moves_count": 20
  }
}
```

**Response Schema**:
```yaml
StepResponse:
  type: object
  required:
    - observation
    - move_result
    - game_state
    - reward
    - terminated
    - truncated
    - info
  properties:
    observation:
      $ref: '#/components/schemas/Observation'
    move_result:
      $ref: '#/components/schemas/Move'
    game_state:
      type: object
      properties:
        status:
          type: string
          enum: [in_progress, checkmate, stalemate, draw, resigned]
        result:
          type: string
          nullable: true
          enum: [white_wins, black_wins, draw]
        move_number:
          type: integer
        last_updated:
          type: string
          format: date-time
    reward:
      type: number
      description: "Reward signal (0 for in-progress, 1 for win, -1 for loss, 0 for draw)"
    terminated:
      type: boolean
      description: "True if game ended naturally (checkmate, stalemate, draw)"
    truncated:
      type: boolean
      description: "True if game ended artificially (timeout, error)"
    info:
      type: object
      description: "Additional context about the move"

Move:
  type: object
  required:
    - from_square
    - to_square
    - piece
    - player
    - uci_notation
    - san_notation
    - is_capture
    - is_castling
    - is_promotion
    - timestamp
  properties:
    from_square:
      type: string
      pattern: "^[a-h][1-8]$"
    to_square:
      type: string
      pattern: "^[a-h][1-8]$"
    piece:
      type: string
      enum: [pawn, knight, bishop, rook, queen, king]
    player:
      type: string
      enum: [white, black]
    uci_notation:
      type: string
      pattern: "^[a-h][1-8][a-h][1-8][qrbn]?$"
    san_notation:
      type: string
      example: "e4"
    is_capture:
      type: boolean
    is_castling:
      type: boolean
    is_promotion:
      type: boolean
    promotion_piece:
      type: string
      nullable: true
      enum: [queen, rook, bishop, knight]
    timestamp:
      type: string
      format: date-time
    thinking_time:
      type: number
      description: "Agent decision time in seconds"
```

**Error Responses**:
- `400 Bad Request`: Invalid move format or illegal move
- `404 Not Found`: Game ID not found
- `409 Conflict`: Game already ended
- `500 Internal Server Error`: Move execution failed

---

### 3. GET /state/{game_id} - Get Game State

**Purpose**: Retrieve current game state without making a move

**Request**:
```http
GET /state/550e8400-e29b-41d4-a716-446655440000 HTTP/1.1
```

**Response (200 OK)**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "game_id": "550e8400-e29b-41d4-a716-446655440000",
  "observation": {
    "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
    "board_tensor": [[...]],
    "legal_moves": ["a7a6", "a7a5", ...],
    "current_turn": "black",
    "is_check": false,
    "is_checkmate": false,
    "is_stalemate": false
  },
  "move_history": [
    {
      "from_square": "e2",
      "to_square": "e4",
      "piece": "pawn",
      "player": "white",
      "uci_notation": "e2e4",
      "san_notation": "e4",
      "timestamp": "2025-10-25T10:00:00Z"
    }
  ],
  "metadata": {
    "status": "in_progress",
    "result": null,
    "started_at": "2025-10-25T10:00:00Z",
    "last_updated": "2025-10-25T10:00:00Z",
    "move_count": 1
  }
}
```

**Response Schema**:
```yaml
StateResponse:
  type: object
  required:
    - game_id
    - observation
    - move_history
    - metadata
  properties:
    game_id:
      type: string
      format: uuid
    observation:
      $ref: '#/components/schemas/Observation'
    move_history:
      type: array
      items:
        $ref: '#/components/schemas/Move'
    metadata:
      type: object
      properties:
        status:
          type: string
        result:
          type: string
          nullable: true
        started_at:
          type: string
          format: date-time
        ended_at:
          type: string
          format: date-time
          nullable: true
        last_updated:
          type: string
          format: date-time
        move_count:
          type: integer
```

**Error Responses**:
- `404 Not Found`: Game ID not found
- `500 Internal Server Error`: State retrieval failed

---

### 4. GET /render/{game_id} - Render Board as SVG

**Purpose**: Get SVG visualization of current board position

**Request**:
```http
GET /render/550e8400-e29b-41d4-a716-446655440000 HTTP/1.1
Accept: image/svg+xml
```

**Query Parameters**:
```yaml
RenderQueryParams:
  type: object
  properties:
    highlight_last_move:
      type: boolean
      default: true
      description: "Highlight squares of last move"
    show_legal_moves:
      type: boolean
      default: false
      description: "Show dots on legal move destinations"
    orientation:
      type: string
      enum: [white, black]
      default: white
      description: "Board orientation"
    size:
      type: integer
      minimum: 200
      maximum: 1000
      default: 400
      description: "SVG canvas size in pixels"
```

**Response (200 OK)**:
```http
HTTP/1.1 200 OK
Content-Type: image/svg+xml
Content-Length: 12847

<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400" viewBox="0 0 400 400">
  <!-- Chess board SVG content -->
  <rect x="0" y="0" width="50" height="50" fill="#f0d9b5"/>
  <rect x="50" y="0" width="50" height="50" fill="#b58863"/>
  <!-- ... piece definitions ... -->
</svg>
```

**Error Responses**:
- `404 Not Found`: Game ID not found
- `500 Internal Server Error`: Rendering failed

---

### 5. GET /health - Health Check

**Purpose**: Service health status for load balancers

**Request**:
```http
GET /health HTTP/1.1
```

**Response (200 OK)**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "healthy",
  "timestamp": "2025-10-25T10:00:00Z",
  "version": "1.0.0",
  "uptime_seconds": 3600,
  "checks": {
    "memory": {
      "status": "healthy",
      "usage_percent": 45.2,
      "available_mb": 1024
    },
    "games": {
      "status": "healthy",
      "active_games": 23,
      "max_games": 100,
      "utilization_percent": 23
    },
    "dependencies": {
      "python_chess": "ok",
      "smolagents": "ok",
      "huggingface_hub": "ok"
    }
  }
}
```

**Response Schema**:
```yaml
HealthResponse:
  type: object
  required:
    - status
    - timestamp
    - version
  properties:
    status:
      type: string
      enum: [healthy, degraded, unhealthy]
    timestamp:
      type: string
      format: date-time
    version:
      type: string
    uptime_seconds:
      type: number
    checks:
      type: object
      additionalProperties:
        type: object
        properties:
          status:
            type: string
            enum: [healthy, degraded, unhealthy]
```

**Status Codes**:
- `200 OK`: Service healthy
- `503 Service Unavailable`: Service degraded or unhealthy

---

### 6. GET /metrics - Prometheus Metrics

**Purpose**: Expose metrics for monitoring

**Request**:
```http
GET /metrics HTTP/1.1
```

**Response (200 OK)**:
```http
HTTP/1.1 200 OK
Content-Type: text/plain; version=0.0.4

# HELP chess_games_total Total number of games created
# TYPE chess_games_total counter
chess_games_total 1247

# HELP chess_games_active Currently active games
# TYPE chess_games_active gauge
chess_games_active 23

# HELP chess_moves_total Total moves made
# TYPE chess_moves_total counter
chess_moves_total 31245

# HELP chess_agent_thinking_time_seconds Agent decision time
# TYPE chess_agent_thinking_time_seconds histogram
chess_agent_thinking_time_seconds_bucket{le="1.0"} 5632
chess_agent_thinking_time_seconds_bucket{le="5.0"} 8945
chess_agent_thinking_time_seconds_bucket{le="10.0"} 9234
chess_agent_thinking_time_seconds_bucket{le="+Inf"} 9456

# HELP chess_illegal_moves_total Illegal moves attempted
# TYPE chess_illegal_moves_total counter
chess_illegal_moves_total 47

# HELP chess_game_duration_seconds Game duration
# TYPE chess_game_duration_seconds histogram
chess_game_duration_seconds_bucket{le="60"} 234
chess_game_duration_seconds_bucket{le="300"} 789
chess_game_duration_seconds_bucket{le="600"} 1023
```

---

## Error Response Schema

All endpoints return errors in consistent format:

```yaml
ErrorResponse:
  type: object
  required:
    - error
    - message
    - timestamp
  properties:
    error:
      type: string
      description: "Error code"
      example: "INVALID_MOVE"
    message:
      type: string
      description: "Human-readable error message"
      example: "Move e2e5 is not legal in current position"
    details:
      type: object
      nullable: true
      description: "Additional error context"
    timestamp:
      type: string
      format: date-time
    request_id:
      type: string
      description: "Request trace ID"
```

**Example Error Response**:
```json
{
  "error": "INVALID_MOVE",
  "message": "Move e2e5 is not legal in current position",
  "details": {
    "move": "e2e5",
    "legal_moves": ["e2e3", "e2e4"],
    "current_turn": "white"
  },
  "timestamp": "2025-10-25T10:00:00Z",
  "request_id": "req_abc123"
}
```

---

## Rate Limiting

**Headers**:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1609459200
```

**HTTP 429 Response**:
```json
{
  "error": "RATE_LIMIT_EXCEEDED",
  "message": "Too many requests. Please try again in 42 seconds.",
  "timestamp": "2025-10-25T10:00:00Z"
}
```

---

## CORS Configuration

```yaml
Access-Control-Allow-Origin: "*"
Access-Control-Allow-Methods: "GET, POST, OPTIONS"
Access-Control-Allow-Headers: "Content-Type"
Access-Control-Max-Age: "3600"
```

---

## API Usage Example

**Complete Game Flow**:

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. Initialize game
response = requests.post(f"{BASE_URL}/reset", json={
    "white_agent": {"name": "Alpha", "personality": "aggressive", "model_name": "Qwen/Qwen2.5-32B-Instruct"},
    "black_agent": {"name": "Beta", "personality": "defensive", "model_name": "Qwen/Qwen2.5-32B-Instruct"}
})
game_data = response.json()
game_id = game_data["game_id"]

# 2. Make move
response = requests.post(f"{BASE_URL}/step", json={
    "game_id": game_id,
    "move": "e2e4"
})
step_data = response.json()
print(f"Move result: {step_data['move_result']['san_notation']}")

# 3. Get current state
response = requests.get(f"{BASE_URL}/state/{game_id}")
state_data = response.json()
print(f"Legal moves: {state_data['observation']['legal_moves']}")

# 4. Render board
response = requests.get(f"{BASE_URL}/render/{game_id}?highlight_last_move=true")
with open("board.svg", "wb") as f:
    f.write(response.content)
```

---

## Performance Targets

| Endpoint | P50 Latency | P95 Latency | Max Throughput |
|----------|-------------|-------------|----------------|
| POST /reset | < 50ms | < 100ms | 20 req/s |
| POST /step | < 10ms | < 50ms | 100 req/s |
| GET /state | < 5ms | < 20ms | 200 req/s |
| GET /render | < 30ms | < 100ms | 50 req/s |
| GET /health | < 2ms | < 10ms | 500 req/s |

---

**Document Status**: Complete  
**Next**: WebSocket event specification  
**Constitution Compliance**: Simple REST interface aligns with Principle II (Simplicity)
