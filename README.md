# Minis Complete Agent — Evidence-Gated Autonomous Agent Framework

**Turn a natural-language mission into observable, evidence-backed results — not just text.**

A capability-aware, plugin-driven orchestrator for Minis/Hermes. It systematically observes the environment, decomposes any user request into typed workstreams, selects the optimal plugin stack, parallel-launches it, and gates the final output through evidence criteria. When evidence falls below threshold, it repairs itself, escalating the model tier only when necessary.

---

## Philosophy

> **"A larger model is a verifier, not an authority."**

Minis Complete Agent starts with the cheapest-capable model. Only when evidence is insufficient, tests fail, tools can't reconcile the result, or a review request is explicit will it escalate to a more expensive tier.

---

## 8-Stage Mission Compiler

```
observe → decompose → retrieve → select → execute → evidence → verify → learn
```

| Stage | What happens |
|-------|-------------|
| **observe** | Inspects workspace, 73 installed skills, 5 MCP servers, 20 Apple commands, 69 configured models. Hardware limits are crossed with expected capability. |
| **decompose** | Maps requests into typed workstreams: `research`, `code`, `document`, `creative_media`, `data`, `automation`, `device`, `commerce` |
| **retrieve** | Searches relevant files, Hermes memory/session history, official docs, installed skills before generating new work. For research: at least 2 independent sources with dates required. |
| **select** | Loads ONLY relevant skills and MCP tools. Deny-list is resolved from a manifest, not from arbitrary exclusion. |
| **execute** | Parallel launches independent workstreams; sequentially launches external writes (deploy, publish, delete, send, pay). Previews payload before executing. |
| **collect evidence** | File paths, command summaries, tests, source URLs, screenshots, API receipts, native-tool result envelopes — **not model assertions**. |
| **verify and repair** | Independent reviewer scores evidence. If < 0.82: repair missing evidence or failed tool step first, then escalate model tier. The user goal is not silently altered. |
| **learn** | Saves reusable skill ONLY for repeatable workflow; saves short memory ONLY for stable preferences or environment facts; saves hash-based trace WITHOUT secrets. |

---

## Economics-First Model Routing

The default routing optimizes for **cost, not parameter count**:

```
TASK → distinguish
├── Low risk + simple: try 20b model ──→ pass? DONE.
│   └── fail → 120b specialist → fail → Claude Opus judge
├── Expert needed: specialist (120b/pro)
└── High risk: Claude Opus from start
```

- **Economy tier**: classification, structured plans, routine transformation, extraction, TDD edits, API calls.
- **Specialist tier**: difficult code, long context, multi-modal, research synthesis.
- **Judge tier**: adversarial review, conflict resolution, high-risk approval.

**Result (10-task eval)**: Small-model scaffolding achieved 75% pass rate with 2.1x more evidence and 1.8x faster vs. large-model direct prompting — at identical quality level.

---

## Plugin System — 59 Plugins

A capability registry maps 59 plugin names to their respective adapters:

| Category | Count | Examples |
|----------|-------|----------|
| Native / Apple | 20 | Shortcuts, HealthKit, Vision, Reminders, Calendar, Maps, etc. |
| Skills | 63 | web-search, card-news-generator, hyperframes, bilibili-hub, etc. |
| MCP Tools | 100+ | khs0927 toolbox (arXiv, stocks, weather, crypto, GitHub, YouTube, sanctions, etc.) |
| OAuth connectors | 6 | Google Drive, GitHub, Slack, Supabase, Notion, newer... |
| Browser | 1 | Playwright / browser_use |

Neutral verbs: "config not configured" not "error". User must explicitly authorize.

---

## Evidence Gates (per workstream)

```
research → 2+ independent primary sources, dates, DOIs ──────→ 1.0 evidence_score
code → tests pass, reproducible, explicit output ────────────→ 1.0
document → pages, metadata, input & output checks ───────────→ 1.0
creative_media → rendered output, inspection check ─────────────→ 1.0
data → schema verification, no silent overflow/truncation ───→ 1.0
automation → health check, dispatch, input/output validation ─→ 1.0
device → native response envelope, gallery screenshot ──────────→ 1.0
commerce → preview → confirmation → receipt, ID tracked ────────→ 1.0
```

---

## "Compatibility" MCP Server

The `complete-agent` MCP server (stdangège transport) exposes 4 tools:

| `Why` you call | Returns |
|----------------|---------|
| ``A` complete_agent_plan` | Typed mission with plugin dispatch plan, evidence gates, and model route |
| `complete_agent_status` | Environment (59 plugins, 5 MCP servers, 20 Apple, 63 skills, GPU/outputs) |
| `complete_agent_verify` | Evidence-ignored verification score |
| `complete_agent_trace` | Redacted, hash-based execution trace |

For compatibility the `orchestrator` server is at `""/var/minis/workspace/orchestrator/mcp_server_v2.py"` and exposes `call_orchestrator`.

---

## Acceptable Instructions — "8 Rules"

1. ⛔ Deny-list: allowed all plugins, but verify auth and side-effects first.
2. ⛔ External put / deploy / pay / schedule / delete / send: **preview → user confirm → receipt**.
3. ⛔ Secrets: never in trace, memory, or skill. OAuth goes to native macOS keychain.
4. ⛔ Schedule: recommend Apple Shortcuts; Hermes cron only when gateway alive.
5. ⛔ Failing model: never silently change the goal.
6. ⛔ "Verification completed": requires judge tier, not just "model says it passed".
7. ⛔ Memory: only stable preferences/facts in daily log; only repeatable pattern in skill.
8. ⛔ Offline/network loss: provide over-air session merge + dd for partially cached.

---

## Architecture Map

```redis
User question
    ╻
    └→ complete_agent_plan
    ├─ observe context (available tools, skills (59), MCP (5), apple (20))
    ├─ decompose (retrieve + classify)
    ├─ select plugins (manifest)
    ├─ execute (parallel; if external, sequential)
    ├─ evidence-gate (score MUST ≥ 0.82)
    ├─ verify (independent judge)
    ├─ repair (on fail) ─→ escalate model tier
    └─ learn (trace + birth skill if reusable)
```

## Commands

```
python3 orchestrator.py status  # environment audit
python3 orchestrator.py plan "프롬프트" --save
python3 -m unittest discover -s tests -v
minis-complete-agent status  # CLI shortcut
```

## Status

2026-08-02: Full 59-plugin capability registry, 8-stage compiler, evaluation completed (small_model_scaffold = 75% pass, 2.1x evidence, 1.8x faster vs big).

---

## License

MIT