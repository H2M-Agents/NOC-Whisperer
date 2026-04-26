# NOC Whisperer — Project Context

> This file is the source of truth for the NOC Whisperer project.
> Reference it at the start of every Cursor session: `@CONTEXT.md`
> Do not modify unless an architectural decision changes.

---

## Project Identity

**Name:** NOC Whisperer

**One-line description:** Agentic alert correlation and incident synthesis
across compute, network, and storage domains.

**Problem:** During any infrastructure event, alerts from compute, network,
and storage monitoring systems arrive simultaneously in incompatible formats
with no unified incident picture. A senior NOC engineer takes 15–20 minutes
to identify root cause. This system does it in under 2 seconds.

**Primary demo scenario:** Stop the Valkey container in the OpenTelemetry
demo stack. Seven alerts fire across three domains simultaneously. The system
correlates them into one incident. Root cause: `valkey-cart`. Confidence: 0.91.

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.11+ |
| Fine-tuning | PyTorch + HuggingFace transformers + peft + trl (GRPO) |
| Prompt optimization | DSPy-AI |
| Incident store | SQLite |
| Concurrency | asyncio |
| Terminal dashboard | rich |
| Live data source (demo) | OpenTelemetry demo app + Node Exporter (Docker Compose) |
| Base model | Qwen/Qwen2.5-7B-Instruct |
| DSPy backing model | GPT-4o-mini |
| Local dev inference | Ollama + Llama3.1:8b |
| IDE | Cursor + Claude Sonnet 4.6 (code) / Opus 4.7 (planning only) |

---

## Directory Structure

```
noc_whisperer/
├── adapters/
│   ├── canonical_alert.py        # CanonicalAlert, TriageDecision, Incident dataclasses
│   └── synthetic_adapter.py     # Synthetic generator output → CanonicalAlert
├── mcp_tools/
│   ├── topology_mcp.py           # Dependency graph queries
│   ├── jaeger_mcp.py             # Application domain alerts; includes _span_to_canonical()
│   ├── prometheus_mcp.py         # Service mesh domain alerts; includes _to_canonical()
│   ├── node_exporter_mcp.py      # Infrastructure domain alerts; includes _to_canonical()
│   └── mocks/
│       ├── mock_topology_mcp.py
│       ├── mock_jaeger_mcp.py
│       ├── mock_prometheus_mcp.py
│       └── mock_node_exporter_mcp.py
├── agents/
│   ├── normalizer_agent.py       # RLVR fine-tuned — domain + severity classification
│   ├── triage_agent.py           # Rule-based router — new vs existing incident
│   ├── correlation_agent.py      # DSPy AlertsToIncident — root cause reasoning
│   └── reconciler_agent.py      # ReAct loop — merge/split/close decisions
├── communications/
│   └── communications_agent.py   # RLVR fine-tuned — NOC advisory generation
├── orchestrator/
│   ├── master_orchestrator.py    # Two concurrent asyncio loops
│   ├── streaming_pipeline.py     # Per-alert: Normalizer→Triage→Correlation→Store
│   ├── batch_reconciler.py       # Scheduled: Reconciler→Communications
│   └── incident_store.py         # SQLite shared state
├── dspy_programs/
│   ├── alerts_to_incident.py     # AlertsToIncident signature definition
│   └── alerts_to_incident_compiled.json  # Saved after optimization run
├── models/
│   ├── normalizer_final_locked/      # Qwen-2.5 7B + LoRA — FROZEN
│   └── communications_final_locked/  # Qwen-2.5 7B + LoRA — FROZEN
├── generator/
│   ├── fault_scenarios.py        # 12 FaultScenario definitions
│   ├── synthetic_generator.py   # ScenarioDrivenGenerator class
│   └── dataset_splits.py        # Train/val/test split management
├── scripts/
│   ├── generate_training_data.py
│   ├── prepare_normalizer_sft.py
│   ├── train_normalizer_sft.py
│   ├── train_normalizer_rlvr.py
│   ├── prepare_communications_sft.py
│   ├── train_communications_sft.py
│   ├── train_communications_rlvr.py
│   └── optimize_dspy.py
├── topology/
│   └── otel_demo_graph.json      # Hardcoded OTel demo service dependencies
├── data/
│   ├── train.json                # 100 incidents — FIXED, never regenerate
│   ├── val.json                  # 30 incidents — FIXED
│   └── test.json                 # 20 incidents — NEVER touch until Week 15 eval
├── evaluation/
│   ├── root_cause_accuracy.py
│   ├── domain_classification.py
│   ├── advisory_compliance.py
│   └── latency_monitor.py
├── demo/
│   ├── inject_failure.sh         # docker compose stop valkey-cart
│   └── run_demo.py               # Scripted hackathon walkthrough
├── ui/
│   └── noc_dashboard.py          # Three-panel rich terminal display
├── config/
│   ├── thresholds.yaml           # Alert severity thresholds per metric
│   ├── mcp_endpoints.yaml        # Prometheus/Jaeger/Node Exporter URLs
│   ├── model_config.yaml         # Model paths — NO API KEYS HERE
│   └── reconciler_config.yaml   # Interval: 30s demo / 900s production
├── docs/
│   └── architecture/
│       └── noc_whisperer_system_architecture.svg
├── CONTEXT.md                    # THIS FILE
├── EXECUTION_PLAN.md             # Session-by-session task list
├── .cursorrules                  # Cursor reads this automatically
├── .env.example                  # API key template — never commit .env
├── .gitignore                    # Must include: .env, models/, data/
├── requirements.txt
└── README.md
```

