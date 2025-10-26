"""Azure GPT Realtime Audio API client for chess commentary.

Provides audio generation using Azure's GPT Realtime API (gpt-realtime-mini)
for natural-sounding chess commentary.
"""

from typing import Optional, Dict, Any
import structlog
import os
import base64
import asyncio
from openai import AsyncAzureOpenAI

logger = structlog.get_logger()


class RealtimeAudioClient:
    """Client for Azure GPT Realtime Audio API."""
    
    def __init__(self):
        """Initialize realtime audio client."""
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.deployment = os.getenv("AZURE_OPENAI_AUDIO_DEPLOYMENT_NAME", "gpt-realtime-mini")
        # Use 2024-10-01-preview for realtime API (latest supported version)
        self.api_version = "2024-10-01-preview"
        
        if not all([self.endpoint, self.api_key]):
            logger.warning(
                "realtime_audio_client_not_configured",
                endpoint_set=bool(self.endpoint),
                key_set=bool(self.api_key),
            )
            self.client = None
        else:
            self.client = AsyncAzureOpenAI(
                azure_endpoint=self.endpoint,
                api_key=self.api_key,
                api_version=self.api_version,
            )
            logger.info(
                "realtime_audio_client_initialized",
                deployment=self.deployment,
            )
    
    def is_available(self) -> bool:
        """Check if realtime audio client is available."""
        return self.client is not None
    
    async def generate_commentary_audio(
        self,
        prompt: str,
        voice_style: str = "excited",
    ) -> Dict[str, Any]:
        """Generate audio commentary using GPT Realtime API.
        
        Args:
            prompt: Commentary prompt/text to speak
            voice_style: Voice style (excited/professional/calm)
            
        Returns:
            Dictionary with audio data and transcript
        """
        if not self.client:
            logger.warning("realtime_audio_client_unavailable")
            return {
                "text": "Audio commentary unavailable",
                "audio": None,
                "error": "Client not configured"
            }
        
        try:
            logger.debug(
                "generating_audio_commentary",
                voice_style=voice_style,
                prompt_length=len(prompt),
            )
            
            audio_chunks = []
            transcript_text = ""
            
            async with self.client.beta.realtime.connect(model=self.deployment) as connection:
                # Update session with anti-sycophancy instructions (use 'modalities' not 'output_modalities')
                await connection.session.update(session={
                    "modalities": ["text", "audio"],
                    "instructions": """You are a grandmaster-level chess commentator with ANALYTICAL depth and CURIOSITY.
                            
KEY RULES:
1. NO SYCOPHANCY - NEVER say "Excellent choice", "Solid play", "Great move", "Building pressure", "Sets the stage"
2. Be CURIOUS and ANALYTICAL - "Interesting", "This aims for...", "The idea is...", "Following the plan..."
3. For OPENING moves (moves 1-15): ALWAYS connect to classical games, historical players, or theoretical lines
   - Example: "This follows Fischer's approach in the 1972 World Championship"
   - Example: "The Najdorf variation, Kasparov's favorite weapon"
   - Example: "Echoing Botvinnik-Tal, 1960, Game 6"
   - Example: "A theoretical novelty—deviating from the main line"
4. Be ANALYTICAL not PRAISING - Focus on PLANS, IDEAS, and CONSEQUENCES
5. Match tone to situation (critical for blunders, curious/analytical for opening, clinical for tactics)
6. Reference the actual player who moved (don't mix up Black and White)
7. VARY vocabulary - never repeat the same phrases
                            
FORBIDDEN PHRASES (NEVER USE):
- "Excellent choice!" ❌
- "Solid play!" ❌
- "Great move!" ❌
- "Building pressure!" ❌
- "Sets the stage!" ❌
- "With purpose!" ❌
- "Right out of the gate!" ❌
- "Let's see how [opponent] responds!" ❌

GOOD examples for OPENING moves:
- "Nf3 develops the knight, following the Italian Game setup seen in Morphy's games"
- "This transpose into the Ruy Lopez, a favorite of Capablanca"
- "The Sicilian Defense—Black invites sharp tactical play"
- "Following the main theoretical line of the King's Indian"
- "An interesting sideline, avoided by most top players"
                            
GOOD examples for MIDDLEGAME:
- "The position becomes complicated after this"
- "This creates concrete threats on the kingside"
- "An interesting choice—White invites tactical complications"
- "The position resembles Kasparov-Karpov 1985"
                            
Bad examples (NEVER use):
- "Excellent choice!" ❌
- "Solid play that sets the stage for a powerful middle game!" ❌
- "Building pressure on White right out of the gate!" ❌"""
                })
                
                # Send the prompt
                await connection.conversation.item.create(
                    item={
                        "type": "message",
                        "role": "user",
                        "content": [{"type": "input_text", "text": prompt}]
                    }
                )
                
                # Request response
                await connection.response.create()
                
                # Collect audio chunks
                async for event in connection:
                    if event.type == "response.audio.delta":
                        audio_chunks.append(event.delta)
                    
                    elif event.type == "response.audio_transcript.delta":
                        transcript_text += event.delta
                    
                    elif event.type == "response.done":
                        break
            
            # Combine audio chunks
            audio_data = "".join(audio_chunks) if audio_chunks else None
            
            logger.info(
                "audio_commentary_generated",
                text_length=len(transcript_text),
                audio_chunks=len(audio_chunks),
                has_audio=audio_data is not None,
            )
            
            return {
                "text": transcript_text or prompt,
                "audio": audio_data,
                "format": "pcm16",
                "voice_style": voice_style,
            }
            
        except Exception as e:
            logger.error(
                "audio_commentary_generation_failed",
                error=str(e),
                voice_style=voice_style,
            )
            return {
                "text": prompt,
                "audio": None,
                "error": str(e),
            }
    
    async def stream_commentary_audio(
        self,
        prompt: str,
        voice_style: str = "excited",
    ):
        """Stream audio commentary using GPT Realtime API.
        
        Args:
            prompt: Commentary prompt/text to speak
            voice_style: Voice style (excited/professional/calm)
            
        Yields:
            Audio chunks as they're generated
        """
        if not self.client:
            logger.warning("realtime_audio_client_unavailable")
            yield {
                "error": "Client not configured",
                "done": True,
            }
            return
        
        try:
            logger.debug(
                "streaming_audio_commentary",
                voice_style=voice_style,
            )
            
            async with self.client.beta.realtime.connect(model=self.deployment) as connection:
                # Update session with anti-sycophancy instructions (use 'modalities' not 'output_modalities')
                await connection.session.update(session={
                    "modalities": ["text", "audio"],
                    "instructions": """You are a grandmaster-level chess commentator with ANALYTICAL depth and CURIOSITY.
                            
KEY RULES:
1. NO SYCOPHANCY - NEVER say "Excellent choice", "Solid play", "Great move", "Building pressure", "Sets the stage"
2. Be CURIOUS and ANALYTICAL - "Interesting", "This aims for...", "The idea is...", "Following the plan..."
3. For OPENING moves (moves 1-15): ALWAYS connect to classical games, historical players, or theoretical lines
   - Example: "This follows Fischer's approach in the 1972 World Championship"
   - Example: "The Najdorf variation, Kasparov's favorite weapon"
   - Example: "Echoing Botvinnik-Tal, 1960, Game 6"
   - Example: "A theoretical novelty—deviating from the main line"
4. Be ANALYTICAL not PRAISING - Focus on PLANS, IDEAS, and CONSEQUENCES
5. Match tone to situation (critical for blunders, curious/analytical for opening, clinical for tactics)
6. Reference the actual player who moved (don't mix up Black and White)
7. VARY vocabulary - never repeat the same phrases
                            
FORBIDDEN PHRASES (NEVER USE):
- "Excellent choice!" ❌
- "Solid play!" ❌
- "Great move!" ❌
- "Building pressure!" ❌
- "Sets the stage!" ❌
- "With purpose!" ❌
- "Right out of the gate!" ❌
- "Let's see how [opponent] responds!" ❌

GOOD examples for OPENING moves:
- "Nf3 develops the knight, following the Italian Game setup seen in Morphy's games"
- "This transpose into the Ruy Lopez, a favorite of Capablanca"
- "The Sicilian Defense—Black invites sharp tactical play"
- "Following the main theoretical line of the King's Indian"
- "An interesting sideline, avoided by most top players"
                            
GOOD examples for MIDDLEGAME:
- "The position becomes complicated after this"
- "This creates concrete threats on the kingside"
- "An interesting choice—White invites tactical complications"
- "The position resembles Kasparov-Karpov 1985"
                            
Bad examples (NEVER use):
- "Excellent choice!" ❌
- "Solid play that sets the stage for a powerful middle game!" ❌
- "Building pressure on White right out of the gate!" ❌"""
                })
                
                # Send the prompt
                await connection.conversation.item.create(
                    item={
                        "type": "message",
                        "role": "user",
                        "content": [{"type": "input_text", "text": prompt}]
                    }
                )
                
                # Request response
                await connection.response.create()
                
                # Stream audio chunks as they arrive
                async for event in connection:
                    if event.type == "response.audio.delta":
                        yield {
                            "audio": event.delta,  # Already base64 encoded
                            "done": False,
                        }
                    
                    elif event.type == "response.audio_transcript.delta":
                        yield {
                            "text": event.delta,
                            "done": False,
                        }
                    
                    elif event.type == "response.done":
                        yield {"done": True}
                        break
                    
                    elif event.type == "error":
                        # Log error but continue - API sends non-fatal errors for unknown parameters
                        logger.warning("realtime_stream_error", error=event.error)
                        # Don't break - continue processing
                
        except Exception as e:
            logger.error(
                "audio_streaming_failed",
                error=str(e),
            )
            yield {
                "error": str(e),
                "done": True,
            }


def get_realtime_client() -> Optional[RealtimeAudioClient]:
    """Get or create realtime audio client.
    
    Returns:
        RealtimeAudioClient instance or None if not configured
    """
    try:
        client = RealtimeAudioClient()
        return client if client.client else None
    except Exception as e:
        logger.error("failed_to_create_realtime_client", error=str(e))
        return None
