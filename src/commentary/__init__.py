"""Chess commentary system with Azure GPT Realtime Audio.

Provides live, exciting commentary for chess games based on:
- Stockfish move evaluations
- Tactical pattern detection
- Historical game references
- Real-time audio streaming
"""

from .triggers import CommentaryTrigger, TriggerDetector
from .commentary_generator import CommentaryGenerator

__all__ = ["CommentaryTrigger", "TriggerDetector", "CommentaryGenerator"]
