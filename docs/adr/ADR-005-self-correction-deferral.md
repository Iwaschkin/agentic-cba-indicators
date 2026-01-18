# ADR-005: Self-Correction and Validation Mechanisms (Deferred)

## Status
**Deferred** - Acknowledged as important for production systems, not implementing in current phase

## Context

The code review (P1-006) identified that the agent has **no self-correction mechanism**. The agent cannot verify its own outputs for correctness, detect errors in its reasoning, or automatically retry with corrections.

**Current State:**
- Agent produces responses based on single inference pass
- No validation of tool outputs or reasoning
- No mechanism to detect and correct hallucinations
- User is responsible for identifying incorrect outputs

**Risk Examples:**
1. Agent misinterprets indicator data, provides wrong recommendation
2. External API returns unexpected format, agent proceeds with bad data
3. Agent makes incorrect calculations, user may not notice
4. KB search returns irrelevant results, agent uses them anyway

## Decision

**Defer self-correction mechanism implementation** to a future enhancement phase.

## Rationale

### Complexity Concerns

1. **Verification Challenge**
   - How to verify correctness without ground truth?
   - Tool outputs may be correct but irrelevant
   - Semantic correctness vs syntactic validity
   - Domain-specific validation rules needed

2. **Feedback Loop Design**
   - What triggers re-evaluation?
   - How many correction attempts before giving up?
   - Risk of infinite loops
   - Performance cost of re-processing

3. **LLM Limitations**
   - LLMs can confidently assert incorrect information
   - Self-verification may reinforce errors
   - Separate verification model adds complexity/cost
   - Chain-of-thought doesn't guarantee correctness

4. **Tool Integration**
   - Each tool would need validation rules
   - External data validation is domain-specific
   - Some errors are not detectable (incorrect but plausible)

5. **User Experience**
   - Correction attempts add latency
   - Visible retries may reduce trust
   - Balance between thoroughness and responsiveness

### Mitigating Factors (Why Defer is Acceptable)

1. **Tool Design**
   - Tools have bounded outputs (validated parameters)
   - Error handling returns clear messages
   - Users can verify critical information

2. **Conversational Context**
   - Users can ask follow-up questions
   - Agent can be asked to explain reasoning
   - Multi-turn allows human-in-the-loop correction

3. **Scope of Application**
   - Advisory tool, not autonomous decision-maker
   - Recommendations require human review
   - Not safety-critical (no irreversible actions)

4. **Strands Framework**
   - Strands may add native validation features
   - Community patterns may emerge
   - Future integration opportunity

## Alternatives Considered

### 1. Immediate Full Implementation
- **Pro:** Maximum reliability
- **Con:** Very complex, unclear ROI
- **Decision:** Deferred due to complexity

### 2. Output Format Validation
- **Pro:** Simple, catches obvious errors
- **Con:** Doesn't address semantic correctness
- **Decision:** Partially implemented (tool output schemas)

### 3. Confidence Scoring
- **Pro:** Users know when to be skeptical
- **Con:** LLM confidence unreliable, may mislead
- **Decision:** Not recommended without calibration

### 4. User Feedback Loop
- **Pro:** Leverages human judgment
- **Con:** Requires UI for feedback collection
- **Decision:** Future enhancement, requires UI work

## Future Considerations

### When to Revisit

1. **Production Deployment**
   - If moving to production use cases
   - If autonomous workflows are needed
   - If error rates become problematic

2. **Strands Enhancements**
   - If Strands adds validation hooks
   - If community validates patterns
   - If guardrails integration available

3. **Use Case Evolution**
   - If high-stakes decisions needed
   - If regulatory compliance requires audit trail
   - If liability concerns arise

### Implementation Sketch (Future)

```python
# Hypothetical validation framework
from strands.validation import ValidationHook

class ToolOutputValidator(ValidationHook):
    """Validates tool outputs before returning to agent."""

    def validate_kb_result(self, result: dict) -> ValidationResult:
        """Validate knowledge base query results."""
        # Check for minimum relevance
        if result.get("relevance", 0) < 0.3:
            return ValidationResult(
                valid=False,
                reason="Low relevance match",
                suggestion="Try broader search terms"
            )
        return ValidationResult(valid=True)

    def validate_api_response(self, response: dict) -> ValidationResult:
        """Validate external API responses."""
        # Check for expected fields
        if "error" in response:
            return ValidationResult(
                valid=False,
                reason=response["error"],
                suggestion="Check parameters or try alternative API"
            )
        return ValidationResult(valid=True)


class SelfCorrectionLoop:
    """Implements retry with correction for agent responses."""

    def __init__(self, max_attempts: int = 3):
        self.max_attempts = max_attempts

    def execute_with_correction(self, agent, prompt: str) -> str:
        """Execute agent with self-correction loop."""
        for attempt in range(self.max_attempts):
            response = agent(prompt)

            validation = self.validate_response(response)
            if validation.valid:
                return response

            # Retry with correction hint
            prompt = f"{prompt}\n\nPrevious attempt had issue: {validation.reason}\n{validation.suggestion}"

        return response  # Return best effort after max attempts
```

## Consequences

### Positive
- Avoids very complex implementation
- Focuses on stable, well-tested features
- Clear path for future enhancement
- User-in-the-loop provides natural correction

### Negative
- Agent may produce incorrect outputs
- Users must verify critical information
- No automated error recovery
- May limit autonomous use cases

## References

- Code Review Finding: P1-006
- Related: ADR-003 (Memory Architecture - deferred features)
- Strands Documentation: https://strandsagents.com/
- Research: "Self-Consistency Improves Chain of Thought Reasoning" (Wang et al., 2022)
