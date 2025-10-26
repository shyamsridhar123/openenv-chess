"""Opening name detection and historical context.

Maps move sequences to opening names with historical references.
"""

from typing import Optional, Dict, List, Tuple
import chess
import structlog

logger = structlog.get_logger()


# Opening book: maps move sequence (UCI) to opening info
OPENING_DATABASE = {
    # Sicilian Defense family
    ("e2e4", "c7c5"): {
        "name": "Sicilian Defense",
        "context": "Bobby Fischer's weapon of choice for aggressive counterplay",
        "description": "Black's sharpest response to 1.e4, aiming for dynamic imbalance"
    },
    ("e2e4", "c7c5", "g1f3", "d7d6", "d2d4"): {
        "name": "Sicilian Defense, Open Variation",
        "context": "The main battleground of modern chess theory",
        "description": "White opens the center while Black prepares counterattack"
    },
    ("e2e4", "c7c5", "g1f3", "d7d6", "d2d4", "c5d4", "f3d4", "g8f6"): {
        "name": "Sicilian Defense, Najdorf Variation",
        "context": "Garry Kasparov's lifetime favorite, known for its complexity",
        "description": "A hypermodern opening with tactical fireworks and deep positional play"
    },
    
    # Ruy Lopez family
    ("e2e4", "e7e5", "g1f3", "b8c6", "f1b5"): {
        "name": "Ruy Lopez (Spanish Opening)",
        "context": "One of the oldest openings, named after 16th-century Spanish priest",
        "description": "Classical opening focusing on central control and piece development"
    },
    ("e2e4", "e7e5", "g1f3", "b8c6", "f1b5", "a7a6"): {
        "name": "Ruy Lopez, Morphy Defense",
        "context": "Named after Paul Morphy, the American chess prodigy",
        "description": "The most popular continuation, with rich strategic possibilities"
    },
    
    # Queen's Gambit family
    ("d2d4", "d7d5", "c2c4"): {
        "name": "Queen's Gambit",
        "context": "Made famous by Netflix series, a classical strategic opening",
        "description": "White offers a pawn to gain central control and rapid development"
    },
    ("d2d4", "d7d5", "c2c4", "d5c4"): {
        "name": "Queen's Gambit Accepted",
        "context": "A pragmatic approach favored by solid positional players",
        "description": "Black accepts the gambit pawn, leading to open play"
    },
    ("d2d4", "d7d5", "c2c4", "e7e6"): {
        "name": "Queen's Gambit Declined",
        "context": "Steinitz's favorite defense, emphasizing solid central control",
        "description": "Classical setup maintaining tension in the center"
    },
    
    # King's Indian Defense
    ("d2d4", "g8f6", "c2c4", "g7g6"): {
        "name": "King's Indian Defense",
        "context": "Fischer and Kasparov's aggressive weapon against 1.d4",
        "description": "Hypermodern defense allowing White center then attacking it violently"
    },
    ("d2d4", "g8f6", "c2c4", "g7g6", "b1c3", "f8g7"): {
        "name": "King's Indian Defense, Classical Variation",
        "context": "The most principled continuation of the King's Indian",
        "description": "Both sides castle kingside before launching opposite-wing attacks"
    },
    
    # French Defense
    ("e2e4", "e7e6"): {
        "name": "French Defense",
        "context": "Botvinnik's strategic choice, creating unique pawn structures",
        "description": "Solid defense leading to closed positions with piece maneuvering"
    },
    ("e2e4", "e7e6", "d2d4", "d7d5"): {
        "name": "French Defense, Main Line",
        "context": "Rich strategic ground with clear plans for both sides",
        "description": "Black challenges White's pawn center immediately"
    },
    
    # Caro-Kann Defense
    ("e2e4", "c7c6"): {
        "name": "Caro-Kann Defense",
        "context": "Anatoly Karpov's solid choice for positional advantage",
        "description": "Robust defense leading to sound positions without weaknesses"
    },
    
    # Italian Game
    ("e2e4", "e7e5", "g1f3", "b8c6", "f1c4"): {
        "name": "Italian Game",
        "context": "One of the oldest recorded openings, dating back to Greco in 1620",
        "description": "Classical development focusing on quick piece mobilization"
    },
    
    # English Opening
    ("c2c4",): {
        "name": "English Opening",
        "context": "Modern flexible opening, popular among World Champions",
        "description": "Transpositional system controlling center from the flank"
    },
    
    # Nimzo-Indian Defense
    ("d2d4", "g8f6", "c2c4", "e7e6", "b1c3", "f8b4"): {
        "name": "Nimzo-Indian Defense",
        "context": "Aron Nimzowitsch's hypermodern masterpiece",
        "description": "Black pins the knight, challenging White's central control"
    },
    
    # Grünfeld Defense
    ("d2d4", "g8f6", "c2c4", "g7g6", "b1c3", "d7d5"): {
        "name": "Grünfeld Defense",
        "context": "Fischer and Kasparov's dynamic choice",
        "description": "Black allows massive White center then demolishes it"
    },
    
    # Scandinavian Defense
    ("e2e4", "d7d5"): {
        "name": "Scandinavian Defense (Center Counter)",
        "context": "Bold counterattacking opening gaining modern popularity",
        "description": "Black challenges the center immediately with the d-pawn"
    },
    
    # Alekhine's Defense
    ("e2e4", "g8f6"): {
        "name": "Alekhine's Defense",
        "context": "Named after Alexander Alekhine, 4th World Champion",
        "description": "Provocative defense inviting White to overextend the center"
    },
    
    # Pirc Defense
    ("e2e4", "d7d6", "d2d4", "g8f6", "b1c3", "g7g6"): {
        "name": "Pirc Defense",
        "context": "Modern flexible setup popular in club and GM play",
        "description": "Similar to King's Indian but avoiding early commitment"
    },
    
    # London System
    ("d2d4", "g8f6", "g1f3", "d7d5", "c1f4"): {
        "name": "London System",
        "context": "Popular at all levels for its solid, systematic approach",
        "description": "Reliable setup with early bishop development to f4"
    },
}


