# WebSocket Event Specification

**Feature**: OpenEnv Multi-Agent Chess Demo  
**Protocol**: WebSocket (RFC 6455)  
**Date**: 2025-10-25  
**Message Format**: JSON

---

## Connection Details

**Endpoint**: `ws://localhost:8000/ws/{game_id}`  
**Subprotocol**: `chess-events-v1`  
**Heartbeat**: Ping every 30 seconds  
**Timeout**: Close after 5 minutes idle

---

## Connection Lifecycle

### 1. Client Connection

```javascript
const gameId = "550e8400-e29b-41d4-a716-446655440000";
const ws = new WebSocket(`ws://localhost:8000/ws/${gameId}`);

ws.onopen = () => {
    console.log("Connected to game:", gameId);
};

ws.onerror = (error) => {
    console.error("WebSocket error:", error);
};

ws.onclose = (event) => {
    console.log("Connection closed:", event.code, event.reason);
};
```

### 2. Server Handshake

**Server Response** (after successful connection):
```json
{
  "type": "connection_established",
  "data": {
    "game_id": "550e8400-e29b-41d4-a716-446655440000",
    "connection_id": "conn_abc123",
    "timestamp": "2025-10-25T10:00:00Z",
    "protocol_version": "1.0"
  }
}
```

### 3. Ping/Pong Heartbeat

**Server → Client** (every 30 seconds):
```json
{
  "type": "ping",
  "timestamp": "2025-10-25T10:00:30Z"
}
```

**Client → Server** (response):
```json
{
  "type": "pong",
  "timestamp": "2025-10-25T10:00:30Z"
}
```

### 4. Disconnection

**Clean Close** (client initiated):
```javascript
ws.close(1000, "User closed tab");
```

**Server Close Codes**:
- `1000`: Normal closure
- `1001`: Going away (server restart)
- `1008`: Policy violation (rate limit)
- `1011`: Internal server error
- `4000`: Game not found
- `4001`: Game already ended
- `4002`: Connection limit reached (max 100 per game)

---

## Event Types

### 1. game_started

**Trigger**: New game initialized via `/reset`  
**Sent to**: All connected clients

```json
{
  "type": "game_started",
  "data": {
    "game_id": "550e8400-e29b-41d4-a716-446655440000",
    "agents": {
      "white": {
        "name": "Aggressive Alpha",
        "personality": "aggressive",
        "model_name": "Qwen/Qwen2.5-32B-Instruct"
      },
      "black": {
        "name": "Defensive Delta",
        "personality": "defensive",
        "model_name": "Qwen/Qwen2.5-32B-Instruct"
      }
    },
    "initial_board": {
      "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
      "current_turn": "white"
    },
    "timestamp": "2025-10-25T10:00:00Z"
  }
}
```

**Schema**:
```yaml
GameStartedEvent:
  type: object
  required:
    - type
    - data
  properties:
    type:
      type: string
      const: "game_started"
    data:
      type: object
      properties:
        game_id:
          type: string
          format: uuid
        agents:
          type: object
          properties:
            white:
              $ref: '#/components/schemas/Agent'
            black:
              $ref: '#/components/schemas/Agent'
        initial_board:
          type: object
          properties:
            fen:
              type: string
            current_turn:
              type: string
        timestamp:
          type: string
          format: date-time
```

---

### 2. agent_thinking

**Trigger**: Agent begins processing move decision  
**Sent to**: All connected clients  
**Frequency**: Once per turn

```json
{
  "type": "agent_thinking",
  "data": {
    "game_id": "550e8400-e29b-41d4-a716-446655440000",
    "agent": {
      "agent_id": "white",
      "name": "Aggressive Alpha",
      "personality": "aggressive"
    },
    "current_position": {
      "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
      "legal_moves_count": 20
    },
    "started_at": "2025-10-25T10:00:00Z"
  }
}
```

**Schema**:
```yaml
AgentThinkingEvent:
  type: object
  required:
    - type
    - data
  properties:
    type:
      type: string
      const: "agent_thinking"
    data:
      type: object
      properties:
        game_id:
          type: string
          format: uuid
        agent:
          type: object
          properties:
            agent_id:
              type: string
            name:
              type: string
            personality:
              type: string
        current_position:
          type: object
          properties:
            fen:
              type: string
            legal_moves_count:
              type: integer
        started_at:
          type: string
          format: date-time
