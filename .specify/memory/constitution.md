<!--
Sync Impact Report - Version 1.0.0
=====================================
Version Change: INITIAL → 1.0.0 (New Constitution)
Created: 2025-10-25

New Constitution Principles:
1. OpenEnv Compliance (NON-NEGOTIABLE)
2. Simplicity & Accessibility First
3. Visual Clarity & Educational Value
4. OpenEnv Reference Quality
5. Performance & Reliability

Added Sections:
- Core Principles (5 principles)
- Technical Standards
- Quality Requirements
- Governance

Templates Status:
✅ plan-template.md - Aligned with constitution principles
✅ spec-template.md - User story format aligns with educational value
✅ tasks-template.md - Test-first approach aligns with quality requirements

Follow-up TODOs:
- None - All principles defined and ready for use

Notes:
- This is the initial constitution derived from PRD v1.0
- Emphasizes demo/educational nature while maintaining production-quality standards
- Balances rapid development with reliability requirements
-->

# Chess OpenEnv Multi-Agent System Constitution

## Core Principles

### I. OpenEnv Compliance (NON-NEGOTIABLE)

**The system MUST adhere to the OpenEnv 0.1 specification at all times.**

- All environment implementations MUST implement `reset()`, `step()`, `state()`, and `close()` methods
- Observations MUST be returned in Gymnasium-compatible format
- Action space MUST be clearly specified and validated
- HTTP API deployment MUST follow OpenEnv standards
- Any deviation from the OpenEnv specification MUST be explicitly documented and justified

**Rationale**: This project serves as a reference implementation for the OpenEnv framework. Compliance is non-negotiable to maintain credibility and educational value.

### II. Simplicity & Accessibility First

**Every feature MUST prioritize ease of understanding and one-command deployment.**

- Setup MUST work with single command: `make docker-up` or equivalent
- Dependencies MUST be minimal and clearly documented
- Code MUST include clear comments explaining OpenEnv concepts
- Architecture MUST be straightforward, avoiding unnecessary abstractions
- Documentation MUST be comprehensive with visual diagrams
- No feature requiring >5 minutes to demonstrate may be added without explicit justification

**Rationale**: Primary users are developers learning OpenEnv. Complex setup or architecture creates barriers to adoption and defeats the educational purpose.

### III. Visual Clarity & Educational Value

**All user-facing features MUST provide clear visual feedback and transparency into agent behavior.**

- Chess board rendering MUST be clear and animate smoothly
- Agent reasoning MUST be visible to users during gameplay
- Move history MUST be accessible and reviewable
- Error states MUST provide actionable feedback
- UI MUST prioritize clarity over visual flourishes
- Performance metrics MUST be observable in real-time

**Rationale**: Visual demonstrations are the primary value proposition. Users must be able to understand what agents are doing and why, making the learning experience intuitive and engaging.

### IV. OpenEnv Reference Quality

**All code MUST serve as a best-practice example that developers can learn from and adapt.**

- Code style MUST follow PEP 8 (Python) and industry standards
- All functions and classes MUST have clear docstrings
- Architecture patterns MUST be production-ready, not demo hacks
- Test coverage MUST be ≥95% for core environment logic
- API design MUST be RESTful and well-documented with OpenAPI
- Security practices MUST be followed (input validation, rate limiting, non-root containers)

**Rationale**: Developers will copy and adapt this code. Poor practices will propagate. The project must demonstrate not just what works, but what works well.

### V. Performance & Reliability

**The system MUST handle production-like load without degradation or crashes.**

- Environment reset MUST complete in <100ms
- Move validation MUST complete in <10ms
- SVG rendering MUST complete in <50ms
- System MUST support ≥10 concurrent games without degradation
- Game completion rate MUST be >95% (no crashes)
- Agent failures MUST be handled gracefully with fallback behaviors
- Memory usage MUST be bounded with automatic cleanup

**Rationale**: Demos that crash or lag create negative impressions. Reliability demonstrates that multi-agent systems can be production-ready, which is a key selling point for OpenEnv adoption.

## Technical Standards

### Technology Stack (MUST)

**Required Technologies:**
- Python 3.11+ (primary language)
- FastAPI (HTTP/WebSocket server)
- python-chess (chess logic - MUST validate all moves)
- smolagents (agent framework from Hugging Face)
- uv (dependency management)
- Docker & Docker Compose (deployment)

**Prohibited:**
- Paid API dependencies in core functionality (demo must work with free tier)
- GPU requirements for demo mode (training mode may differ)
- Database persistence for game state (in-memory acceptable for demo scope)
- Heavyweight frameworks that obscure OpenEnv patterns

**Rationale**: Technology choices must support both ease of setup and clear demonstration of OpenEnv concepts.

### API Design Standards

**REST API Requirements:**
- MUST provide standard OpenEnv endpoints: `/reset`, `/step`, `/state`, `/render`
- MUST include `/health` endpoint for monitoring
- MUST document with OpenAPI/Swagger specification
- MUST validate all inputs and return meaningful error messages
- MUST implement rate limiting (100 req/min default)
- MUST follow RESTful conventions (proper HTTP verbs and status codes)

**WebSocket API Requirements:**
- MUST emit `game_started`, `move_made`, `game_ended` events at minimum
- MUST handle disconnections gracefully with reconnection logic
- MUST maintain separate state per game session
- SHOULD emit `agent_thinking` events for transparency

**Rationale**: Well-designed APIs enable integration and demonstrate professional development practices.

