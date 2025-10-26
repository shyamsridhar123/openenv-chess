# Feature Specification: Phase 1 Quick Wins - Chess Agent & Commentary Improvements

**Feature Branch**: `001-phase1-quick-wins`  
**Created**: October 25, 2025  
**Status**: Draft  
**Input**: User description: "Implement Phase 1 Quick Wins: Hybrid agent architecture with Stockfish integration, opening book integration, Syzygy tablebase support, enhanced commentary prompts with deep analysis, and strategic theme detection"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Hybrid Agent Architecture (Priority: P1)

As a chess game operator, I need agents to make tactically sound moves while maintaining their unique personalities, so that games are both entertaining and competitive without embarrassing blunders.

**Why this priority**: This is the foundation for all gameplay improvements. Without tactical soundness, agents produce low-quality games regardless of other enhancements. Eliminates the most critical problem (frequent blunders) while maintaining personality differentiation.

**Independent Test**: Can be fully tested by running games between hybrid agents and comparing move quality metrics (blunder rate, average centipawn loss, tactical accuracy) against baseline LLM-only agents. Delivers immediate value through playable, competitive games.

**Acceptance Scenarios**:

1. **Given** a hybrid agent is playing a game, **When** the agent needs to select a move, **Then** the agent queries Stockfish for top 5 candidate moves with evaluations
2. **Given** Stockfish returns top 5 moves with scores, **When** the agent makes a decision, **Then** the selected move is always one of the top 5 options (no illegal or clearly losing moves)
3. **Given** an aggressive personality agent has 5 move candidates, **When** multiple candidates include attacking moves, **Then** the agent prefers the most aggressive option from the top candidates
4. **Given** a defensive personality agent faces top 5 candidates, **When** some candidates are risky sacrifices, **Then** the agent selects the safer positional option
5. **Given** a move requires selection, **When** Stockfish is unavailable, **Then** the system gracefully falls back to traditional LLM-only move generation with appropriate logging

---

### User Story 2 - Opening Book Integration (Priority: P1)

As a chess game operator, I need agents to play established opening theory efficiently, so that games begin with sound positions and agents don't waste resources "reinventing" well-known opening moves.

**Why this priority**: Opening phase represents first 15-20 moves of every game. Poor opening play wastes tokens and creates weak positions that cascade into poor middlegames. Using book moves is instant (no LLM call needed) and follows grandmaster theory.

**Independent Test**: Can be fully tested by starting games and verifying that opening moves match grandmaster database for the first 10-15 moves, with personality-appropriate line selection. Delivers immediate value through faster, stronger opening play and reduced API costs.

**Acceptance Scenarios**:

