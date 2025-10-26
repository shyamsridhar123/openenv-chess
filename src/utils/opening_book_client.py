"""Opening Book Client for querying Lichess Masters database.

Provides opening move recommendations from grandmaster games with
personality-based filtering (aggressive, defensive, balanced).
"""

from typing import Dict, List, Optional, Any, Tuple
import requests
import structlog
from dataclasses import dataclass

logger = structlog.get_logger()


@dataclass
class OpeningMove:
    """Represents a move from the opening book with statistics."""
    
    uci: str
    san: str
    white_wins: int
    draws: int
    black_wins: int
    average_rating: int
    
    @property
    def total_games(self) -> int:
        """Total number of games with this move."""
        return self.white_wins + self.draws + self.black_wins
    
    @property
    def draw_rate(self) -> float:
        """Percentage of games ending in draws (0.0-1.0)."""
        if self.total_games == 0:
            return 0.0
        return self.draws / self.total_games
    
    @property
    def win_rate_for_white(self) -> float:
        """Percentage of games won by white (0.0-1.0)."""
        if self.total_games == 0:
            return 0.0
        return self.white_wins / self.total_games
    
    @property
    def win_rate_for_black(self) -> float:
        """Percentage of games won by black (0.0-1.0)."""
        if self.total_games == 0:
            return 0.0
        return self.black_wins / self.total_games


class OpeningBookClient:
    """Client for querying Lichess Masters opening book API.
    
    Provides move recommendations from grandmaster games (2200+ rated)
    with personality-based filtering for agent move selection.
    """
    
    def __init__(
        self,
        api_url: str = "https://explorer.lichess.ovh/masters",
        timeout: float = 1.0,
        cache_size: int = 1000,
    ):
        """Initialize the opening book client.
        
        Args:
            api_url: Lichess Masters API endpoint
            timeout: Request timeout in seconds
            cache_size: Maximum number of positions to cache
        """
        self.api_url = api_url
        self.timeout = timeout
        self.cache_size = cache_size
        
        # Position cache: fen -> API response
        self._cache: Dict[str, Dict[str, Any]] = {}
        
        logger.info(
            "opening_book_client_initialized",
            api_url=api_url,
            timeout=timeout,
            cache_size=cache_size,
        )
    
    def query_opening_book(self, fen: str) -> Optional[List[OpeningMove]]:
        """Query Lichess Masters database for opening moves.
        
        Args:
            fen: Position in FEN notation
            
        Returns:
            List of opening moves with statistics, or None on failure
        """
        # Check cache first
        if fen in self._cache:
            logger.debug("opening_book_cache_hit", fen=fen)
            response_data = self._cache[fen]
        else:
            # Query API
            try:
                response = requests.get(
                    self.api_url,
                    params={"fen": fen},
                    timeout=self.timeout,
                )
                response.raise_for_status()
                response_data = response.json()
                
                # Cache response (with size limit)
                if len(self._cache) >= self.cache_size:
                    # Remove oldest entry (simple FIFO)
                    first_key = next(iter(self._cache))
                    del self._cache[first_key]
                
                self._cache[fen] = response_data
                
                logger.debug(
                    "opening_book_api_success",
                    fen=fen,
                    moves_count=len(response_data.get("moves", [])),
                )
                
            except requests.Timeout:
                logger.warning("opening_book_timeout", fen=fen, timeout=self.timeout)
                return None
            except requests.RequestException as e:
                logger.warning("opening_book_api_error", fen=fen, error=str(e))
                return None
            except Exception as e:
                logger.error("opening_book_unexpected_error", fen=fen, error=str(e))
                return None
        
        # Parse moves from response
        moves_data = response_data.get("moves", [])
        if not moves_data:
            logger.debug("opening_book_no_moves", fen=fen)
            return None
        
        opening_moves = []
        for move_data in moves_data:
            try:
                opening_move = OpeningMove(
                    uci=move_data["uci"],
                    san=move_data["san"],
                    white_wins=move_data["white"],
                    draws=move_data["draws"],
                    black_wins=move_data["black"],
                    average_rating=move_data.get("averageRating", 2200),
                )
                opening_moves.append(opening_move)
            except (KeyError, TypeError) as e:
                logger.warning("opening_book_parse_error", move_data=move_data, error=str(e))
                continue
        
        if not opening_moves:
            logger.warning("opening_book_no_valid_moves", fen=fen)
            return None
        
        return opening_moves
    
    def select_opening_move(
        self,
        opening_moves: List[OpeningMove],
        personality: str,
        is_white: bool,
    ) -> Optional[str]:
        """Select a move from opening book based on agent personality.
        
        Args:
            opening_moves: List of available opening moves
            personality: Agent personality (aggressive, defensive, balanced, tactical, positional)
            is_white: Whether agent is playing white
            
        Returns:
            Selected move in UCI notation, or None if no suitable move
        """
        if not opening_moves:
            return None
        
        # Filter and sort based on personality
        if personality == "aggressive":
            # Prefer sharp lines (high draw rate = complex positions)
            # Also prefer moves with imbalanced results
            scored_moves = []
            for move in opening_moves:
                # Score based on: game count (popularity) + draw rate (sharpness)
                score = move.total_games * 0.5 + move.draw_rate * 1000
                scored_moves.append((score, move))
            
            scored_moves.sort(key=lambda x: x[0], reverse=True)
            candidates = [move for _, move in scored_moves[:3]]
            
        elif personality == "defensive":
            # Prefer solid lines (low draw rate = theoretical positions)
            # Prefer moves with balanced results
            scored_moves = []
            for move in opening_moves:
                # Score based on: game count + (1 - draw_rate) for solid positions
                score = move.total_games * 0.5 + (1.0 - move.draw_rate) * 1000
                scored_moves.append((score, move))
            
            scored_moves.sort(key=lambda x: x[0], reverse=True)
            candidates = [move for _, move in scored_moves[:3]]
            
        else:  # balanced, tactical, positional
            # Prefer popular moves (play frequency)
            sorted_moves = sorted(opening_moves, key=lambda m: m.total_games, reverse=True)
            candidates = sorted_moves[:3]
        
        if not candidates:
            return None
        
        # Select top candidate (could randomize in future)
        selected = candidates[0]
        
        logger.info(
            "opening_book_move_selected",
            move=selected.uci,
            san=selected.san,
            personality=personality,
            total_games=selected.total_games,
            draw_rate=round(selected.draw_rate, 3),
        )
        
        return selected.uci
    
    def should_use_opening_book(self, move_number: int) -> bool:
        """Check if opening book should be used for this move.
        
        Args:
            move_number: Current move number (1-based)
            
        Returns:
            True if move_number <= 15 (opening phase)
        """
        return move_number <= 15
    
    def clear_cache(self):
        """Clear the position cache."""
        self._cache.clear()
        logger.debug("opening_book_cache_cleared")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache size and capacity
        """
        return {
            "size": len(self._cache),
            "capacity": self.cache_size,
        }
