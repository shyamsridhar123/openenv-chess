"""FastAPI application for Chess OpenEnv demo.

Provides REST API endpoints for the chess environment following OpenEnv spec.
"""

from dotenv import load_dotenv
load_dotenv(override=True)  # Override shell environment variables with .env file

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import structlog
import os
from pathlib import Path

from src.state_manager import StateManager
from src.api.routes import router

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

# Global state manager
state_manager: StateManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    global state_manager
    
    # Startup
    max_games = int(os.getenv("MAX_CONCURRENT_GAMES", "100"))
    state_manager = StateManager(max_games=max_games)
    logger.info("application_started", max_concurrent_games=max_games)
    
    yield
    
    # Shutdown
    if state_manager:
        stats = state_manager.get_stats()
        logger.info("application_shutdown", final_stats=stats)


# Create FastAPI app
app = FastAPI(
    title="Chess OpenEnv Demo",
    description="Multi-agent chess environment using OpenEnv 0.1 specification",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1", tags=["chess"])

# Mount static files for web interface
web_dir = Path(__file__).parent.parent.parent / "web"
if web_dir.exists():
    app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with web interface."""
    web_path = Path(__file__).parent.parent.parent / "web" / "index.html"
    if web_path.exists():
        return HTMLResponse(content=web_path.read_text())
    
    return HTMLResponse(content="""
    <html>
        <head><title>Chess OpenEnv Demo API</title></head>
        <body style="font-family: sans-serif; max-width: 800px; margin: 50px auto; padding: 20px;">
            <h1>Chess OpenEnv Demo API</h1>
            <p>Multi-agent chess environment using OpenEnv 0.1 specification</p>
            <h2>Quick Start</h2>
            <ol>
                <li>POST /reset - Initialize a new game</li>
                <li>POST /step - Make a move</li>
                <li>GET /state/{game_id} - Check game state</li>
                <li>GET /render/{game_id} - View board visualization</li>
            </ol>
            <ul>
                <li><a href="/docs">API Documentation (Swagger)</a></li>
                <li><a href="/health">Health Check</a></li>
                <li><a href="/api/v1/metrics">Metrics</a></li>
            </ul>
        </body>
    </html>
    """)


@app.get("/health")
async def health():
    """Health check endpoint."""
    stats = state_manager.get_stats() if state_manager else {}
    return {
        "status": "healthy",
        "service": "chess-env",
        "version": "0.1.0",
        "stats": stats,
    }


# Import and include API routes
from src.api import routes

app.include_router(routes.router)


if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload = os.getenv("RELOAD", "false").lower() == "true"
    
    uvicorn.run(
        "src.api.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )
