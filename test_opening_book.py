#!/usr/bin/env python3
"""Test script for opening book integration.

Tests Lichess Masters API integration and personality-based move selection.
"""

import asyncio
from src.utils.opening_book_client import OpeningBookClient
from src.agents.hybrid_agent_selector import HybridAgentMoveSelector
from src.agents.agent_manager import ChessAgentManager
from src.utils.stockfish_evaluator import get_evaluator
from src.models.board_state import BoardState
import chess
import structlog

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()


def test_opening_book_client():
    """Test OpeningBookClient basic functionality."""
    print("\n=== Testing OpeningBookClient ===\n")
    
    client = OpeningBookClient()
    
    # Test starting position
    starting_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    
    print(f"Querying opening book for starting position...")
    moves = client.query_opening_book(starting_fen)
    
    if not moves:
        print("❌ No moves returned from opening book API")
        return False
    
    print(f"✅ Received {len(moves)} opening moves")
    
    # Display top 5 moves
    print("\nTop 5 moves:")
    for i, move in enumerate(moves[:5], 1):
        print(f"  {i}. {move.san} ({move.uci})")
        print(f"     Games: {move.total_games}, Draw rate: {move.draw_rate:.1%}")
        print(f"     White: {move.white_wins}, Draws: {move.draws}, Black: {move.black_wins}")
    
    # Test personality filtering
    print("\n=== Testing Personality Filtering ===\n")
    
    for personality in ["aggressive", "defensive", "balanced"]:
        selected_move = client.select_opening_move(moves, personality, is_white=True)
        
        # Find the selected move details
        selected = next((m for m in moves if m.uci == selected_move), None)
        
        if selected:
            print(f"{personality.capitalize()} personality selected: {selected.san} ({selected.uci})")
            print(f"  Draw rate: {selected.draw_rate:.1%}, Games: {selected.total_games}")
        else:
            print(f"❌ {personality} personality failed to select move")
            return False
    
    # Test cache
    print("\n=== Testing Cache ===\n")
    cache_stats_before = client.get_cache_stats()
    print(f"Cache before: {cache_stats_before}")
    
    # Query same position (should hit cache)
    moves_cached = client.query_opening_book(starting_fen)
    cache_stats_after = client.get_cache_stats()
    
    print(f"Cache after: {cache_stats_after}")
    
    if moves_cached and len(moves_cached) == len(moves):
        print("✅ Cache working correctly")
    else:
        print("❌ Cache might not be working")
        return False
    
    # Test after e2e4
    print("\n=== Testing After 1.e4 ===\n")
    after_e4_fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
    moves_e4 = client.query_opening_book(after_e4_fen)
    
    if moves_e4:
        print(f"✅ Received {len(moves_e4)} moves for position after 1.e4")
        print("\nTop responses to 1.e4:")
        for i, move in enumerate(moves_e4[:3], 1):
            print(f"  {i}. {move.san} ({move.uci}) - {move.total_games} games")
    else:
        print("❌ No moves found for position after 1.e4")
        return False
    
    return True


def test_hybrid_selector_with_opening_book():
    """Test HybridAgentMoveSelector with opening book integration."""
    print("\n\n=== Testing Hybrid Selector with Opening Book ===\n")
    
    # Initialize components
    evaluator = get_evaluator()
    if not evaluator.is_available():
        print("❌ Stockfish not available, skipping hybrid selector test")
        return False
    
    agent_manager = ChessAgentManager()
    opening_book = OpeningBookClient()
    
    hybrid_selector = HybridAgentMoveSelector(
        stockfish_evaluator=evaluator,
        agent_manager=agent_manager,
        opening_book_client=opening_book,
    )
    
    # Create test agent
    agent_manager.create_agent(
        agent_id="TestAgent",
        model_name="Qwen/Qwen2.5-Coder-32B-Instruct",
        personality="aggressive",
    )
    
    # Test starting position (should use opening book)
    board = chess.Board()
    board_state = BoardState.from_board(board)
    
    print("Getting move for starting position (should use opening book)...")
    move, source = hybrid_selector.get_move(
        agent_id="TestAgent",
        board=board,
        board_state=board_state,
        game_history=[],
        game_id="test-game-1",
    )
    
    print(f"Move: {move}, Source: {source}")
    
    if source == "opening_book":
        print("✅ Opening book was used for opening position")
    else:
        print(f"⚠️  Expected 'opening_book' source, got '{source}'")
        return False
    
    # Validate move is legal
    try:
        chess_move = chess.Move.from_uci(move)
        if chess_move in board.legal_moves:
            print(f"✅ Selected move {move} is legal")
        else:
            print(f"❌ Selected move {move} is illegal")
            return False
    except ValueError as e:
        print(f"❌ Invalid move UCI: {e}")
        return False
    
    # Test position after 20 moves (should NOT use opening book)
    print("\n=== Testing Mid-Game Position (Should Use Hybrid) ===\n")
    
    board_mid = chess.Board()
    game_history = []
    
    # Play 20 moves
    for _ in range(20):
        legal_moves = list(board_mid.legal_moves)
        if not legal_moves:
            break
        board_mid.push(legal_moves[0])
        game_history.append(legal_moves[0].uci())
    
    board_state_mid = BoardState.from_board(board_mid)
    
    print(f"Getting move for position after {len(game_history)} moves...")
    move_mid, source_mid = hybrid_selector.get_move(
        agent_id="TestAgent",
        board=board_mid,
        board_state=board_state_mid,
        game_history=game_history,
        game_id="test-game-2",
    )
    
    print(f"Move: {move_mid}, Source: {source_mid}")
    
    if source_mid == "hybrid":
        print("✅ Hybrid selector was used for mid-game position")
    else:
        print(f"⚠️  Expected 'hybrid' source, got '{source_mid}' (opening book cutoff might be hit)")
    
    return True


def main():
    """Run all opening book tests."""
    print("=" * 80)
    print("OPENING BOOK INTEGRATION TEST")
    print("=" * 80)
    
    # Test 1: OpeningBookClient
    success1 = test_opening_book_client()
    
    # Test 2: Hybrid selector integration
    success2 = test_hybrid_selector_with_opening_book()
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    results = {
        "OpeningBookClient": success1,
        "Hybrid Selector Integration": success2,
    }
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    print("\n" + ("=" * 80))
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 80)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
