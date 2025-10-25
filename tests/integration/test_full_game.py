"""Integration tests for Chess OpenEnv API.

Tests the complete game flow via REST API including:
- Game initialization
- Move execution  
- Agent integration
- Game termination

Uses FastAPI TestClient for in-process testing without requiring a running server.
"""

import pytest
from typing import Dict, Any


class TestFullGameFlow:
    """Test complete game flow through REST API."""
    
    def _create_game(self, client):
        """Helper method to create a game and return its ID."""
        response = client.post(
            "/api/v1/reset",
            json={
                "white_agent_id": "test_white",
                "black_agent_id": "test_black"
            }
        )
        assert response.status_code == 200
        return response.json()["game_id"]
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "stats" in data
    
    def test_game_initialization(self, client):
        """Test game creation via /reset endpoint."""
        response = client.post(
            "/api/v1/reset",
            json={
                "white_agent_id": "test_white",
                "black_agent_id": "test_black"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "game_id" in data
        assert "observation" in data
        assert "info" in data
        
        # Verify observation structure
        obs = data["observation"]
        assert "board_state" in obs
        assert "legal_moves" in obs
        assert "current_player" in obs
        assert obs["current_player"] == "white"
        
        # Verify initial position
        assert obs["board_state"]["fen"].startswith("rnbqkbnr/pppppppp")
        assert len(obs["legal_moves"]) == 20  # 20 legal moves in starting position
    
    def test_move_execution(self, client):
        """Test move execution via /step endpoint."""
        # Initialize game
        game_id = self._create_game(client)
        
        # Execute first move (e2e4)
        response = client.post(
            "/api/v1/step",
            json={
                "game_id": game_id,
                "action": "e2e4"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["game_id"] == game_id
        assert "observation" in data
        assert "reward" in data
        assert "terminated" in data
        assert "info" in data
        
        # Verify game state after move
        obs = data["observation"]
        assert obs["current_player"] == "black"  # Turn switched
        assert data["terminated"] is False
        assert data["info"]["san_move"] == "e4"
        assert data["info"]["last_move"] == "e2e4"
    
    def test_invalid_move(self, client):
        """Test invalid move handling."""
        game_id = self._create_game(client)
        
        # Try illegal move
        response = client.post(
            "/api/v1/step",
            json={
                "game_id": game_id,
                "action": "e2e5"  # Invalid - pawn can't jump 3 squares
            }
        )
        assert response.status_code == 400
        assert "Illegal move" in response.json()["detail"]
    
    def test_state_endpoint(self, client):
        """Test state metadata endpoint."""
        game_id = self._create_game(client)
        
        response = client.get(f"/api/v1/state/{game_id}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["game_id"] == game_id
        assert data["status"] == "active"
        assert data["move_count"] == 0
        assert data["current_player"] == "white"
        assert data["is_terminal"] is False
    
    def test_render_endpoint(self, client):
        """Test board rendering endpoint."""
        game_id = self._create_game(client)
        
        # Test ASCII render
        response = client.get(f"/api/v1/render/{game_id}?mode=ascii")
        assert response.status_code == 200
        data = response.json()
        assert "game_id" in data
        assert "board" in data
        ascii_board = data["board"]
        # Check for piece characters in ASCII board
        assert "r" in ascii_board or "R" in ascii_board  # Rook
        assert "k" in ascii_board or "K" in ascii_board  # King
        
        # Test SVG render
        response = client.get(f"/api/v1/render/{game_id}?mode=svg")
        assert response.status_code == 200
        # HTMLResponse returns text/html content-type with SVG content
        assert "text/html" in response.headers["content-type"]
        # Verify SVG content
        assert "<svg" in response.text
        assert "</svg>" in response.text
    
    def test_random_game_completion(self, client):
        """Test complete game with random moves."""
        game_id = self._create_game(client)
        
        # Play random moves until game ends or 20 moves
        move_count = 0
        max_moves = 20
        terminated = False
        
        while not terminated and move_count < max_moves:
            # Get current state
            state_response = client.get(f"/api/v1/state/{game_id}")
            state = state_response.json()
            
            if state["is_terminal"]:
                break
            
            # Get legal moves from last step response or initial state
            if move_count == 0:
                reset_response = client.get(f"/api/v1/state/{game_id}")
                # For first move, we need to get from reset - simplified test
                legal_moves = ["e2e4", "d2d4", "g1f3"]  # Common openings
            else:
                # In real scenario, we'd track legal moves from last step
                legal_moves = ["e2e4"]  # Simplified
            
            # Make a safe move
            import random
            move = random.choice(legal_moves) if legal_moves else "e2e4"
            
            try:
                step_response = client.post(
                    "/api/v1/step",
                    json={"game_id": game_id, "action": move}
                )
                if step_response.status_code == 200:
                    step_data = step_response.json()
                    terminated = step_data["terminated"]
                    move_count += 1
                else:
                    break  # Invalid move, stop test
            except:
                break
        
        assert move_count > 0  # At least one move executed
    
    def test_stats_endpoint(self, client):
        """Test server statistics endpoint."""
        response = client.get("/api/v1/stats")
        assert response.status_code == 200
        data = response.json()
        
        assert "total_games" in data
        assert "active_games" in data
        assert "completed_games" in data
        assert data["total_games"] >= 0
    
    def test_metrics_endpoint(self, client):
        """Test Prometheus metrics endpoint."""
        response = client.get("/api/v1/metrics")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
        
        metrics_text = response.text
        assert "chess_games_total" in metrics_text
        assert "chess_games_active" in metrics_text


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