```

---

### 3. move_made

**Trigger**: Agent successfully executes move via `/step`  
**Sent to**: All connected clients  
**Frequency**: Once per move

```json
{
  "type": "move_made",
  "data": {
    "game_id": "550e8400-e29b-41d4-a716-446655440000",
    "move": {
      "from_square": "e2",
      "to_square": "e4",
      "piece": "pawn",
      "player": "white",
      "uci_notation": "e2e4",
      "san_notation": "e4",
      "is_capture": false,
      "is_castling": false,
      "is_promotion": false,
      "thinking_time": 2.34
    },
    "new_position": {
      "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
      "current_turn": "black",
      "legal_moves": ["a7a6", "a7a5", "b7b6", ...],
      "is_check": false
    },
    "move_number": 1,
    "timestamp": "2025-10-25T10:00:02Z"
  }
}
```

**Schema**:
```yaml
MoveMadeEvent:
  type: object
  required:
    - type
    - data
  properties:
    type:
      type: string
      const: "move_made"
    data:
      type: object
      properties:
        game_id:
          type: string
          format: uuid
        move:
          $ref: '#/components/schemas/Move'
        new_position:
          type: object
          properties:
            fen:
              type: string
            current_turn:
              type: string
            legal_moves:
              type: array
              items:
                type: string
            is_check:
              type: boolean
        move_number:
          type: integer
        timestamp:
          type: string
          format: date-time
```

---

### 4. game_ended

**Trigger**: Game reaches terminal state (checkmate, stalemate, draw)  
**Sent to**: All connected clients  
**Frequency**: Once per game

```json
{
  "type": "game_ended",
  "data": {
    "game_id": "550e8400-e29b-41d4-a716-446655440000",
    "result": {
      "status": "checkmate",
      "winner": "white",
      "reason": "Black king checkmated"
    },
    "final_position": {
      "fen": "r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4",
      "move_count": 8
    },
    "statistics": {
      "duration_seconds": 187.5,
      "total_moves": 8,
      "white_avg_thinking_time": 3.2,
      "black_avg_thinking_time": 4.1,
      "illegal_moves_attempted": 0
    },
    "timestamp": "2025-10-25T10:03:07Z"
  }
}
```

**Schema**:
```yaml
GameEndedEvent:
  type: object
  required:
    - type
    - data
  properties:
    type:
      type: string
      const: "game_ended"
    data:
      type: object
      properties:
        game_id:
          type: string
          format: uuid
        result:
          type: object
          properties:
            status:
              type: string
              enum: [checkmate, stalemate, draw, resigned, timeout]
            winner:
              type: string
              nullable: true
              enum: [white, black]
            reason:
              type: string
        final_position:
          type: object
          properties:
            fen:
              type: string
            move_count:
              type: integer
        statistics:
          type: object
          properties:
            duration_seconds:
              type: number
            total_moves:
              type: integer
            white_avg_thinking_time:
              type: number
            black_avg_thinking_time:
              type: number
            illegal_moves_attempted:
              type: integer
        timestamp:
          type: string
          format: date-time
```

---

### 5. illegal_move_attempted

**Trigger**: Agent tries to make invalid move  
**Sent to**: All connected clients  
**Frequency**: As needed (should be rare)

```json
{
  "type": "illegal_move_attempted",
  "data": {
    "game_id": "550e8400-e29b-41d4-a716-446655440000",
    "agent": {
      "agent_id": "white",
      "name": "Aggressive Alpha"
    },
    "attempted_move": {
      "uci_notation": "e2e5",
      "san_notation": "e5"
    },
    "error": {
      "code": "ILLEGAL_MOVE",
      "message": "Pawn cannot move from e2 to e5",
      "reason": "blocked_by_piece"
    },
    "current_position": {
      "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
      "legal_moves": ["e2e3", "e2e4"]
    },
    "timestamp": "2025-10-25T10:00:05Z"
  }
}
```

**Schema**:
```yaml
IllegalMoveAttemptedEvent:
  type: object
  required:
    - type
    - data
  properties:
    type:
      type: string
      const: "illegal_move_attempted"
    data:
      type: object
      properties:
        game_id:
          type: string
          format: uuid
        agent:
          type: object
          properties:
            agent_id:
              type: string
            name:
              type: string
        attempted_move:
          type: object
          properties:
            uci_notation:
              type: string
            san_notation:
              type: string
        error:
          type: object
          properties:
            code:
              type: string
            message:
              type: string
            reason:
              type: string
        current_position:
          type: object
          properties:
            fen:
              type: string
            legal_moves:
              type: array
              items:
                type: string
        timestamp:
          type: string
          format: date-time