---

## The Three Core Data Structures

Every agent speaks these three types and nothing else.
Define once in `adapters/canonical_alert.py`. Import everywhere.

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

@dataclass
class CanonicalAlert:
    alert_id:      str        # UUID — generated at normalization time
    timestamp:     datetime   # UTC — normalized from source format
    domain:        str        # infrastructure | service_mesh | application
    severity:      str        # critical | major | minor | warning
    device:        str        # normalized device identifier
    metric:        str        # what was measured (e.g. cpu_usage_percent)
    message:       str        # human readable description
    source_system: str        # jaeger | prometheus | node_exporter | synthetic
    value:         float      # raw metric value
    threshold:     float      # threshold that was breached
    confidence:    float      # normalizer classification confidence 0.0-1.0
    raw_payload:   dict       # original untouched payload — audit trail


@dataclass
class TriageDecision:
    alert:       CanonicalAlert
    action:      str                # "append" | "new"
    incident_id: Optional[str]      # incident to append to, or None if "new"


@dataclass
class Incident:
    incident_id:               str
    created_at:                datetime
    updated_at:                datetime
    status:                    str             # open | resolved
    root_cause_device:         str             # DSPy output
    incident_title:            str             # DSPy output
    affected_services:         List[str]       # DSPy output
    confidence:                float           # increases as evidence accumulates
    recommended_action:        str             # DSPy output
    alerts:                    List[CanonicalAlert]  # full alert history
    preliminary_advisory_sent: bool = False
    confirmed_advisory_sent:   bool = False
```

---

## The Four MCP Tools — Interface Contracts

Each tool returns `List[CanonicalAlert]` or structured data.
All tools must have a mock version in `mcp_tools/mocks/`.
Agents call tools through these interfaces — never directly against APIs.
Each MCP tool contains its own internal conversion method
(_to_canonical() or _span_to_canonical()) that converts
raw API responses to CanonicalAlert. There are no separate
adapter files for live MCP tools — conversion is co-located
with the tool that owns the data source.

```python
class TopologyMCP:
    # Data source: topology/otel_demo_graph.json (static file)
    def get_downstream(self, device: str) -> List[str]: ...
    def get_upstream(self, device: str) -> List[str]: ...
    def are_related(self, device_a: str, device_b: str) -> bool: ...
    def get_cascade_chain(self, root_device: str) -> List[str]: ...
    def get_topology_context(self, devices: List[str]) -> dict: ...

class JaegerMCP:
    # Data source: GET http://localhost:16686/api/traces
    def get_error_spans(self, since_seconds: int = 30) -> List[CanonicalAlert]: ...

