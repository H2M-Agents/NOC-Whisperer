## NOC Whisperer — Agent Mental Models (Demo Ground Truth)

This document is a “mental map” of what each agent does in the **NOC Whisperer** demo, with the minimum detail needed to reason about behavior during a live run.

### The core contract (shared vocabulary)

All agents/tools communicate using three dataclasses from `adapters/canonical_alert.py`:

- **`CanonicalAlert`**: normalized alert (domain, severity, device, metric, confidence)
- **`TriageDecision`**: routing decision (`action: "new"|"append"`, `incident_id`)
- **`Incident`**: incident record (root cause, affected services, confidence, alerts list, advisory flags)

### The ADK demo loop (what actually runs on demo day)

The ADK orchestrator is an LLM that calls tools in order (see `orchestrator/adk_orchestrator.py`). The system behavior is determined by the **tools and agents behind them**, not by free-form LLM reasoning.

High-level sequence per cycle (15s polling in `scripts/run_demo_adk.py`):

- **STEP 1**: `get_active_alerts()` (Prometheus tool wrapper)
- **STEP 2**: `normalize_alert()` (NormalizerAgent tool wrapper)
- **STEP 3**: `route_alert()` (TriageAgent tool wrapper)
- **STEP 4**: `correlate_alert()` (CorrelationAgent tool wrapper + dedup guard)
- **STEP 5**: `generate_advisory()` when thresholds met
- **STEP 6**: health + close + resolution advisory

The three dashboard panels are updated through a shared in-process `NOCDashboard` object:

- RAW ALERT STREAM: `normalizer_tools.update_alert_stream()`
- INCIDENT BOARD: refreshed from `IncidentStore.get_open_incidents()` each cycle
- NOC ADVISORY: `communications_tools.update_advisory()` on successful generation

---

## Agent 1 — NormalizerAgent

**File**: `agents/normalizer_agent.py`  
**Type**: fine-tuned LoRA model (preferred) with deterministic fallback  
**Tool wrapper**: `agents/adk_tools/normalizer_tools.py` → `normalize_alert()`

### Mental model

“**Turn noisy, source-specific signals into a clean, typed alert**.”

```mermaid
flowchart TD
  RA[Raw alert fields: device, metric, value, message, threshold] --> NA[normalize_alert tool]
  NA --> BCA[Build raw_payload dict + source_system]
  BCA --> NP[NormalizerAgent.process()]
  NP -->|first call| LM[Lazy-load LoRA adapter if present]
  LM --> INF{LoRA available and inference parses?}
  NP --> INF
  INF -->|yes| LLM[Local Qwen+LoRA inference: domain/severity plus confidence]
  INF -->|no| RB[Rule-based fallback: domain/severity]
  LLM --> CA[CanonicalAlert]
  RB --> CA
  CA --> DAS[Dashboard.update_alert_stream RAW ALERT STREAM]
  CA --> OUT[Return CanonicalAlert.to_dict()]
```

### Inputs

- A small raw payload dict (device, metric, value, threshold, message)
- `source_system` (e.g. prometheus, node_exporter, jaeger, synthetic)

### Outputs

- `CanonicalAlert` with:
  - **domain**: infrastructure | service_mesh | application
  - **severity**: critical | major | minor | warning
  - **confidence**: classifier confidence
  - **device/metric/message/value** normalized into consistent fields

### Key behaviors to remember for the demo

- **Lazy-load**: model loads on first `.process()` call.
- **Fallback exists**: if adapter missing or inference parsing fails, it uses rule-based domain/severity.
- **Dashboard**: successful normalize pushes the alert into RAW ALERT STREAM (last 10).

### Failure modes that show up live

- Model unavailable → rule-based classification (usually still fine for the demo)
- Garbage model output → fallback path, or default domain/severity heuristics

---

## Agent 2 — TriageAgent

**File**: `agents/triage_agent.py`  
**Type**: rule-based (no LLM)  
**Tool wrapper**: `agents/adk_tools/triage_tools.py` → `route_alert()`

### Mental model

“**Decide whether this alert extends an existing incident, or starts a new one**.”

