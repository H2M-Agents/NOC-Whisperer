# NOC Whisperer — Open Reminders and Pending Confirmations

> Cursor: At the start of every session, check this file.
> If any reminder is marked BLOCKING for the current session,
> alert the user before proceeding with any code changes.

---

## DEMO DAY RUNBOOK
**This is the step-by-step sequence for demo day.**

### Pre-Demo Setup (T-5 minutes)
  ssh bmammen@ada-vm-1
  cd ~/projects/opentelemetry-demo
  docker compose up -d
  # llm container has restart:no in override file
  # it will start once and stay stable
  # no action needed for llm
  docker compose ps | grep -v "Up" | grep -v "NAME"
  # All containers must show Up

### Verify Data Flowing (T-2 minutes)
  curl -s "http://10.0.50.50:9090/api/v1/label/__name__/values" \
    | python3 -m json.tool | grep "app_" | head -5
  # Must show app_cart_* metrics

### Start Demo (T=0)
  # On Mac
  .venv/bin/python3 scripts/run_demo.py
  # Dashboard appears — all panels empty — this is correct

### Inject Fault (T+30s)
  # On ada-vm-1 in second terminal
  docker stop valkey-cart

### What To Expect
  T+60s:  Prometheus detects valkey-cart failure
  T+75s:  MCP tool polls — picks up alerts
  T+90s:  Alerts appear in RAW ALERT STREAM panel
  T+120s: Incident created in INCIDENT BOARD panel
  T+150s: Advisory fires in NOC ADVISORY panel

### Stop Demo
  Ctrl+C on Mac terminal
  Summary prints automatically

### Restore After Demo
  docker start valkey-cart
  # Wait 60 seconds for services to reconnect

---

## REMINDER-007 — Fix Noise Alerts In Synthetic Mode
**Status:** OPEN
**Blocking:** Synthetic demo cleanliness
**Action required:**
  Fix orchestrator/streaming_pipeline.py
  Add early return in process_alert() for synthetic_noise:
    if getattr(alert, "source_system", "") == "synthetic_noise":
        return
  Confidence: 97.5%
  Apply before demo day.

## REMINDER-008 — Commit Pending Changes
**Status:** OPEN
**Blocking:** Nothing — but must commit before demo
**Files to commit:**
  mcp_tools/prometheus_mcp.py
  mcp_tools/jaeger_mcp.py
  config/mcp_endpoints.yaml
  docs/REMINDERS.md
  scripts/run_demo.py
  .env.example

## REMINDER-009 — Second Demo Scenario (Checkout Failure)
**Status:** OPEN — try after GPU rehearsal
**Priority:** Nice-to-have — adds demo impact
**Last updated:** Sat May 9 2026

**What:**
  Test checkout service failure as second demo scenario.
  No retraining needed — pipeline generalizes to any failure.

**Live mode test:**
  On ada-vm-1: docker stop checkout
  On Mac: python3 scripts/run_demo.py (NOC_LIVE_MODE=true)
  Watch for checkout + payment + accounting cascade

**Synthetic mode (if needed):**
  Add CHECKOUT_CASCADE_SCENARIO to generator/fault_scenarios.py
  No GPU needed — ~30 minutes of work

**Presentation value:**
  "NOC Whisperer generalizes to any failure mode.
   We demonstrate two scenarios — cache failure
   and service failure — with zero retraining."

**When to do this:**
  After Session 27 GPU rehearsal confirms
  primary valkey-cart scenario works end-to-end.
  Target: Mon May 11 if time permits.

## REMINDER-010 — Fix CommunicationsAgent RLVR Training Data
**Status:** OPEN
**Priority:** High — affects advisory quality on demo day
**Last updated:** Mon May 11 2026

**Problem:**
  Fine-tuned communications model repeats the same phrase
  for every field in the advisory. Example:
    Impact: INVESTIGATING suspected cart root cause
    Resolution: INVESTIGATING suspected cart root cause
    Status: INVESTIGATING suspected cart root cause

  Root cause: RLVR reward function rewards keyword presence
  but does not penalize repetition. Model learned to
  repeat "INVESTIGATING suspected [device] root cause"
  everywhere to maximize reward.

**Fix needed:**

  Step 1: Review data/communications_sft_train.json
          Verify SFT examples have diverse field content
          Each field should have different meaningful content

  Step 2: Fix reward function in
          scripts/train_communications_rlvr.py
          Add repetition penalty:
            lines = completion.strip().split("\n")
            unique_lines = set(lines)
            repetition_ratio = len(unique_lines) / max(len(lines), 1)
            score += 0.4 * repetition_ratio
          Remove or reduce pure keyword matching rewards

  Step 3: Retrain on GPU (RLVR only — SFT checkpoint ok)
          ~50 minutes on RTX 4060 Ti or RTX 4090
          Save to models/communications_final_locked/

  Step 4: Test advisory quality with:
          python3 -c "
          from communications.communications_agent import CommunicationsAgent
          agent = CommunicationsAgent()
          # test generate() output quality
          "

