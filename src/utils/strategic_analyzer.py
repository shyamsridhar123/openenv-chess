"""Strategic theme detection for chess positions.

Analyzes positions to identify strategic themes like:
- Isolated pawns
- Bad bishops
- Rooks on 7th/2nd rank
- Space advantages
- King safety issues
- Piece activity
"""

from typing import List, Dict, Optional
import chess
import structlog

logger = structlog.get_logger()


def analyze_position(board: chess.Board) -> Dict[str, List[str]]:
    """Analyze position for strategic themes.
    
    Args:
        board: Chess board position
        
    Returns:
        Dictionary with:
        - white_themes: List of strategic themes for White
        - black_themes: List of strategic themes for Black
        - general_themes: List of general position characteristics
    """
    white_themes = []
    black_themes = []
    general_themes = []
    
    # Analyze pawn structure
    isolated_pawns_white = _detect_isolated_pawns(board, chess.WHITE)
    isolated_pawns_black = _detect_isolated_pawns(board, chess.BLACK)
    
    if isolated_pawns_white:
        white_themes.append(f"isolated pawn on {chess.square_name(isolated_pawns_white[0])}")
    if isolated_pawns_black:
        black_themes.append(f"isolated pawn on {chess.square_name(isolated_pawns_black[0])}")
    
    # Analyze bishops
    bad_bishop_white = _detect_bad_bishop(board, chess.WHITE)
    bad_bishop_black = _detect_bad_bishop(board, chess.BLACK)
    
    if bad_bishop_white:
        white_themes.append(f"bad bishop on {chess.square_name(bad_bishop_white)}")
    if bad_bishop_black:
        black_themes.append(f"bad bishop on {chess.square_name(bad_bishop_black)}")
    
    # Analyze rooks
    rooks_on_7th_white = _detect_rooks_on_7th(board, chess.WHITE)
    rooks_on_7th_black = _detect_rooks_on_7th(board, chess.BLACK)
    
    if rooks_on_7th_white:
        white_themes.append(f"rook on 7th rank ({', '.join(chess.square_name(r) for r in rooks_on_7th_white)})")
    if rooks_on_7th_black:
        black_themes.append(f"rook on 2nd rank ({', '.join(chess.square_name(r) for r in rooks_on_7th_black)})")
    
    # Analyze space advantage
    space_white = _calculate_space(board, chess.WHITE)
    space_black = _calculate_space(board, chess.BLACK)
    
    if space_white > space_black + 3:
        white_themes.append("significant space advantage")
    elif space_black > space_white + 3:
        black_themes.append("significant space advantage")
    
    # Analyze king safety
    king_safety_white = _analyze_king_safety(board, chess.WHITE)
    king_safety_black = _analyze_king_safety(board, chess.BLACK)
    
    if king_safety_white == "exposed":
        white_themes.append("exposed king position")
    if king_safety_black == "exposed":
        black_themes.append("exposed king position")
    
    # Analyze piece activity
    active_pieces_white = _count_active_pieces(board, chess.WHITE)
    active_pieces_black = _count_active_pieces(board, chess.BLACK)
    
    if active_pieces_white > active_pieces_black + 2:
        white_themes.append("superior piece activity")
    elif active_pieces_black > active_pieces_white + 2:
        black_themes.append("superior piece activity")
    
    # Detect passed pawns
    passed_pawns_white = _detect_passed_pawns(board, chess.WHITE)
    passed_pawns_black = _detect_passed_pawns(board, chess.BLACK)
    
    if passed_pawns_white:
        squares = ', '.join(chess.square_name(p) for p in passed_pawns_white)
        white_themes.append(f"passed pawn on {squares}")
    if passed_pawns_black:
        squares = ', '.join(chess.square_name(p) for p in passed_pawns_black)
        black_themes.append(f"passed pawn on {squares}")
    
    # Detect doubled pawns
    doubled_white = _detect_doubled_pawns(board, chess.WHITE)
    doubled_black = _detect_doubled_pawns(board, chess.BLACK)
    
    if doubled_white:
        white_themes.append(f"doubled pawns on {chess.FILE_NAMES[doubled_white[0]]}-file")
    if doubled_black:
        black_themes.append(f"doubled pawns on {chess.FILE_NAMES[doubled_black[0]]}-file")
    
    # General position characteristics
    if len(list(board.legal_moves)) < 10:
        general_themes.append("cramped position")
    
    if board.is_check():
        general_themes.append("king under check")
    
    result = {
        "white_themes": white_themes,
        "black_themes": black_themes,
        "general_themes": general_themes,
    }
    
    logger.debug("strategic_analysis", **result)
    return result


