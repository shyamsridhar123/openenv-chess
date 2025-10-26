"""Test commentary variety and emotional range."""

import asyncio
import os
from dotenv import load_dotenv
import chess

load_dotenv()

from src.commentary.commentary_generator import CommentaryGenerator
from src.commentary.triggers import CommentaryTrigger, TriggerContext


async def test_variety():
    """Test that commentary has variety and correct player identification."""
    
    print("=" * 80)
    print("TESTING COMMENTARY VARIETY AND EMOTIONAL RANGE")
    print("=" * 80)
    
    generator = CommentaryGenerator()
    
    if not generator.is_available():
        print("❌ Commentary generator not available")
        return
    
    print("✅ Commentary generator initialized")
    print()
    
    # Test same position multiple times to check variety
    print("\n" + "=" * 80)
    print("TEST: Generate commentary 3 times for similar tactical situations")
    print("Goal: Verify varied language, no repetitive 'Excellent choice' phrases")
    print("=" * 80)
    
    for i in range(3):
        print(f"\n--- Iteration {i+1} ---")
        
        context = TriggerContext(
            trigger=CommentaryTrigger.TACTICAL,
            priority=5,
            player="white",  # Make sure it's WHITE playing
            move="e2e4",
            san_move="e4",
            move_number=1,
            eval_before=15,
            eval_after=25,
            eval_swing=10,
            centipawn_loss=0,
            quality="good",
            is_best_move=True,
            best_move_alternative="e2e4",
            game_phase="opening",
            material_balance=0,
            position_type="open",
            is_check=False,
            is_checkmate=False,
            tactical_motif="central_control",
        )
        
        result = await generator.generate_commentary(
            trigger_context=context,
            game_context={
                "fen": chess.Board().fen(),
                "game_phase": "opening",
                "history": [],
                "evaluation": {
                    "centipawn_loss": 0,
                    "quality": "good",
                    "eval_before": 15,
                    "eval_after": 25,
                }
            }
        )
        
        commentary = result.get("text", "")
        print(f"Player: {context.player.upper()}")
        print(f"Move: {context.san_move}")
        print(f"\nCommentary:")
        print("-" * 80)
        print(commentary)
        print("-" * 80)
        
        # Check for issues
        issues = []
        if "excellent choice" in commentary.lower():
            issues.append("⚠️  Contains 'Excellent choice' (too generic)")
        if "solid play" in commentary.lower():
            issues.append("⚠️  Contains 'Solid play' (too generic)")
        if "building pressure" in commentary.lower():
            issues.append("⚠️  Contains 'Building pressure' (sycophantic)")
        if "sets the stage" in commentary.lower():
            issues.append("⚠️  Contains 'Sets the stage' (sycophantic)")
        
        # Check if commentary correctly identifies WHO MOVED (not whether it mentions opponent)
        # Look for patterns like "{player} plays" or "{player} moves" at the start
        if context.player.lower() == "white":
            if not any(pattern in commentary.lower() for pattern in ["white plays", "white moves", "white stakes", "white seizes", "white aims"]):
                issues.append("❌ WRONG PLAYER - Doesn't clearly state White moved!")
        elif context.player.lower() == "black":
            if not any(pattern in commentary.lower() for pattern in ["black plays", "black moves", "black stakes", "black seizes", "black aims"]):
                issues.append("❌ WRONG PLAYER - Doesn't clearly state Black moved!")
        
        if issues:
            print("\nISSUES FOUND:")
            for issue in issues:
                print(issue)
        else:
            print("\n✅ No generic phrases, correct player identification")
        
        await asyncio.sleep(1)  # Small delay between requests
    
    print("\n" + "=" * 80)
    print("VARIETY TEST COMPLETE")
    print("=" * 80)
    print("\nReview the 3 commentaries above:")
    print("1. Are they DIFFERENT from each other?")
    print("2. Do they avoid 'Excellent choice' and 'Solid play'?")
    print("3. Do they correctly identify WHITE as the player?")
    print("4. Do they show different emotional tones?")


if __name__ == "__main__":
    asyncio.run(test_variety())
