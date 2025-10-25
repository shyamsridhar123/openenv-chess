# Implementation Plan: OpenEnv Multi-Agent Chess Demo

**Branch**: `001-openenv-chess-demo` | **Date**: 2025-10-25 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-openenv-chess-demo/spec.md`

**Note**: This plan integrates the technical architecture from TRD v2.2 with the product requirements from the feature specification.

## Summary

Build a visually compelling chess demo where two AI agents play against each other using the OpenEnv 0.1 specification and Hugging Face's smolagents framework. The system prioritizes simplicity (5-minute setup), visual clarity (real-time agent reasoning display), and educational value (reference-quality OpenEnv implementation). Technical approach uses containerized architecture with in-memory state management, FastAPI for HTTP/WebSocket APIs, python-chess for game logic, and SVG rendering for the visual interface.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI, uvicorn, python-chess, smolagents, transformers, websockets, Pydantic, structlog, prometheus-client  
**Storage**: In-memory (Python dictionaries) - no external database required for demo scope  
**Testing**: pytest, pytest-asyncio, pytest-cov, httpx (for API testing)  
**Target Platform**: Linux server (Ubuntu 22.04+), macOS 12+, Windows WSL2, Docker containers  
**Project Type**: Web application (backend API + frontend interface)  
**Performance Goals**: 
  - Environment reset: <100ms (P95)
  - Move validation: <10ms (P95)
  - SVG rendering: <50ms (P95)
  - Agent move selection: <30s timeout
  - Support 10-20 concurrent games
**Constraints**: 
  - Single command deployment: `make docker-up`
  - <2GB total memory usage
  - No paid API dependencies (free tier only)
  - 95%+ game completion rate
  - No GPU required for demo mode
**Scale/Scope**: 
  - Demo/educational use (not production gaming)
  - 10-20 concurrent games maximum
  - 100 game limit with automatic cleanup
  - Single-server deployment initially

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ✅ I. OpenEnv Compliance (NON-NEGOTIABLE)
- [x] Will implement `reset()`, `step()`, `state()`, `close()` methods per OpenEnv 0.1 spec
- [x] Observations will use Gymnasium-compatible format (Dict space with board tensor, FEN, legal moves)
- [x] Action space specified as UCI notation strings with validation
- [x] HTTP API endpoints follow OpenEnv standards (/reset, /step, /state, /render, /health)
- [x] No deviations from specification planned

**Status**: PASS - Full compliance with OpenEnv 0.1 specification as documented in TRD

### ✅ II. Simplicity & Accessibility First
- [x] Single command setup: `make docker-up` (Makefile-based automation)
- [x] Minimal dependencies: uv for fast dependency management (10-100x faster than pip)
- [x] Clear code comments explaining OpenEnv patterns throughout
- [x] Straightforward architecture: 3 containers (chess-env, game-manager, web-interface)
- [x] Comprehensive documentation with architecture diagrams
- [x] 5-minute deployment target from clone to running game

**Status**: PASS - Architecture prioritizes simplicity, uses in-memory storage (no Redis), modern tooling (uv)

### ✅ III. Visual Clarity & Educational Value
- [x] SVG chess board rendering with smooth animations (200ms transitions)
- [x] Agent reasoning panels showing thinking process in plain language
- [x] Move history with algebraic notation and review capability
- [x] Clear error messages with recovery suggestions
- [x] UI focuses on clarity (8×8 board, agent panels, move history, game controls)
- [x] Real-time performance metrics (thinking time, confidence scores)

**Status**: PASS - Visual interface designed for educational value per TRD Section 5 (UX Design)

### ✅ IV. OpenEnv Reference Quality
- [x] PEP 8 compliance enforced via black, isort, flake8
- [x] Docstrings with type hints for all public functions/classes
- [x] Production-ready patterns: FastAPI, proper error handling, graceful degradation
- [x] Test coverage target: 95% for core environment logic
- [x] OpenAPI/Swagger documentation for all endpoints
- [x] Security practices: input validation, rate limiting (100 req/min), non-root Docker containers

**Status**: PASS - Code quality standards embedded in Makefile, CI/CD pipeline includes automated checks

### ✅ V. Performance & Reliability
- [x] Environment reset: <100ms target (in-memory state)
- [x] Move validation: <10ms target (python-chess library)
- [x] SVG rendering: <50ms target (cached for identical positions)
- [x] Concurrent games: 10-20 supported with automatic cleanup at 100 games
- [x] Game completion: 95%+ target with graceful error handling
- [x] Agent failure handling: timeouts, illegal moves, connection loss with fallback to random legal moves
- [x] Memory bounded: <2GB total with <50MB per game

**Status**: PASS - Performance targets documented in TRD Section 4.2, in-memory approach optimized for speed

### Constitution Compliance Summary

**Overall Status**: ✅ **ALL GATES PASSED**

No violations detected. Architecture aligns with all 5 core principles:
- OpenEnv compliance through strict specification adherence
- Simplicity through Docker/uv/Makefile automation and in-memory storage
- Visual clarity through SVG rendering and agent transparency panels
- Reference quality through comprehensive testing and documentation standards
- Performance through optimized in-memory state and caching strategies

**Ready to proceed to Phase 0 Research**

## Project Structure

### Documentation (this feature)

```text
specs/001-openenv-chess-demo/
├── plan.md              # This file (implementation plan)
├── research.md          # Phase 0: Technology decisions and best practices
├── data-model.md        # Phase 1: Entity schemas and state management
├── quickstart.md        # Phase 1: 5-minute setup guide
├── contracts/           # Phase 1: API specifications
│   ├── openenv-api.yaml # OpenEnv REST endpoints (OpenAPI 3.0)
│   └── websocket-events.md # WebSocket event specifications
├── checklists/          # Quality validation checklists
│   └── requirements.md  # Specification quality checklist (completed)
└── tasks.md             # Phase 2: NOT created by /speckit.plan - use /speckit.tasks
```

### Source Code (repository root)

```text
chess-openenv/
├── Makefile                    # Build automation with uv integration
├── pyproject.toml              # Project metadata and dependencies (uv format)
├── uv.lock                     # Locked dependency versions
├── docker-compose.yml          # Multi-container orchestration (3 services)
├── .env.example                # Environment variable template
├── .python-version             # Python 3.11 pinning
├── README.md                   # Project documentation with quick start
│
├── src/                        # Backend source code
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── chess_env.py            # ChessOpenEnv environment class
│   ├── chess_logic.py          # python-chess wrapper
│   ├── state_manager.py        # In-memory state management
│   │
│   ├── game_manager/           # Agent orchestration
│   │   ├── __init__.py
│   │   ├── main.py             # Game manager entry point
│   │   ├── orchestrator.py     # Turn coordination logic
│   │   └── error_handler.py    # Failure recovery strategies
│   │
│   ├── agents/                 # Agent configurations
│   │   ├── __init__.py
│   │   ├── agent_white.py      # White agent setup
│   │   └── agent_black.py      # Black agent setup
│   │
│   └── utils/                  # Utility modules
│       ├── __init__.py
│       ├── logger.py           # Structured logging (structlog)
│       └── metrics.py          # Prometheus metrics
│
├── tests/                      # Test suite
│   ├── __init__.py
│   ├── unit/                   # Unit tests (95% coverage target)
│   │   ├── test_chess_env.py
│   │   ├── test_chess_logic.py
│   │   └── test_state_manager.py
│   │
│   └── integration/            # Integration tests (80% coverage target)
│       ├── test_api.py
│       ├── test_agents.py
│       └── test_game_flow.py
│
├── web-interface/              # Frontend application
│   ├── index.html              # Main HTML structure
│   ├── styles.css              # CSS styling
│   ├── app.js                  # JavaScript client (WebSocket + REST)
│   ├── Dockerfile              # Frontend container
│   └── nginx.conf              # Nginx web server config
│
├── chess-env/                  # Chess environment container
│   └── Dockerfile              # Backend container with uv
│
├── game-manager/               # Game manager container
│   └── Dockerfile              # Orchestrator container
│
├── config/                     # Configuration files
│   ├── agent_configs.yaml      # Agent personality configurations
│   └── env_configs.yaml        # Environment settings
│
├── examples/                   # Example scripts
│   ├── two_agents_play.py      # Demo game runner
│   └── custom_agent_example.py # Agent customization example
│
├── docs/                       # Generated documentation
│   ├── architecture.md         # System architecture diagrams
│   └── api/                    # Auto-generated API docs
│
└── specs/                      # Feature specifications (this directory)
    └── 001-openenv-chess-demo/