```

---

### 6. error

**Trigger**: Server-side error during game execution  
**Sent to**: All connected clients  
**Frequency**: As needed (should be rare)

```json
{
  "type": "error",
  "data": {
    "game_id": "550e8400-e29b-41d4-a716-446655440000",
    "error": {
      "code": "AGENT_TIMEOUT",
      "message": "Agent 'white' exceeded 30-second timeout",
      "severity": "warning"
    },
    "action_taken": "Game continues with fallback move",
    "timestamp": "2025-10-25T10:00:35Z"
  }
}
```

**Schema**:
```yaml
ErrorEvent:
  type: object
  required:
    - type
    - data
  properties:
    type:
      type: string
      const: "error"
    data:
      type: object
      properties:
        game_id:
          type: string
          format: uuid
        error:
          type: object
          properties:
            code:
              type: string
              enum: [AGENT_TIMEOUT, AGENT_ERROR, SERVER_ERROR, MEMORY_LIMIT]
            message:
              type: string
            severity:
              type: string
              enum: [info, warning, error, critical]
        action_taken:
          type: string
        timestamp:
          type: string
          format: date-time
```

---

### 7. state_sync

**Trigger**: Client requests full state sync (client-initiated)  
**Sent to**: Requesting client only  
**Frequency**: On demand

**Client Request**:
```json
{
  "type": "request_state_sync",
  "timestamp": "2025-10-25T10:00:00Z"
}
```

**Server Response**:
```json
{
  "type": "state_sync",
  "data": {
    "game_id": "550e8400-e29b-41d4-a716-446655440000",
    "current_position": {
      "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
      "current_turn": "black",
      "legal_moves": ["a7a6", "a7a5", ...],
      "is_check": false
    },
    "move_history": [
      {
        "from_square": "e2",
        "to_square": "e4",
        "san_notation": "e4",
        "timestamp": "2025-10-25T10:00:02Z"
      }
    ],
    "game_status": {
      "status": "in_progress",
      "move_count": 1,
      "started_at": "2025-10-25T10:00:00Z"
    },
    "timestamp": "2025-10-25T10:00:10Z"
  }
}
```

---

## Client Implementation Examples

### JavaScript/Browser

```javascript
class ChessWebSocketClient {
    constructor(gameId) {
        this.gameId = gameId;
        this.ws = null;
        this.handlers = {};
    }
    
    connect() {
        this.ws = new WebSocket(`ws://localhost:8000/ws/${this.gameId}`);
        
        this.ws.onopen = () => {
            console.log("Connected to game:", this.gameId);
        };
        
        this.ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            this.handleEvent(message);
        };
        
        this.ws.onerror = (error) => {
            console.error("WebSocket error:", error);
        };
        
        this.ws.onclose = (event) => {
            console.log("Disconnected:", event.reason);
            this.reconnect();
        };
    }
    
    handleEvent(message) {
        const handler = this.handlers[message.type];
        if (handler) {
            handler(message.data);
        } else {
            console.warn("No handler for event:", message.type);
        }
    }
    
    on(eventType, handler) {
        this.handlers[eventType] = handler;
    }
    
    requestStateSync() {
        this.ws.send(JSON.stringify({
            type: "request_state_sync",
            timestamp: new Date().toISOString()
        }));
    }
    
    reconnect() {
        setTimeout(() => this.connect(), 5000);
    }
}

// Usage
const client = new ChessWebSocketClient("550e8400-e29b-41d4-a716-446655440000");

client.on("game_started", (data) => {
    console.log("Game started:", data.agents);
    renderBoard(data.initial_board.fen);
});

client.on("agent_thinking", (data) => {
    showThinkingIndicator(data.agent.name);
});

client.on("move_made", (data) => {
    console.log("Move:", data.move.san_notation);
    updateBoard(data.new_position.fen);
    highlightSquares(data.move.from_square, data.move.to_square);
});

