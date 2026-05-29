# NOC Whisperer — Session Handoff
# Generated: May 24, 2026
# For: New session pickup — skip all GPU host login troubleshooting

---

## Current State

| Item | Status |
|------|--------|
| Tests | **299 passing** |
| Demo script | `run_demo_adk.py` — end-to-end validated May 17 |
| Demo date | **May 30, 2026** |
| Git | All commits pushed to origin/main |
| Hosts | gho-vm-1 (OTel stack), gho-gpu-vm (demo runtime) |
| Docker | Restored on gho-vm-1 ✅ |
| GPU host | Login changed to bmammen1 — models inaccessible (pending admin) |

---

## Commit History (latest first)
aef2fa7  fix: REMINDER-017 - confirmed advisory marks preliminary
e2a096c  fix: close_incident() removes resolved incidents from board
fb9ca0a  feat: add Started timestamp column to Incident Board
d32ea01  feat: switch ADK correlation to production mode
8def693  fix: timestamps on log lines; remove 60s duplicate guard window
---

## All ADK Fixes Shipped (299 tests)

| Fix | File | Tests Added |
|-----|------|-------------|
| Advisory state — flags in correlate_alert return | `correlation_tools.py` | +6 |
| Advisory guard + flag persistence | `communications_tools.py` | +11 |
| Option C — frontend /api/data → device=ad | `prometheus_mcp.py` | +4 |
| Same-cycle duplicate guard | `correlation_tools.py` | +5 |
| DSPy production mode | `correlation_tools.py` | 0 |
| Timestamps on [Agent]/[ADK] lines | `run_demo_adk.py` | 0 |
| Started column on Incident Board | `noc_dashboard.py` | +1 |
| close_incident → update_incident_board | `incident_tools.py` | +2 |
| REMINDER-017 confirmed also marks preliminary | `communications_tools.py` | +2 |
| REMINDER-015 timezone fix | `communications_agent.py` | +21 |

---

## Open Items Before May 30

| Priority | Item | Blocked on |
|----------|------|-----------|
| 1 | Build PPTX (Cursor prompt ready) | Nothing — do this now |
| 2 | GPU host model access | Admin granting bmammen1 access to models |
| 3 | Dress rehearsal | GPU host models |
| 4 | PromQL [1m] window fix | Live Prometheus (verify timing) |

---

## Presentation — 10 Slides (Cursor-validated)

### Slide 1 — Title
NOC Whisperer
Real-time multi-agent alert correlation
for distributed infrastructure
H2M Agents  |  May 30, 2026
### Slide 2 — The Problem
The NOC Alert Flood Problem
A single infrastructure failure cascades across 7+ services
— each generating its own alert.

L1 operators manually correlate dozens of noisy alerts
Root cause identification takes 15-30 minutes
Alert fatigue leads to missed signals

Can a multi-agent AI system correlate alerts in real time,
identify root cause, and generate actionable advisories
— automatically?
### Slide 3 — Architecture
DATA SOURCES       MCP TOOL LAYER        AGENT PIPELINE (Google ADK)
Prometheus    →    PrometheusMCP    →    NormalizerAgent   (LLM fine-tuned)
Jaeger        →    JaegerMCP        →    TriageAgent        (rule-based)
Node Exporter →    TopologyMCP      →    CorrelationAgent   (LLM DSPy)
OTel Stack    →    NodeExporterMCP  →    CommunicationsAgent (LLM fine-tuned)
↓
NOC DASHBOARD
RAW ALERT STREAM
INCIDENT BOARD (+ Started column)
NOC ADVISORY
Storage: SQLite IncidentStore (in-memory)
Topology: otel_demo_graph.json
Note: Jaeger/Node Exporter MCPs in codebase; not wired into ADK demo loop
### Slide 4 — The Tool Stack
Two Layers of Tools
LAYER 1 — ADK FunctionTools  (agents/adk_tools/)
What the LLM agent sees and calls:
get_active_alerts()    normalize_alert()
route_alert()          correlate_alert()
generate_advisory()    check_open_incidents()
check_service_health() close_incident()
↓ each FunctionTool internally calls
LAYER 2 — MCP Tool Classes  (mcp_tools/)
PrometheusMCP  →  Prometheus HTTP API (10.0.50.60:9090)
JaegerMCP      →  Jaeger trace API
TopologyMCP    →  otel_demo_graph.json
NodeExporterMCP → Node Exporter metrics
The agent reasons about tools.
The tools handle infrastructure.
### Slide 5 — How It Works
From Raw Alert to NOC Advisory — 6 Steps

get_active_alerts()    Pull threshold breaches from Prometheus MCP
normalize_alert()      Raw metric → canonical CanonicalAlert
route_alert()          Rule-based topology + temporal proximity →
new incident or append to existing
correlate_alert()      DSPy LLM reasons over alert cluster +
topology → root cause + confidence
generate_advisory()    Fine-tuned model writes NOC advisory
(preliminary → confirmed → resolution)
check_service_health() Prometheus confirms recovery →
close_incident() → SERVICE RESTORED