def _detect_isolated_pawns(board: chess.Board, color: bool) -> List[int]:
    """Detect isolated pawns (no friendly pawns on adjacent files).
    
    Args:
        board: Chess board
        color: Player color (chess.WHITE or chess.BLACK)
        
    Returns:
        List of squares with isolated pawns
    """
    isolated = []
    pawn_squares = list(board.pieces(chess.PAWN, color))
    
    for square in pawn_squares:
        file = chess.square_file(square)
        has_neighbor = False
        
        # Check adjacent files for friendly pawns
        for adj_file in [file - 1, file + 1]:
            if 0 <= adj_file <= 7:
                for rank in range(8):
                    adj_square = chess.square(adj_file, rank)
                    if board.piece_at(adj_square) == chess.Piece(chess.PAWN, color):
                        has_neighbor = True
                        break
        
        if not has_neighbor:
            isolated.append(square)
    
    return isolated


def _detect_bad_bishop(board: chess.Board, color: bool) -> Optional[int]:
    """Detect bad bishop (blocked by own pawns on same color).
    
    Args:
        board: Chess board
        color: Player color
        
    Returns:
        Square of bad bishop, or None
    """
    bishops = list(board.pieces(chess.BISHOP, color))
    pawns = list(board.pieces(chess.PAWN, color))
    
    for bishop_sq in bishops:
        bishop_color = chess.square_name(bishop_sq)[1] in '1357'  # Light squares
        
        # Count own pawns on same colored squares
        blocked_count = 0
        for pawn_sq in pawns:
            pawn_color = chess.square_name(pawn_sq)[1] in '1357'
            if pawn_color == bishop_color:
                blocked_count += 1
        
        # Bad bishop if more than 3 pawns on same color
        if blocked_count >= 4:
            return bishop_sq
    
    return None


def _detect_rooks_on_7th(board: chess.Board, color: bool) -> List[int]:
    """Detect rooks on 7th/2nd rank (opponent's back rank area).
    
    Args:
        board: Chess board
        color: Player color
        
    Returns:
        List of squares with rooks on 7th/2nd rank
    """
    target_rank = 6 if color == chess.WHITE else 1  # 7th for white, 2nd for black
    rooks = list(board.pieces(chess.ROOK, color))
    
    rooks_on_7th = []
    for rook_sq in rooks:
        if chess.square_rank(rook_sq) == target_rank:
            rooks_on_7th.append(rook_sq)
    
    return rooks_on_7th


def _calculate_space(board: chess.Board, color: bool) -> int:
    """Calculate space control (number of squares controlled in center).
    
    Args:
        board: Chess board
        color: Player color
        
    Returns:
        Space score (higher = more space)
    """
    # Center squares: d4, e4, d5, e5
    # Extended center: c3-f3, c4-f4, c5-f5, c6-f6
    center_squares = [
        chess.D4, chess.E4, chess.D5, chess.E5,
        chess.C3, chess.F3, chess.C4, chess.F4,
        chess.C5, chess.F5, chess.C6, chess.F6,
    ]
    
    space = 0
    for square in center_squares:
        if board.is_attacked_by(color, square):
            space += 1
    
    return space