```

**Structure Decision**: **Web application (Option 2)** with backend API and frontend interface.

**Rationale**:
- **Backend (`src/`)**: FastAPI server implementing OpenEnv specification with HTTP/WebSocket endpoints
- **Frontend (`web-interface/`)**: Static HTML/CSS/JS served by Nginx for visual chess interface
- **Separation**: Backend focuses on OpenEnv compliance and agent orchestration; frontend focuses on visual clarity
- **Containerization**: Three Docker containers (chess-env, game-manager, web-interface) for clean separation of concerns
- **Testing**: Separate test suites for backend logic (unit/integration) vs frontend (manual/browser testing)
- **Simplicity**: No mobile apps needed; browser-based interface works across devices

## Complexity Tracking

> **No violations detected - this section intentionally left empty**

All architectural decisions align with constitution principles. No complexity justifications required.

---

## Phase 0: Research ✅ Complete

**Status**: Complete  
**Artifact**: `research.md`

Documented 11 major technology decisions with alternatives considered:
1. OpenEnv 0.1 compliance strategy
2. smolagents agent framework selection
3. python-chess library justification
4. In-memory state management architecture
5. FastAPI with WebSockets decision
6. Vanilla JavaScript frontend choice
7. uv dependency manager adoption
8. Docker Compose 3-container strategy
9. pytest testing approach
10. Prometheus monitoring setup
11. Makefile automation workflow

All decisions align with constitution principles. Technology stack finalized in research.md.

---

## Phase 1: Design & Contracts ✅ Complete

**Status**: Complete  
**Artifacts**: 
- `data-model.md` (6 core entities)
- `contracts/rest-api.md` (OpenAPI 3.0 spec)
- `contracts/websocket-events.md` (Real-time protocol)
- `quickstart.md` (5-minute setup guide)

### 1. Data Model (`data-model.md`)

**Entities Defined**:
1. **Game** - Chess match with move history, status, timestamps
2. **BoardState** - FEN + 8×8×12 tensor + legal moves + game state flags
3. **Move** - UCI/SAN notation, piece, player, timing, captures, promotions
4. **Agent** - Name, personality, model config, system prompt, timeout
5. **AgentStats** - Games played/won/lost/drawn, thinking time, errors
6. **GameSession** - Runtime context, WebSocket connections, active flag

**Storage Architecture**:
```python
StateManager:
    games: Dict[str, Game]           # game_id -> Game
    sessions: Dict[str, GameSession] # session_id -> GameSession
    agents: Dict[str, Agent]          # agent_id -> Agent
    max_concurrent_games: 100         # LRU eviction at limit
    cleanup_after_hours: 24           # Auto-cleanup completed games
