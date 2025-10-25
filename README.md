# Chess OpenEnv Multi-Agent Demo

**A visually compelling demonstration of OpenEnv's multi-agent capabilities using chess**

[![OpenEnv](https://img.shields.io/badge/OpenEnv-0.1-blue)](https://openenv.dev)
[![Python](https://img.shields.io/badge/Python-3.11+-green)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](https://docker.com)

This project demonstrates two AI agents playing chess against each other using the [OpenEnv 0.1 specification](https://openenv.dev) and [Hugging Face's smolagents framework](https://huggingface.co/docs/smolagents). The system prioritizes simplicity (5-minute setup), visual clarity (real-time agent reasoning display), and educational value (reference-quality OpenEnv implementation).

## ✨ Features

- 🤖 **Two AI agents** playing chess with different personalities (aggressive vs defensive)
- 🎯 **OpenEnv 0.1 compliant** - reference implementation of the specification
- 👁️ **Real-time visualization** - watch agents "think" and make decisions
- ⚡ **5-minute setup** - single command deployment with Docker
- 🔄 **WebSocket updates** - live board state and agent reasoning
- 🧠 **Transparent AI** - see confidence scores, thinking time, and reasoning
- 📊 **Performance tracking** - agent statistics and game analytics

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)
- [uv](https://github.com/astral-sh/uv) - ultra-fast Python package manager (optional but recommended)

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/openenv-chess.git
cd openenv-chess

# Start all services (3 containers)
make docker-up

# Or without make:
docker-compose up --build
```

### Access the Demo

Open your browser to: **http://localhost:3000**

- **Chess Environment API**: http://localhost:8000
- **Game Manager**: http://localhost:8001
- **Web Interface**: http://localhost:3000

Click "Start New Game" and watch the agents play!

## 📚 Documentation

- **[Quickstart Guide](specs/001-openenv-chess-demo/quickstart.md)** - 5-minute setup with troubleshooting
- **[Feature Specification](specs/001-openenv-chess-demo/spec.md)** - Product requirements and user stories
- **[Implementation Plan](specs/001-openenv-chess-demo/plan.md)** - Technical architecture and design
- **[Data Model](specs/001-openenv-chess-demo/data-model.md)** - Entity schemas and relationships
- **[REST API Contracts](specs/001-openenv-chess-demo/contracts/rest-api.md)** - OpenAPI 3.0 specification
- **[WebSocket Events](specs/001-openenv-chess-demo/contracts/websocket-events.md)** - Real-time protocol
- **[Technical Requirements](chess-openenv-trd-v2-2.md)** - Complete TRD v2.2
- **[Project Constitution](/.specify/memory/constitution.md)** - Guiding principles

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Interface Layer                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   HTML/CSS/JS   │  │  WebSocket API  │  │  SVG Render  │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                Agent Orchestration Layer                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Agent White   │  │  Game Manager   │  │  Agent Black │ │
│  │  (smolagents)   │  │  (Coordinator)  │  │ (smolagents) │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                 OpenEnv Environment Layer                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │  Chess Engine   │  │   HTTP Server   │  │  State Mgmt  │ │
│  │ (python-chess)  │  │   (FastAPI)     │  │  (In-Memory) │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**3-Container Docker Setup:**
- `chess-env` - OpenEnv-compliant chess environment (Port 8000)
- `game-manager` - Agent orchestration and coordination (Port 8001)
- `web-interface` - Visual interface with real-time updates (Port 3000)

## 🛠️ Technology Stack

- **Python 3.11+** - Primary language
- **FastAPI** - Async web framework with auto-documentation
- **python-chess** - FIDE-compliant chess rule engine
- **smolagents** - Hugging Face agent framework
- **uv** - Ultra-fast Python package manager (10-100x faster than pip)
- **Docker Compose** - Container orchestration
- **WebSockets** - Real-time communication
- **Vanilla JavaScript** - Simple, dependency-free frontend
- **SVG** - Chess board visualization

## 📋 Project Status

### ✅ Completed

- [x] Project constitution (5 core principles)
- [x] Feature specification (5 user stories, 46 requirements)
- [x] Phase 0: Research (11 technology decisions)
- [x] Phase 1: Design & Contracts (data model, APIs, quickstart)
- [x] Clarifications (token management, error handling, reconnection)
- [x] Technical architecture documentation

### 🚧 In Progress

- [ ] Phase 2: Task breakdown (`/speckit.tasks`)
- [ ] Implementation (code generation)
- [ ] Testing (unit, integration, E2E)
- [ ] Deployment

## 🎯 Constitution Principles

This project follows 5 non-negotiable principles:

1. **OpenEnv Compliance (NON-NEGOTIABLE)** - Strict adherence to OpenEnv 0.1 spec
2. **Simplicity & Accessibility First** - Single command setup, minimal dependencies
3. **Visual Clarity & Educational Value** - Transparent agent reasoning, clear UX
4. **OpenEnv Reference Quality** - Production-ready code, comprehensive tests
5. **Performance & Reliability** - <100ms resets, 95%+ completion rate

## 🤝 Contributing

Contributions are welcome! Please check out our [constitution](.specify/memory/constitution.md) first to understand our guiding principles.

### Development Setup

```bash
# Install uv (ultra-fast package manager)
make uv-install

# Install dependencies
make setup

# Run tests
make test

# Start development server
make dev

# Format code
make format

# Run linters
make lint
```

### Common Commands

```bash
make help              # Show all available commands
make docker-up         # Start all containers
make docker-logs       # View container logs
make test              # Run test suite with coverage
make ci                # Run CI checks (format, lint, test)
```

## 📊 Success Criteria

- ✅ Developers can deploy and see their first game in under 5 minutes
- ✅ 90% of users watch games for at least 2 minutes
- ✅ Games complete successfully 95% of the time
- ✅ System handles 10+ concurrent games without degradation
- ✅ Move updates appear in under 2 seconds

## 🔐 Environment Configuration

Create a `.env` file with your Hugging Face token:

```bash
# Copy example environment file
cp .env.example .env

# Edit with your token
HUGGINGFACE_TOKEN=your_token_here
```

## 📝 License

MIT License - see [LICENSE](LICENSE) for details

## 🙏 Acknowledgments

- [OpenEnv](https://openenv.dev) - Agentic execution environment specification
- [Hugging Face smolagents](https://huggingface.co/docs/smolagents) - Agent framework
- [python-chess](https://python-chess.readthedocs.io) - Chess library
- [uv](https://github.com/astral-sh/uv) - Ultra-fast Python package manager

## 🔗 Links

- [OpenEnv Specification](https://openenv.dev/docs/spec/0.1)
- [smolagents Documentation](https://huggingface.co/docs/smolagents)
- [Project Wiki](https://github.com/YOUR_USERNAME/openenv-chess/wiki)

---

**Built with ❤️ for the OpenEnv community**
