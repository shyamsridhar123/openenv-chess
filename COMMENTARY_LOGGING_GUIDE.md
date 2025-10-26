# Commentary Decision Logging Guide

## Overview
The dynamic commentary system now logs detailed information at each move to help analyze why commentary is or isn't being generated.

## Log Emoji Guide

| Emoji | Log Type | Description |
|-------|----------|-------------|
| 🎙️ | `COMMENTARY_CHECK_START` | Commentary evaluation begins for this move |
| 📊 | `POSITION_ANALYSIS` | Position interest score and evaluation metrics |
| 🎯 | `COMMENTARY_DECISION` | Final decision from CommentaryStrategist |
| ⏭️ | `COMMENTARY_SKIPPED` | Move skipped - no commentary generated |
| 🌐 | `STRATEGIC_OVERVIEW_START` | Strategic overview generation begins |
| ✅ | `STRATEGIC_OVERVIEW_COMPLETE` | Strategic overview successfully generated |
| 💬 | `MOVE_COMMENTARY_START` | Move-specific commentary begins |
| 🔍 | `TRIGGER_DETECTOR_RESULT` | TriggerDetector found specific trigger type |
| 📝 | `GENERATING_MOVE_COMMENTARY` | Commentary generation in progress |
| ✅ | `MOVE_COMMENTARY_COMPLETE` | Move commentary successfully generated |
| ⚠️ | `NO_TRIGGER_DESPITE_DECISION` | Strategist wanted commentary but TriggerDetector said no |
| ❌ | `COMMENTARY_GENERATION_FAILED` | Error during commentary generation |

## Key Fields to Watch

### 🎙️ COMMENTARY_CHECK_START
```json
{
  "move_number": 5,
  "move": "e7e5",
  "san_move": "e5",
  "player": "black",
  "last_commentary_move": 0,
  "moves_since_last": 5
}
```
**Analysis**: Shows how many moves since last commentary. High numbers mean more likely for overview.

### 📊 POSITION_ANALYSIS
```json
{
  "move_number": 5,
  "interest_score": 42,
  "centipawns": 15,
  "eval_swing": 10,
  "just_after_tactical": false,
  "eval_history_length": 5
}
```
**Analysis**: 
- **interest_score < 30** → Usually skipped
- **interest_score 30-59** → Maybe commented (depends on moves_since_last)
- **interest_score 60-74** → Move commentary
- **interest_score ≥ 75** → Critical moment
- **eval_swing > 150** → Critical moment (overrides interest)
- **eval_swing > 100** → just_after_tactical = true

### 🎯 COMMENTARY_DECISION
```json
{
  "move_number": 5,
  "decision": "skip" | "move_comment" | "strategic_overview" | "critical_moment",
  "reason": "Low interest (25) and recent commentary (2 moves ago)",
  "interest_score": 25,
  "moves_since_last": 2,
  "will_generate": false
}
```
**Analysis**: 
- **decision = "skip"** → No commentary, saves API costs
- **decision = "strategic_overview"** → Holistic analysis of position
- **decision = "move_comment"** → Standard move commentary
- **decision = "critical_moment"** → Urgent tactical/blunder commentary

### ⏭️ COMMENTARY_SKIPPED
```json
{
  "move_number": 3,
  "move": "Nf3",
  "san_move": "Nf3",
  "reason": "Low interest (25) and recent commentary (2 moves ago)",
  "interest_score": 25,
  "moves_since_last": 2
}
```
**Analysis**: This is GOOD - routine moves should be skipped!

## Decision Logic Reference

### SKIP Decision
```
interest_score < 30 AND moves_since_last < 5
```
**Means**: Position is routine and we just commented recently

### STRATEGIC_OVERVIEW Decision
```
moves_since_last >= 8 OR
(moves_since_last >= 5 AND interest_score < 40) OR
just_after_tactical == true
```
**Means**: 
- Long time since commentary, OR
- Quiet position needs context, OR
- Just resolved a tactical sequence

### MOVE_COMMENT Decision
```
interest_score >= 60 OR
eval_swing > 75 OR
moves_since_last >= 3
```
**Means**: Moderately interesting position worth noting

### CRITICAL_MOMENT Decision
```
interest_score >= 75 OR
eval_swing > 150
```
**Means**: Highly tactical or major evaluation change

## Analyzing Logs for Turn-by-Turn Issue

### If you see commentary on EVERY move:
1. **Check `moves_since_last`** - Should reset to 0 after each commentary
2. **Check `last_commentary_move`** - Should update after generation
3. **Check decision = "skip"** - Should see many skips for routine moves
4. **Check `interest_score`** - Routine opening moves should be < 40

### Expected Pattern for Healthy System:
```
Move 1: 🎙️ CHECK → 📊 ANALYSIS (interest=20) → 🎯 DECISION (skip) → ⏭️ SKIPPED
Move 2: 🎙️ CHECK → 📊 ANALYSIS (interest=18) → 🎯 DECISION (skip) → ⏭️ SKIPPED
Move 3: 🎙️ CHECK → 📊 ANALYSIS (interest=22) → 🎯 DECISION (skip) → ⏭️ SKIPPED
Move 4: 🎙️ CHECK → 📊 ANALYSIS (interest=25) → 🎯 DECISION (skip) → ⏭️ SKIPPED
Move 5: 🎙️ CHECK → 📊 ANALYSIS (interest=15) → 🎯 DECISION (skip) → ⏭️ SKIPPED
Move 6: 🎙️ CHECK → 📊 ANALYSIS (interest=35) → 🎯 DECISION (overview) → 🌐 OVERVIEW → ✅ COMPLETE
Move 7: 🎙️ CHECK → 📊 ANALYSIS (interest=28) → 🎯 DECISION (skip) → ⏭️ SKIPPED
Move 8: 🎙️ CHECK → 📊 ANALYSIS (interest=72) → 🎯 DECISION (move_comment) → 💬 MOVE → ✅ COMPLETE
```

### If seeing turn-by-turn, look for:
```
❌ EVERY move has decision="move_comment" or decision="critical_moment"
❌ interest_score is always high (> 60)
❌ No "skip" decisions at all
❌ last_commentary_move never updates
❌ moves_since_last is always high (> 5)
```

## Troubleshooting Commands

### Grep for all commentary decisions in logs:
```bash
grep "COMMENTARY_DECISION" logs/*.log
```

### Count skips vs generated:
```bash
grep "COMMENTARY_SKIPPED" logs/*.log | wc -l
grep "COMMENTARY_COMPLETE" logs/*.log | wc -l
```

### See interest scores:
```bash
grep "POSITION_ANALYSIS" logs/*.log | grep -o "interest_score=[0-9]*"
```

### Check if state is updating:
```bash
grep "last_commentary_move" logs/*.log | tail -20
```

## What to Report

When reporting issues, include:
1. **Decision pattern**: How many skips vs generated?
2. **Interest scores**: Are they realistic for the moves?
3. **moves_since_last**: Is it resetting after commentary?
4. **Sample log snippet**: Include 5-10 consecutive moves showing the pattern

## Next Steps

1. Start a game with commentary enabled
2. Monitor logs in real-time: `tail -f logs/chess_env_*.log`
3. Look for emoji-marked log lines
4. Share the decision pattern and interest scores
5. We'll adjust thresholds if needed
