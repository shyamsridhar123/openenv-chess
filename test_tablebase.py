"""Quick test of Syzygy tablebase integration."""

import chess
from src.utils.tablebase_client import TablebaseClient

def test_tablebase():
    """Test tablebase with a simple K+R vs K endgame."""
    client = TablebaseClient()
    
    # King + Rook vs King endgame (White to move, winning)
    # White: King on e1, Rook on h1
    # Black: King on e8
    fen = "4k3/8/8/8/8/8/8/4K2R w - - 0 1"
    
    print(f"\nTesting position: {fen}")
    print("White: King on e1, Rook on h1")
    print("Black: King on e8 (isolated)")
    
    result = client.query_position(fen)
    
    if result:
        print(f"\n✅ Tablebase found move: {result['uci']}")
        print(f"   WDL: {result['wdl']} (2=win, 0=draw, -2=loss)")
        print(f"   DTZ: {result['dtz']} (moves to zeroing)")
        print(f"   Category: {result['category']}")
        
        if client.is_winning(result['wdl']):
            print("\n🎯 Position is winning with perfect play!")
        elif client.is_drawing(result['wdl']):
            print("\n🤝 Position is drawn with perfect play")
        else:
            print("\n😞 Position is losing")
    else:
        print("\n❌ Tablebase query failed or position not found")
    
    # Test position with too many pieces (should skip tablebase)
    fen_many_pieces = chess.STARTING_FEN
    print(f"\n\nTesting starting position (should skip): {fen_many_pieces}")
    
    if client.should_query_tablebase(fen_many_pieces):
        print("❌ ERROR: Should not query tablebase for starting position")
    else:
        print("✅ Correctly skipped tablebase (too many pieces)")

if __name__ == "__main__":
    test_tablebase()