```

**Key Design Decisions**:
- In-memory Python dictionaries (no external DB)
- LRU eviction when 100 games reached
- FEN validation via python-chess
- Board tensor: 8×8×12 (rows × cols × piece types)
- State machine: in_progress → {checkmate, stalemate, draw, resigned}

### 2. REST API (`contracts/rest-api.md`)

**OpenAPI 3.0 Specification**:

| Endpoint | Method | Purpose | Target Latency |
|----------|--------|---------|----------------|
| `/reset` | POST | Initialize game with agents | < 50ms (P95) |
| `/step` | POST | Execute move | < 10ms (P95) |
| `/state/{game_id}` | GET | Get current state | < 5ms (P95) |
| `/render/{game_id}` | GET | SVG board visualization | < 30ms (P95) |
| `/health` | GET | Health check | < 2ms (P95) |
| `/metrics` | GET | Prometheus metrics | < 5ms (P95) |

**Request/Response Examples**:

**POST /reset**:
```json
Request:
{
  "white_agent": {"name": "Alpha", "personality": "aggressive", "model_name": "Qwen/Qwen2.5-32B-Instruct"},
  "black_agent": {"name": "Beta", "personality": "defensive", "model_name": "Qwen/Qwen2.5-32B-Instruct"}
}

Response (200 OK):
{
  "game_id": "550e8400-e29b-41d4-a716-446655440000",
  "observation": {"fen": "...", "legal_moves": [...], "current_turn": "white"},
  "agents": {"white": {...}, "black": {...}}
}
```

**POST /step**:
```json
Request: {"game_id": "...", "move": "e2e4"}

