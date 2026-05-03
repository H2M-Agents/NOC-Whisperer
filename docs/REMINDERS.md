# NOC Whisperer — Open Reminders and Pending Confirmations

> Cursor: At the start of every session, check this file.
> If any reminder is marked BLOCKING for the current session,
> alert the user before proceeding with any code changes.

---

## REMINDER-001 — SV Cluster Configuration
**Status:** OPEN
**Blocking:** Session 22 (optimize_dspy.py) — due Fri May 8
**Action required:** Confirm the following with your reviewer
  before starting Session 22:

  1. Exact SV cluster endpoint URL
     → Goes into OPENAI_API_BASE in .env
     → Example: http://SV_CLUSTER_IP:PORT/v1

  2. Exact model name
     → Currently assumed: gpt-oss-20b
     → Confirm this is the correct model string

  3. API key requirement
     → Does the SV cluster require an API key?
     → If no: set OPENAI_API_KEY=none in .env
     → If yes: get the internal key from reviewer

  4. API format
     → Confirm it is OpenAI-compatible REST API
     → dspy.OpenAI() assumes this format
     → If different: a custom DSPy LM adapter may be needed

**What to do when resolved:**
  1. Update .env with OPENAI_API_BASE and OPENAI_API_KEY
  2. Update config/llm_endpoints.yaml dspy_optimization.base_url
  3. Mark this reminder as RESOLVED

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

## REMINDER-005 — RLVR Training GPU Constraint
**Status:** OPEN — ESCALATED
**Blocking:** Session 14 Part 2, Session 18 Part 2
**Last updated:** Sun May 3
**Situation:**
  Better GPU procurement failed.
  RTX 4060 Ti estimated runtime: 7+ hours per RLVR job
  SV cluster 2-hour limit makes this infeasible.
  Two RLVR jobs needed:
    1. Normalizer RLVR  (Session 14 Part 2)
    2. Communications RLVR (Session 18 Part 2)

**Options still open:**
  1. Find GPU with no time limit (A100, H100, RTX 3090+)
  2. Use reduced dataset (50 examples, 1 epoch, ~54 min)
     Script already updated for this option
  3. Use Google Colab Pro+ (~$12/month, A100 access)
  4. Use Lambda Labs (~$1.10/hr for A100)
  5. Skip RLVR entirely — use SFT model only for demo
     (lower accuracy but still functional)

**Deadline:** Must resolve by Fri May 9
  to have models ready for evaluation on Sat May 10

**What to do when resolved:**
  1. SSH to GPU machine
  2. git pull
  3. python3 scripts/train_normalizer_rlvr.py
  4. python3 scripts/train_communications_rlvr.py
  5. Record results in docs/evaluation_results.md
  6. Mark RESOLVED

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

(Move resolved items here with resolution date)