```mermaid
flowchart TD
  CAIN[Canonical alert fields: device, domain, severity, metric, value, confidence] --> RA[route_alert tool]
  RA --> B[Build CanonicalAlert with now timestamp]
  B --> T[TriageAgent.route()]
  T --> O[Load open incidents from IncidentStore]
  O --> M{Any incident matches? time<=300s and topology related}
  M -->|yes| AP[action append, incident_id matched]
  M -->|no| NW[action new, incident_id none]
  AP --> OUT[Return TriageDecision.to_dict()]
  NW --> OUT
```

### Inputs

- `CanonicalAlert`
- Open incidents from `IncidentStore.get_open_incidents()`
- Topology relations via `TopologyMCP.are_related()`

### Outputs

- `TriageDecision`:
  - `action="append"` + `incident_id=<existing>`
  - or `action="new"` + `incident_id=None`

### How it matches

An open incident is a match when BOTH are true:

- **Temporal proximity**: alert time within **300s** of `incident.updated_at`
- **Topological proximity**: `topology.are_related(alert.device, incident.root_cause_device)`

### Failure modes that show up live

- If many open incidents exist, the “first matching incident” wins (store ordering matters).
- The ADK wrapper constructs the triage `CanonicalAlert` timestamp at call time (not original Prometheus timestamp).

---

## Agent 3 — CorrelationAgent

**File**: `agents/correlation_agent.py`  
**Type**: DSPy-based correlator (production) with baseline fallback  
**Tool wrapper**: `agents/adk_tools/correlation_tools.py` → `correlate_alert()`

### Mental model

“**Given a cluster of alerts + topology, synthesize the incident story** (root cause, blast radius, confidence, recommended action).”

```mermaid
flowchart TD
  TDIN[TriageDecision fields: action, incident_id, alert fields] --> CT[correlate_alert tool]
  CT --> GUARD[Always-run dedup guard: valid id kept else match cart-valkey-cart]
  GUARD --> D[Build TriageDecision]
  D --> C[CorrelationAgent.correlate()]
  C --> PR[Prune sliding buffer (180s)]
  PR --> EX{append + incident_id found in store?}
  EX -->|yes| CL1[Cluster = existing.alerts + new alert]
  EX -->|no| CL2[Cluster equals buffer plus new alert or existing missing gives new UUID]
  CL1 --> TOP[TopologyMCP.get_topology_context(devices)]
  CL2 --> TOP
  TOP --> DSPy[DSPyCorrelator.predict compiled program if available]
  DSPy -->|failure| BASE[BaselineCorrelator.predict()]
  DSPy --> INC[Build Incident root cause, affected, confidence, action]
  BASE --> INC
  INC --> UPS[IncidentStore._upsert_sync()]
  UPS -->|exception| LOG[Log warning]
  UPS --> RET[Return incident fields to orchestrator]
  LOG --> RET
```

### Inputs

- `TriageDecision` (alert + action + incident_id)
- Topology context from `TopologyMCP.get_topology_context()`
- Sliding window buffer (180s) when action is `"new"`
- Existing incident alerts when action is `"append"`

### Outputs

- An `Incident` with:
  - `root_cause_device`, `incident_title`, `affected_services`
  - `confidence` (parsed from correlator output)
  - `recommended_action`
  - `alerts` = the full cluster used for reasoning

### What “production” means here

In ADK demo initialization (`agents/adk_tools/correlation_tools.py`), `CorrelationAgent(mode="production")` selects `DSPyCorrelator`.

DSPy correlator behavior (see `dspy_programs/alerts_to_incident.py`):

- Uses a compiled DSPy program when available and API keys are configured
- Falls back to a lightweight heuristic correlator if compiled program fails to load or run

### Critical guardrail (duplicate incident prevention)

The tool wrapper `correlate_alert()` runs a **dedup guard** before building `TriageDecision`. This exists to prevent the orchestrator LLM from creating duplicate incidents (e.g., passing `action="append"` with a bogus `incident_id`).

For the May 30 demo, this guard is the “last line of defense” against incident board explosion.

### Failure modes that show up live

- Bad append `incident_id` → correlation can mint a new UUID unless wrapper guard corrects it
- Silent store write failures → open incidents vanish from `get_open_incidents()` and dedup logic can’t see prior state

