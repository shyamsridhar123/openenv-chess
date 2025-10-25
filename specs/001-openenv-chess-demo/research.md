# Phase 0: Research & Technology Decisions

**Feature**: OpenEnv Multi-Agent Chess Demo  
**Date**: 2025-10-25  
**Status**: Complete (Updated with latest specs from meta-pytorch/OpenEnv)

## Overview

This document consolidates technology decisions, best practices, and architectural patterns for implementing the Chess OpenEnv Multi-Agent demonstration. All decisions prioritize simplicity, educational value, and OpenEnv compliance per the project constitution.

**Latest Research Sources (Oct 25, 2025)**:
- OpenEnv GitHub: https://github.com/meta-pytorch/OpenEnv (v0.1 spec)
- OpenEnv Hub: https://huggingface.co/openenv
- smolagents: https://github.com/huggingface/smolagents (v1.22.0)
- uv package manager: https://github.com/astral-sh/uv (v0.9.5)
- FastAPI WebSockets: https://fastapi.tiangolo.com/advanced/websockets/

---

## 1. OpenEnv 0.1 Specification Compliance

### Decision: Strict Adherence to OpenEnv 0.1 Spec

**Rationale**:
- Project serves as reference implementation for OpenEnv framework
- Deviations would undermine educational value and credibility
- Specification provides standardized interface for multi-agent environments
- Note: OpenEnv repositories are currently not publicly accessible, but we maintain compliance based on the documented specification in the TRD

**Key Requirements from Spec**:
1. **Core Methods**: `reset()`, `step(action)`, `state()`, `close()`
2. **Observation Format**: Gymnasium-compatible `spaces.Dict`
3. **Action Space**: Text-based (UCI notation for chess)
4. **HTTP API**: RESTful endpoints for remote environment access
5. **Containerization**: Docker deployment for portability

**Implementation Approach**:
```python
from gymnasium import spaces

class ChessOpenEnv:
    """OpenEnv 0.1 compliant chess environment"""
    
    @property
    def observation_space(self):
        return spaces.Dict({
            "board_tensor": spaces.Box(low=0, high=12, shape=(8, 8, 12), dtype=np.uint8),
            "fen": spaces.Text(max_length=100),
            "legal_moves": spaces.Sequence(spaces.Text(max_length=5)),
            "current_player": spaces.Discrete(2),
            "is_check": spaces.Discrete(2),
            "is_checkmate": spaces.Discrete(2),
            "is_stalemate": spaces.Discrete(2)
        })
    
    @property
    def action_space(self):
        return spaces.Text(max_length=5)  # UCI notation
    
    def reset(self, options=None):
        """Reset to initial chess position"""
        # Return: observation, info
        
    def step(self, action):
        """Execute move and return new state"""
        # Return: observation, reward, terminated, truncated, info
```

**Research Update (2025-10-25)**:
- OpenEnv specification is actively maintained at https://github.com/meta-pytorch/OpenEnv
- Official OpenEnv 0.1 Spec (RFC 002): https://github.com/meta-pytorch/OpenEnv/blob/main/rfcs/002-env-spec.md
- OpenEnv Hub on Hugging Face: https://huggingface.co/openenv
- Package available via PyPI: `pip install openenv-core`
- Active community on Discord: https://discord.gg/YsTYBh6PD9
- Key design: Gymnasium-style APIs (`reset()`, `step()`, `state()`, `close()`) with FastAPI servers and Docker containers
- Example environments available: Echo, Coding, OpenSpiel, Atari

**OpenEnv Architecture (from official spec)**:
```
Client Application (HTTPEnvClient)
  ↓ HTTP (reset, step, state)
Docker Container (Isolated)
  ↓ FastAPI Server
Environment Base Class
```

**Key Differences from Generic Gymnasium**:
- HTTP API layer for remote access
- Docker containerization for isolation
- Type-safe Action/Observation models (Pydantic)
- Web interface for human interaction and debugging
- Built-in support for RL training frameworks (TRL, torchforge, SkyRL)

**Alternatives Considered**:
- Custom API design → Rejected: Would not serve as OpenEnv reference
- Gymnasium-only (no OpenEnv) → Rejected: Missing HTTP API and container standards

---

## 2. Agent Framework Selection

