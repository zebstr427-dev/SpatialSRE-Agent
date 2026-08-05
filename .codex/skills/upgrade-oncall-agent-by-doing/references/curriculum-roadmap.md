# Fixed P0-P3 Curriculum

This is the single source of truth for lesson numbering and scope. The curriculum has 31 lessons numbered 0-30. All lessons are accepted after the P0-P3 implementation and full verification completed on 2026-08-05.

## Stage Totals

| Stage | Accepted | Remaining | Lesson numbers |
| --- | ---: | ---: | --- |
| P0 Production Agent Foundation | 10 | 0 | 0-9 |
| P1 Controlled Enterprise Execution | 6 | 0 | 10-15 |
| P2 AIOps Root-Cause Enhancement | 6 | 0 | 16-21 |
| P3 High-Barrier Capabilities | 9 | 0 | 22-30 |
| Total | 31 | 0 | 0-30 |

## Accepted Work

Lessons 0-9 cover the runnable baseline, pytest baseline, dependency upgrade, typed incident state, PostgreSQL infrastructure, checkpointer lifecycle, durable AIOps API, cross-process recovery proof, persistent tool-call auditing, and deterministic initial EvalOps.

Lessons 10-15 establish the P1 controlled execution plane: unified Tool Gateway, fail-closed risk and dry-run enforcement, Agent Identity, versioned Policy-as-Code, durable human approval, and evidence-bound output guardrails.

Lessons 16-21 establish P2 root-cause enhancement: versioned Runbook-as-Code, runbook-first planning, explainable Change Intelligence, Hybrid RAG, rerank, metadata filters, stable citations, and retrieval evaluation.

Lessons 22-30 establish P3 high-barrier capabilities: Incident Graph queries, Hybrid GraphRAG, isolated Failure Replay and metrics, structured LangGraph orchestration, parallel failure isolation, five in-project Agent roles, OpenTelemetry AgentOps, a typed API, and the deterministic final demo.

Final verification: `115` non-PostgreSQL tests, `2` PostgreSQL integration tests, `117` tests in the complete suite, and `64.34%` total application coverage.

## Accepted Lessons 16-30

| Stage | Lesson | Title | Fixed feature points |
| --- | ---: | --- | --- |
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