class PrometheusMCP:
    # Data source: GET http://localhost:9090/api/v1/query
    def get_threshold_breaches(self) -> List[CanonicalAlert]: ...
    def query(self, promql: str) -> dict: ...
    def get_alerts_since(self, seconds: int) -> List[CanonicalAlert]: ...

class NodeExporterMCP:
    # Data source: Prometheus scrape of localhost:9100
    def get_host_alerts(self) -> List[CanonicalAlert]: ...
```

---

## The Five Agents — Contracts

### Agent 1 — Normalizer Agent
```
File:   agents/normalizer_agent.py
Type:   RLVR fine-tuned small model
Model:  models/normalizer_final_locked (Qwen-2.5 7B + LoRA)
Dev:    Ollama/llama3.1:8b as drop-in until model is trained

Input:  raw_payload: dict, source_system: str
Output: CanonicalAlert

Task:   Classify domain (infrastructure | service_mesh | application)
        and severity (critical | major | minor | warning)
        from raw heterogeneous metric events.

Key method:
    def process(self, raw_payload: dict, source_system: str) -> CanonicalAlert
```

### Agent 2 — Triage Agent
```
File:   agents/triage_agent.py
Type:   Rule-based — NO LLM
Input:  CanonicalAlert, incident_store reference
Output: TriageDecision

Logic:
    1. Get all open incidents from incident_store
    2. For each open incident:
       a. temporal proximity: alert.timestamp within 300s of incident.updated_at
       b. topological proximity: topology_mcp.are_related(alert.device,
                                 incident.root_cause_device)
    3. If both met: action="append", incident_id=matched_id
    4. Else:        action="new",    incident_id=None

Key method:
    def route(self, alert: CanonicalAlert) -> TriageDecision
```

### Agent 3 — Correlation Agent
```
File:   agents/correlation_agent.py
Type:   DSPy ChainOfThought (large model via API)
Model:  GPT-4o-mini (dev) | Claude Opus 4.7 (hackathon demo only)
DSPy:   dspy_programs/alerts_to_incident_compiled.json

Input:  TriageDecision
Output: Incident

Logic:
    1. action="append": cluster = existing_incident.alerts + [new_alert]
       action="new":    cluster = sliding_window_buffer + [new_alert]
    2. devices = [a.device for a in cluster]
    3. context = topology_mcp.get_topology_context(devices)
    4. result  = dspy_program(alert_cluster=cluster, topology_context=context)
    5. Return updated or new Incident

Key method:
    def correlate(self, decision: TriageDecision) -> Incident
```

### Agent 4 — Reconciler Agent
```
File:   agents/reconciler_agent.py
Type:   ReAct loop — LLM reasoning with tool calls
Model:  GPT-4o-mini
Fires:  Every 30s (demo) / 900s (production) — config/reconciler_config.yaml

Input:  List[Incident] — all open incidents from incident_store
Output: List[ReconcilerDecision] — merge | split | close

Logic (ReAct, max 3 iterations per incident pair):
    THINK:   Are incidents A and B the same root cause?
    ACT:     topology_mcp.are_related(A.root_cause, B.root_cause)
             prometheus_mcp.query(current metric state)
    OBSERVE: Evidence for or against merge
    DECIDE:  merge | split | close | keep

Key method:
    def reconcile(self, open_incidents: List[Incident]) -> List[ReconcilerDecision]
```

### Agent 5 — Communications Agent
```
File:   communications/communications_agent.py
Type:   RLVR fine-tuned small model
Model:  models/communications_final_locked (Qwen-2.5 7B + LoRA)
Dev:    Ollama/llama3.1:8b as drop-in until model is trained

Input:  Incident, advisory_type: str ("preliminary" | "confirmed")
Output: str (formatted NOC advisory text)

Triggers:
    confidence > 0.50 AND preliminary_advisory_sent = False → "preliminary"
    confidence > 0.85 AND confirmed_advisory_sent  = False → "confirmed"

Key method:
    def generate(self, incident: Incident, advisory_type: str) -> str