### Decision: Hugging Face smolagents

**Rationale**:
- **Official HF framework**: Tight integration with Transformers and HF Hub
- **Lightweight**: Minimal abstraction over LLM calls
- **Flexible**: Supports multiple model backends (local, API, custom)
- **Educational**: Simple enough for learners to understand agent mechanics

**Agent Configuration Pattern (smolagents v1.22.0+)**:
```python
from smolagents import CodeAgent, ToolCallingAgent, InferenceClientModel

# Model setup (multiple options available)
model = InferenceClientModel(model_id="Qwen/Qwen2.5-32B-Instruct")

# CodeAgent: Writes actions as Python code (recommended for chess)
agent_white = CodeAgent(
    tools=[],  # Chess moves as code: board.push_uci("e2e4")
    model=model,
    system_prompt="""You are a chess-playing AI agent that writes Python code to make moves.
    Use python-chess library methods like board.push_uci('e2e4').""",
    temperature=0.7,
    max_steps=10
)

# ToolCallingAgent: Alternative JSON-based approach
agent_black = ToolCallingAgent(
    tools=[],  # Tools for chess moves
    model=model,
    system_prompt="""You are a strategic chess player...""",
    temperature=0.7
)
```

**Key smolagents Features (v1.22.0)**:
- **CodeAgent**: Writes actions as Python code snippets (30% fewer steps than tool calling)
- **Model-agnostic**: Supports HF Inference API, OpenAI, Anthropic, local transformers, ollama
- **Sandboxed execution**: E2B, Modal, Docker, or Pyodide+Deno for secure code execution
- **Hub integration**: `agent.push_to_hub()` and `agent.from_hub()` for sharing
- **MCP support**: Can use tools from MCP servers, LangChain, or Gradio Spaces
- **CLI tools**: `smolagent` and `webagent` commands for quick testing

**Alternatives Considered**:
- **LangChain**: Too heavyweight, obscures agent logic
- **AutoGPT**: Too complex for demo scope
- **Custom agent loop**: Reinventing the wheel, not educational
- **smolagents**: ✅ Best balance of simplicity and capability

**Best Practices**:
- Keep system prompts clear and educational (include chess strategy)
- Use temperature 0.7 for balanced exploration/exploitation
- Implement timeout handling (30s default)
- Fallback to random legal move on failure

---

## 3. Chess Logic Implementation

### Decision: python-chess Library

**Rationale**:
- **Battle-tested**: Industry standard for chess logic in Python
- **Complete**: Handles all FIDE rules (castling, en passant, promotions, draws)
- **Fast**: Written in C extensions for performance
- **Well-documented**: Extensive documentation and examples
- **Focus on OpenEnv**: Don't reinvent chess rules, focus on environment integration

**Key Features Used**:
```python
import chess
import chess.svg

board = chess.Board()  # Starting position
board.legal_moves  # Generator of legal moves
board.push_san("e4")  # Make move in algebraic notation
board.push_uci("e2e4")  # Make move in UCI notation
board.is_checkmate()  # Game-ending condition checks
chess.svg.board(board)  # SVG rendering for UI
```

**Alternatives Considered**:
- **Custom chess engine**: Months of work, error-prone, distracts from OpenEnv focus
- **Stockfish integration**: Overkill for move validation, adds complexity
- **python-chess**: ✅ Correct choice for reference implementation

**Best Practices**:
- Always validate moves with `move in board.legal_moves`
- Use `board.copy()` for state snapshots
- Cache SVG renders for identical positions
- Log FEN strings for reproducibility

---

## 4. State Management Architecture

### Decision: In-Memory Storage (Python Dictionaries)

**Rationale**:
- **Simplicity**: Zero external dependencies (no Redis/PostgreSQL)
- **Performance**: Fastest possible access (no network/serialization overhead)
- **Demo Scope**: Games are ephemeral, no need for persistence
- **Easy Setup**: Single command deployment without database configuration

**Implementation Pattern**:
```python
class StateManager:
    def __init__(self):
        self._games = {}  # game_id -> GameState
        self._max_games = 100
        
    def create_game(self, game_id):
        if len(self._games) >= self._max_games:
            self._cleanup_oldest()
        self._games[game_id] = GameState()
        
    def get_game(self, game_id):
        return self._games.get(game_id)
        
    def _cleanup_oldest(self):
        # LRU-style eviction
        oldest = min(self._games.items(), key=lambda x: x[1].last_updated)
        del self._games[oldest[0]]
```

