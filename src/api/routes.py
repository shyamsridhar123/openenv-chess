"""API routes for Chess OpenEnv endpoints.

Implements OpenEnv 0.1 REST API specification:
- POST /reset - Initialize environment
- POST /step - Execute action
- GET /state/{game_id} - Get game state
- GET /render/{game_id} - Render board visualization
"""

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import structlog
import uuid
import json

from src.chess_env import ChessOpenEnv

logger = structlog.get_logger()

router = APIRouter()


def get_state_manager():
    """Get state manager from main app to avoid circular import."""
    from src.api.main import state_manager
    return state_manager


# Request/Response models
class ResetRequest(BaseModel):
    """Request body for /reset endpoint."""
    fen: Optional[str] = Field(None, description="Optional FEN string for custom starting position")
    white_agent_id: str = Field("white", description="White agent identifier")
    black_agent_id: str = Field("black", description="Black agent identifier")
    game_id: Optional[str] = Field(None, description="Optional game ID (generated if not provided)")


class ResetResponse(BaseModel):
    """Response body for /reset endpoint."""
    game_id: str
    observation: Dict[str, Any]
    info: Dict[str, Any]


class StepRequest(BaseModel):
    """Request body for /step endpoint."""
    game_id: str = Field(..., description="Game identifier")
    action: str = Field(..., description="Move in UCI notation (e.g., 'e2e4')")


class AgentMoveRequest(BaseModel):
    """Request body for /agent-move endpoint."""
    game_id: str = Field(..., description="Game identifier")


class StepResponse(BaseModel):
    """Response body for /step endpoint."""
    game_id: str
    observation: Dict[str, Any]
    reward: float
    terminated: bool
    truncated: bool
    info: Dict[str, Any]


@router.post("/reset", response_model=ResetResponse)
async def reset_environment(request: ResetRequest):
    """Initialize a new chess game.
    
    OpenEnv /reset endpoint - creates a new game instance.
    """
    state_mgr = get_state_manager()
    
    try:
        # Generate game ID if not provided
        game_id = request.game_id or str(uuid.uuid4())
        
        # Create environment
        env = ChessOpenEnv(game_id=game_id)
        
        # Reset environment
        observation, info = env.reset(
            fen=request.fen,
            white_agent_id=request.white_agent_id,
            black_agent_id=request.black_agent_id,
        )
        
        # Store game in state manager
        state_mgr.create_game(env.game)
        
        logger.info(
            "game_reset",
            game_id=game_id,
            white_agent=request.white_agent_id,
            black_agent=request.black_agent_id,
            custom_fen=request.fen is not None,
        )
        
        return ResetResponse(
            game_id=game_id,
            observation=observation,
            info=info,
        )
        
    except Exception as e:
        logger.error("reset_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to reset environment: {str(e)}")