def detect_opening(move_history: List[str]) -> Optional[Dict[str, str]]:
    """Detect opening name and context from move history.
    
    Args:
        move_history: List of moves in UCI format (e.g., ["e2e4", "c7c5", ...])
        
    Returns:
        Dictionary with:
        - name: Opening name
        - context: Historical/cultural context
        - description: Strategic description
        Returns None if opening not recognized
    """
    if not move_history:
        return None
    
    # Try to match progressively longer sequences (longest match wins)
    best_match = None
    best_length = 0
    
    for length in range(min(len(move_history), 10), 0, -1):
        sequence = tuple(move_history[:length])
        if sequence in OPENING_DATABASE:
            opening_info = OPENING_DATABASE[sequence]
            if length > best_length:
                best_match = opening_info
                best_length = length
    
    if best_match:
        logger.debug(
            "opening_detected",
            opening=best_match["name"],
            moves_matched=best_length,
        )
        return best_match
    
    # Fallback: identify opening family from first few moves
    if len(move_history) >= 1:
        first_move = move_history[0]
        if first_move == "e2e4":
            return {
                "name": "King's Pawn Opening",
                "context": "Classical aggressive opening, most popular at all levels",
                "description": "White seizes central space and opens lines for pieces"
            }
        elif first_move == "d2d4":
            return {
                "name": "Queen's Pawn Opening",
                "context": "Strategic opening favoring positional maneuvering",
                "description": "Solid central control with slower, strategic play"
            }
        elif first_move == "c2c4":
            return {
                "name": "English Opening",
                "context": "Modern flexible opening system",
                "description": "Transpositional flank opening with rich possibilities"
            }
        elif first_move == "g1f3":
            return {
                "name": "Réti Opening",
                "context": "Hypermodern approach named after Richard Réti",
                "description": "Knight development first, controlling center from afar"
            }
    
    return None


def get_opening_context(move_history: List[str]) -> str:
    """Get contextual commentary about the opening.
    
    Args:
        move_history: List of moves in UCI format
        
    Returns:
        String with opening context for commentary, or empty string if unknown
    """
    opening = detect_opening(move_history)
    
    if not opening:
        return ""
    
    # Format context for commentary
    return f"Playing the {opening['name']}, {opening['context']}. {opening['description']}"


def is_opening_phase(move_number: int) -> bool:
    """Determine if we're still in opening phase.
    
    Args:
        move_number: Current move number
        
    Returns:
        True if still in opening phase (typically first 10-15 moves)
    """
    return move_number <= 15