```

---

## Orchestration Architecture

```
STREAMING LOOP (asyncio — continuous, polls MCP tools every 15 seconds):

    [JaegerMCP] [PrometheusMCP] [NodeExporterMCP] [TopologyMCP]
          ↓ raw_payload per alert
    Normalizer Agent → CanonicalAlert
          ↓
    Triage Agent → TriageDecision
          ↓
    Correlation Agent (DSPy) → Incident
          ↓
    Incident Store (SQLite) upsert
          ↓
    check_advisory_triggers(incident)
          ↓ if threshold crossed
    Communications Agent → advisory string
          ↓
    Dashboard Panel 3 update


BATCH LOOP (asyncio — scheduled per reconciler_config.yaml):

    Incident Store → get_open_incidents()
          ↓
    Reconciler Agent (ReAct, max 3 iter) → decisions
          ↓
    Incident Store — execute merge/split/close
          ↓
    check_advisory_triggers(updated incidents)
          ↓ if threshold crossed
    Communications Agent → advisory string
          ↓
    Dashboard Panel 3 update


SHARED STATE:    incident_store (SQLite) — both loops read and write
MASTER:          asyncio.gather(streaming_loop(), batch_loop())
```

---

## DSPy Signature

```python
# dspy_programs/alerts_to_incident.py

import dspy

class AlertsToIncident(dspy.Signature):
    """Correlate a cluster of alerts into a unified incident report."""

    alert_cluster = dspy.InputField(
        desc="JSON list of canonical alerts — timestamp, domain, severity, "
             "device, metric, message, value"
    )
    topology_context = dspy.InputField(
        desc="JSON dict of service dependency relationships for devices "
             "in the alert cluster"
    )
    root_cause_device = dspy.OutputField(
        desc="Specific device most likely responsible for triggering the cascade"
    )
    incident_title = dspy.OutputField(
        desc="One-line description suitable for a NOC dashboard"
    )
    affected_services = dspy.OutputField(
        desc="Comma-separated list of downstream affected services"
    )
    confidence = dspy.OutputField(
        desc="Score 0.0-1.0 followed by one sentence of reasoning"
    )
    recommended_action = dspy.OutputField(
        desc="Single most important action for a NOC engineer right now"
    )

# Optimizer:  dspy.BootstrapFewShot(max_bootstrapped_demos=8)
# Metric:     root_cause_device accuracy on val set (30 incidents)
# Model:      GPT-4o-mini
# Run ONCE:   Week 15, scripts/optimize_dspy.py
# Save:       dspy_programs/alerts_to_incident_compiled.json
```

---

## RLVR Reward Functions

### Normalizer Reward
```python
def normalizer_reward(predicted: dict, ground_truth: dict) -> float:
    domain_correct = float(
        predicted["domain"] == ground_truth["domain"]
    )
    severity_ranks = {"critical": 3, "major": 2, "minor": 1, "warning": 0}
    delta = abs(
        severity_ranks.get(predicted["severity"], 0) -
        severity_ranks.get(ground_truth["severity"], 0)
    )
    severity_score = {0: 1.0, 1: 0.5, 2: 0.0}.get(delta, 0.0)
    return 0.6 * domain_correct + 0.4 * severity_score
```

### Communications Reward
```python
import re
from textstat import flesch_kincaid_grade

KNOWN_SERVICES = [
    "valkey-cart", "postgresql", "cart", "checkout",
    "payment", "product-catalog", "frontend", "kafka",
    "accounting", "fraud-detection", "shippingservice"
]

def advisory_reward(generated: str) -> float:
    scores = []
    scores.append(float(any(w in generated.upper() for w in
                  ["INCIDENT", "FAILURE", "OUTAGE", "DEGRADATION"])))
    named = sum(1 for s in KNOWN_SERVICES if s.lower() in generated.lower())
    scores.append(min(1.0, named / 2))
    scores.append(float(bool(re.search(r'\d{1,2}:\d{2}', generated))))
    scores.append(float("ACTION" in generated.upper()))
    scores.append(float("NOC" in generated.upper()))
    fk = flesch_kincaid_grade(generated)
    scores.append(1.0 if 7 <= fk <= 10 else 0.5)
    return sum(scores) / len(scores)