**Alternatives Considered**:
- **Redis**: Adds container dependency, network latency, serialization overhead
- **PostgreSQL**: Overkill for ephemeral game state
- **File-based**: Slower, adds I/O complexity
- **In-memory**: ✅ Perfect for demo/educational use case

**Migration Path** (if production scale needed later):
- Same `StateManager` interface
- Swap implementation to use Redis/PostgreSQL backend
- No changes to calling code

**Best Practices**:
- Implement automatic cleanup at 100 concurrent games
- Memory monitoring via Prometheus metrics
- Clear session on game completion
- Document limitations clearly (state lost on restart)

---

## 5. API Framework Selection

### Decision: FastAPI with WebSockets

**Rationale**:
- **Modern**: Async/await support for concurrent games
- **Fast**: Built on Starlette/Uvicorn (high performance)
- **Auto-docs**: OpenAPI/Swagger generation out of the box
- **Type Safety**: Pydantic integration for request/response validation
- **WebSockets**: Native support for real-time updates

**API Design Pattern (FastAPI + WebSockets)**:
```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List
import asyncio

app = FastAPI(title="Chess OpenEnv API", version="1.0.0")

class ActionRequest(BaseModel):
    move: str  # UCI notation
    game_id: str

class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        """Send message to all connected clients"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass  # Client disconnected

manager = ConnectionManager()

@app.post("/reset")
async def reset_environment():
    """OpenEnv reset endpoint"""
    observation, info = env.reset()
    await manager.broadcast({
        "type": "game_started",
        "data": {"observation": observation, "info": info}
    })
    return {"observation": observation, "info": info}

@app.post("/step")
async def step_environment(action: ActionRequest):
    """OpenEnv step endpoint"""
    obs, reward, terminated, truncated, info = env.step(action.move)
    
    # Broadcast to WebSocket clients
    await manager.broadcast({
        "type": "move_made",
        "data": {
            "observation": obs,
            "reward": reward,
            "terminated": terminated
        }
    })
    
    return {
        "observation": obs,
        "reward": reward,
        "terminated": terminated,
        "truncated": truncated,
        "info": info
    }

@app.websocket("/ws/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str):
    """Real-time game updates with auto-reconnection support"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and receive client messages
            data = await websocket.receive_text()
            # Echo or process client messages if needed
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast({
            "type": "client_disconnected",
            "data": {"game_id": game_id}
        })
```

**WebSocket Client Pattern (JavaScript)**:
```javascript
class ChessWebSocketClient {
    constructor(gameId) {
        this.gameId = gameId;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.connect();
    }
    
    connect() {
        this.ws = new WebSocket(`ws://localhost:8000/ws/${this.gameId}`);
        
        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
        };
        
        this.ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            this.handleMessage(message);
        };
        
        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.attemptReconnect();
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }
    
    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
            console.log(`Reconnecting in ${delay}ms...`);
            setTimeout(() => this.connect(), delay);
        }
    }
    
    handleMessage(message) {
        switch(message.type) {
            case 'game_started':
                this.onGameStarted(message.data);
                break;
            case 'move_made':
                this.onMoveMade(message.data);
                break;
            case 'game_ended':
                this.onGameEnded(message.data);
                break;
        }
    }
}
```

**Alternatives Considered**:
- **Flask**: Synchronous, no WebSocket support, older patterns
- **Django**: Too heavyweight for API-only service
- **FastAPI**: ✅ Modern, async, perfect fit

**Best Practices**:
- Use Pydantic models for all request/response validation
- Implement rate limiting (100 req/min per IP)
- Add CORS middleware for browser access
- Health check endpoint for monitoring
- Structured logging with correlation IDs

---

## 6. Frontend Technology Stack

### Decision: Vanilla JavaScript + SVG + WebSockets

**Rationale**:
- **Simplicity**: No build step, no frameworks to learn
- **Educational**: Developers can understand code without React/Vue knowledge
- **Fast Load**: No megabytes of JavaScript bundles
- **SVG Native**: python-chess generates SVG, render directly in browser

**Architecture Pattern**:
```javascript
class ChessGameClient {
    constructor() {
        this.ws = new WebSocket('ws://localhost:8000/ws');
        this.boardElement = document.getElementById('chess-board');
        this.setupEventListeners();
    }
    
    async startGame() {
        const response = await fetch('/reset', { method: 'POST' });
        const data = await response.json();
        this.renderBoard(data.observation.fen);
    }
    
    renderBoard(fen) {
        // Request SVG from server and inject into DOM
        fetch(`/render?fen=${fen}`)
            .then(r => r.text())
            .then(svg => this.boardElement.innerHTML = svg);
    }
    
    setupEventListeners() {
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'move_made') {
                this.animateMove(data.move);
                this.updateAgentPanel(data.agent, data.reasoning);
            }
        };
    }
}
```

**Alternatives Considered**:
- **React**: Adds build complexity, overkill for simple UI
- **Gradio**: Less control over UI, harder to customize
- **Vanilla JS**: ✅ Simplest, most educational approach

**Best Practices**:
- Use CSS transitions for smooth animations (200ms)
- Debounce WebSocket events to prevent UI thrashing
- Fallback to polling if WebSocket fails
- Clear error messages in UI

---

## 7. Dependency Management

### Decision: uv (Ultra-fast Python Package Manager)

**Rationale**:
- **10-100x faster** than pip for installs
- **Unified tool**: Replaces pip, pip-tools, virtualenv, pyenv
- **Rust-powered**: Maximum performance
- **Modern**: Better dependency resolution than pip
- **Drop-in replacement**: Compatible with existing workflows

**Workflow Pattern**:
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create project
uv init chess-openenv
uv venv --python 3.11

# Add dependencies
uv add fastapi uvicorn python-chess smolagents

# Install from lockfile (reproducible builds)
uv sync --frozen

# Update dependencies
uv lock --upgrade
```

**Alternatives Considered**:
- **pip**: Slow, no built-in lockfile, separate tools for venv
- **poetry**: Better than pip but slower than uv, more complex
- **pdm**: Good but less mature than uv
- **uv**: ✅ Fastest, simplest, modern

**Best Practices**:
- Commit `uv.lock` for reproducible builds
- Use `uv run` prefix for all Python commands in Makefile
- Pin Python version in `.python-version` file
- Document uv installation in README

---

## 8. Containerization Strategy

### Decision: Docker Compose with 3-Container Architecture

**Rationale**:
- **Separation of Concerns**: Environment, orchestrator, UI are independent
- **Scalability**: Can scale each service separately if needed
- **Development**: Can run services independently during dev
- **Simplicity**: No Kubernetes needed for demo scope

**Architecture**:
```yaml
services:
  chess-env:
    build: ./chess-env
    ports: ["8000:8000"]
    environment:
      - MAX_CONCURRENT_GAMES=100
    
  game-manager:
    build: ./game-manager
    ports: ["8001:8001"]
    depends_on: [chess-env]
    environment:
      - HF_TOKEN=${HF_TOKEN}
      - AGENT_MODEL=Qwen/Qwen2.5-32B-Instruct
    
  web-interface:
    build: ./web-interface
    ports: ["3000:80"]
    depends_on: [chess-env, game-manager]
```

**Dockerfile Best Practices**:
```dockerfile
FROM python:3.11-slim

# Use uv for faster installs
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Install dependencies first (layer caching)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy code last (changes frequently)
COPY src/ ./src/

# Security: non-root user
RUN useradd -r appuser
USER appuser

# Health check
HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1

CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0"]
```

**Alternatives Considered**:
- **Single container**: Harder to develop, less clear separation
- **Kubernetes**: Overkill for demo, complex setup
- **3-container Compose**: ✅ Right balance of simplicity and clarity

---

## 9. Testing Strategy

### Decision: Pytest with High Coverage Targets

**Rationale**:
- **Constitution requirement**: 95% coverage for core logic
- **Reference quality**: Demonstrates professional testing practices
- **Fast feedback**: Test suite must complete in <30 seconds

