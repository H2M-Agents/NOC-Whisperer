# NOC Whisperer — Open Reminders and Pending Confirmations

> Cursor: At the start of every session, check this file.
> If any reminder is marked BLOCKING for the current session,
> alert the user before proceeding with any code changes.

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
