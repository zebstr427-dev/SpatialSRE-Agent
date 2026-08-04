# Fixed P0-P3 Curriculum

This is the single source of truth for lesson numbering and scope. The curriculum has 31 lessons numbered 0-30. Lessons 0-10 are accepted; 20 lessons remain including current lesson 11.

## Stage Totals

| Stage | Accepted | Remaining | Lesson numbers |
| --- | ---: | ---: | --- |
| P0 Production Agent Foundation | 10 | 0 | 0-9 |
| P1 Controlled Enterprise Execution | 1 | 5 | 10-15 |
| P2 AIOps Root-Cause Enhancement | 0 | 6 | 16-21 |
| P3 High-Barrier Capabilities | 0 | 9 | 22-30 |
| Total | 11 | 20 | 0-30 |

## Accepted Work

Lessons 0-9 cover the runnable baseline, pytest baseline, dependency upgrade, typed incident state, PostgreSQL infrastructure, checkpointer lifecycle, durable AIOps API, cross-process recovery proof, persistent tool-call auditing, and deterministic initial EvalOps.

Lesson 10 establishes the P1 MCP Tool Gateway with a unified registry and routing path, standard execution errors, per-call timeout, bounded retry capability, and an audit hook integrated with durable AIOps execution.

## Remaining Lessons

| Stage | Lesson | Title | Fixed feature points |
| --- | ---: | --- | --- |
| P1 | 11 | Risk levels and dry-run | Risk enum; metadata binding; readonly allow; write dry-run; high-risk block; tests |
| P1 | 12 | Agent Identity | Identity model; role; tool scope; service scope; risk ceiling; identity propagation |
| P1 | 13 | Policy-as-Code | Policy schema; loader; condition matching; allow/deny/approval; decision audit; tests |
| P1 | 14 | Human Approval | Approval request; LangGraph interrupt; approve/reject; resume; restart recovery; API |
| P1 | 15 | Evidence Chain and Guardrails | Evidence links; provenance; report citation; no-evidence degradation; input/output constraints; API |
| P2 | 16 | Runbook foundation | YAML schema; validation; loader; versioning; registry; deterministic tests |
| P2 | 17 | Runbook-driven workflow | Alert matching; planner preference; executor steps; stop conditions; fallback; tests |
| P2 | 18 | Change Intelligence | Change model; deployment/config/Git/K8s tools; time windows; correlation; evidence; report integration |
| P2 | 19 | Query Rewrite and Hybrid RAG | Query rewrite; BM25; vector recall; rank fusion; fallback; retrieval tests |
| P2 | 20 | Rerank and metadata filters | Rerank interface; deterministic fallback; service/type/version/time filters; TopK; tests |
| P2 | 21 | Citation and retrieval evaluation | Citation schema; answer binding; missing-evidence constraint; dataset extension; metrics; API |
| P3 | 22 | Incident Graph foundation | Graph model; nodes/edges; storage abstraction; topology import; change import; tests |
| P3 | 23 | Incident Graph queries | Impact query; dependency traversal; time correlation; similar incidents; context extraction; evidence |
| P3 | 24 | GraphRAG | Entity seeds; local traversal; global summary; vector fusion; provenance; evaluation |
| P3 | 25 | Failure Replay foundation | Case layout; loader; fixed tool responses; simulator; expected comparison; isolation |
| P3 | 26 | Replay metrics and reports | Root-cause hit; tool accuracy; evidence coverage; hallucination check; latency/cost; CLI report |
| P3 | 27 | LangGraph multi-node workflow | Triage; Plan; Evidence; Root Cause; Remediation; Report nodes |
| P3 | 28 | Parallelism and failure isolation | SRE/Change parallelism; join; timeout; partial results; recovery semantics; deterministic tests |
| P3 | 29 | In-project multi-agent roles | Five agent roles; I/O contracts; subgraphs; registry; role isolation; collaboration tests |
| P3 | 30 | Orchestration, AgentOps, and final demo | Scheduling; OpenTelemetry; cost/latency; approval/evidence integration; end-to-end demo; full regression |

## Progress Rules

- Keep lesson numbers and P0 -> P1 -> P2 -> P3 order fixed.
- Each lesson contains 3-6 related feature points; each batch closes one observable behavior.
- Debugging, formatting, and cleanup stay inside the current lesson and do not create new lessons.
- Do not split, merge, reorder, or renumber lessons without explicit learner approval for a material scope change.
- Use accepted learning notes, repository diffs, tests, and runtime evidence to mark feature points complete.