**Estimated time:** 2 hours (including GPU training)
**Target:** Before demo day Sun May 17
**Fallback:** Use Ollama qwen3:8b for advisory generation
             (already working, good quality output)

---

## REMINDER-001 — SV Cluster Configuration
**Status:** RESOLVED — Wed May 6 2026

SV cluster confirmed live and reachable from Mac.
Real endpoint and credentials stored in .env only.
DSPy config uses dspy.LM with openai/ provider prefix.
See config/llm_endpoints.yaml for placeholder structure.

---

## REMINDER-002 — VM Docker Compose Setup
**Status:** RESOLVED — Sat May 9 2026

OTel stack running on ada-vm-1 (10.0.50.50)  
All 24 containers running  

Prometheus: http://10.0.50.50:9090 ✅  
Jaeger:     http://10.0.50.50:16686/jaeger/ui ✅  
            API prefix: /jaeger/ui/api/  
Frontend:   http://10.0.50.50:8080 ✅  
18 services reporting telemetry

---

## REMINDER-003 — GPU Access for Training
**Status:** OPEN
**Blocking:** Session 12 (train_normalizer_sft.py) — due Wed Apr 29
**Action required:**
  Confirm GPU access on SV cluster or VM before Session 12.
  Run: nvidia-smi
  Expected: RTX 5090 or equivalent with 16GB+ VRAM

**What to do when resolved:**
  1. Note GPU model and available VRAM in this file
  2. Confirm training scripts can be submitted as background jobs
  3. Mark this reminder as RESOLVED

---

## REMINDER-004 — Architecture SVG For Presentation
**Status:** OPEN
**Blocking:** Session 28 (presentation assets) — due Thu May 14
**Action required:**
  The architecture diagram SVG was generated in our planning
  conversation but needs to be committed to the repo.
  Save it to: docs/architecture/noc_whisperer_system_architecture.svg

**What to do when resolved:**
  1. Commit SVG to docs/architecture/
  2. Mark this reminder as RESOLVED

---

## REMINDER-006 — run_evaluation.py Partially Complete
**Status:** OPEN — DEFERRED
**Blocking:** Nothing critical — deferred in favor of run_demo.py
**Last updated:** Wed May 6 2026

**Current state:**
  Script written and tests passing (204/204) ✅
  Runs without error and produces output ✅
  BUT metrics use heuristics not real agents:
    - Root cause: BaselineCorrelator only (not DSPyCorrelator)
    - Domain/severity: source_system heuristic (not NormalizerAgent)
    - Latency: stub timings (not real agent calls)
    - Advisory: CommunicationsAgent.generate() IS real ✅

**What needs to be done:**
  Before calling this complete, fix evaluate_root_cause()
  to call DSPyCorrelator and evaluate_domain_severity()
  to call NormalizerAgent.

  Must run on ram-vm-1 (not Mac) to use fine-tuned models.

  Steps when ready:
    1. Diagnose agent constructor requirements first:
       Read normalizer_agent.py, triage_agent.py,
       correlation_agent.py and report __init__ signatures
    2. Fix evaluate_root_cause() to use DSPyCorrelator
    3. Fix evaluate_domain_severity() to use NormalizerAgent
    4. Run on ram-vm-1: python3 scripts/run_evaluation.py
    5. Update docs/evaluation_results.md with real numbers

**Priority:** Low — address after run_demo.py is working
**Target:** May 12 if time permits
**Fallback:** Use docs/evaluation_results.md training metrics
             for presentation — these are real numbers

---

## How To Add New Reminders

Copy this template:

## REMINDER-XXX — Short Title
**Status:** OPEN
**Blocking:** Session N (task name) — due Day Month
**Action required:**
  Description of what needs to be done.

**What to do when resolved:**
  1. Steps to close this reminder
  2. Mark this reminder as RESOLVED

---

## Resolved Reminders

## REMINDER-005 — RLVR Training GPU Constraint
**Status:** RESOLVED — Sun May 3

  All four training jobs complete:
    - Normalizer SFT      ✅ train_loss=0.541, avg_loss=0.917
    - Communications SFT  ✅ train_loss=0.250, avg_loss=1.071
    - Normalizer RLVR     ✅ train_loss=0.034 (reward ranged 0.2-1.0)
    - Communications RLVR ✅ train_loss=-0.001, compliance=0.8646
  Models saved to models/ on GPU machine
  To be copied to Mac before demo day
