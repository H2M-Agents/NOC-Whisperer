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
**Status:** OPEN
**Blocking:** Session 25 (live OTel integration) — due Mon May 11
**Action required:**
  1. Get Docker Compose V2 plugin installed on VM
     sudo apt-get install -y docker-compose-plugin
  2. Run Session 7 OTel environment setup
  3. Note the VM IP address
  4. Update config/mcp_endpoints.yaml with VM IP

**What to do when resolved:**
  1. Complete Session 7 checklist
  2. Update config/mcp_endpoints.yaml
  3. Mark this reminder as RESOLVED

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