@router.post("/step", response_model=StepResponse)
async def step_environment(request: StepRequest):
    """Execute a move in the chess game.
    
    OpenEnv /step endpoint - applies an action and returns new state.
    """
    state_mgr = get_state_manager()
    
    try:
        # Get game from state manager
        game = state_mgr.get_game(request.game_id)
        if not game:
            raise HTTPException(status_code=404, detail=f"Game {request.game_id} not found")
        
        # Recreate environment from stored game
        env = ChessOpenEnv(game_id=request.game_id)
        env.game = game
        env.chess.board = env.chess.board.__class__(game.board_state.fen)
        env._move_count = game.total_moves
        
        # Execute step
        observation, reward, terminated, truncated, info = env.step(request.action)
        
        # Update game in state manager
        state_mgr.update_game(env.game)
        
        logger.info(
            "game_step",
            game_id=request.game_id,
            action=request.action,
            san_move=info.get("san_move"),
            terminated=terminated,
        )
        
        return StepResponse(
            game_id=request.game_id,
            observation=observation,
            reward=reward,
            terminated=terminated,
            truncated=truncated,
            info=info,
        )
        
    except ValueError as e:
        logger.warning("invalid_move", game_id=request.game_id, action=request.action, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("step_failed", game_id=request.game_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to execute step: {str(e)}")


@router.get("/state/{game_id}")
async def get_state(game_id: str):
    """Get current game state metadata.
    
    OpenEnv /state endpoint - returns game metadata without full observation.
    """
    state_mgr = get_state_manager()
    
    try:
        game = state_mgr.get_game(game_id)
        if not game:
            raise HTTPException(status_code=404, detail=f"Game {game_id} not found")
        
        return {
            "game_id": game_id,
            "status": game.status.value,
            "result": game.result.value,
            "move_count": game.total_moves,
            "current_player": game.board_state.current_player,
            "fen": game.board_state.fen,
            "is_terminal": game.is_terminal(),
            "is_check": game.board_state.is_check,
            "is_checkmate": game.board_state.is_checkmate,
            "is_stalemate": game.board_state.is_stalemate,
            "white_agent": game.white_agent_id,
            "black_agent": game.black_agent_id,
            "created_at": game.created_at.isoformat(),
            "updated_at": game.updated_at.isoformat(),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_state_failed", game_id=game_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get state: {str(e)}")


@router.get("/render/{game_id}")
async def render_board(
    game_id: str,
    mode: str = Query("svg", description="Render mode: 'svg' or 'ascii'"),
    size: int = Query(400, description="Board size in pixels (SVG only)")
):
    """Render board visualization.
    
    OpenEnv /render endpoint - returns visual representation of board.
    """
    state_mgr = get_state_manager()
    
    try:
        game = state_mgr.get_game(game_id)
        if not game:
            raise HTTPException(status_code=404, detail=f"Game {game_id} not found")
        
        # Recreate environment for rendering
        env = ChessOpenEnv(game_id=game_id)
        env.chess.board = env.chess.board.__class__(game.board_state.fen)
        
        # Render board
        rendered = env.render(mode=mode, size=size)
        
        if mode == "svg":
            return HTMLResponse(content=rendered)
        else:
            return {"game_id": game_id, "board": rendered}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("render_failed", game_id=game_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to render board: {str(e)}")


@router.get("/games")
async def list_games(
    limit: int = Query(10, description="Maximum number of games to return"),
    active_only: bool = Query(False, description="Only return active games")
):
    """List all games."""
    state_mgr = get_state_manager()
    
    try:
        games = state_mgr.list_games(limit=limit)
        
        if active_only:
            games = [g for g in games if not g.is_terminal()]
        
        return {
            "games": [
                {
                    "game_id": g.game_id,
                    "status": g.status.value,
                    "result": g.result.value,
                    "move_count": g.total_moves,
                    "current_player": g.board_state.current_player,
                    "white_agent": g.white_agent_id,
                    "black_agent": g.black_agent_id,
                    "created_at": g.created_at.isoformat(),
                }
                for g in games
            ],
            "total": len(games),
        }
        
    except Exception as e:
        logger.error("list_games_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list games: {str(e)}")


@router.delete("/games/{game_id}")
async def delete_game(game_id: str):
    """Delete a game."""
    state_mgr = get_state_manager()
    
    try:
        success = state_mgr.delete_game(game_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Game {game_id} not found")
        
        logger.info("game_deleted", game_id=game_id)
        
        return {"message": f"Game {game_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_game_failed", game_id=game_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to delete game: {str(e)}")


@router.get("/stats")
async def get_stats():
    """Get state manager statistics."""
    state_mgr = get_state_manager()
    
    try:
        stats = state_mgr.get_stats()
        return stats
    except Exception as e:
        logger.error("get_stats_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.post("/agent-move")
async def agent_move(request: AgentMoveRequest):
    """Execute a move using an LLM agent.
    
    This endpoint uses the game orchestrator to generate a move using an LLM,
    then executes it.
    """
    state_mgr = get_state_manager()
    
    # Get game from state manager
    game = state_mgr.get_game(request.game_id)
    if not game:
        raise HTTPException(status_code=404, detail=f"Game {request.game_id} not found")
    
    logger.debug("agent_move_requested", game_id=request.game_id)
    
    try:
        # Recreate environment from stored game (like step endpoint does)
        env = ChessOpenEnv(game_id=request.game_id)
        env.game = game
        env.chess.board = env.chess.board.__class__(game.board_state.fen)
        env._move_count = game.total_moves
        
        # Get current player
        current_player = 'white' if env.chess.board.turn else 'black'
        agent_id = game.white_agent_id if current_player == 'white' else game.black_agent_id
        
        # Get agent personality from agent ID
        personality = 'balanced'
        for p in ['aggressive', 'defensive', 'tactical', 'positional']:
            if p in agent_id.lower():
                personality = p
                break
        
        # Import dependencies
        from src.agents.agent_manager import ChessAgentManager
        from src.game_manager.game_orchestrator import GameOrchestrator
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        # Create agent manager and orchestrator
        agent_mgr = ChessAgentManager()
        
        # Create agent if it doesn't exist
        try:
            agent_mgr.create_agent(agent_id, personality=personality)
            logger.info("agent_created", agent_id=agent_id, personality=personality)
        except ValueError:
            # Agent already exists
            pass
        
        orchestrator = GameOrchestrator(agent_mgr)
        
        logger.info("requesting_agent_move", 
                   game_id=request.game_id,
                   agent_id=agent_id,
                   personality=personality)
        
        # Execute one move using orchestrator in thread pool (takes 2-30 seconds)
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as pool:
            result = await loop.run_in_executor(
                pool,
                lambda: asyncio.run(orchestrator.run_game_step(
                    env=env,
                    agent_id=agent_id,
                    move_history=[]
                ))
            )
        
        logger.info("agent_move_generated",
                   game_id=request.game_id,
                   agent_id=agent_id,
                   move=result['move'],
                   san_move=result['san_move'])
        
        # Update game in state manager
        state_mgr.update_game(env.game)
        
        logger.debug("agent_move_executed",
                    game_id=request.game_id,
                    terminated=result['terminated'])
        
        return {
            "game_id": request.game_id,
            "observation": result['observation'],
            "reward": result['reward'],
            "terminated": result['terminated'],
            "truncated": result['truncated'],
            "info": result['info'],
            "agent_id": agent_id,
            "personality": personality
        }
        
    except Exception as e:
        logger.error("agent_move_failed",
                    game_id=request.game_id,
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Agent move failed: {str(e)}")


@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    state_mgr = get_state_manager()
    stats = state_mgr.get_stats()
    
    # Build Prometheus format metrics
    metrics_text = f"""# HELP chess_games_total Total number of games
# TYPE chess_games_total gauge
chess_games_total {stats['total_games']}

# HELP chess_games_active Active games count
# TYPE chess_games_active gauge
chess_games_active {stats['active_games']}

# HELP chess_games_completed Completed games count
# TYPE chess_games_completed gauge
chess_games_completed {stats['completed_games']}

# HELP chess_capacity_used_percent Capacity utilization percentage
# TYPE chess_capacity_used_percent gauge
chess_capacity_used_percent {stats['capacity_used_percent']}
"""
    
    return Response(content=metrics_text, media_type="text/plain")


@router.get("/commentary/introduction")
async def stream_introduction(white_agent: str = Query("White"), black_agent: str = Query("Black")):
    """Stream energetic game introduction before the first move.
    
    Returns Server-Sent Events (SSE) with audio chunks and transcripts.
    """
    from src.commentary.realtime_audio_client import get_realtime_client
    
    logger.info("game_introduction_requested", white_agent=white_agent, black_agent=black_agent)
    
    try:
        client = get_realtime_client()
        
        if not client or not client.is_available():
            # Return error event
            async def error_stream():
                yield f"data: {json.dumps({'error': 'Audio commentary not available', 'done': True})}\n\n".encode('utf-8')
            
            return StreamingResponse(
                error_stream(),
                media_type="text/event-stream"
            )
        
        # Generate energetic introduction
        async def generate():
            try:
                prompt = f"""Welcome to this exciting chess match! Today we have {white_agent} playing as White against {black_agent} as Black! 
This is going to be an intense battle of strategy and tactics - and like Kimi, these drivers actually know where the finish line is! 
Both players are ready at the board, the pieces are set, and White is about to make the opening move. 
Bwoah, let's see what happens! The game begins NOW!"""
                
                async for event in client.stream_commentary_audio(prompt, voice_style="excited"):
                    if event.get('audio'):
                        data = json.dumps({'audio': event['audio']})
                        yield f"data: {data}\n\n".encode('utf-8')
                    
                    if event.get('text'):
                        data = json.dumps({'text': event['text']})
                        yield f"data: {data}\n\n".encode('utf-8')
                    
                    if event.get('done'):
                        data = json.dumps({'done': True})
                        yield f"data: {data}\n\n".encode('utf-8')
                        break
                    
                    if event.get('error'):
                        data = json.dumps({'error': event['error'], 'done': True})
                        yield f"data: {data}\n\n".encode('utf-8')
                        break
                        
            except Exception as e:
                logger.error("introduction_stream_failed", error=str(e))
                data = json.dumps({'error': str(e), 'done': True})
                yield f"data: {data}\n\n".encode('utf-8')
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
        
    except Exception as e:
        logger.error("introduction_setup_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/commentary/stream")
async def stream_commentary(
    san_move: str = Query(..., description="Move in Standard Algebraic Notation (e.g., 'Nf3', 'e4')"),
    player: str = Query(..., description="Player who made the move ('white' or 'black')"),
    evaluation: Optional[int] = Query(None, description="Stockfish evaluation in centipawns"),
    eval_change: Optional[int] = Query(None, description="Change in evaluation after this move"),
    trigger: Optional[str] = Query("REGULAR", description="Commentary trigger type"),
    fen: Optional[str] = Query(None, description="Current position FEN"),
    move_number: Optional[int] = Query(None, description="Move number in the game"),
):
    """Stream real-time audio commentary for chess moves.
    
    Returns Server-Sent Events (SSE) with audio chunks and transcripts.
    Uses actual move data and Stockfish evaluation to generate grandmaster-level commentary.
    """
    from src.commentary.realtime_audio_client import get_realtime_client
    from src.commentary.triggers import CommentaryTrigger
    from dataclasses import dataclass
    
    logger.info("commentary_stream_requested", 
                san_move=san_move, 
                player=player, 
                evaluation=evaluation,
                trigger=trigger)
    
    try:
        client = get_realtime_client()
        
        if not client or not client.is_available():
            # Return error event
            async def error_stream():
                yield f"data: {json.dumps({'error': 'Audio commentary not available', 'done': True})}\n\n".encode('utf-8')
            
            return StreamingResponse(
                error_stream(),
                media_type="text/event-stream"
            )
        
        # Build a simplified trigger context-like object for prompt generation
        # Use dataclass to match what _build_prompt expects
        @dataclass
        class SimpleTriggerContext:
            trigger: CommentaryTrigger
            player: str
            move: str  # UCI move (we'll use san_move for now)
            san_move: str
            move_number: int
            eval_before: Optional[int] = None
            eval_after: Optional[int] = None
            eval_swing: Optional[int] = None
            centipawn_loss: float = 0.0
            quality: str = "good"
            is_best_move: bool = False
            best_move_alternative: Optional[str] = None
            game_phase: str = "middlegame"
            material_balance: int = 0
            position_type: str = "normal"
            is_check: bool = False
            is_checkmate: bool = False
            tactical_motif: Optional[str] = None
        
        # Determine trigger type
        try:
            trigger_enum = CommentaryTrigger[trigger.upper()]
        except (KeyError, AttributeError):
            trigger_enum = CommentaryTrigger.TACTICAL  # Default to TACTICAL for generic moves
        
        # Determine quality based on evaluation change
        quality = "good"
        if eval_change is not None:
            abs_change = abs(eval_change)
            if eval_change < -300:
                quality = "blunder"
                trigger_enum = CommentaryTrigger.BLUNDER
            elif eval_change < -100:
                quality = "mistake"
            elif eval_change > 100:
                quality = "excellent"
                trigger_enum = CommentaryTrigger.BRILLIANT
        
        # Determine game phase based on move number
        game_phase = "opening"
        if move_number and move_number > 15:
            game_phase = "middlegame"
        if move_number and move_number > 40:
            game_phase = "endgame"
        
        # Create simplified context
        context = SimpleTriggerContext(
            trigger=trigger_enum,
            player=player,
            move=san_move,  # Using san_move for both move and san_move
            san_move=san_move,
            move_number=move_number or 1,
            eval_after=evaluation,
            eval_swing=eval_change,
            centipawn_loss=abs(eval_change) if eval_change else 0.0,
            quality=quality,
            game_phase=game_phase,
        )
        
        # Import CommentaryGenerator to use its prompt building
        from src.commentary.commentary_generator import CommentaryGenerator
        
        # Create a temporary generator instance just for prompt building
        temp_generator = CommentaryGenerator()
        
        # Build the proper chess commentary prompt
        game_context = {
            "move_number": move_number or 1,
            "fen": fen,
        }
        
        # Without evaluation data, create a simpler, more engaging prompt
        if evaluation is None and eval_change is None:
            # Simple prompt that works without evaluation
            prompt = f"""You are an enthusiastic, knowledgeable chess commentator providing exciting live commentary.

Player: {player.capitalize()}
Move: {san_move}
Move number: {move_number or 1}
Game phase: {game_phase}

Generate energetic, insightful commentary in 2-3 sentences about this move:
1. What the move accomplishes (development, central control, attacking, defending)
2. The strategic or tactical idea behind it
3. How it fits into the current game plan

Be enthusiastic like a sports commentator! Focus on what makes this move interesting or important in the position. Use phrases like "Excellent choice!", "Solid play!", "Building pressure!", "Developing with purpose!"

Keep it short and exciting - maximum 3 sentences!"""
            
            logger.debug("using_simple_prompt_no_evaluation", 
                        san_move=san_move,
                        player=player,
                        game_phase=game_phase)
        else:
            # Try to use the template-based prompt
            try:
                prompt = temp_generator._build_prompt(context, game_context)
            except Exception as e:
                logger.warning("prompt_build_failed", error=str(e))
                # Fallback to simple prompt
                prompt = f"""You are an enthusiastic chess commentator. 

{player.capitalize()} plays {san_move}!

Generate exciting 2-3 sentence commentary about this move. Be energetic and knowledgeable like a grandmaster chess commentator!"""
        
        logger.debug("commentary_prompt_built", 
                    trigger=trigger_enum.value,
                    quality=quality,
                    prompt_length=len(prompt))
        
        # Stream commentary audio with proper prompt
        async def generate():
            try:
                async for event in client.stream_commentary_audio(prompt, voice_style="excited"):
                    if event.get('audio'):
                        data = json.dumps({'audio': event['audio']})
                        yield f"data: {data}\n\n".encode('utf-8')
                    
                    if event.get('text'):
                        data = json.dumps({'text': event['text']})
                        yield f"data: {data}\n\n".encode('utf-8')
                    
                    if event.get('done'):
                        data = json.dumps({'done': True})
                        yield f"data: {data}\n\n".encode('utf-8')
                        break
                    
                    if event.get('error'):
                        data = json.dumps({'error': event['error'], 'done': True})
                        yield f"data: {data}\n\n".encode('utf-8')
                        break
                        
            except Exception as e:
                logger.error("commentary_stream_failed", error=str(e))
                data = json.dumps({'error': str(e), 'done': True})
                yield f"data: {data}\n\n".encode('utf-8')
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            }
        )
        
    except Exception as e:
        logger.error("commentary_endpoint_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Commentary stream failed: {str(e)}")


# Stockfish Evaluation Endpoints

class EvaluatePositionRequest(BaseModel):
    """Request body for position evaluation."""
    fen: str = Field(..., description="Position in FEN notation")
    depth: Optional[int] = Field(15, description="Stockfish search depth")


class EvaluatePositionResponse(BaseModel):
    """Response body for position evaluation."""
    fen: str
    evaluation: Optional[int]
    best_move: Optional[str]
    available: bool


class EvaluateMoveRequest(BaseModel):
    """Request body for move evaluation."""
    fen: str = Field(..., description="Position before move in FEN notation")
    move: str = Field(..., description="Move in UCI notation")


class EvaluateMoveResponse(BaseModel):
    """Response body for move evaluation."""
    move: str
    evaluation: Dict[str, Any]
    available: bool


@router.post("/evaluate/position", response_model=EvaluatePositionResponse)
async def evaluate_position(request: EvaluatePositionRequest):
    """Evaluate a chess position using Stockfish.
    
    Returns centipawn evaluation and best move recommendation.
    """
    from src.utils.stockfish_evaluator import get_evaluator
    import chess
    
    try:
        evaluator = get_evaluator()
        
        if not evaluator.is_available():
            return EvaluatePositionResponse(
                fen=request.fen,
                evaluation=None,
                best_move=None,
                available=False
            )
        
        # Parse FEN and evaluate
        board = chess.Board(request.fen)
        evaluation = evaluator.evaluate_position(board)
        best_move = evaluator.get_best_move(board)
        
        return EvaluatePositionResponse(
            fen=request.fen,
            evaluation=evaluation,
            best_move=best_move.uci() if best_move else None,
            available=True
        )
        
    except Exception as e:
        logger.error("position_evaluation_failed", error=str(e), fen=request.fen)
        raise HTTPException(status_code=400, detail=f"Evaluation failed: {str(e)}")


@router.post("/evaluate/move", response_model=EvaluateMoveResponse)
async def evaluate_move(request: EvaluateMoveRequest):
    """Evaluate quality of a specific move using Stockfish.
    
    Returns centipawn loss, move quality rating, and comparison to best move.
    """
    from src.utils.stockfish_evaluator import get_evaluator
    import chess
    
    try:
        evaluator = get_evaluator()
        
        if not evaluator.is_available():
            return EvaluateMoveResponse(
                move=request.move,
                evaluation={"error": "Stockfish not available"},
                available=False
            )
        
        # Parse FEN and move
        board = chess.Board(request.fen)
        move = chess.Move.from_uci(request.move)
        
        # Evaluate move
        evaluation = evaluator.evaluate_move(board, move)
        
        return EvaluateMoveResponse(
            move=request.move,
            evaluation=evaluation,
            available=True
        )
        
    except Exception as e:
        logger.error("move_evaluation_failed", error=str(e), move=request.move)
        raise HTTPException(status_code=400, detail=f"Evaluation failed: {str(e)}")


@router.get("/evaluate/status")
async def evaluation_status():
    """Check if Stockfish evaluation is available."""
    from src.utils.stockfish_evaluator import get_evaluator
    
    evaluator = get_evaluator()
    
    return {
        "available": evaluator.is_available(),
        "stockfish_path": evaluator.stockfish_path if evaluator else None,
        "depth": evaluator.depth if evaluator else None,
        "time_limit": evaluator.time_limit if evaluator else None,
    }
    
    return Response(content=metrics_text, media_type="text/plain")
