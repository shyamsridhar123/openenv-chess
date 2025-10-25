# Phase 0: Research & Technology Decisions

**Feature**: OpenEnv Multi-Agent Chess Demo  
**Date**: 2025-10-25  
**Status**: Complete

## Overview

This document consolidates technology decisions, best practices, and architectural patterns for implementing the Chess OpenEnv Multi-Agent demonstration. All decisions prioritize simplicity, educational value, and OpenEnv compliance per the project constitution.

---

## 1. OpenEnv 0.1 Specification Compliance

### Decision: Strict Adherence to OpenEnv 0.1 Spec

**Rationale**:
- Project serves as reference implementation for OpenEnv framework
- Deviations would undermine educational value and credibility
- Specification provides standardized interface for multi-agent environments

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

**Agent Configuration Pattern**:
```python
from smolagents import ToolCallingAgent
from transformers import AutoTokenizer, AutoModelForCausalLM

agent_white = ToolCallingAgent(
    model="Qwen/Qwen2.5-32B-Instruct",
    system_prompt="""You are a chess-playing AI agent...""",
    temperature=0.7,
    max_tokens=2048
)
```

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

**API Design Pattern**:
```python
from fastapi import FastAPI, WebSocket
from pydantic import BaseModel

app = FastAPI(title="Chess OpenEnv API", version="1.0.0")

class ActionRequest(BaseModel):
    move: str  # UCI notation
    game_id: str

@app.post("/reset")
async def reset_environment():
    """OpenEnv reset endpoint"""
    observation, info = env.reset()
    return {"observation": observation, "info": info}

@app.post("/step")
async def step_environment(action: ActionRequest):
    """OpenEnv step endpoint"""
    obs, reward, terminated, truncated, info = env.step(action.move)
    return {
        "observation": obs,
        "reward": reward,
        "terminated": terminated,
        "truncated": truncated,
        "info": info
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Real-time game updates"""
    await websocket.accept()
    # Stream move_made, agent_thinking, game_ended events
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

### Technology Stack (Finalized)

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Language** | Python 3.11+ | OpenEnv reference language, mature ecosystem |
| **Environment** | python-chess | Industry standard, complete FIDE rules |
| **Agents** | smolagents | Official HF framework, simple, flexible |
| **API** | FastAPI | Modern, async, auto-docs, WebSocket support |
| **State** | In-memory (dict) | Simplest, fastest, perfect for demo scope |
| **Frontend** | Vanilla JS + SVG | No build step, educational, fast load |
| **Deps** | uv | 10-100x faster than pip, modern tooling |
| **Container** | Docker Compose | 3-service architecture, simple, scalable |
| **Testing** | pytest | Modern, expressive, excellent fixtures |
| **Monitoring** | Prometheus + structlog | Industry standard, lightweight |
| **Automation** | Makefile | Ubiquitous, simple, powerful |

### Key Architectural Decisions

1. **OpenEnv Compliance**: Strict adherence to 0.1 specification
2. **Simplicity First**: In-memory storage, no Redis, 3 containers only
3. **Educational Focus**: Vanilla JS, clear code, comprehensive docs
4. **Reference Quality**: 95% test coverage, PEP 8, type hints
5. **Performance**: <100ms resets, <10ms validation, <50ms rendering
6. **Modern Tooling**: uv for speed, FastAPI for async, structlog for observability

### Next Steps

✅ **Phase 0 Complete** - All technology decisions made  
→ **Phase 1**: Create data-model.md, contracts/, quickstart.md  
→ **Phase 2**: Generate tasks.md with `/speckit.tasks` command

---

**Document Status**: Complete  
**Ready for Phase 1**: Yes  
**Constitution Compliance**: All decisions align with 5 core principles
