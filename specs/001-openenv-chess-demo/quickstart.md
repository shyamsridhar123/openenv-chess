# Quickstart Guide: Chess OpenEnv Multi-Agent Demo

**Get the demo running in 5 minutes**

---

## Prerequisites

Before starting, ensure you have:

- **Python 3.11+** - Check with `python3 --version`
- **uv** - Ultra-fast Python package manager ([install guide](#installing-uv))
- **Docker & Docker Compose** - For containerized deployment ([install guide](#installing-docker))
- **Git** - For cloning the repository
- **4GB RAM** - Minimum for running all three containers
- **2 CPU cores** - Recommended for smooth performance

---

## Quick Start (5 Minutes)

### 1. Clone Repository

```bash
git clone https://github.com/your-org/openenv-chess.git
cd openenv-chess
```

### 2. Install Dependencies

Using **uv** (recommended, 10-100x faster than pip):

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

Using **pip** (traditional):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 3. Run with Docker Compose

```bash
# Start all three containers (chess-env, game-manager, web-interface)
make docker-up

# Or without make:
docker-compose up --build
```

**Wait for startup** (approximately 30 seconds):
```
✓ chess-env started on port 8000
✓ game-manager started on port 8001
✓ web-interface started on port 3000
```

### 4. Access the Demo

Open your browser to: **http://localhost:3000**

You should see:
- ✅ Interactive chess board (8×8 grid with pieces)
- ✅ Two agent cards (White and Black players)
- ✅ "Start New Game" button
- ✅ Move history panel (empty initially)

### 5. Play Your First Game

**Option A: Auto-play mode** (agents play each other):

1. Click **"Start New Game"** button
2. Watch agents make moves automatically
3. See real-time board updates
4. Observe agent "thinking" indicators
5. View game completion message when finished

**Option B: Manual mode** (you play as white):

1. Toggle **"Manual Mode"** switch
2. Click **"Start New Game"**
3. Click a piece to see legal moves (green dots)
4. Click destination square to make move
5. Agent responds automatically as black

---

## Project Structure

```
openenv-chess/
├── src/
│   ├── chess_env.py          # OpenEnv-compliant environment
│   ├── chess_logic.py         # Chess rule engine wrapper
│   ├── agent_manager.py       # smolagents integration
│   └── state_manager.py       # In-memory game storage
├── api/
│   ├── main.py                # FastAPI server entry point
│   ├── routes.py              # REST endpoints
│   └── websocket.py           # WebSocket event broadcasting
├── web/
│   ├── index.html             # Frontend interface
│   ├── app.js                 # WebSocket client + board rendering
│   └── styles.css             # Chess board styling
├── tests/
│   ├── test_env.py            # Environment unit tests
│   └── test_integration.py    # End-to-end tests
├── docker-compose.yml         # 3-container orchestration
├── Dockerfile                 # Multi-stage build
├── Makefile                   # Common commands
└── pyproject.toml             # Python dependencies (uv-compatible)
```

---

## Common Commands (Makefile)

```bash
# Development
make install          # Install dependencies with uv
make dev              # Run dev server with hot reload
make test             # Run all tests with coverage
make lint             # Run ruff linter
make format           # Auto-format code with black

# Docker
make docker-up        # Start all containers
make docker-down      # Stop all containers
make docker-logs      # View container logs
make docker-rebuild   # Rebuild images from scratch

# Monitoring
make metrics          # View Prometheus metrics
make logs             # Tail application logs

# Cleanup
make clean            # Remove cache files
make clean-docker     # Remove Docker images/volumes
```

---

## API Endpoints (Manual Testing)

### Initialize Game

```bash
curl -X POST http://localhost:8000/reset \
  -H "Content-Type: application/json" \
  -d '{
    "white_agent": {
      "name": "Aggressive Alpha",
      "personality": "aggressive",
      "model_name": "Qwen/Qwen2.5-32B-Instruct"
    },
    "black_agent": {
      "name": "Defensive Delta",
      "personality": "defensive",
      "model_name": "Qwen/Qwen2.5-32B-Instruct"
    }
  }'
```

### Make a Move

```bash
curl -X POST http://localhost:8000/step \
  -H "Content-Type: application/json" \
  -d '{
    "game_id": "550e8400-e29b-41d4-a716-446655440000",
    "move": "e2e4"
  }'
```

### Get Game State

```bash
curl http://localhost:8000/state/550e8400-e29b-41d4-a716-446655440000
```

### Render Board as SVG

```bash
curl http://localhost:8000/render/550e8400-e29b-41d4-a716-446655440000 > board.svg
```

### Health Check

```bash
curl http://localhost:8000/health
```

---

## WebSocket Connection (JavaScript)

```javascript
const gameId = "550e8400-e29b-41d4-a716-446655440000";
const ws = new WebSocket(`ws://localhost:8000/ws/${gameId}`);

ws.onopen = () => {
    console.log("Connected to game");
};

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    
    switch(message.type) {
        case "game_started":
            console.log("Game started:", message.data);
            break;
        case "move_made":
            console.log("Move:", message.data.move.san_notation);
            updateBoard(message.data.new_position.fen);
            break;
        case "game_ended":
            console.log("Winner:", message.data.result.winner);
            break;
    }
};

ws.onerror = (error) => {
    console.error("WebSocket error:", error);
};
```

---

## Troubleshooting

### Port Already in Use

```bash
# Check what's using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use different ports in docker-compose.yml
```

### Docker Build Fails

```bash
# Clear Docker cache
docker system prune -a

# Rebuild without cache
docker-compose build --no-cache
```

### Dependencies Not Found

```bash
# Reinstall with uv
uv pip install --force-reinstall -e .

# Or clear pip cache
pip cache purge
pip install -e .
```

### WebSocket Connection Refused

```bash
# Check if backend is running
curl http://localhost:8000/health

# View logs
docker-compose logs chess-env

# Restart containers
make docker-down && make docker-up
```

### Slow Agent Moves (>30 seconds)

**Causes**:
- Hugging Face API rate limiting
- Network latency to model endpoint
- Large model inference time

**Solutions**:
```bash
# 1. Use faster model in config
"model_name": "microsoft/phi-2"  # Smaller, faster

# 2. Increase timeout
"timeout_seconds": 60

# 3. Use local model (requires Ollama)
"model_name": "ollama://llama2"
```

### Game Not Rendering

**Check browser console**:
```javascript
// Open DevTools (F12), check for errors
Console: Failed to load resource: ws://localhost:8000/ws/...
```

**Solutions**:
1. Ensure backend is running (`curl http://localhost:8000/health`)
2. Check CORS headers in browser network tab
3. Verify game_id exists (`curl http://localhost:8000/state/{game_id}`)

---

## Installation Guides

### Installing uv

**Linux/macOS**:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows**:
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Verify installation**:
```bash
uv --version
# Output: uv 0.1.0
```

### Installing Docker

**Ubuntu/Debian**:
```bash
# Install Docker
sudo apt-get update
sudo apt-get install docker.io docker-compose

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

**macOS**:
```bash
# Download Docker Desktop from https://www.docker.com/products/docker-desktop
# Or use Homebrew:
brew install --cask docker
```

**Windows**:
1. Download Docker Desktop: https://www.docker.com/products/docker-desktop
2. Run installer
3. Enable WSL2 backend (recommended)

**Verify installation**:
```bash
docker --version
# Output: Docker version 24.0.0

docker-compose --version
# Output: Docker Compose version v2.18.0
```

---

## Development Workflow

### 1. Make Code Changes

```bash
# Edit files in src/ or api/
vim src/chess_env.py

# Linter will auto-check on save (if using VS Code + Ruff extension)
```

### 2. Run Tests

```bash
# Run all tests with coverage
make test

# Run specific test file
pytest tests/test_env.py -v

# Run with coverage report
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

### 3. Test Locally (Hot Reload)

```bash
# Start dev server (auto-reloads on file changes)
make dev

# Or manually:
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Build Docker Image

```bash
# Build and run with Docker Compose
make docker-rebuild

# Or manually:
docker build -t chess-openenv:latest .
docker run -p 8000:8000 chess-openenv:latest
```

### 5. View Logs

```bash
# Follow all container logs
make docker-logs

# Follow specific service
docker-compose logs -f chess-env

# View last 100 lines
docker-compose logs --tail=100
```

---

## Performance Tuning

### Adjust Agent Timeout

Edit `src/agent_manager.py`:

```python
DEFAULT_TIMEOUT = 30  # Change to 60 for slower models
```

### Increase Max Concurrent Games

Edit `src/state_manager.py`:

```python
max_concurrent_games = 100  # Change to 500 for production
```

### Configure Logging Level

Edit `api/main.py`:

```python
import structlog
structlog.configure(
    processors=[...],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO)  # Change to WARNING for less verbosity
)
```

### Enable Response Caching

Edit `api/routes.py`:

```python
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend

@app.on_event("startup")
async def startup():
    FastAPICache.init(InMemoryBackend(), prefix="chess-cache:")
```

---

## Next Steps

### Customize Agents

1. **Edit personalities** in `src/agent_manager.py`:
```python
PERSONALITY_PROMPTS = {
    "aggressive": "You are an aggressive chess player...",
    "defensive": "You are a defensive chess player...",
    "custom_genius": "You are a chess grandmaster..."  # Add new personality
}
```

2. **Try different models**:
```json
{
  "model_name": "microsoft/phi-2",        // Fast, 2.7B params
  "model_name": "meta-llama/Llama-2-7b",  // Balanced, 7B params
  "model_name": "Qwen/Qwen2.5-32B",       // Powerful, 32B params
}
```

### Add New Features

- **Undo Move**: Implement `POST /undo` endpoint
- **Game History**: Store games in SQLite for replay
- **Opening Book**: Integrate chess opening database
- **Analysis Mode**: Add Stockfish engine evaluation
- **Multiplayer**: Allow human vs. agent games

### Deploy to Production

1. **Set environment variables**:
```bash
export ENVIRONMENT=production
export LOG_LEVEL=warning
export MAX_GAMES=500
export HUGGINGFACE_TOKEN=your_token_here
```

2. **Use production Docker Compose**:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

3. **Configure reverse proxy** (nginx):
```nginx
server {
    listen 80;
    server_name chess.yourdomain.com;
    
    location / {
        proxy_pass http://localhost:3000;
    }
    
    location /api {
        proxy_pass http://localhost:8000;
    }
    
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## Monitoring & Observability

### Prometheus Metrics

Access metrics at: **http://localhost:8000/metrics**

Key metrics:
- `chess_games_total` - Total games created
- `chess_games_active` - Currently active games
- `chess_moves_total` - Total moves made
- `chess_agent_thinking_time_seconds` - Agent decision latency
- `chess_illegal_moves_total` - Invalid move attempts

### Structured Logs

View logs with context:
```bash
docker-compose logs chess-env | grep "event=move_made"
```

Example log entry:
```json
{
  "event": "move_made",
  "game_id": "550e8400-e29b-41d4-a716-446655440000",
  "move": "e2e4",
  "player": "white",
  "thinking_time": 2.34,
  "timestamp": "2025-10-25T10:00:00Z"
}
```

### Health Checks

Automated health endpoint:
```bash
curl http://localhost:8000/health | jq
```

Response:
```json
{
  "status": "healthy",
  "checks": {
    "memory": {"status": "healthy", "usage_percent": 45.2},
    "games": {"status": "healthy", "active_games": 23},
    "dependencies": {"python_chess": "ok", "smolagents": "ok"}
  }
}
```

---

## Resources

### Documentation
- **OpenEnv Specification**: https://openenv.dev/docs/spec/0.1
- **smolagents Guide**: https://huggingface.co/docs/smolagents
- **python-chess API**: https://python-chess.readthedocs.io
- **FastAPI Docs**: https://fastapi.tiangolo.com

### Community
- **GitHub Issues**: https://github.com/your-org/openenv-chess/issues
- **Discord**: https://discord.gg/openenv
- **Twitter**: @openenv_dev

### Related Projects
- **OpenEnv Reference**: https://github.com/openenv/openenv
- **Chess Agent Examples**: https://github.com/huggingface/chess-agents
- **Multi-Agent Demos**: https://github.com/openenv/demos

---

## FAQ

**Q: Can I use OpenAI models instead of Hugging Face?**  
A: Yes! Edit `src/agent_manager.py` to use OpenAI API:
```python
from openai import OpenAI
client = OpenAI(api_key="your-api-key")
```

**Q: How do I change the board colors?**  
A: Edit `web/styles.css`:
```css
.square-light { background: #f0d9b5; }  /* Light squares */
.square-dark { background: #b58863; }   /* Dark squares */
```

**Q: Can agents learn from previous games?**  
A: Not in this demo (stateless). For learning, integrate a reinforcement learning framework like Stable-Baselines3.

**Q: What's the maximum game length?**  
A: 100 moves per player (200 total), enforced by 50-move draw rule.

**Q: How do I contribute?**  
A: See CONTRIBUTING.md for guidelines. We welcome pull requests!

---

**Quickstart Complete!** 🎉

You now have a working Chess OpenEnv demo running locally. Try customizing agent personalities, experimenting with different models, or adding new features.

**Need help?** Open an issue on GitHub or ask in Discord.

**Document Status**: Complete  
**Constitution Compliance**: Simple 5-minute setup aligns with Principle II (Simplicity)
