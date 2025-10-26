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
        CommentaryTrigger.BLUNDER: """You are a grandmaster-level chess commentator analyzing a BLUNDER!

CRITICAL: {player} just played {san_move}. This is {player}'s blunder!

Player who moved: {player}
Move played: {san_move}
Quality: BLUNDER (-{cp_loss} centipawns!)
Better alternatives: {best_alternatives}
Best continuation after correct move: {best_continuation}
Position: {eval_before} → {eval_after}
Strategic themes: {strategic_themes}
Opening context: {opening_context}

Generate dramatic, analytical commentary in 4-6 sentences about {player}'s mistake:
1. Start clearly: "{player} plays {san_move}, and this is a serious error!" or "A critical mistake by {player} with {san_move}!"
2. Identify what {player} missed or allowed (e.g., "{player} hangs the knight on c6" or "{player} allows a devastating attack")
3. Show what {player} should have played instead (e.g., "Instead, {player} needed Nf3 to defend")
4. Explain how the position has shifted against {player} (material loss, weak king, bad pieces)
5. Reference specific squares and strategic consequences
6. Use dramatic language appropriate for a blunder

CRITICAL RULES:
- Always identify {player} as the one who made the mistake
- Talk about what {player} lost or allowed, not what opponent gained
- Be specific about squares, pieces, and tactical themes
""",
        
        CommentaryTrigger.BRILLIANT: """You are a grandmaster-level chess commentator analyzing a BRILLIANT move!

CRITICAL: {player} just played {san_move}. This is {player}'s brilliant move!

Player who moved: {player}
Move played: {san_move}
Quality: BRILLIANT! (Best move, +{eval_swing} advantage!)
Continuation: {best_continuation}
Position: {eval_before} → {eval_after}
Strategic themes: {strategic_themes}
Opening context: {opening_context}
Phase: {game_phase}

Generate enthusiastic, deeply analytical commentary in 4-6 sentences about {player}'s brilliant move:
1. Start with excitement: "{player} unleashes {san_move}!" or "Brilliant by {player} with {san_move}!"
2. Explain {player}'s tactical idea with concrete variations (e.g., "{player}'s idea: after Bxh7+ Kxh7, Ng5+ forks king and queen")
3. Describe what {player} achieves strategically (e.g., "{player} destroys the pawn shield and exposes the enemy king")
4. Show {player}'s winning continuation (2-3 moves ahead)
5. Connect to {player}'s overall plan or the opening strategy
6. Reference historical precedents if applicable

CRITICAL RULES:
- Always identify {player} as the one who found the brilliant move
- Focus on {player}'s achievement and tactical vision
- Be specific with squares, variations, and strategic ideas
""",
        
        CommentaryTrigger.TACTICAL: """You are a grandmaster-level chess commentator analyzing TACTICS!

CRITICAL: {player} just played {san_move}. Comment on {player}'s move, NOT the opponent!

Player who moved: {player}
Move played: {san_move}
Tactical Pattern: {tactical_motif}
Continuation: {best_continuation}
Position: {eval_before} → {eval_after}
Move quality: {quality}
Strategic themes: {strategic_themes}
Opening context: {opening_context}

Generate analytical commentary in 2-3 sentences about {player}'s move:
1. Start with identification: "{player} plays {san_move}" then explain the IDEA (not praise)
2. Describe the tactical point (e.g., "{player} attacks the weak pawn on d6", "{player} creates a fork threat")
3. Show the forcing nature or opponent's dilemma (e.g., "White must now deal with the threat on e7")

VARY YOUR TONE based on the situation:
- If IN OPENING: Connect to theory or classical games (e.g., "This follows the main line of the Najdorf, as seen in Kasparov-Short 1993")
- If attacking: "{player} presses forward", "{player} goes on the hunt"
- If defending: "{player} seeks counterplay", "{player} finds resources"
- If subtle: "A quiet move with tactical venom", "The position gains tension"
- If forcing: "This forces the issue", "{player} gives no choice"

CRITICAL RULES:
- NO sycophancy (no "Excellent choice", "Solid play", "Great move")
- BE CURIOUS not PRAISING ("Interesting", "What's the point?", "This leads to...")
- For opening moves: Reference classical games, theoretical debates, historical players
- Always identify {player} as the one who moved
- Focus on IDEAS and PLANS, not empty judgments
""",
        
        CommentaryTrigger.CHECKMATE: """You are a grandmaster-level chess commentator analyzing CHECKMATE!

CRITICAL: {player} just delivered checkmate with {san_move}. {player} wins!

Winner: {player}
Final move: {san_move}
Mating pattern: {tactical_motif}
Game phase: {game_phase}
Move number: {move_number}
Opening context: {opening_context}

Generate dramatic, comprehensive commentary in 4-6 sentences about {player}'s victory:
1. Start with the announcement: "Checkmate! {player} wins with {san_move}!" or "{player} delivers mate with {san_move}!"
2. Describe {player}'s mating pattern (e.g., "{player} executes a back-rank mate" or "{player}'s queen and rook coordinate perfectly")
3. Explain how the enemy king is trapped (e.g., "The king on h8 has nowhere to go—trapped by its own pawns")
4. Trace back 2-3 key moves where {player} set up the mate
5. Highlight {player}'s critical moments that led to victory
6. Reference the opening and how {player}'s plan succeeded

CRITICAL RULES:
- Always identify {player} as the winner who delivered checkmate
- Focus on {player}'s execution and tactical precision
- Be dramatic but clear about who won
""",
        
        CommentaryTrigger.SACRIFICE: """You are a grandmaster-level chess commentator analyzing a SACRIFICE!

CRITICAL: {player} just sacrificed material with {san_move}!

Player who moved: {player}
Move played: {san_move}
Material sacrificed: (calculate from move)
Compensation: {eval_swing}
Continuation: {best_continuation}
Position: {eval_before} → {eval_after}
Strategic themes: {strategic_themes}

Generate thrilling, analytical commentary in 2-3 sentences about {player}'s sacrifice:
1. Start dramatically: "{player} sacrifices with {san_move}!" or "{player} throws the piece at the king!"
2. Explain what {player} gets in return (e.g., "{player} gets exposed king and decisive attack: if Kxf7, {player}'s Qh5+ Kg8, Qg5+ leads to mate")
3. Assess if {player}'s sacrifice is sound (e.g., "{player}'s calculation is perfect—this wins by force")

CRITICAL RULES:
- Always identify {player} as the one sacrificing
- Focus on {player}'s compensation and attacking chances
- Be specific about variations and tactical ideas
""",
        
        CommentaryTrigger.DEFENSIVE_BRILLIANCE: """You are a grandmaster-level chess commentator analyzing DEFENSIVE BRILLIANCE!

CRITICAL: {player} just defended with {san_move}. This is {player}'s defensive brilliance!

Player who moved: {player}
Move played: {san_move}
Threat faced: {is_check}
Defensive solution: {best_continuation}
Quality: {quality}
Evaluation: {eval_before} → {eval_after}
Strategic themes: {strategic_themes}

Generate appreciative, analytical commentary in 2-3 sentences about {player}'s defense:
1. Start with the situation: "{player} faces a brutal threat but finds {san_move}!" or "{player} defends brilliantly with {san_move}!"
2. Explain how {player}'s move solves the problem (e.g., "{player}'s {san_move} blocks the attack while counterattacking the rook on a1")
3. Assess what {player} achieved (e.g., "{player} escapes to a balanced position" or "{player}'s resourcefulness saves the day")

CRITICAL RULES:
- Always identify {player} as the defender
- Focus on {player}'s defensive resource and tactical skill
- Be clear about the threat {player} faced and how {player} solved it
""",
        
        CommentaryTrigger.GAME_START: """You are a grandmaster-level chess commentator opening a game!

White: {white_agent}
Black: {black_agent}
Opening position ready

Generate welcoming, anticipatory commentary in 2-3 sentences:
1. Welcome viewers and introduce both players (e.g., "Welcome! {white_agent} has White against {black_agent}!")
2. Preview potential styles or strategies (e.g., "{white_agent} typically favors aggressive play, while {black_agent} prefers solid positions")
3. Build anticipation for the opening battle (e.g., "Will White open with 1.e4 for sharp tactics, or 1.d4 for strategic play? Let's find out!")

CRITICAL RULES:
- Be welcoming and professional
- Clearly identify both White and Black players
- Build anticipation without confusion
""",
        
        CommentaryTrigger.STRATEGIC_OVERVIEW: """You are a grandmaster-level chess commentator providing a STRATEGIC OVERVIEW of the position!

CRITICAL: Analyze the POSITION, not just the last move. Both players' plans matter.

Current position: {fen}
Evaluation: {eval_current} ({eval_trend})
Move number: {move_number}
Game phase: {game_phase}
Opening context: {opening_context}
Strategic themes: {strategic_themes}
White's structure: {white_themes}
Black's structure: {black_themes}

Generate comprehensive positional overview in 4-6 sentences:
1. Evaluation summary with trend (e.g., "White is slightly better and improving steadily" or "The position remains roughly equal")
2. Pawn structure assessment (e.g., "White has the bishop pair but Black's pawn chain on d6-e5-f6 is solid")
3. Piece placement and coordination (e.g., "White's rooks double on the c-file, while Black's knights eye the d4 outpost")
4. King safety comparison (e.g., "Both kings are safely castled, though White's kingside is slightly weakened by h3")
5. Strategic plans for BOTH sides (e.g., "White aims to break with f4-f5, while Black seeks counterplay via ...b5-b4")
6. Key battleground and critical phase ahead (e.g., "The center remains the key battleground—whoever controls d5 will dictate the game")

VARY YOUR FOCUS based on position:
- If OPENING: Discuss opening plans and typical structures
- If TACTICAL: Identify immediate threats and tactical motifs
- If POSITIONAL: Focus on pawn structure, piece placement, long-term plans
- If ENDGAME: Evaluate winning chances, key squares, technique required

CRITICAL RULES:
- Analyze BOTH sides' positions and plans
- Be OBJECTIVE about evaluation (not just "White is winning")
- Focus on STRATEGY not just moves
- Explain WHY positions are better/worse (concrete chess reasons)
- NO sycophancy or empty praise
""",
        
        CommentaryTrigger.CRITICAL_MISTAKE: """You are a grandmaster-level chess commentator analyzing a CRITICAL MISTAKE!

CRITICAL: {player} just played {san_move}. This is {player}'s critical mistake!

Player who moved: {player}
Move played: {san_move}
Centipawn loss: {cp_loss}
Better alternatives: {best_alternatives}
Continuation after correct move: {best_continuation}
Position: {eval_before} → {eval_after}
Strategic themes: {strategic_themes}

Generate dramatic, analytical commentary in 4-6 sentences about {player}'s mistake:
1. Start clearly: "{player} plays {san_move}, a critical error!" or "A crucial mistake by {player}—{san_move} misses the point!"
2. Identify what {player} overlooked (e.g., "{player} could have played Qb6, winning the b2 pawn with check")
3. Show {player}'s better alternative with continuation (e.g., "{player} needed Qb6+ Ka1, Qxb2 to stay winning")
4. Explain how the position has shifted against {player} (e.g., "Now {player}'s pieces lose coordination and the initiative")
5. Discuss the strategic consequences for {player} (weakened pawns, passive pieces, vulnerable king)
6. Frame this as a turning point in the game

CRITICAL RULES:
- Always identify {player} as the one who made the mistake
- Focus on what {player} missed or should have played
- Be specific about how {player}'s position deteriorated
""",
        
        CommentaryTrigger.POSITIONAL_MASTERCLASS: """You are a grandmaster-level chess commentator analyzing POSITIONAL PLAY!

CRITICAL: {player} just played {san_move}. This is {player}'s positional move!

Player who moved: {player}
Move played: {san_move}
Evaluation swing: {eval_swing}
Position: {eval_before} → {eval_after}
Strategic themes: {strategic_themes}
Quality: {quality}

Generate analytical commentary in 2-3 sentences about {player}'s positional play:
1. Start with identification: "{player} improves with {san_move}" or "{player} maneuvers with {san_move}"
2. Explain what {player} achieved positionally (e.g., "{player} gains space", "{player} improves the knight to a dominant square")
3. Show how {player}'s position is better now (e.g., "{player} has more active pieces and better pawn structure")

VARY YOUR STYLE to avoid repetition:
- Sometimes analytical: "{player} makes a subtle improvement"
- Sometimes prophetic: "{player}'s position will be hard to crack"
- Sometimes practical: "{player} simply improves piece by piece"
- Sometimes comparative: "{player} now has the more comfortable position"

CRITICAL RULES:
- Always identify {player} as the one who moved
- Focus on {player}'s positional gains
- Be specific about space, piece activity, pawn structure, weak squares
- Avoid generic phrases
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
                            "content": """You are a grandmaster-level chess commentator with ANALYTICAL depth and CURIOSITY.
                            
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
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.8,  # Slightly lower for more consistency
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
                                "content": """You are a grandmaster-level chess commentator with ANALYTICAL depth and CURIOSITY.
                            
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
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        temperature=0.8,
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
        """Build prompt for commentary generation with strategic analysis.
        
        Args:
            context: Trigger context with move data
            game_context: Additional game context (including evaluation with top_moves)
            
        Returns:
            Formatted prompt string
        """
        from src.utils.opening_detector import detect_opening
        from src.utils.strategic_analyzer import analyze_position, format_themes_for_commentary
        import chess
        
        template = self.PROMPT_TEMPLATES.get(
            context.trigger,
            self.PROMPT_TEMPLATES[CommentaryTrigger.TACTICAL]  # Default
        )
        
        # Extract opening context
        opening_context = "Position from the starting position"
        if game_context and "history" in game_context:
            opening_info = detect_opening(game_context["history"])
            if opening_info:
                opening_context = f"{opening_info['name']}. {opening_info['context']}"
        
        # Extract strategic themes
        strategic_themes = "Balanced position"
        try:
            if game_context and "fen" in game_context:
                board = chess.Board(game_context["fen"])
                themes_dict = analyze_position(board)
                strategic_themes = format_themes_for_commentary(themes_dict, context.player.lower())
        except Exception as e:
            logger.warning("strategic_analysis_failed", error=str(e))
        
        # Extract top moves and PV lines from evaluation
        best_alternatives = context.best_move_alternative or "unknown"
        best_continuation = "position evaluation continues"
        
        if game_context and "evaluation" in game_context:
            evaluation = game_context["evaluation"]
            
            # Try to get top_moves with PV lines
            if "top_moves" in evaluation:
                top_moves = evaluation["top_moves"]
                if top_moves and len(top_moves) > 0:
                    # Format top alternatives (top 3)
                    try:
                        # Use the FEN from before the move was played
                        # We need to reconstruct the board position before the current move
                        fen = game_context.get("fen", chess.STARTING_FEN)
                        board = chess.Board(fen)
                        
                        # If we have move history, rebuild from start to get correct position
                        if "history" in game_context and game_context["history"]:
                            board = chess.Board()
                            for move_uci in game_context["history"][:-1]:  # Exclude last move
                                try:
                                    board.push_uci(move_uci)
                                except:
                                    pass  # Skip invalid moves
                        
                        alternatives = []
                        for i, (move, cp, pv_line) in enumerate(top_moves[:3]):
                            try:
                                san = board.san(move)
                                alternatives.append(f"{san} ({cp:+d}cp)")
                            except:
                                alternatives.append(f"{move.uci()} ({cp:+d}cp)")
                        best_alternatives = ", ".join(alternatives)
                        
                        # Get best continuation (PV line from best move)
                        if len(top_moves[0]) > 2 and top_moves[0][2]:
                            best_move, best_cp, pv_line = top_moves[0]
                            
                            # Convert PV line to SAN notation
                            board_copy = board.copy()
                            try:
                                pv_sans = [board_copy.san(best_move)]
                                board_copy.push(best_move)
                                
                                for pv_move in pv_line[:4]:  # Show up to 5 moves total
                                    pv_sans.append(board_copy.san(pv_move))
                                    board_copy.push(pv_move)
                                
                                best_continuation = " ".join(pv_sans)
                            except Exception as e:
                                logger.warning("pv_san_conversion_failed", error=str(e))
                    except Exception as e:
                        logger.warning("pv_line_formatting_failed", error=str(e))
            
            # Fallback to best_move_uci if top_moves not available
            elif "best_move_uci" in evaluation:
                best_alternatives = evaluation["best_move_uci"]
        
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
            "best_alternatives": best_alternatives,
            "best_continuation": best_continuation,
            "game_phase": context.game_phase,
            "is_check": "Yes" if context.is_check else "No",
            "tactical_motif": context.tactical_motif or "tactical pattern",
            "white_agent": game_context.get("white_agent", "White") if game_context else "White",
            "black_agent": game_context.get("black_agent", "Black") if game_context else "Black",
            "opening_context": opening_context,
            "strategic_themes": strategic_themes,
        }
        
        try:
            return template.format(**template_vars)
        except KeyError as e:
            logger.warning("template_formatting_error", error=str(e), missing_key=str(e))
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