### Chess Rule Enforcement

**MUST enforce all standard chess rules (FIDE):**
- Move legality validation using python-chess library
- Checkmate, stalemate, and draw detection
- En passant, castling, pawn promotion support
- 50-move rule and threefold repetition

**Rationale**: Incorrect chess rules undermine credibility. Using python-chess ensures correctness and focuses development on OpenEnv integration.

## Quality Requirements

### Testing Standards

**Test Coverage Requirements:**
- Core environment logic: ≥95% coverage (MANDATORY)
- API endpoints: ≥80% coverage (MANDATORY)
- Agent orchestration: ≥90% coverage (MANDATORY)

**Required Test Types:**
- Unit tests for environment methods (`reset`, `step`, validation)
- Integration tests for API endpoints
- Contract tests for OpenEnv compliance
- Performance tests for response time targets

**Test Execution:**
- All tests MUST pass before merging to main branch
- Test suite MUST complete in <30 seconds
- Tests MUST be deterministic (no flaky tests)

**Rationale**: High test coverage ensures reliability and demonstrates quality engineering practices that users can learn from.

### Code Quality Standards

**Code Style:**
- MUST follow PEP 8 style guide
- MUST use black for formatting
- MUST use isort for import sorting
- MUST pass flake8 linting

**Documentation:**
- All public functions MUST have docstrings with type hints
- All classes MUST have docstrings explaining purpose
- Complex algorithms MUST have inline comments
- README MUST include quick start guide and architecture diagram

**Error Handling:**
- All inputs MUST be validated
- All errors MUST return meaningful messages
- All errors MUST be logged with context
- Critical failures MUST not crash the server

**Rationale**: Consistent code quality makes the project easier to understand and adapt.

### Performance Benchmarks (MUST Meet)

**Response Times:**
- Environment reset: <100ms (P95)
- Move validation: <10ms (P95)
- SVG rendering: <50ms (P95)
- API response time: <200ms (P95)

**Scalability:**
- Concurrent games: ≥10 supported
- Memory per game: <50MB
- Total memory (single server): <2GB

**Reliability:**
- Game completion rate: ≥95%
- Uptime (if hosted): ≥99%
- Error rate: <1% of requests

**Rationale**: Performance targets ensure the demo is responsive and can handle showcase scenarios like conference presentations.

## Development Workflow

### Feature Development Process

1. **Specification**: Create spec in `.specify/specs/[###-feature]/spec.md`
2. **Planning**: Generate plan with `/speckit.plan` command
3. **Constitution Check**: Verify compliance with all principles
4. **Implementation**: Follow tasks.md generated by `/speckit.tasks`
5. **Testing**: Ensure all tests pass and coverage targets met
6. **Documentation**: Update README and architecture docs
7. **Review**: Code review focusing on OpenEnv best practices
8. **Merge**: Only after all quality gates pass

### Quality Gates (MUST Pass Before Merge)

- [ ] All tests passing with ≥95% coverage for core logic
- [ ] Code style checks passing (black, isort, flake8)
- [ ] OpenEnv specification compliance verified
- [ ] Performance benchmarks met
- [ ] Documentation updated (README, docstrings, diagrams)
- [ ] API changes documented in OpenAPI spec
- [ ] No security vulnerabilities introduced
- [ ] Docker build successful
- [ ] Manual testing completed (UI, workflows)

### Complexity Justification

Any feature that adds significant complexity MUST be justified in the implementation plan:

- Additional dependencies → Why needed, what problem solved
- New architectural patterns → Why simpler approach insufficient
- Performance optimization → Benchmarks showing necessity
- Breaking changes → Migration path and backwards compatibility plan

**Rationale**: Simplicity is a core principle. Complexity must earn its place.

## Governance

### Amendment Process

1. **Proposal**: Document proposed change with rationale
2. **Impact Analysis**: Assess effect on existing features and templates
3. **Version Bump**: Determine MAJOR, MINOR, or PATCH following semantic versioning:
   - **MAJOR**: Backward incompatible changes (e.g., removing a principle)
   - **MINOR**: New principles or expanded guidance
   - **PATCH**: Clarifications, wording improvements, non-semantic changes
4. **Template Updates**: Modify all affected templates for consistency
5. **Sync Report**: Document changes in HTML comment at top of constitution
6. **Approval**: Requires explicit sign-off from project maintainers
7. **Communication**: Update all dependent documentation and notify contributors

### Compliance Verification

**All code reviews MUST verify:**
- OpenEnv specification compliance
- Adherence to simplicity and accessibility principles
- Visual clarity and educational value
- Code quality standards met
- Performance benchmarks maintained

**Automated checks MUST enforce:**
- Test coverage thresholds
- Code style compliance
- Security scanning (container vulnerabilities)
- Performance regression tests

### Constitution Authority

This constitution supersedes all other development practices. In case of conflict:
1. Constitution principles take precedence
2. Maintainers may grant temporary exceptions for critical issues
3. All exceptions MUST be documented with justification and remediation plan
4. Repeated exceptions indicate need for constitutional amendment

### Runtime Guidance

For day-to-day development decisions not covered by this constitution, developers should:
- Refer to the PRD (chess-openenv-prd.md) for product requirements
- Consult OpenEnv 0.1 specification for framework details
- Review existing code for established patterns
- Ask maintainers for clarification when principles conflict

**Version**: 1.0.0 | **Ratified**: 2025-10-25 | **Last Amended**: 2025-10-25