client.on("game_ended", (data) => {
    console.log("Game ended:", data.result);
    showGameResult(data.result.winner, data.result.reason);
});

client.connect();
```

### Python

```python
import asyncio
import websockets
import json

class ChessWebSocketClient:
    def __init__(self, game_id: str):
        self.game_id = game_id
        self.ws = None
        self.handlers = {}
    
    async def connect(self):
        uri = f"ws://localhost:8000/ws/{self.game_id}"
        async with websockets.connect(uri) as websocket:
            self.ws = websocket
            print(f"Connected to game: {self.game_id}")
            
            async for message in websocket:
                data = json.loads(message)
                await self.handle_event(data)
    
    async def handle_event(self, message):
        event_type = message["type"]
        handler = self.handlers.get(event_type)
        
        if handler:
            await handler(message["data"])
        else:
            print(f"No handler for event: {event_type}")
    
    def on(self, event_type: str, handler):
        self.handlers[event_type] = handler
    
    async def request_state_sync(self):
        await self.ws.send(json.dumps({
            "type": "request_state_sync",
            "timestamp": datetime.utcnow().isoformat()
        }))

# Usage
async def main():
    client = ChessWebSocketClient("550e8400-e29b-41d4-a716-446655440000")
    
    client.on("game_started", lambda data: print(f"Game started: {data['agents']}"))
    client.on("move_made", lambda data: print(f"Move: {data['move']['san_notation']}"))
    client.on("game_ended", lambda data: print(f"Game ended: {data['result']}"))
    
    await client.connect()

asyncio.run(main())
```

---

## Event Flow Diagram

```
[Client 1]          [Server]          [Client 2]
    |                   |                   |
    |--- connect ------>|                   |
    |<-- connection_established ------------|
    |                   |<--- connect ------|
    |                   |-- connection_established ->|
    |                   |                   |
    |<-- game_started --|-- game_started -->|
    |                   |                   |
    |<-- agent_thinking|-- agent_thinking ->|
    |                   |                   |
    |<-- move_made -----|-- move_made ----->|
    |                   |                   |
    |<-- agent_thinking|-- agent_thinking ->|
    |                   |                   |
    |<-- move_made -----|-- move_made ----->|
    |                   |                   |
    |                  ... (game continues)
    |                   |                   |
    |<-- game_ended ----|-- game_ended ---->|
    |                   |                   |
    |--- close -------->|                   |
    |                   |<--- close --------|
```

---

## Performance Characteristics

| Metric | Target | Notes |
|--------|--------|-------|
| Connection Latency | < 50ms | Initial WebSocket handshake |
| Event Broadcast Latency | < 10ms | Server → all clients |
| Message Size | < 5KB | Typical event payload |
| Max Concurrent Connections | 10,000 | Per server instance |
| Max Connections per Game | 100 | To prevent memory issues |
| Heartbeat Interval | 30s | Keep-alive ping/pong |
| Idle Timeout | 5 min | Close inactive connections |

---

## Error Handling

### Connection Failures

**Client Side**:
1. Implement exponential backoff (5s, 10s, 20s, 40s)
2. Maximum 5 reconnection attempts
3. Show "Reconnecting..." UI indicator
4. Request state sync after reconnection

**Server Side**:
1. Log disconnection reason
2. Clean up session resources after 1 minute
3. Notify other clients if last observer disconnects

### Message Validation

**Server validates**:
- JSON structure matches schema
- Required fields present
- Field types correct
- Enum values valid

**Invalid Message Response**:
```json
{
  "type": "error",
  "data": {
    "error": {
      "code": "INVALID_MESSAGE",
      "message": "Field 'type' is required",
      "severity": "error"
    },
    "timestamp": "2025-10-25T10:00:00Z"
  }
}
```

---

## Security Considerations

1. **Rate Limiting**: Max 100 messages/minute per connection
2. **Message Size Limit**: Max 64KB per message
3. **Origin Validation**: CORS headers checked
4. **Authentication**: None (public demo), but auth-ready
5. **Input Sanitization**: All JSON fields validated
6. **Connection Limits**: Max 100 per game, 10,000 per server

---

**Document Status**: Complete  
**Next**: Quickstart guide  
**Constitution Compliance**: Real-time updates align with Principle III (Visual Clarity)
