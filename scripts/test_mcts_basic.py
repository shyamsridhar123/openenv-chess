#!/usr/bin/env python3
"""
Quick test: Does basic MCTS actually work with our chess env?

Run this to verify the approach before investing time in complex implementations.
"""

import sys
import random
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.chess_env import ChessOpenEnv


def random_playout(env: ChessOpenEnv, max_moves: int = 50) -> float:
    """Play random moves until game ends. Returns reward."""
    moves = 0
    while moves < max_moves:
        legal_moves = env.get_legal_moves()
        if not legal_moves:
            break
        
        move = random.choice(legal_moves)
        obs, reward, done, truncated, info = env.step(move)
        
        if done:
            return reward
        
        moves += 1
    
    return 0.0  # Draw if timeout


def simple_mcts_move(env: ChessOpenEnv, num_simulations: int = 10) -> str:
    """
    Ultra-simple MCTS: Try each legal move N times, pick best average.
    
    This is NOT full MCTS but proves the concept works.
    """
    legal_moves = env.get_legal_moves()
    if not legal_moves:
        return None
    
    move_scores = {}
    
    for move in legal_moves:
        # Try this move multiple times
        total_reward = 0
        for _ in range(num_simulations):
            # Clone environment
            test_env = ChessOpenEnv()
            test_env.reset(fen=env.state()["fen"])
            
            # Apply move
            obs, reward, done, truncated, info = test_env.step(move)
            
            # Random playout
            if not done:
                reward = -random_playout(test_env)  # Flip for opponent
            
            total_reward += reward
        
        move_scores[move] = total_reward / num_simulations
    
    # Return best move
    best_move = max(move_scores.items(), key=lambda x: x[1])
    return best_move[0]


def play_game(mcts_simulations: int = 10):
    """Play one game: MCTS vs Random."""
    env = ChessOpenEnv()
    obs, info = env.reset()
    
    move_count = 0
    max_moves = 100
    
    print(f"\n{'='*60}")
    print(f"Game: Simple MCTS ({mcts_simulations} sims) vs Random")
    print(f"{'='*60}\n")
    
    while move_count < max_moves:
        state = env.state()
        current_player = state["current_player"]
        
        if current_player == "white":
            # MCTS plays white
            start_time = time.time()
            move = simple_mcts_move(env, num_simulations=mcts_simulations)
            elapsed = time.time() - start_time
            
            if move is None:
                print("No legal moves!")
                break
            
            print(f"Move {move_count+1}. White (MCTS): {move} ({elapsed:.2f}s)")
        else:
            # Random plays black
            legal_moves = env.get_legal_moves()
            if not legal_moves:
                print("No legal moves!")
                break
            move = random.choice(legal_moves)
            print(f"Move {move_count+1}. Black (Random): {move}")
        
        obs, reward, done, truncated, info = env.step(move)
        move_count += 1
        
        if done:
            result = info.get("result", "unknown")
            print(f"\n{'='*60}")
            print(f"Game Over! Result: {result}")
            print(f"Total moves: {move_count}")
            print(f"{'='*60}\n")
            return result
    
    print("Game reached move limit (draw)")
    return "draw"


def main():
    """Test if MCTS approach actually works."""
    print("\n" + "="*60)
    print("Testing: Simple MCTS with Your Chess Environment")
    print("="*60)
    print("\nThis tests if MCTS-style thinking works at all.")
    print("If this works, we can make it smarter.\n")
    
    # Test 1: Can we even do simulations?
    print("Test 1: Running basic simulation...")
    try:
        env = ChessOpenEnv()
        env.reset()
        reward = random_playout(env, max_moves=20)
        print(f"✅ Basic playout works! Final reward: {reward}")
    except Exception as e:
        print(f"❌ Failed: {e}")
        return
    
    # Test 2: Can we evaluate moves?
    print("\nTest 2: Evaluating moves with simple MCTS...")
    try:
        env = ChessOpenEnv()
        env.reset()
        move = simple_mcts_move(env, num_simulations=5)
        print(f"✅ Move selection works! Chose: {move}")
    except Exception as e:
        print(f"❌ Failed: {e}")
        return
    
    # Test 3: Full game
    print("\nTest 3: Playing full game...")
    try:
        result = play_game(mcts_simulations=10)
        print(f"✅ Full game works! Result: {result}")
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "="*60)
    print("Summary:")
    print("="*60)
    print("✅ The basic MCTS approach WORKS with your environment!")
    print("\nNext steps if you want to continue:")
    print("1. Increase simulations (10 → 100) for stronger play")
    print("2. Add proper UCB tree search instead of flat evaluation")
    print("3. Add position evaluation heuristics")
    print("4. Parallelize simulations for speed")
    print("\nBut honestly? You already have Stockfish.")
    print("The real question: What do you actually want to build?")


if __name__ == "__main__":
    main()