```

---

## Fine-Tuning Specifications

```python
BASE_MODEL = "Qwen/Qwen2.5-7B-Instruct"

lora_config = LoraConfig(
    r=16, lora_alpha=32,
    target_modules=["q_proj", "v_proj"],
    lora_dropout=0.05, bias="none",
    task_type="CAUSAL_LM"
)

sft_args = SFTConfig(
    num_train_epochs=3,
    per_device_train_batch_size=4,
    learning_rate=2e-4,
)

grpo_args = GRPOConfig(
    num_generations=8,   # G=8 — capstone requirement
    num_train_epochs=2,
)

# GPU budget (RTX 5090):
# Normalizer SFT:       ~2 hours
# Normalizer RLVR:      ~3 hours
# Communications SFT:   ~1 hour
# Communications RLVR:  ~2 hours
# Total:                ~8-10 hours
```

---

## Training Dataset Specifications

```
data/train.json  — 100 incidents × ~40 alerts  (noise_ratio=0.3)
data/val.json    — 30  incidents × ~40 alerts  (noise_ratio=0.3)
data/test.json   — 20  incidents × ~40 alerts  (noise_ratio=0.4)

Rules:
- Generate ALL THREE in ONE script run with fixed random seed
- NEVER regenerate after Week 13 Day 5
- NEVER touch test.json until Week 15 final evaluation

Ground truth per incident:
    root_cause_device, initiating_domain, affected_services,
    cascade_type, correlation_window_seconds
```

---

## The 12 Fault Scenarios

| # | Name | Domain | Key Signal |
|---|---|---|---|
| 1 | Redis cache failure → DB overload | Storage | Cache miss ratio → DB CPU spike |
| 2 | Disk full → DB read-only | Storage | Write failures only, reads succeed |
| 3 | I/O latency → DB slowdown | Storage | Disk latency precedes DB latency |
| 4 | OOM kill → service death | Compute | Memory alert precedes service death |
| 5 | CPU starvation → latency | Compute | Simultaneous latency, same host, no errors |
| 6 | Container throttling | Compute | Throttle metric present, slowness not errors |
| 7 | Network partition | Network | Cross-rack failures, same-rack successes |
| 8 | DNS failure | Network | Gradual spread by connection churn rate |
| 9 | Load balancer failure | Network | Uniform latency increase, no errors initially |
| 10 | Certificate expiry | Dependency | Failures at precise time boundary |
| 11 | Bad deployment config | Dependency | Failures correlate with deploy timestamp |
| 12 | External API degradation | Dependency | Latency at external boundary only |

**Scenario 1 (Redis cascade) = PRIMARY demo scenario.**

---

## Configuration Files

### config/thresholds.yaml
```yaml
compute:
  cpu_utilization_percent:
    critical: 90.0
    major: 80.0
    minor: 70.0
  memory_available_mb:
    critical: 500
    major: 1000
    minor: 2000
  oom_kill_count:
    critical: 1

storage:
  disk_used_percent:
    critical: 90.0
    major: 80.0
    minor: 70.0
  disk_io_latency_ms:
    critical: 50.0
    major: 20.0
    minor: 10.0
  cache_miss_ratio:
    critical: 0.90
    major: 0.70
    minor: 0.50

service_mesh:
  http_error_rate_per_min:
    critical: 20
    major: 10
    minor: 5
  http_latency_seconds:
    critical: 5.0
    major: 2.0
    minor: 1.0
  connection_pool_saturation:
    critical: 0.95
    major: 0.80
    minor: 0.70
```

### config/mcp_endpoints.yaml
```yaml
jaeger:
  base_url: http://localhost:16686
  traces_endpoint: /api/traces

prometheus:
  base_url: http://localhost:9090
  query_endpoint: /api/v1/query
  range_endpoint: /api/v1/query_range

node_exporter:
  prometheus_base_url: http://localhost:9090
  job_name: node
```

### config/reconciler_config.yaml
```yaml
reconciler_interval_seconds:
  demo:        30
  development: 60
  production:  900

