"""
Syzygy Tablebase Client for perfect endgame play.

Queries Lichess Tablebase API for positions with 7 or fewer pieces,
providing optimal moves with forced win/draw/loss evaluations.
"""

import httpx
import structlog
from typing import Optional, Dict, Any
from functools import lru_cache

logger = structlog.get_logger(__name__)


class TablebaseClient:
    """Client for querying Syzygy tablebase via Lichess API."""
    
    def __init__(
        self,
        api_url: str = "https://tablebase.lichess.ovh/standard",
        timeout: float = 1.0,
        cache_size: int = 1000
    ):
        """
        Initialize tablebase client.
        
        Args:
            api_url: Lichess tablebase API endpoint
            timeout: API request timeout in seconds
            cache_size: Number of positions to cache per game session
        """
        self.api_url = api_url
        self.timeout = timeout
        self._session_cache: Dict[str, Dict[str, Any]] = {}
        
        logger.info(
            "tablebase_client_initialized",
            api_url=api_url,
            timeout=timeout,
            cache_size=cache_size
        )
    
    def should_query_tablebase(self, fen: str) -> bool:
        """
        Check if position should be queried in tablebase (7 or fewer pieces).
        
        Args:
            fen: Position in FEN notation
            
        Returns:
            True if position has 7 or fewer pieces
        """
        # Count pieces in FEN (first field contains piece placement)
        piece_placement = fen.split()[0]
        # Remove rank separators and empty square numbers
        pieces = piece_placement.replace("/", "")
        piece_count = sum(1 for c in pieces if c.isalpha())
        
        return piece_count <= 7
    
    def query_position(self, fen: str) -> Optional[Dict[str, Any]]:
        """
        Query tablebase for optimal move in position.
        
        Args:
            fen: Position in FEN notation
            
        Returns:
            Dict with 'uci' (best move), 'wdl' (win/draw/loss), 'dtz' (distance to zero)
            None if position not in tablebase or error occurred
        """
        # Check cache first
        if fen in self._session_cache:
            logger.debug("tablebase_cache_hit", fen=fen)
            return self._session_cache[fen]
        
        # Check piece count
        if not self.should_query_tablebase(fen):
            logger.debug("tablebase_skipped_too_many_pieces", fen=fen)
            return None
        
        try:
            logger.debug("tablebase_api_query", fen=fen, api_url=self.api_url)
            
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    self.api_url,
                    params={"fen": fen}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Lichess API returns moves array with evaluations
                    if "moves" in data and len(data["moves"]) > 0:
                        # Get best move (first in sorted list)
                        best_move = data["moves"][0]
                        
                        # WDL can be in move object or category
                        # Convert category to WDL: win=2, maybe-win=1, draw=0, maybe-loss=-1, loss=-2
                        category = data.get("category", "unknown")
                        wdl = best_move.get("wdl")
                        if wdl is None:
                            category_to_wdl = {
                                "win": 2,
                                "maybe-win": 1,
                                "draw": 0,
                                "maybe-loss": -1,
                                "loss": -2
                            }
                            wdl = category_to_wdl.get(category, 0)
                        
                        result = {
                            "uci": best_move["uci"],
                            "wdl": wdl,  # 2=win, 1=cursed win, 0=draw, -1=blessed loss, -2=loss
                            "dtz": best_move.get("dtz"),  # Distance to zeroing (capture/pawn move)
                            "category": category  # win/maybe-win/draw/maybe-loss/loss
                        }
                        
                        # Cache result
                        self._session_cache[fen] = result
                        
                        logger.info(
                            "tablebase_api_success",
                            fen=fen,
                            move=result["uci"],
                            wdl=result["wdl"],
                            category=result["category"]
                        )
                        
                        return result
                    else:
                        logger.debug("tablebase_position_not_found", fen=fen)
                        return None
                        
                elif response.status_code == 404:
                    # Position not in tablebase (e.g., too many pieces or illegal position)
                    logger.debug("tablebase_position_not_found", fen=fen)
                    return None
                else:
                    logger.warning(
                        "tablebase_api_error",
                        status_code=response.status_code,
                        fen=fen
                    )
                    return None
                    
        except httpx.TimeoutException:
            logger.warning("tablebase_timeout", fen=fen, timeout=self.timeout)
            return None
        except Exception as e:
            logger.error("tablebase_query_failed", error=str(e), fen=fen)
            return None
    
    def clear_cache(self):
        """Clear session cache. Call between games."""
        cache_size = len(self._session_cache)
        self._session_cache.clear()
        logger.debug("tablebase_cache_cleared", entries_cleared=cache_size)
    
    def is_winning(self, wdl: Optional[int]) -> bool:
        """
        Check if WDL score indicates a winning position.
        
        Args:
            wdl: Win/Draw/Loss score (2=win, 1=cursed win, 0=draw, -1=blessed loss, -2=loss)
            
        Returns:
            True if position is winning (wdl >= 1)
        """
        return wdl is not None and wdl >= 1
    
    def is_drawing(self, wdl: Optional[int]) -> bool:
        """
        Check if WDL score indicates a drawn position.
        
        Args:
            wdl: Win/Draw/Loss score
            
        Returns:
            True if position is drawn (wdl == 0)
        """
        return wdl is not None and wdl == 0
    
    def is_losing(self, wdl: Optional[int]) -> bool:
        """
        Check if WDL score indicates a losing position.
        
        Args:
            wdl: Win/Draw/Loss score
            
        Returns:
            True if position is losing (wdl <= -1)
        """
        return wdl is not None and wdl <= -1
