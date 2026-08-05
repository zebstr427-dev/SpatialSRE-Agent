# P1 Controlled Enterprise Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete P1 lessons 11-15 with enforceable risk, identity, policy, approval, and evidence controls.

**Architecture:** Pure models evaluate risk, identity, policy, approval, and evidence. Tool Gateway composes the controls at the execution boundary, while AIOpsService persists approval interrupts and resumes through LangGraph.

**Tech Stack:** Python 3.13, Pydantic 2, LangChain tools, LangGraph 1.2, FastAPI, pytest.

---

### Task 1: Risk and dry-run enforcement

**Files:** `app/agent/tool_risk.py`, `app/agent/tool_gateway.py`, `tests/unit/test_tool_risk.py`, `tests/unit/test_tool_gateway.py`

- [ ] Add Gateway tests for read-only execution, forced write dry-run, high-risk block, and unknown fail-closed behavior.
- [ ] Run the focused tests and confirm missing Gateway behavior causes RED.
- [ ] Bind risk metadata to registrations and return stable `tool_dry_run_required` / `tool_risk_blocked` results.
- [ ] Run focused tests to GREEN, then refactor repeated result construction without changing behavior.

### Task 2: Agent identity propagation

**Files:** `app/agent/identity.py`, `app/agent/aiops/state.py`, `app/models/aiops.py`, `app/services/aiops_service.py`, `app/api/aiops.py`, corresponding unit tests.

- [ ] Add tests for role, tool scope, service scope, risk ceiling, serialization, and API-to-state propagation.
- [ ] Confirm imports or assertions fail because identity contracts are absent.
- [ ] Implement immutable identity models, default observer identity, and checkpoint-safe state propagation.
- [ ] Run identity, model, service, and API tests to GREEN.

### Task 3: Policy-as-Code

**Files:** `app/agent/policy.py`, `policies/tool-execution.json`, `app/agent/tool_gateway.py`, `tests/unit/test_policy.py`, `tests/unit/test_tool_gateway.py`.

- [ ] Add tests for schema validation, file loading, condition matching, default deny, and serializable decision audit.
- [ ] Confirm RED because policy types and loader do not exist.
- [ ] Implement ordered first-match policy evaluation after mandatory identity/risk controls.
- [ ] Integrate policy decisions into Gateway results and audits; run focused tests to GREEN.

### Task 4: Durable human approval

**Files:** `app/agent/approval.py`, `app/agent/aiops/state.py`, `app/agent/aiops/executor.py`, `app/services/aiops_service.py`, `app/models/aiops.py`, `app/api/aiops.py`, approval/service/API tests.

- [ ] Add tests for request binding, reject behavior, LangGraph interrupt, approve resume, and service rebuild with the same checkpointer.
- [ ] Confirm RED at the missing approval node/API contracts.
- [ ] Persist pending tool calls, route to an approval node, resume using `Command`, and expose the decision endpoint.
- [ ] Run focused approval, executor, service, and API tests to GREEN.

### Task 5: Evidence chain and guardrails

**Files:** `app/agent/evidence.py`, `app/agent/aiops/state.py`, `app/agent/aiops/executor.py`, `app/agent/aiops/replanner.py`, `app/services/aiops_service.py`, evidence/executor/API tests.

- [ ] Add tests for provenance, citation binding, no-evidence degradation, input/output limits, and API evidence fields.
- [ ] Confirm RED because evidence guardrail contracts do not exist.
- [ ] Convert successful tool calls to evidence, constrain generated reports, and expose evidence/citations.
- [ ] Run focused tests to GREEN.

### Task 6: Documentation and acceptance

**Files:** `docs/learning/11-*.md` through `15-*.md`, `docs/learning/README.md`, `.codex/skills/upgrade-oncall-agent-by-doing/references/curriculum-roadmap.md`.

- [ ] Record architecture location, behavior, failure semantics, tests, runtime flow, and interview summary for each lesson.
- [ ] Mark P1 lessons 11-15 accepted and update exact test totals from fresh output.
- [ ] Run non-PostgreSQL, PostgreSQL, full-suite, Ruff on changed Python, compileall, and `git diff --check`.
- [ ] Inspect the final diff and preserve unrelated worktree content.
