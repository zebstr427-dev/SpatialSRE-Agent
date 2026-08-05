# P1 Controlled Enterprise Execution Design

## Goal

Turn the existing Tool Gateway into a fail-closed enterprise execution boundary. Every tool call must be attributable to an agent identity, evaluated by policy, recoverable across human approval, and represented by evidence that the final report can cite.

## Control Flow

```text
API request
  -> AgentIdentity in IncidentState
  -> Planner selects registered tools
  -> Executor asks ToolGateway for authorization
      -> identity scope and risk ceiling
      -> policy rule matching
      -> allow / deny / require approval
  -> Approval node interrupts and checkpoints when required
  -> API resumes with approve or reject decision
  -> ToolGateway enforces dry-run and executes
  -> audit + evidence provenance enter IncidentState
  -> report guardrail binds citations or degrades safely
```

## Boundaries

- `tool_risk.py` owns risk classification. Unknown tools are high risk.
- `identity.py` owns immutable agent identity and scope checks.
- `policy.py` owns JSON policy validation, loading, matching, and decision records.
- `approval.py` owns checkpoint-safe approval records and resume validation.
- `tool_gateway.py` is the only execution boundary. It must not trust callers to enforce risk, identity, policy, approval, or dry-run.
- `evidence.py` owns provenance records and report guardrails.
- `AIOpsService` owns LangGraph interrupt/resume lifecycle and exposes it to the API.

## Stable Semantics

- Read-only tools may execute when identity and policy allow them.
- Write tools always execute with the registered dry-run argument forcibly set to `True` in P1.
- High-risk and unknown tools are blocked even when a policy rule appears to allow them.
- Identity scope violations and risk-ceiling violations fail closed.
- Policy evaluation returns `allow`, `deny`, or `require_approval`; no matching rule uses the policy default.
- Approval decisions are bound to an incident, tool-call ID, arguments, and requester. A rejection never executes the tool.
- Successful tool outputs become evidence records with tool-call provenance.
- A report with no evidence is replaced by an explicit evidence-insufficient response. A report with evidence includes stable `[evidence:<id>]` citations.

## Recovery

The executor stores pending tool calls and approval requests before routing to a dedicated approval node. The approval node calls LangGraph `interrupt()`, so the pending request is checkpointed. Resuming uses `Command(resume=...)`; rebuilding `AIOpsService` with the same checkpointer proves restart recovery.

## Testing

Unit tests cover each pure boundary, Gateway enforcement, executor propagation, interrupt/resume, API contracts, evidence provenance, and output degradation. Existing non-PostgreSQL and PostgreSQL suites remain regression gates. Ruff, compileall, and `git diff --check` are final static gates.
