#!/usr/bin/env python3
"""Test script to verify personality system is working correctly."""

import requests
import json
import time

API_BASE = "http://localhost:8000/api/v1"

def test_personality_flow():
    """Test that personalities flow from reset request through to agent creation."""
    
    print("=" * 80)
    print("PERSONALITY SYSTEM TEST")
    print("=" * 80)
    
    # Test 1: Create game with aggressive white, tactical black
    print("\n[TEST 1] Creating game with White=aggressive, Black=tactical")
    print("-" * 80)
    
    reset_payload = {
        "white_agent_id": "TestWhite",
        "black_agent_id": "TestBlack",
        "white_personality": "aggressive",
        "black_personality": "tactical"
    }
    
    print(f"Request payload: {json.dumps(reset_payload, indent=2)}")
    
    response = requests.post(f"{API_BASE}/reset", json=reset_payload)
    
    if response.status_code != 200:
        print(f"❌ FAILED: Reset request failed with status {response.status_code}")
        print(f"Response: {response.text}")
        return False
    
    data = response.json()
    game_id = data["game_id"]
    print(f"✓ Game created: {game_id}")
    
    # Test 2: Request white agent move (should use aggressive personality)
    print("\n[TEST 2] Requesting WHITE move (should use 'aggressive' personality)")
    print("-" * 80)
    
    move_response = requests.post(f"{API_BASE}/agent-move", json={"game_id": game_id})
    
    if move_response.status_code != 200:
        print(f"❌ FAILED: Agent move request failed with status {move_response.status_code}")
        print(f"Response: {move_response.text}")
        return False
    
    move_data = move_response.json()
    print(f"✓ White agent made move: {move_data.get('move', {}).get('san', 'N/A')}")
    if 'error' in move_data:
        print(f"⚠ WARNING: {move_data['error']}")
    
    # Test 3: Request black agent move (should use tactical personality)
    print("\n[TEST 3] Requesting BLACK move (should use 'tactical' personality)")
    print("-" * 80)
    
    move_response = requests.post(f"{API_BASE}/agent-move", json={"game_id": game_id})
    
    if move_response.status_code != 200:
        print(f"❌ FAILED: Agent move request failed with status {move_response.status_code}")
        print(f"Response: {move_response.text}")
        return False
    
    move_data = move_response.json()
    print(f"✓ Black agent made move: {move_data.get('move', {}).get('san', 'N/A')}")
    if 'error' in move_data:
        print(f"⚠ WARNING: {move_data['error']}")
    
    # Test 4: Create game with different personalities
    print("\n[TEST 4] Creating game with White=defensive, Black=positional")
    print("-" * 80)
    
    reset_payload = {
        "white_agent_id": "DefensivePlayer",
        "black_agent_id": "PositionalPlayer",
        "white_personality": "defensive",
        "black_personality": "positional"
    }
    
    print(f"Request payload: {json.dumps(reset_payload, indent=2)}")
    
    response = requests.post(f"{API_BASE}/reset", json=reset_payload)
    
    if response.status_code != 200:
        print(f"❌ FAILED: Reset request failed with status {response.status_code}")
        print(f"Response: {response.text}")
        return False
    
    data = response.json()
    game_id = data["game_id"]
    print(f"✓ Game created: {game_id}")
    
    # Test 5: Request white agent move (should use defensive personality)
    print("\n[TEST 5] Requesting WHITE move (should use 'defensive' personality)")
    print("-" * 80)
    
    move_response = requests.post(f"{API_BASE}/agent-move", json={"game_id": game_id})
    
    if move_response.status_code != 200:
        print(f"❌ FAILED: Agent move request failed with status {move_response.status_code}")
        print(f"Response: {move_response.text}")
        return False
    
    move_data = move_response.json()
    print(f"✓ White agent made move: {move_data.get('move', {}).get('san', 'N/A')}")
    if 'error' in move_data:
        print(f"⚠ WARNING: {move_data['error']}")
    
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print("✓ All API calls succeeded")
    print("\nIMPORTANT: Check server logs for:")
    print("  1. 'reset_request_received' - personalities sent from frontend")
    print("  2. 'game_object_created' - personalities stored in Game object")
    print("  3. 'agent_move_personality_check' - personality used for agent creation")
    print("  4. 'agent_created' - confirm correct personality in agent logs")
    print("\nExpected log entries:")
    print("  - white_personality='aggressive' for TestWhite")
    print("  - black_personality='tactical' for TestBlack")
    print("  - white_personality='defensive' for DefensivePlayer")
    print("  - black_personality='positional' for PositionalPlayer")
    print("=" * 80)
    
    return True


def test_all_personalities():
    """Test all 5 personality types."""
    
    personalities = ["aggressive", "defensive", "balanced", "tactical", "positional"]
    
    print("\n" + "=" * 80)
    print("TESTING ALL PERSONALITY TYPES")
    print("=" * 80)
    
    for personality in personalities:
        print(f"\n[TEST] Creating game with {personality.upper()} white agent")
        print("-" * 80)
        
        reset_payload = {
            "white_agent_id": f"{personality.capitalize()}White",
            "black_agent_id": "BalancedBlack",
            "white_personality": personality,
            "black_personality": "balanced"
        }
        
        response = requests.post(f"{API_BASE}/reset", json=reset_payload)
        
        if response.status_code != 200:
            print(f"❌ FAILED: {personality}")
            continue
        
        data = response.json()
        game_id = data["game_id"]
        
        # Make one move
        move_response = requests.post(f"{API_BASE}/agent-move", json={"game_id": game_id})
        
        if move_response.status_code != 200:
            print(f"❌ FAILED: {personality} - move request failed")
            continue
        
        move_data = move_response.json()
        print(f"✓ {personality.upper()} agent made move: {move_data.get('move', {}).get('san', 'N/A')}")
        if 'error' in move_data:
            print(f"⚠ WARNING: {move_data['error']}")
    
    print("\n" + "=" * 80)
    print("Check server logs to verify each personality was used correctly!")
    print("=" * 80)


if __name__ == "__main__":
    print("\nMake sure the server is running on http://localhost:8000")
    print("Waiting 2 seconds before starting tests...\n")
    time.sleep(2)
    
    try:
        # Test basic personality flow
        success = test_personality_flow()
        
        if success:
            # Test all personality types
            test_all_personalities()
        
        print("\n✓ Tests completed! Review server logs for detailed personality flow.")
        
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Could not connect to server at http://localhost:8000")
        print("Make sure the server is running: make run")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
