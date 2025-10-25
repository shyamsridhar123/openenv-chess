"""Chess commentary generator using Azure GPT with excitement and historical context.

Generates engaging, energizing commentary for chess moves based on:
- Move quality and evaluation
- Tactical patterns
- Game phase and context
- Historical chess references
"""

from typing import Optional, Dict, Any
import structlog
import os
from openai import AzureOpenAI

from .triggers import CommentaryTrigger, TriggerContext
from .realtime_audio_client import get_realtime_client

logger = structlog.get_logger()


class CommentaryGenerator:
    """Generates exciting chess commentary."""
    
    # Prompt templates for different trigger types
    PROMPT_TEMPLATES = {
        CommentaryTrigger.BLUNDER: """You are an excited chess commentator. A BLUNDER just happened!

Player: {player}
Move: {san_move}
Quality: BLUNDER (-{cp_loss} centipawns!)
Better move was: {best_move}
Position went from {eval_before} to {eval_after}

Generate excited, dramatic commentary in 2-3 sentences explaining:
1. What terrible mistake was just made
2. Why this move is so bad
3. How the game dynamics have changed

Be energetic and engaging like a sports commentator! Use phrases like "Oh no!", "What a disaster!", "This could be game-changing!"
""",
        
        CommentaryTrigger.BRILLIANT: """You are an enthusiastic chess commentator. A BRILLIANT move just happened!

Player: {player}
Move: {san_move}
Quality: BRILLIANT! (Best move, +{eval_swing} advantage!)
Position evaluation: {eval_before} → {eval_after}
Phase: {game_phase}

Generate excited, appreciative commentary in 2-3 sentences explaining:
1. Why this move is so brilliant
2. The tactical or strategic genius behind it
3. How it shifts the game momentum

Be enthusiastic like a sports commentator celebrating a great play! Use phrases like "Magnificent!", "What a move!", "Pure genius!"
""",
        
        CommentaryTrigger.TACTICAL: """You are an energetic chess commentator. A TACTICAL pattern just appeared!

Player: {player}
Move: {san_move}
Tactical Pattern: {tactical_motif}
Position evaluation: {eval_before} → {eval_after}
Move quality: {quality}

Generate exciting commentary in 2-3 sentences explaining:
1. The tactical pattern being executed (fork/pin/skewer/etc.)
2. What pieces are under attack or being threatened
3. The immediate consequences

Be engaging and help viewers see the tactics! Use phrases like "Beautiful combination!", "Tactical strike!", "Watch this sequence!"
""",
        
        CommentaryTrigger.CHECKMATE: """You are a dramatic chess commentator. CHECKMATE has been delivered!

Winner: {player}
Final move: {san_move}
Game phase: {game_phase}
Move number: {move_number}

Generate dramatic, conclusive commentary in 2-3 sentences:
1. Announce the checkmate emphatically
2. Describe how the winning attack was executed
3. Summarize the key moments that led to victory

Be dramatic and conclusive! Use phrases like "Checkmate!", "Game over!", "Victory is sealed!", "What a finish!"
""",
        
        CommentaryTrigger.SACRIFICE: """You are an excited chess commentator. A SACRIFICE just happened!

Player: {player}
Move: {san_move} (sacrificing material!)
Evaluation swing: +{eval_swing}
Position: {eval_before} → {eval_after}

Generate thrilling commentary in 2-3 sentences explaining:
1. What material was sacrificed
2. The compensation (attack, position, initiative)
3. Whether it's sound or risky

Be thrilling like a commentator during a risky sports play! Use phrases like "Bold sacrifice!", "High stakes!", "Will it pay off?"
""",
        
        CommentaryTrigger.DEFENSIVE_BRILLIANCE: """You are an appreciative chess commentator. A DEFENSIVE MASTERCLASS!

Player: {player}
Move: {san_move}
Under pressure: {is_check} (check!)
Quality: {quality}
Evaluation: {eval_before} → {eval_after}

Generate appreciative commentary in 2-3 sentences:
1. The defensive challenge faced
2. How the player solved it skillfully
3. Whether the danger is now averted

Be appreciative of defensive skill! Use phrases like "Excellent defense!", "Cool under pressure!", "Crisis averted!"
""",
        
        CommentaryTrigger.GAME_START: """You are an enthusiastic chess commentator. The game is STARTING!

White: {white_agent}
Black: {black_agent}
Opening position ready

Generate welcoming, energetic commentary in 2-3 sentences:
1. Welcome viewers to this exciting match
2. Introduce the competing agents/styles
3. Build anticipation for the game ahead

Be welcoming and exciting! Use phrases like "Welcome to this exciting match!", "Let's see what unfolds!", "The battle begins!"
""",
        
        CommentaryTrigger.CRITICAL_MISTAKE: """You are a dramatic chess commentator. A CRITICAL MISTAKE just occurred!

Player: {player}
Move: {san_move}
Centipawn loss: {cp_loss}
Position: {eval_before} → {eval_after} (major swing!)
Better alternative: {best_move}

Generate dramatic commentary in 2-3 sentences:
1. The magnitude of this error
2. What opportunity was missed or given away
3. How the game balance has shifted

Be dramatic about the turning point! Use phrases like "Critical error!", "The momentum has shifted!", "This could decide the game!"
""",
    }
    
    def __init__(self):
        """Initialize commentary generator with Azure OpenAI."""
        # Get configuration from environment
        self.mode = os.getenv("COMMENTARY_MODE", "text")  # audio, text, or both
        self.voice_style = os.getenv("COMMENTARY_VOICE_STYLE", "excited")
        
        # Initialize clients based on mode
        self.text_client = None
        self.audio_client = None
        
        if self.mode in ["text", "both"]:
            # Initialize text client (GPT-4)
            deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1")
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            api_key = os.getenv("AZURE_OPENAI_API_KEY")
            api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
            
            if endpoint and api_key:
                self.text_client = AzureOpenAI(
                    azure_endpoint=endpoint,
                    api_key=api_key,
                    api_version=api_version,
                )
                self.text_deployment = deployment
        
        if self.mode in ["audio", "both"]:
            # Initialize audio client (GPT Realtime)
            self.audio_client = get_realtime_client()
        
        # Check if at least one client is configured
        if not self.text_client and not self.audio_client:
            logger.warning(
                "commentary_generator_not_configured",
                deployment_set=bool(os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")),
                endpoint_set=bool(os.getenv("AZURE_OPENAI_ENDPOINT")),
                key_set=bool(os.getenv("AZURE_OPENAI_API_KEY")),
            )
        else:
            logger.info(
                "commentary_generator_initialized",
                deployment=os.getenv("AZURE_OPENAI_AUDIO_DEPLOYMENT_NAME" if self.mode == "audio" else "AZURE_OPENAI_DEPLOYMENT_NAME"),
                mode=self.mode,
            )
    
    def is_available(self) -> bool:
        """Check if commentary generator is available (has at least one client configured)."""
        return self.text_client is not None or self.audio_client is not None

    
    async def generate_commentary(
        self,
        trigger_context: TriggerContext,
        game_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate commentary for a move.
        
        Args:
            trigger_context: Trigger context with move and evaluation data
            game_context: Additional game context
            
        Returns:
            Dictionary with commentary text and optionally audio
        """
        # Check if any client is available
        if not self.text_client and not self.audio_client:
            return {
                "text": f"{trigger_context.player} plays {trigger_context.san_move}",
                "audio": None,
                "trigger": trigger_context.trigger.value,
                "error": "Commentary generator not configured",
            }
        
        try:
            # Build prompt from template
            prompt = self._build_prompt(trigger_context, game_context)
            
            logger.debug(
                "generating_commentary",
                trigger=trigger_context.trigger.value,
                player=trigger_context.player,
                move=trigger_context.san_move,
                mode=self.mode,
            )
            
            result = {
                "trigger": trigger_context.trigger.value,
                "priority": trigger_context.priority,
                "move": trigger_context.san_move,
                "player": trigger_context.player,
            }
            
            # Route to appropriate client based on mode
            if self.mode == "audio" and self.audio_client:
                # Audio mode: Use realtime audio API (gpt-realtime-mini)
                logger.info("using_audio_client", deployment="gpt-realtime-mini")
                audio_result = await self.audio_client.generate_commentary_audio(
                    prompt,
                    voice_style=self.voice_style,
                )
                result["audio"] = audio_result.get("audio")
                result["text"] = audio_result.get("text", f"{trigger_context.player} plays {trigger_context.san_move}")
                
            elif self.mode == "text" and self.text_client:
                # Text mode: Use chat completions API (GPT-4)
                logger.info("using_text_client", deployment=self.text_deployment)
                response = self.text_client.chat.completions.create(
                    model=self.text_deployment,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an enthusiastic, knowledgeable chess commentator providing exciting live commentary. Keep responses to 2-3 sentences maximum. Be energetic and engaging!"
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.9,  # High temperature for varied, exciting commentary
                    max_tokens=150,
                )
                result["text"] = response.choices[0].message.content.strip()
                result["audio"] = None
                
            elif self.mode == "both":
                # Both mode: Generate text first, then audio
                if self.text_client:
                    response = self.text_client.chat.completions.create(
                        model=self.text_deployment,
                        messages=[
                            {
                                "role": "system",
                                "content": "You are an enthusiastic, knowledgeable chess commentator providing exciting live commentary. Keep responses to 2-3 sentences maximum. Be energetic and engaging!"
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        temperature=0.9,
                        max_tokens=150,
                    )
                    result["text"] = response.choices[0].message.content.strip()
                else:
                    result["text"] = f"{trigger_context.player} plays {trigger_context.san_move}"
                
                if self.audio_client:
                    audio_result = await self.audio_client.generate_commentary_audio(
                        result["text"],
                        voice_style=self.voice_style,
                    )
                    result["audio"] = audio_result.get("audio")
            
            logger.info(
                "commentary_generated",
                trigger=trigger_context.trigger.value,
                text_length=len(result.get("text", "")),
                has_audio=result.get("audio") is not None,
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "commentary_generation_failed",
                error=str(e),
                trigger=trigger_context.trigger.value,
            )
            return {
                "text": f"{trigger_context.player} plays {trigger_context.san_move}",
                "audio": None,
                "trigger": trigger_context.trigger.value,
                "error": str(e),
            }
    
    def _build_prompt(
        self,
        context: TriggerContext,
        game_context: Optional[Dict[str, Any]],
    ) -> str:
        """Build prompt for commentary generation.
        
        Args:
            context: Trigger context with move data
            game_context: Additional game context
            
        Returns:
            Formatted prompt string
        """
        template = self.PROMPT_TEMPLATES.get(
            context.trigger,
            self.PROMPT_TEMPLATES[CommentaryTrigger.TACTICAL]  # Default
        )
        
        # Prepare template variables
        template_vars = {
            "player": context.player.capitalize(),
            "move": context.move,
            "san_move": context.san_move,
            "move_number": context.move_number,
            "cp_loss": int(context.centipawn_loss),
            "eval_swing": abs(context.eval_swing) if context.eval_swing else 0,
            "eval_before": context.eval_before or "unknown",
            "eval_after": context.eval_after or "unknown",
            "quality": context.quality,
            "best_move": context.best_move_alternative or "unknown",
            "game_phase": context.game_phase,
            "is_check": "Yes" if context.is_check else "No",
            "tactical_motif": context.tactical_motif or "unknown",
            "white_agent": game_context.get("white_agent", "White") if game_context else "White",
            "black_agent": game_context.get("black_agent", "Black") if game_context else "Black",
        }
        
        try:
            return template.format(**template_vars)
        except KeyError as e:
            logger.warning("template_formatting_error", error=str(e))
            # Fallback to simple commentary
            return f"Commentate on {context.player}'s move {context.san_move} (quality: {context.quality})"


# Global generator instance
_global_generator: Optional[CommentaryGenerator] = None


def get_commentary_generator(mode: Optional[str] = None) -> CommentaryGenerator:
    """Get or create global commentary generator instance.
    
    Args:
        mode: Commentary mode (text/audio/both), reads from env if None
    """
    global _global_generator
    
    # If mode is provided and different from existing, recreate generator
    if mode and _global_generator is not None:
        if _global_generator.mode != mode:
            _global_generator = None
    
    if _global_generator is None:
        # Set environment variable if mode is explicitly provided
        if mode:
            os.environ["COMMENTARY_MODE"] = mode
        _global_generator = CommentaryGenerator()
    
    return _global_generator