1. **Given** a game starts from the initial position, **When** an agent needs to select its first move, **Then** the system queries the opening book database for known moves
2. **Given** the opening book contains multiple candidate moves for a position, **When** an aggressive personality agent is moving, **Then** sharp tactical lines (Sicilian, King's Indian, etc.) are preferred over quiet systems
3. **Given** a positional personality agent is selecting from book moves, **When** multiple lines are available, **Then** quiet strategic openings (Catalan, English, Reti) are selected
4. **Given** a position is found in the opening book, **When** the move is made, **Then** no LLM API call is required (instant move generation)
5. **Given** a position is not found in the opening book, **When** the agent needs a move, **Then** the system transitions seamlessly to hybrid agent move generation
6. **Given** the opening book database is unavailable, **When** an opening move is needed, **Then** the system falls back to hybrid agent generation with appropriate logging

---

### User Story 3 - Syzygy Tablebase Integration (Priority: P2)

As a chess game operator, I need agents to convert winning endgames correctly, so that technically won positions don't end in draws due to imprecise play.

**Why this priority**: While less frequent than opening/middlegame, endgames determine final outcomes. Perfect endgame play ensures agents don't throw away winning positions, improving competitive credibility. Lower priority than P1 items since it affects fewer moves per game.

**Independent Test**: Can be fully tested by creating endgame positions (7 pieces or fewer), running games to completion, and verifying that all technically winning positions are converted to wins with optimal move sequences. Delivers value through reliable endgame technique.

**Acceptance Scenarios**:

1. **Given** a position has 7 or fewer pieces on the board, **When** an agent needs to select a move, **Then** the system queries the Syzygy tablebase API
2. **Given** the tablebase indicates a forced win, **When** the agent moves, **Then** the optimal move from tablebase is selected (no LLM involvement)
3. **Given** the tablebase indicates a draw or loss, **When** the agent is choosing, **Then** the system falls back to hybrid agent move generation to find the best practical try
4. **Given** a position with more than 7 pieces, **When** move selection occurs, **Then** the tablebase is skipped and hybrid agent generation is used
5. **Given** the tablebase API is unavailable or times out, **When** an endgame move is needed, **Then** the system falls back to hybrid agent generation with appropriate logging

---

### User Story 4 - Enhanced Commentary Prompts (Priority: P1)

As a viewer of chess games, I need commentary that explains WHY moves are strong or weak with strategic context, so that I understand the game's narrative and learn from the analysis.

**Why this priority**: Commentary is the primary user-facing output. Current generic commentary ("What a move!") provides no educational or entertainment value. Enhanced prompts transform commentary from play-by-play to grandmaster-level analysis, dramatically improving user experience.

**Independent Test**: Can be fully tested by generating commentary for sample positions with known tactical/strategic themes and evaluating whether commentary mentions best alternatives, strategic implications, pawn structure, and multi-move continuations. Delivers immediate value through substantive game narration.

**Acceptance Scenarios**:

1. **Given** a move triggers commentary generation, **When** building the prompt, **Then** the system includes the best alternative move from Stockfish with its continuation
2. **Given** a move is evaluated as a mistake, **When** generating commentary, **Then** the output explains WHY the move is weak and what specific advantage was lost
3. **Given** commentary is generated for any move, **When** presenting the analysis, **Then** the output discusses the resulting position's strategic themes (pawn structure, piece activity, king safety)
4. **Given** a tactical move occurs, **When** commentary is generated, **Then** the output includes the 3-5 move continuation showing consequences
5. **Given** a positional move occurs, **When** commentary is generated, **Then** the output references specific squares, weaknesses, and long-term plans
6. **Given** any commentary prompt is built, **When** assembling context, **Then** the prompt includes current evaluation, top 3 candidate moves with scores, and move quality assessment

---

### User Story 5 - Strategic Theme Detection (Priority: P2)

As a viewer of chess games, I need commentary that identifies and explains strategic patterns (isolated pawns, bad bishops, space advantages), so that I understand positional dynamics beyond individual moves.

**Why this priority**: Strategic themes provide the "story" of the position. Without theme detection, commentary treats each move in isolation. This adds depth to analysis but depends on having enhanced prompts (P1) in place first.

**Independent Test**: Can be fully tested by analyzing positions with known strategic features (isolated d-pawn, bad bishop, rook on 7th) and verifying that the detection system correctly identifies these patterns. Delivers value through richer, more educational commentary.

**Acceptance Scenarios**:

1. **Given** a position contains an isolated pawn, **When** strategic analysis runs, **Then** the system detects the isolated pawn and identifies the square
2. **Given** a position has a bishop blocked by its own pawns on the same color, **When** strategic analysis runs, **Then** the system identifies the "bad bishop"
3. **Given** one side has significantly more central space control, **When** strategic analysis runs, **Then** the system quantifies the space advantage
4. **Given** a rook occupies the 7th rank attacking pawns, **When** strategic analysis runs, **Then** the system identifies "rook on 7th rank" as an active theme
5. **Given** strategic themes are detected, **When** building commentary prompts, **Then** the themes are included in the context with explanations of their significance
6. **Given** no significant strategic themes are present, **When** analysis runs, **Then** the system returns an empty or minimal theme list without failing

---

### Edge Cases

- What happens when Stockfish evaluation service is completely unavailable for extended period? (System should fall back to LLM-only mode with degraded performance warnings)
- How does the system handle transpositions in the opening book? (Book should recognize transposed positions and offer moves for the resulting position)
- What happens when the tablebase API rate-limits requests? (Implement caching and fallback to hybrid agent after timeout threshold)
- How does commentary generation handle positions with mate-in-N evaluations? (Should convert mate scores to descriptive text, e.g., "forced mate in 3 moves")
- What happens when strategic theme detection identifies conflicting themes (e.g., both "strong pawn structure" and "weak pawn structure")? (Prioritize the most significant theme or present multiple balanced themes)
- How does the hybrid agent handle positions where all top 5 Stockfish moves are evaluated as losing? (Agent should select the least-worst option and commentary should reflect defensive situation)

## Requirements *(mandatory)*

### Functional Requirements

**Hybrid Agent Architecture:**

- **FR-001**: System MUST query Stockfish for top N candidate moves (configurable, default 5) before agent decision-making
- **FR-002**: System MUST include move evaluations (centipawn scores) and Principal Variation (PV) lines for each candidate move
- **FR-003**: Agent move selection MUST be constrained to Stockfish's candidate moves (hybrid architecture replaces LLM-only flow entirely)
- **FR-004**: System MUST adapt candidate move selection based on agent personality (aggressive agents see attacking candidates emphasized, defensive agents see safe candidates)
- **FR-005**: System MUST provide fallback to traditional LLM-only move generation when Stockfish is unavailable
- **FR-006**: System MUST log all fallback events with reasons (Stockfish unavailable, timeout, error)

**Opening Book Integration:**

- **FR-007**: System MUST query opening book database before hybrid agent move generation in opening phase (up to move 15)
- **FR-008**: Opening book MUST support personality-based move filtering (aggressive personalities prefer sharp lines, defensive prefer solid lines)
- **FR-009**: System MUST transition seamlessly to hybrid agent when position is not in opening book
- **FR-010**: Opening book moves MUST bypass LLM API calls (direct move return)
- **FR-011**: System MUST use Lichess Masters API or equivalent grandmaster game database as opening source
- **FR-012**: System MUST handle opening book unavailability with graceful fallback to hybrid agent

**Syzygy Tablebase Integration:**

- **FR-013**: System MUST query Syzygy tablebase for positions with 7 or fewer pieces
- **FR-014**: System MUST return optimal tablebase move when position is in tablebase database
- **FR-015**: Tablebase moves MUST bypass both Stockfish candidate generation and LLM decision-making
- **FR-016**: System MUST use Lichess Tablebase API or equivalent as data source
- **FR-017**: System MUST fall back to hybrid agent generation when tablebase is unavailable or position not found
- **FR-018**: System MUST cache tablebase results per game session to reduce API calls for repeated positions

**Enhanced Commentary Prompts:**

- **FR-019**: Commentary prompts MUST include best alternative move from Stockfish evaluation
- **FR-020**: Commentary prompts MUST include 3-5 move continuation (Principal Variation) for played move
- **FR-021**: Commentary prompts MUST include current position evaluation in centipawns
- **FR-022**: Commentary prompts MUST include move quality assessment (excellent/good/inaccuracy/mistake/blunder)
- **FR-023**: Commentary generation MUST explain WHY a move is strong or weak (positional/tactical justification)
- **FR-024**: Commentary MUST discuss strategic implications (pawn structure effects, piece activity changes, king safety impact)
- **FR-025**: Commentary MUST reference specific squares and pieces (e.g., "weakens the d5 square", "knight has no outpost")
- **FR-026**: Commentary MUST be 4-6 sentences for high-priority triggers (blunders, brilliant moves, checkmate)
- **FR-027**: Commentary MUST be 2-3 sentences for standard triggers (tactical patterns, regular moves)

**Strategic Theme Detection:**

- **FR-028**: System MUST analyze positions for isolated pawns (pawns with no friendly pawns on adjacent files)
- **FR-029**: System MUST analyze positions for bad bishops (bishops blocked by own pawns on same color squares)
- **FR-030**: System MUST analyze positions for rooks on 7th rank (opponent's 2nd rank)
- **FR-031**: System MUST analyze positions for space advantages (central square control)
- **FR-032**: System MUST analyze positions for king safety issues (exposed king, pawn storm, back rank weakness)
- **FR-033**: Strategic themes MUST be included in commentary prompts when detected (report all themes, let commentary generation prioritize)
- **FR-034**: System MUST handle positions with no significant strategic themes without failing

### Key Entities

- **HybridAgent**: Represents chess agent that combines Stockfish evaluation with LLM decision-making, maintains personality configuration, manages move selection workflow
- **OpeningBook**: Database of opening positions mapped to grandmaster moves, supports personality-based filtering, handles position lookups via FEN or hash
- **TablebaseClient**: Interface to Syzygy tablebase API, queries positions with ≤7 pieces, caches results, handles API failures gracefully
- **CommentaryPromptBuilder**: Constructs enriched prompts for commentary generation, aggregates Stockfish analysis, strategic themes, and move continuations
- **StrategicThemeAnalyzer**: Detects positional patterns (isolated pawns, bad bishops, space control), provides theme descriptions for commentary context
- **MoveEvaluation**: Represents Stockfish evaluation result, contains centipawn score, move quality classification, best alternative move, principal variation line

## Success Criteria *(mandatory)*

### Measurable Outcomes

**Agent Gameplay Quality:**

- **SC-001**: Agent blunder rate (moves losing >300 centipawns) decreases to below 5% of total moves (measured across 100 games)
- **SC-002**: Average centipawn loss per move decreases to below 50 centipawns (measured across 100 games)
- **SC-003**: Tactical accuracy (percentage of non-mistake/non-blunder moves) increases to above 85% (measured across 100 games)
- **SC-004**: Agents demonstrate differentiated playing styles (aggressive agents select sharper moves, defensive agents select safer moves) in 80%+ of decision points where multiple candidates have similar evaluations

**Opening Phase Performance:**

- **SC-005**: Opening moves (first 15 moves) match grandmaster theory in 90%+ of games
- **SC-006**: Opening phase move generation completes in under 0.5 seconds per move (vs. 2-5 seconds for LLM calls)
- **SC-007**: LLM API calls during opening phase (first 15 moves) reduce by 80%+ compared to baseline

**Endgame Performance:**

- **SC-008**: Agents convert 100% of tablebase-confirmed winning endgames (positions with 7 or fewer pieces showing forced win)
- **SC-009**: Endgame positions with 7 or fewer pieces are resolved optimally without unnecessary move delays

**Commentary Quality:**

- **SC-010**: Commentary includes alternative move analysis in 100% of mistake/blunder triggers
- **SC-011**: Commentary includes strategic theme references in 70%+ of generated outputs
- **SC-012**: Commentary avoids generic phrases ("great move", "what a position") and uses specific chess terminology in 90%+ of outputs
- **SC-013**: Commentary includes multi-move continuations (3-5 moves ahead) in 80%+ of tactical position comments
- **SC-014**: Human evaluators rate commentary quality improvement as "significantly better" in blind comparison tests (target: 80%+ prefer enhanced commentary over baseline)

**System Reliability:**

- **SC-015**: System handles Stockfish unavailability gracefully with < 1 second fallback time
- **SC-016**: System handles opening book unavailability without game interruption
- **SC-017**: System handles tablebase API failures without game interruption
- **SC-018**: All fallback scenarios log appropriately for monitoring and debugging

## Assumptions

1. **Stockfish Availability**: Stockfish chess engine is installed and accessible on the deployment environment (can query via python-chess library)
2. **API Access**: System has network access to Lichess Masters API and Lichess Tablebase API (or equivalent alternatives)
3. **Response Times**: External APIs (opening book, tablebase) respond within 1 second for 95% of requests
4. **Evaluation Depth**: Stockfish depth of 15-20 plies provides sufficient accuracy for move candidate selection (balance of speed vs. quality)
5. **Personality Configuration**: Existing agent personality system (aggressive, defensive, balanced, tactical, positional) remains unchanged
6. **Commentary Trigger System**: Existing commentary trigger detection (blunders, brilliant moves, tactics) remains functional
7. **Azure OpenAI Access**: GPT-4 and Azure Realtime API remain available and configured for commentary generation

## Out of Scope

- Multi-move planning with extended PV line analysis (Phase 2 feature)
- Position-type specific prompting (Phase 2 feature)
- Historical game reference integration (Phase 3 feature)
- Predictive commentary (Phase 3 feature)
- Self-play learning and adaptive prompting (Phase 3 feature)
- Agent Elo rating calculation and tracking system
- Graphical visualization of strategic themes
- Commentary personalization based on viewer expertise level
- Multi-language commentary support
- Real-time commentary streaming optimization

## Clarifications

### Session 2025-10-25

**Q1: Integration Strategy**  
**Question**: Should the hybrid agent architecture replace the current LLM-only flow entirely, or should it supplement it (e.g., Stockfish as an optional enhancement)?  
**Answer**: Replace current flow - All agents become hybrid agents by default. This ensures consistent tactical quality across all personalities.

**Q2: PV Line Extraction**  
**Question**: How should PV (Principal Variation) lines be extracted from Stockfish for commentary?  
**Answer**: Enhance `get_top_moves()` method to return `List[Tuple[Move, score, PV_line]]` where PV_line is the continuation sequence.

**Q3: Opening Book Cutoff**  
**Question**: At what move number should the system stop consulting the opening book and transition to hybrid agent generation?  
**Answer**: Move 15 (aligns with success criteria SC-005 which measures first 15 moves).

**Q4: Theme Detection Threshold**  
**Question**: Should strategic theme detection report ALL detected themes or only the most significant ones (threshold-based)?  
**Answer**: Report all detected themes. Let commentary generation decide which to emphasize based on context.

**Q5: Tablebase Cache Duration**  
**Question**: How long should tablebase results be cached?  
**Answer**: Cache for game session only (prevents stale data across games, reduces repeated API calls within a single game).