def _analyze_king_safety(board: chess.Board, color: bool) -> str:
    """Analyze king safety.
    
    Args:
        board: Chess board
        color: Player color
        
    Returns:
        Safety status: "safe", "moderate", or "exposed"
    """
    king_square = board.king(color)
    if not king_square:
        return "unknown"
    
    # Check if king is castled
    king_file = chess.square_file(king_square)
    king_rank = chess.square_rank(king_square)
    
    # Check for pawn shield
    shield_count = 0
    if color == chess.WHITE:
        # Check squares in front of king
        for file_offset in [-1, 0, 1]:
            file = king_file + file_offset
            if 0 <= file <= 7 and king_rank < 7:
                shield_square = chess.square(file, king_rank + 1)
                if board.piece_at(shield_square) == chess.Piece(chess.PAWN, color):
                    shield_count += 1
    else:
        for file_offset in [-1, 0, 1]:
            file = king_file + file_offset
            if 0 <= file <= 7 and king_rank > 0:
                shield_square = chess.square(file, king_rank - 1)
                if board.piece_at(shield_square) == chess.Piece(chess.PAWN, color):
                    shield_count += 1
    
    # Check for enemy attackers near king
    attackers = 0
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece and piece.color != color:
            if chess.square_distance(square, king_square) <= 2:
                if board.is_attacked_by(not color, king_square):
                    attackers += 1
    
    if shield_count >= 2 and attackers == 0:
        return "safe"
    elif shield_count >= 1 or attackers <= 1:
        return "moderate"
    else:
        return "exposed"


def _count_active_pieces(board: chess.Board, color: bool) -> int:
    """Count actively placed pieces (not on back rank).
    
    Args:
        board: Chess board
        color: Player color
        
    Returns:
        Number of active pieces
    """
    back_rank = 0 if color == chess.WHITE else 7
    active = 0
    
    for piece_type in [chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN]:
        pieces = list(board.pieces(piece_type, color))
        for square in pieces:
            if chess.square_rank(square) != back_rank:
                active += 1
    
    return active


def _detect_passed_pawns(board: chess.Board, color: bool) -> List[int]:
    """Detect passed pawns (no enemy pawns can stop them).
    
    Args:
        board: Chess board
        color: Player color
        
    Returns:
        List of squares with passed pawns
    """
    passed = []
    pawn_squares = list(board.pieces(chess.PAWN, color))
    enemy_pawns = list(board.pieces(chess.PAWN, not color))
    
    for square in pawn_squares:
        file = chess.square_file(square)
        rank = chess.square_rank(square)
        
        is_passed = True
        # Check if any enemy pawn can block this pawn
        for enemy_sq in enemy_pawns:
            enemy_file = chess.square_file(enemy_sq)
            enemy_rank = chess.square_rank(enemy_sq)
            
            # Check if enemy pawn is on same or adjacent file and ahead
            if abs(enemy_file - file) <= 1:
                if (color == chess.WHITE and enemy_rank > rank) or \
                   (color == chess.BLACK and enemy_rank < rank):
                    is_passed = False
                    break
        
        if is_passed:
            passed.append(square)
    
    return passed


def _detect_doubled_pawns(board: chess.Board, color: bool) -> List[int]:
    """Detect doubled pawns (two pawns on same file).
    
    Args:
        board: Chess board
        color: Player color
        
    Returns:
        List of files with doubled pawns
    """
    doubled_files = []
    
    for file in range(8):
        count = 0
        for rank in range(8):
            square = chess.square(file, rank)
            if board.piece_at(square) == chess.Piece(chess.PAWN, color):
                count += 1
        
        if count >= 2:
            doubled_files.append(file)
    
    return doubled_files


def format_themes_for_commentary(themes_dict: Dict[str, List[str]], player: str) -> str:
    """Format strategic themes into natural language for commentary.
    
    Args:
        themes_dict: Dictionary from analyze_position
        player: "white" or "black"
        
    Returns:
        Formatted string describing themes
    """
    themes = themes_dict.get(f"{player}_themes", [])
    general = themes_dict.get("general_themes", [])
    
    if not themes and not general:
        return "The position is balanced"
    
    parts = []
    if themes:
        parts.append(f"{player.capitalize()} has {', '.join(themes)}")
    if general:
        parts.append(', '.join(general))
    
    return '. '.join(parts) + '.'