---

## Agent 4 — CommunicationsAgent

**File**: `communications/communications_agent.py`  
**Type**: fine-tuned LoRA model (preferred) with Ollama fallback  
**Tool wrapper**: `agents/adk_tools/communications_tools.py` → `generate_advisory()`

### Mental model

“**Convert incident state into operator-ready text**.”

```mermaid
flowchart TD
  INCIN[Incident + advisory_type] --> GA[generate_advisory tool]
  GA --> GUARD[Guard already_sent flags preliminary and confirmed]
  GUARD -->|already sent| AS[Return already_sent:*]
  GUARD -->|not sent| GEN[CommunicationsAgent.generate()]
  GEN --> LOAD{First call?}
  LOAD -->|yes| LM[Lazy-load LoRA adapter if present else Ollama]
  LOAD -->|no| PROMPT[_format_prompt(incident, type)]
  LM --> PROMPT
  PROMPT --> INF{Backend == LoRA?}
  INF -->|yes| LOC[_infer_local decode plus dedup plus caps]
  INF -->|no| OLL[_infer_ollama()]
  LOC --> POST[Scrub stale dates + finalize]
  OLL --> POST
  POST --> FLAG[Persist advisory_sent flag(s)]
  FLAG --> DASH[Dashboard.update_advisory NOC ADVISORY]
  DASH --> OUT[Return advisory text]
```

### Inputs

- `Incident`
- `advisory_type`: preliminary | confirmed | resolution

### Outputs

- Advisory text (string), and dashboard panel updated if wired

### When advisories fire in the ADK flow

From `orchestrator/adk_orchestrator.py` instruction:

- **confirmed**: confidence > 0.85 AND alert_count ≥ 2 AND confirmed flag false
- **preliminary**: confidence > 0.50 AND alert_count ≥ 2 AND preliminary flag false
- **resolution**: after health check succeeds and incident is closed

### Demo-grade safeguards (why May 25 issues happened)

Confirmed advisories historically risked repetitive “ACTION REQUIRED” spam due to:

- Prompt wording (“ACTION REQUIRED lines” plural)
- Generous decode parameters and sampling
- Only exact-duplicate line dedup

Mitigations were added in the local inference path to cap and truncate repeated ACTION REQUIRED patterns for the demo.

---

## “Agent 0” — The ADK Orchestrator (not a domain agent, but crucial)

**File**: `orchestrator/adk_orchestrator.py`  
**Type**: tool-calling coordinator (LLM)  
**Mental model**: “**A workflow runner that calls tools**.”

```mermaid
flowchart TD
  CYCLE[Start monitoring cycle] --> A1[get_active_alerts]
  A1 --> Z{Any alerts?}
  Z -->|no| S6[STEP 6 health+close loop]
  Z -->|yes| S2[STEP 2 normalize_alert for each]
  S2 --> S3[STEP 3 route_alert for each]
  S3 --> S4[STEP 4 correlate_alert for each]
  S4 --> S5[STEP 5 generate_advisory thresholds]
  S5 --> S6
  S6 --> WAIT[Sleep 15s and repeat]
```

It should be treated like a scheduler:

- It does not own data structures (tools do).
- It does not persist state (IncidentStore does).
- It can make tool-call mistakes (hence dedup guards).

---

## What is persisted vs in-memory (important for demo reasoning)

### Persisted in `IncidentStore` (SQLite)

- The `incidents` table stores incident rows, including:
  - open/resolved status
  - incident metadata
  - full `alerts` JSON list
  - advisory sent flags

### NOT persisted by default

- Advisory text (only held in the dashboard object’s memory)
- Raw alert stream (dashboard memory only)

---

## Practical “demo debugging” checklist

If something looks wrong on the Incident Board:

- **Too many duplicate incidents**:
  - suspect `correlate_alert()` wrapper guard / store visibility
  - look for upsert warnings

- **Confidence not rising / no confirmed advisory**:
  - suspect correlation mode fallback or alert clustering not appending
  - check `alert_count` and incident `confidence` reported by `correlate_alert()`

- **Advisory spam / repetition**:
  - suspect communications prompt + local inference post-processing
  - confirm whether LoRA vs Ollama path was used