Response (200 OK):
{
  "observation": {"fen": "...", "legal_moves": [...], "current_turn": "black"},
  "move_result": {"from_square": "e2", "to_square": "e4", "san_notation": "e4", "thinking_time": 2.34},
  "reward": 0.0,
  "terminated": false,
  "truncated": false
}
```

**Features**:
- Consistent error format with `error`, `message`, `details`, `timestamp`
- Rate limiting: 100 requests/minute per IP (headers: X-RateLimit-*)
- CORS enabled for browser access
- Performance targets documented per endpoint

### 3. WebSocket Events (`contracts/websocket-events.md`)

**Connection**: `ws://localhost:8000/ws/{game_id}`

**Event Types**:
1. **game_started** - Game initialized (agents, initial board)
2. **agent_thinking** - Agent begins move decision (position, legal_moves_count)
3. **move_made** - Move executed (move details, new position, move_number)
4. **game_ended** - Terminal state reached (winner, reason, statistics)
5. **illegal_move_attempted** - Invalid move tried (error, legal_moves)
6. **error** - Server error (code, severity, action_taken)
7. **state_sync** - Full state sync (on client request)

**Client Example (JavaScript)**:
```javascript
const ws = new WebSocket(`ws://localhost:8000/ws/${gameId}`);
ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    switch(msg.type) {
        case "game_started": renderInitialBoard(msg.data); break;
        case "move_made": updateBoard(msg.data.new_position.fen); break;
        case "game_ended": showGameResult(msg.data.result); break;
    }
};
```

**Performance Characteristics**:
- Connection latency: < 50ms
- Event broadcast: < 10ms to all clients
- Max 100 connections per game
- Heartbeat ping/pong: every 30 seconds
- Idle timeout: 5 minutes
- Max message size: 64KB

### 4. Quickstart Guide (`quickstart.md`)

**5-Minute Setup**:
1. Clone repo: `git clone https://github.com/your-org/openenv-chess.git`
2. Install deps: `uv pip install -e .` (or `pip install -e .`)
3. Start containers: `make docker-up`
4. Open browser: `http://localhost:3000`
5. Click "Start New Game"

**Prerequisites**:
- Python 3.11+
- uv or pip
- Docker & Docker Compose
- 4GB RAM, 2 CPU cores

**Common Commands**:
```bash
make install      # Install dependencies with uv
make dev          # Run dev server (hot reload)
make test         # Run tests with coverage
make docker-up    # Start all containers
make docker-logs  # View container logs
make metrics      # View Prometheus metrics
```

**Troubleshooting Guide**:
- Port conflicts: `lsof -i :8000`
- Docker build failures: `docker system prune -a`
- Slow agent moves: Increase timeout or use faster model
- WebSocket errors: Check CORS and backend health

**Next Steps**:
- Customize agent personalities in `src/agent_manager.py`
- Try different Hugging Face models (microsoft/phi-2, meta-llama/Llama-2-7b)
- Add features (undo move, game history, Stockfish analysis)
- Deploy to production with nginx reverse proxy

---

## Phase 2: Task Breakdown

**Status**: Pending (requires `/speckit.tasks` command)

Phase 2 involves generating `tasks.md` with granular implementation tasks. This is a separate workflow command and should be run after Phase 1 artifacts are reviewed and approved.

**Next Action**: User should run `/speckit.tasks` to generate detailed task breakdown for implementation.

---

## Agent Context Update

**Action Required**: Run the following command to update AI agent context with new technology stack:

```bash
.specify/scripts/bash/update-agent-context.sh copilot
```

This will add the finalized technology stack from this plan to the agent context file, preserving any manual additions between markers.