merge_confidence_threshold: 0.75
close_inactivity_seconds:   1200
max_react_iterations:       3
```

### config/model_config.yaml
```yaml
# API keys loaded from .env — never hardcode here
normalizer_agent:
  development: ollama/llama3.1:8b
  production:  models/normalizer_final_locked

communications_agent:
  development: ollama/llama3.1:8b
  production:  models/communications_final_locked

correlation_agent:
  development:       ollama/llama3.1:8b
  dspy_optimization: gpt-4o-mini
  demo:              gpt-4o-mini

reconciler_agent:
  all: gpt-4o-mini
```

---

## NOC Dashboard Layout

```
Three-panel rich terminal display — ui/noc_dashboard.py

Panel 1 — RAW ALERT STREAM    (left,   border=red)
  Last 10 alerts | Columns: Time | Source | Device | Signal
  Updates every 15 seconds

Panel 2 — INCIDENT BOARD      (center, border=yellow)
  Open incidents | Columns: ID | Root Cause | Affected | Confidence | Status
  Updates on every Incident Store write

Panel 3 — NOC ADVISORY        (right,  border=green)
  Latest advisory text — preliminary first, confirmed when fired
  Updates when Communications Agent fires

Refresh: 2 Hz via rich Live.update()
```

---

## Advisory Trigger Logic

```python
async def check_advisory_triggers(incident: Incident):
    if (incident.confidence > 0.50 and
            not incident.preliminary_advisory_sent):
        advisory = communications_agent.generate(
            incident, advisory_type="preliminary"
        )
        dashboard.update_advisory(advisory)
        incident.preliminary_advisory_sent = True
        await incident_store.upsert(incident)

    elif (incident.confidence > 0.85 and
              not incident.confirmed_advisory_sent):
        advisory = communications_agent.generate(
            incident, advisory_type="confirmed"
        )
        dashboard.update_advisory(advisory)
        incident.confirmed_advisory_sent = True
        await incident_store.upsert(incident)
```

---

## OTel Demo Service Topology

Encoded in `topology/otel_demo_graph.json`:

```
valkey-cart    → feeds: [cart, product-catalog]
postgresql     → feeds: [cart, product-catalog, checkout]
kafka          → feeds: [accounting, fraud-detection]
payment        → feeds: [checkout]
cart           → feeds: [checkout, frontend]
                 depends: [valkey-cart, postgresql]
checkout       → feeds: [frontend]
                 depends: [cart, payment, postgresql,
                           currencyservice, emailservice, shippingservice]
product-catalog→ feeds: [checkout, recommendation, frontend]
                 depends: [postgresql]
frontend       → feeds: [frontend-proxy]
                 depends: [cart, checkout, product-catalog,
                           recommendation, ad]
frontend-proxy → feeds: []
                 depends: [frontend]
```

---

## Environment Setup

```bash
# OTel demo
git clone https://github.com/open-telemetry/opentelemetry-demo
cd opentelemetry-demo
# Add Node Exporter to docker-compose.yml then:
docker compose up

# Verify
curl http://localhost:9090/api/v1/query?query=up
curl http://localhost:16686/api/services
curl http://localhost:9100/metrics | head -20

# Python
pip install -r requirements.txt

# Ollama (local dev inference)
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull llama3.1:8b
```

---

## requirements.txt

```
torch
transformers
peft
trl
dspy-ai
openai
python-dotenv
aiosqlite
rich
textstat
requests
pandas
numpy
pytest
pyyaml
```

---

## .gitignore — Critical Entries

```
.env
models/
data/
*.pyc
__pycache__/
.DS_Store
checkpoints/
*.log
```

---

## Key Rules

1. Never hardcode API keys — use `.env`, load with `python-dotenv`
2. Never commit `.env` — in `.gitignore`
3. Never commit `models/` — too large, use git-lfs or exclude
4. Never commit `data/` — regenerate from scripts
5. Never touch `data/test.json` until Week 15 final evaluation
6. All agents independently testable with mock MCP tools
7. One file per Cursor session — no mixed concerns
8. Commit after every session — even stubs