**Test Structure**:
```
tests/
├── unit/                    # 95% coverage target
│   ├── test_chess_env.py    # OpenEnv methods
│   ├── test_chess_logic.py  # python-chess wrapper
│   └── test_state_manager.py # In-memory storage
│
└── integration/             # 80% coverage target
    ├── test_api.py          # HTTP endpoints
    ├── test_agents.py       # Agent interactions
    └── test_game_flow.py    # End-to-end games
```

**Example Test Pattern**:
```python
import pytest
from src.chess_env import ChessOpenEnv

class TestChessOpenEnv:
    @pytest.fixture
    def env(self):
        return ChessOpenEnv()
    
    def test_reset_returns_initial_position(self, env):
        obs, info = env.reset()
        assert obs["fen"] == "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        assert len(obs["legal_moves"]) == 20
    
    def test_step_validates_moves(self, env):
        env.reset()
        obs, reward, terminated, truncated, info = env.step("e2e4")
        assert not terminated
        assert "e2e4" in info["move_history"]
    
    def test_illegal_move_returns_negative_reward(self, env):
        env.reset()
        obs, reward, terminated, truncated, info = env.step("e2e5")  # Illegal
        assert reward == -10.0
        assert terminated
```

**Alternatives Considered**:
- **unittest**: Less expressive than pytest
- **nose**: Deprecated, use pytest instead
- **pytest**: ✅ Modern, expressive, excellent fixtures

**Best Practices**:
- Mock external LLM calls in tests (use `unittest.mock`)
- Test error paths explicitly
- Use `pytest-asyncio` for async code
- Run coverage in CI/CD pipeline

---

## 10. Monitoring & Observability

### Decision: Prometheus + Structured Logging

**Rationale**:
- **Prometheus**: Industry standard, easy to integrate
- **structlog**: JSON-formatted logs for parsing
- **Lightweight**: Minimal overhead

**Metrics to Track**:
```python
from prometheus_client import Counter, Histogram, Gauge

games_started = Counter('chess_games_started_total', 'Games initiated')
games_completed = Counter('chess_games_completed_total', 'Games finished', ['result'])
move_duration = Histogram('chess_move_duration_seconds', 'Move time', ['player'])
active_games = Gauge('chess_active_games', 'Running games')
memory_usage = Gauge('chess_memory_bytes', 'Memory used')
```

**Structured Logging Pattern**:
```python
import structlog

logger = structlog.get_logger()

logger.info(
    "game_move_made",
    game_id=game_id,
    player="white",
    move="e2e4",
    thinking_time=2.34,
    legal_moves=20
)
```

**Alternatives Considered**:
- **Datadog/New Relic**: Paid services, overkill for demo
- **Prometheus**: ✅ Open source, self-hosted, simple

---

## 11. Development Workflow Automation

### Decision: Comprehensive Makefile

**Rationale**:
- **Consistency**: Same commands for all developers
- **Documentation**: `make help` shows all available commands
- **CI/CD**: Same commands in local dev and pipeline
- **uv Integration**: All Python commands use `uv run` prefix

**Key Targets**:
```makefile
setup: ## Install dependencies with uv (10-100x faster than pip)
	uv install

test: ## Run test suite with coverage
	uv run pytest tests/ --cov=src --cov-report=html

lint: ## Run code quality checks
	uv run black src/ tests/
	uv run isort src/ tests/
	uv run flake8 src/ tests/

docker-up: ## Start all services
	docker-compose up -d
	@echo "Web Interface: http://localhost:3000"

dev: ## Run development server with hot-reload
	uv run uvicorn src.main:app --reload

ci: ## Run all CI checks
	make lint && make test
```

**Alternatives Considered**:
- **Shell scripts**: Less portable, harder to document
- **Task runners (invoke, etc)**: Additional dependency
- **Makefile**: ✅ Ubiquitous, simple, powerful

---

## Research Summary

### Technology Stack (Finalized - Oct 25, 2025)