Cycle time: 15s  |  CONFIRMED when confidence > 0.85 AND alert_count ≥ 2
### Slide 6 — Fine-tuned Models
Three LLM-Powered Agents
BASE MODEL: Qwen2.5-7B-Instruct  |  LoRA adapters ~10MB each
Agent                | Training        | Loss  | Accuracy
NormalizerAgent      | SFT 200 ex.     | 0.541 | 80.9%
CommunicationsAgent  | SFT 80 ex.+RLVR | 0.250 | 94.2%
CorrelationAgent     | DSPy optimized  |  —    | 96.7%*
Advisory generation: LoRA when present; Ollama qwen3:8b fallback
Runtime: gpt-oss-20b via SV cluster (10.0.10.51:8124)

Rule-based baseline scored 100% on same eval set.
LLM advantage: confidence calibration + advisory generation.

DISCOVERY: Reward Hacking in Communications RLVR
Symptom:    Model repeated boilerplate to harvest scores
Root cause: No repetition penalty in reward function
Fix:        advisory_reward() applies unique-line ratio
+ length tier penalties
Result:     Stable output; 94.2% accuracy preserved
### Slide 7 — The Agentic Architecture
Google ADK LlmAgent + 8 FunctionTools | 6-step workflow | 15s poll
Which advisory type?          When to close?
Preliminary or confirmed      Only when Prometheus health
based on confidence +         check confirms recovery —
alert count + flags           LLM calls close_incident()
on True result
Same alert, different outcomes:
Depends on evolving store state — open incidents,
flags, correlation history
All 6 steps are orchestrated by the LLM.
Routing and health decisions happen inside
rule-based tools the LLM calls — not in the LLM itself.
### Slide 8 — Results
What It Does In Production (observed in demo runs — May 2026)
299 tests passing       end-to-end, ~13s full suite
0.90 – 0.95            live confidence scores (DSPyCorrelator)
CONFIRMED advisory      fires within 2-3 cycles of fault injection
SERVICE RESTORED        incident removed from board 1-2 cycles after healing
ad noise isolated       separate from valkey-cart cascade
T+60-90s detection      docker stop to first cart alert in stream
### Slide 9 — Live Demo
[ LIVE DEMO ]
Scenario: valkey-cart cache failure cascade
OpenTelemetry demo environment

Baseline    — system monitoring, ad noise isolated
Fault       — docker stop valkey-cart
Detection   — cart cascade alerts, new incident
Advisory    — CONFIRMED NOC ADVISORY (confidence > 0.85)
Healing     — docker start valkey-cart
Resolution  — SERVICE RESTORED, incident removed from board
### Slide 10 — Lessons Learned
What We Learned — And Would Do Differently

Baseline heuristics can beat LLM for structured tasks
→ Establish baseline before investing in fine-tuning
Statelessness is a fundamental challenge in agentic systems
→ Design state management into architecture from day one
Trust code over prompts for invariants
→ Behavioral guarantees belong in code, not LLM instructions
Noise isolation is as important as detection
→ Understand operating environment before tuning accuracy
Fine-tuning teaches format, not temporal awareness
→ Know the boundary of what training can and cannot do
Migration surfaces invisible assumptions
→ Choose orchestration framework first;
build everything around it
---

## PPTX Cursor Prompt (ready to run)

Reference file: this handoff doc contains all 10 slides.
Cursor prompt was generated and validated May 24.
Run it in a fresh Cursor session with:
@CONTEXT.md @EXECUTION_PLAN.md @docs/REMINDERS.md

The full PPTX prompt is in the previous session — paste it
verbatim into Cursor. Output: docs/NOC_Whisperer_Capstone.pptx

---

## Demo Runbook (updated)

### Pre-Demo (gho-vm-1)
```bash
ssh bmammen1@gho-vm-1
cd ~/projects/opentelemetry-demo
docker compose up -d
docker start valkey-cart
curl -s "http://localhost:9090/api/v1/label/__name__/values" \
  | python3 -m json.tool | grep "app_cart" | head -3
```

### Start Demo (gho-gpu-vm)
```bash
ssh bmammen1@gho-gpu-vm
source ~/.venvs/NOC-Whisperer/bin/activate
cd ~/projects/NOC-Whisperer
python3 scripts/run_demo_adk.py
```

### Inject Fault (gho-vm-1 second terminal)
```bash
docker stop valkey-cart
```

### Healing
```bash
docker start valkey-cart
```

### Expected Timeline
- T+60-90s:  cart_threshold_breach in RAW ALERT STREAM
- T+90-120s: separate cart incident in INCIDENT BOARD
- T+120-180s: CONFIRMED NOC ADVISORY (confidence > 0.85)
- Healing: 1-2 cycles → SERVICE RESTORED → incident removed

---

## Key Files
- `docs/DEMO_QA.md` — Q&A cheat sheet for May 30
- `docs/REMINDERS.md` — REMINDER-016/017 open, rest resolved
- `docs/presentation_outline.md` — SUPERSEDED (15-min slot, old data)
- `scripts/run_demo_adk.py` — primary demo script
- `orchestrator/adk_orchestrator.py` — ADK agent + NOC_INSTRUCTION

---

## Known Issues (post-demo, not blockers)
- REMINDER-016: ad duplicate incidents (cosmetic)
- PromQL [5m] window → [1m] improvement pending live verification
- GPU host model access under bmammen1 (admin needed)
