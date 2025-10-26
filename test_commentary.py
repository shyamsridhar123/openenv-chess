"""Test enhanced commentary generation with sample positions."""

import asyncio
import os
import chess
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import commentary components
from src.commentary.commentary_generator import CommentaryGenerator
from src.commentary.triggers import CommentaryTrigger, TriggerContext
from src.utils.stockfish_evaluator import StockfishEvaluator


async def test_commentary():
    """Test commentary generation for various scenarios."""
    
    print("=" * 80)
    print("TESTING ENHANCED COMMENTARY SYSTEM")
    print("=" * 80)
    
    # Initialize components
    generator = CommentaryGenerator()
    evaluator = StockfishEvaluator()
    
    if not generator.is_available():
        print("❌ Commentary generator not available (check Azure OpenAI config)")
        return
    
    if not evaluator.is_available():
        print("❌ Stockfish evaluator not available")
        return
    
    print("✅ All components initialized")
    print()
    
    # Test Case 1: Opening - Sicilian Defense
    print("\n" + "=" * 80)
    print("TEST 1: Opening Move - Sicilian Defense")
    print("=" * 80)
    
    board1 = chess.Board()
    board1.push_san("e4")
    move1 = board1.push_san("c5")
    
    eval1 = evaluator.evaluate_move(chess.Board("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"), move1)
    
    context1 = TriggerContext(
        trigger=CommentaryTrigger.TACTICAL,
        priority=5,
        player="black",
        move="c7c5",
        san_move="c5",
        move_number=1,
        eval_before=eval1.get("eval_before"),
        eval_after=eval1.get("eval_after"),
        eval_swing=0,
        centipawn_loss=eval1.get("centipawn_loss", 0),
        quality=eval1.get("quality", "good"),
        is_best_move=eval1.get("is_best_move", True),
        best_move_alternative=eval1.get("best_move_uci"),
        game_phase="opening",
        material_balance=0,
        position_type="open",
        is_check=False,
        is_checkmate=False,
    )
    
    result1 = await generator.generate_commentary(
        trigger_context=context1,
        game_context={
            "fen": board1.fen(),
            "game_phase": "opening",
            "history": ["e2e4", "c7c5"],
            "evaluation": eval1,
        }
    )
    
    print(f"Move: {context1.san_move}")
    print(f"Evaluation: {eval1.get('quality')}")
    print(f"\nCommentary:")
    print("-" * 80)
    print(result1.get("text", "No commentary generated"))
    print("-" * 80)
    
    # Test Case 2: Tactical Blunder
    print("\n" + "=" * 80)
    print("TEST 2: Blunder - Hanging Piece")
    print("=" * 80)
    
    # Position with a blunder: Scholar's Mate setup gone wrong
    board2 = chess.Board("r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 0 1")
    # Bad move: Qxf7+ is checkmate but let's simulate a bad move instead
    move2 = chess.Move.from_uci("f3g3")  # Random bad queen move
    
    eval2 = evaluator.evaluate_move(board2, move2)
    
    context2 = TriggerContext(
        trigger=CommentaryTrigger.BLUNDER,
        priority=9,
        player="white",
        move="f3g3",
        san_move="Qg3",
        move_number=5,
        eval_before=eval2.get("eval_before"),
        eval_after=eval2.get("eval_after"),
        eval_swing=abs(eval2.get("eval_after", 0) - eval2.get("eval_before", 0)) if eval2.get("eval_after") else 0,
        centipawn_loss=eval2.get("centipawn_loss", 0),
        quality="blunder",
        is_best_move=False,
        best_move_alternative=eval2.get("best_move_uci"),
        game_phase="opening",
        material_balance=0,
        position_type="tactical",
        is_check=False,
        is_checkmate=False,
    )
    
    result2 = await generator.generate_commentary(
        trigger_context=context2,
        game_context={
            "fen": board2.fen(),
            "game_phase": "opening",
            "history": ["e2e4", "e7e5", "f1c4", "b8c6", "d1f3"],
            "evaluation": eval2,
        }
    )
    
    print(f"Position: {board2.fen()}")
    print(f"Move: {context2.san_move}")
    print(f"Evaluation: {eval2.get('quality')} (-{eval2.get('centipawn_loss', 0)}cp)")
    print(f"Best alternative: {eval2.get('best_move_uci')}")
    print(f"\nCommentary:")
    print("-" * 80)
    print(result2.get("text", "No commentary generated"))
    print("-" * 80)
    
    # Test Case 3: Brilliant Tactical Shot
    print("\n" + "=" * 80)
    print("TEST 3: Brilliant Move - Tactical Shot")
    print("=" * 80)
    
    # Position with brilliant tactical opportunity
    board3 = chess.Board("r1bq1rk1/pp3pbp/2np1np1/2p1p3/2P1P3/2NP1NP1/PP2PPBP/R1BQ1RK1 w - - 0 1")
    # Strong tactical move
    move3 = chess.Move.from_uci("f3g5")  # Ng5 attacking f7
    
    eval3 = evaluator.evaluate_move(board3, move3)
    
    context3 = TriggerContext(
        trigger=CommentaryTrigger.BRILLIANT,
        priority=8,
        player="white",
        move="f3g5",
        san_move="Ng5",
        move_number=12,
        eval_before=eval3.get("eval_before"),
        eval_after=eval3.get("eval_after"),
        eval_swing=abs(eval3.get("eval_after", 0) - eval3.get("eval_before", 0)) if eval3.get("eval_after") else 0,
        centipawn_loss=eval3.get("centipawn_loss", 0),
        quality="excellent",
        is_best_move=eval3.get("is_best_move", True),
        best_move_alternative=eval3.get("best_move_uci"),
        game_phase="middlegame",
        material_balance=0,
        position_type="tactical",
        is_check=False,
        is_checkmate=False,
        tactical_motif="knight_fork",
    )
    
    result3 = await generator.generate_commentary(
        trigger_context=context3,
        game_context={
            "fen": board3.fen(),
            "game_phase": "middlegame",
            "history": ["e2e4", "c7c5", "g1f3", "d7d6", "d2d4", "c5d4", "f3d4", "g8f6", "b1c3", "g7g6"],
            "evaluation": eval3,
        }
    )
    
    print(f"Position: {board3.fen()}")
    print(f"Move: {context3.san_move}")
    print(f"Evaluation: {eval3.get('quality')}")
    print(f"\nCommentary:")
    print("-" * 80)
    print(result3.get("text", "No commentary generated"))
    print("-" * 80)
    
    print("\n" + "=" * 80)
    print("TESTING COMPLETE")
    print("=" * 80)
    print("\n✅ All commentary tests executed successfully!")
    print("\nNote: Review commentary quality:")
    print("  - Does it mention specific squares and pieces?")
    print("  - Does it include strategic themes (pawn structure, king safety)?")
    print("  - Does it show PV lines/continuations?")
    print("  - Does it reference opening names where applicable?")
    print("  - Is the length appropriate (4-6 sentences for critical, 2-3 for regular)?")


if __name__ == "__main__":
    asyncio.run(test_commentary())