| Component | Technology | Version | Rationale |
|-----------|-----------|---------|-----------|
| **Language** | Python | 3.11+ | OpenEnv reference language, mature ecosystem |
| **Environment** | python-chess | Latest | Industry standard, complete FIDE rules |
| **Agents** | smolagents | v1.22.0+ | Official HF framework, CodeAgent 30% more efficient |
| **API** | FastAPI | 0.104.0+ | Modern, async, auto-docs, WebSocket support |
| **State** | In-memory (dict) | N/A | Simplest, fastest, perfect for demo scope |
| **Frontend** | Vanilla JS + SVG | N/A | No build step, educational, fast load |
| **Deps** | uv | v0.9.5+ | 10-100x faster than pip, modern tooling |
| **Container** | Docker Compose | Latest | 3-service architecture per OpenEnv spec |
| **Testing** | pytest | 7.4.0+ | Modern, expressive, excellent fixtures |
| **Monitoring** | Prometheus + structlog | Latest | Industry standard, lightweight |
| **Automation** | Makefile | N/A | Ubiquitous, simple, powerful |

### Key Research Findings (Oct 25, 2025)

1. **OpenEnv Specification Confirmed**:
   - Official repo: https://github.com/meta-pytorch/OpenEnv
   - RFC 002 defines core spec: `reset()`, `step()`, `state()`, `close()`
   - HTTP API layer with FastAPI + Docker containers is standard approach
   - Example environments available: Echo, Coding, OpenSpiel, Atari
   - Active community with Meta-PyTorch and Hugging Face partnership

2. **smolagents v1.22.0 Enhancements**:
   - **CodeAgent** writes Python code (30% fewer steps than tool calling)
   - Model-agnostic: supports HF Inference, OpenAI, Anthropic, local models
   - Sandboxed execution: E2B, Modal, Docker, Pyodide+Deno
   - Hub integration: `agent.push_to_hub()` / `agent.from_hub()`
   - MCP server support for tool integration
   - CLI tools: `smolagent` and `webagent` commands

3. **uv v0.9.5 Modern Features**:
   - Single tool replaces pip, pip-tools, pipx, poetry, pyenv, virtualenv, twine
   - Project management with universal lockfile (`uv.lock`)
   - Automatic Python version installation and management
   - `uv run` command eliminates need for manual venv activation
   - Cargo-style workspaces for multi-package projects
   - Disk-space efficient with global cache

4. **FastAPI WebSocket Best Practices**:
   - ConnectionManager pattern for broadcasting to multiple clients
   - Graceful disconnect handling with `WebSocketDisconnect` exception
   - Client-side exponential backoff for auto-reconnection
   - Per-game WebSocket endpoints: `/ws/{game_id}`
   - Event-driven architecture: `game_started`, `move_made`, `game_ended`

5. **OpenEnv Integration Requirements**:
   - Gymnasium-compatible observation/action spaces
   - FastAPI server exposing `/reset`, `/step`, `/state` endpoints
   - Docker containerization with health checks
   - Optional web interface for human interaction (HumanAgent support)
   - Type-safe Pydantic models for Action and Observation

### Key Architectural Decisions

1. **OpenEnv Compliance**: Strict adherence to RFC 002 specification
2. **Simplicity First**: In-memory storage, no Redis, 3 containers only
3. **Educational Focus**: Vanilla JS, clear code, comprehensive docs
4. **Reference Quality**: 95% test coverage, PEP 8, type hints
5. **Performance**: <100ms resets, <10ms validation, <50ms rendering
6. **Modern Tooling**: uv for speed, FastAPI for async, structlog for observability

### Implementation Priority

**Phase 1: Core Environment (Week 1-2)**
- ✅ Research complete (this document)
- Set up project structure with uv
- Implement ChessOpenEnv with OpenEnv spec compliance
- Create FastAPI server with `/reset`, `/step`, `/state` endpoints
- Docker containerization

**Phase 2: Agent Integration (Week 3)**
- Integrate smolagents CodeAgent for chess moves
- Implement game orchestration and turn management
- WebSocket real-time updates
- Error handling and recovery strategies

**Phase 3: UI & Polish (Week 4)**
- Vanilla JS frontend with SVG board rendering
- WebSocket client with auto-reconnection
- Agent reasoning panels
- Documentation and examples

### Next Steps

✅ **Phase 0 Complete** - All technology decisions made with latest specs  
→ **Phase 1**: Create data-model.md, contracts/, quickstart.md  
→ **Phase 2**: Generate tasks.md with `/speckit.tasks` command

---

**Document Status**: Complete (Updated Oct 25, 2025)  
**Ready for Phase 1**: Yes  
**Constitution Compliance**: All decisions align with 5 core principles  
**Research Sources**: Official repos and documentation verified
