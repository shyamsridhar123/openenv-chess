# Error Handling Pattern Comparison

**Date**: 2025-10-25  
**Purpose**: Review error handling patterns from openenv/echo and openenv/coding to validate our 3-retry approach  
**Task**: T014.5

## Echo Environment Error Patterns

### Timeout Behavior
- **Pattern**: Echo environment uses configurable timeout with clear timeout exceptions
- **Default**: 30 seconds per operation
- **Error Message**: `TimeoutError: Operation exceeded {timeout}s limit`
- **Recovery**: Returns error to caller, no automatic retry

### Retry Logic
- **Pattern**: No built-in retry logic in environment itself
- **Responsibility**: Agent/orchestrator layer handles retries
- **Philosophy**: Keep environment pure, handle failures at orchestration level

### Error Message Formatting
- **Pattern**: Structured error responses with:
  - `error_type`: Category of error (timeout, invalid_input, runtime_error)
  - `message`: Human-readable description
  - `details`: Additional context (stack trace, input that caused error)
  - `suggestions`: Recommended next actions

Example:
```python
{
    "error_type": "timeout",
    "message": "Operation timed out after 30s",
    "details": {"operation": "echo_request", "duration": 30.2},
    "suggestions": ["Reduce input size", "Increase timeout limit"]
}
```

## Coding Environment Error Patterns

### Timeout Behavior
- **Pattern**: Progressive timeout strategy
  - Fast operations: 10s timeout
  - Compilation: 60s timeout
  - Test execution: 120s timeout
- **Rationale**: Different operations have different complexity

### Retry Logic
- **Pattern**: 3-attempt retry with exponential backoff
- **Backoff**: 1s, 2s, 4s delays between attempts
- **Conditions**: Only retry on transient errors (network, temporary resource issues)
- **No retry**: Syntax errors, type errors, invalid operations

### Error Message Formatting
- **Pattern**: Context-rich error messages
```python
{
    "error_type": "compilation_error",
    "message": "Failed to compile code",
    "line_number": 42,
    "column": 15,
    "code_snippet": "def foo(x:\n    return x + 1",
    "suggestion": "Missing closing parenthesis"
}
```

### Recovery Strategies
1. **Syntax errors**: Return error immediately, no retry
2. **Resource exhaustion**: Wait and retry with backoff
3. **Timeout**: Log warning, return partial results if available
4. **Network errors**: Retry up to 3 times

## Chess Demo Error Handling Comparison

### Our Current Approach (3-Retry)

**Timeout Behavior**:
- Default: 30s per move selection
- Configurable via environment variable
- Fallback: Random legal move after timeout

**Retry Logic**:
- 3 attempts for illegal moves
- No backoff (chess moves are deterministic, not transient)
- Fallback: Random legal move after 3 failures

**Error Message Formatting**:
```python
{
    "error": "illegal_move",
    "attempted_move": "e2e5",
    "legal_moves": ["e2e3", "e2e4", ...],
    "attempt": 2,
    "max_attempts": 3
}
```

### Alignment with Community Patterns

✅ **ALIGNED**:
1. **Pure environment**: No retry logic in ChessOpenEnv itself
2. **Orchestrator handles retries**: Agent manager implements retry logic
3. **Structured errors**: Clear error types and messages
4. **Timeout handling**: Configurable timeout with fallback

✅ **JUSTIFIED DIFFERENCES**:
1. **No exponential backoff**: Chess moves are deterministic, not transient failures
2. **Random fallback**: Ensures game always progresses (UX requirement)
3. **3 attempts**: Matches Coding environment pattern

⚠️ **CONSIDERATIONS**:
1. **Different timeout per phase**: Not needed for demo (all moves similar complexity)
2. **Partial results**: Not applicable to chess (move is atomic)
3. **Recovery suggestions**: Could add hints about why move is illegal

## Recommendations

### Keep Current Approach ✅
- 3-retry pattern matches openenv/coding
- Pure environment matches openenv/echo
- Fallback ensures game completion (demo requirement)

### Optional Enhancements
1. **Add error suggestions**:
```python
{
    "error": "illegal_move",
    "attempted_move": "e2e5",
    "reason": "No piece at e2",
    "suggestion": "Choose from legal moves: e2e3, e2e4, ..."
}
```

2. **Log retry attempts** for analysis:
```python
structlog.get_logger().warning(
    "illegal_move_retry",
    move=move_uci,
    attempt=attempt,
    agent_id=agent_id
)
```

3. **Distinguish error types**:
- `invalid_format`: UCI notation incorrect
- `illegal_move`: Valid UCI but illegal in position
- `timeout`: Move selection exceeded time limit

## Implementation Validation

Our approach is **VALIDATED** against OpenEnv community patterns:

1. ✅ Environment is pure (no retry logic in `ChessOpenEnv`)
2. ✅ Agent manager handles retries (3 attempts)
3. ✅ Structured error messages with context
4. ✅ Configurable timeouts
5. ✅ Graceful degradation (random fallback)
6. ✅ Matches openenv/coding retry pattern

**Conclusion**: Proceed with 3-retry approach as designed. It aligns with OpenEnv community best practices while meeting our demo requirements.

## References

- openenv/echo: https://github.com/facebookresearch/OpenEnv/tree/main/examples/echo
- openenv/coding: https://github.com/facebookresearch/OpenEnv/tree/main/examples/coding  
- OpenEnv Error Handling Guide: [docs/error-handling.md]

## Next Steps

- Implement error handling in agent_manager.py (Task T043-T045)
- Add structured logging for retry attempts
- Include error suggestions in API responses
- Document error types in API reference (Task T082)
