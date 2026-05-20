> ⚠️ SUPERSEDED — May 30 2026
> This outline was written for a 15-minute slot (Session 28,
> May 12 2026). The active presentation for the May 30 demo
> is the 10-minute 9-slide deck validated against the current
> repo state. Key differences: 299 tests (not 211),
> run_demo_adk.py (not run_demo.py), ADK loop has no
> ReconcilerAgent, dedupe window removed.
> See docs/DEMO_QA.md for current Q&A preparation.

# NOC Whisperer — Presentation Outline (Hybrid VC + Technical Capstone)

**Format:** 12 slides · **15 minutes** total (~75s/slide average; compress slides 1–2 and 12 for buffer)  
**Sources:** `CONTEXT.md`, `docs/evaluation_results.md`  
**Session:** 28 · **Date:** Tue May 12, 2026

---

## 30-second elevator pitch

NOC Whisperer turns a flood of incompatible observability alerts into **one correlated incident** and **operator-ready advisories** in **under two seconds**, using a **hybrid five-agent pipeline**: **three** LLM-backed agents (fine-tuned **Qwen** normalizer + advisories, **DSPy** correlation on **gpt-oss-20b**) plus **two** fast **rule-based** agents (triage + reconciler). We ship a **live OpenTelemetry demo** (Valkey cascade) and measured **~97% DSPy root-cause accuracy** on a held-out val set—while learning hard lessons about **RL reward hacking** in advisory training and fixing the reward function.

---

## Slide 1 — Title + one-liner

**Hook:** Turn incident chaos into a single, actionable story before revenue and SLAs burn.

**Bullets:**
- **NOC Whisperer** — agentic alert correlation + incident synthesis
- Live path: Prometheus, Jaeger, Node Exporter, topology → SQLite + dashboard
- Capstone: end-to-end system, not a slide-only ML toy

**Technical depth:** Primary demo: **7 alerts**, **3 domains**, **1 incident**, root cause **`valkey-cart`**, confidence **0.91** (`CONTEXT.md`).

**Speaker note:** Open with the Valkey line in one breath, then name the stack (OTel demo + Python orchestrator). State you will prove speed and accuracy with numbers on slide 8.

---

## Slide 2 — Problem (alert fatigue + market size)

**Hook:** Alert fatigue is a tax on every digital business—minutes of confusion cost millions at scale.

**Bullets:**
- **Alert fatigue:** simultaneous, multi-tool fires; no unified incident object
- **Human bottleneck:** senior NOC **15–20 minutes** to a coherent root-cause picture (`CONTEXT.md`)
- **Market:** global enterprises run 24/7 NOC/SOC; observability + AIOps budgets scale with cloud and SLA penalties (qualitative TAM—cite your org’s segment in talk)

**Technical depth:** Contrast **15–20 min** manual synthesis vs **&lt; 2 s** target correlation in architecture (`CONTEXT.md`).

**Speaker note:** Keep “market size” honest: use industry framing, not fabricated billions unless you bring a cited stat. The win is **MTTR** and **operator minutes**.

---

## Slide 3 — Solution (5-agent pipeline overview)

**Hook:** One pipeline replaces tribal knowledge with repeatable machine reasoning—**not** “five LLMs in a trench coat.”

**Bullets:**
1. **Normalizer** — **LLM** (Qwen + LoRA): domain + severity  
2. **Triage** — **rules** (topology + store): new vs append — **no LLM**  
3. **Correlation** — **LLM** (DSPy program): incident fields + confidence  
4. **Reconciler** — **rules** (ReAct-shaped loop): merge / split / close — **no LLM**  
5. **Communications** — **LLM** (Qwen + LoRA, Ollama fallback): preliminary / confirmed advisories  
- **Hybrid:** 3 LLM-powered agents + 2 rule-based agents

**Technical depth:** Advisory triggers: **confidence &gt; 0.50** preliminary, **&gt; 0.85** confirmed (`CONTEXT.md`). **Three** agents call foundation models; **two** are deterministic.

**Speaker note:** Emphasize **typed contracts** (CanonicalAlert → Incident) and **two loops** (streaming + batch). Tease slide 5 for the explicit LLM vs rule split and latency story.

---

## Slide 4 — Architecture (4 pillars)

**Hook:** Production-shaped design: ingest, reason, persist, and show—not just a chatbot.

**Bullets:**
- **Pillar 1 — Ingest:** 4 MCP tools, each canonicalizes to `List[CanonicalAlert]`
- **Pillar 2 — Reason:** hybrid **five-agent** pipeline (**3 LLM**, **2 rule**) + DSPy compiled program artifact
- **Pillar 3 — Orchestrate:** asyncio streaming (15s poll) + batch reconciler; **SQLite** source of truth
- **Pillar 4 — Operate:** Rich terminal dashboard (raw stream, incident board, advisory)
- **Hybrid:** 3 LLM-powered agents + 2 rule-based agents

**Technical depth:** DSPy compiled program path: `dspy_programs/alerts_to_incident_compiled.json` (`evaluation_results.md`).

**Speaker note:** One diagram if available (architecture SVG); otherwise read the four pillars as a checklist live ops teams recognize.

---

## Slide 5 — The 5 Agents (hybrid: LLM + rules)

**Hook:** Reserve foundation models for **language and judgment**; use **deterministic code** where rules already beat LLMs on speed and auditability.

**Bullets:**

  **LLM-POWERED AGENTS (3):**

  - **NormalizerAgent:**  
    fine-tuned Qwen2.5-7B-Instruct (SFT + RLVR)  
    loss 3.1 → 0.541, 80.9% domain accuracy  

  - **CorrelationAgent:**  
    DSPy BootstrapFewShot + gpt-oss-20b  
    96.7% root cause accuracy, confidence 0.55→0.95  

  - **CommunicationsAgent:**  
    fine-tuned Qwen2.5-7B-Instruct (SFT + RLVR)  
    94.2% token accuracy, Ollama fallback  

  **RULE-BASED AGENTS (2):**

  - **TriageAgent:**  
    topology graph routing + temporal clustering  
    deterministic, no LLM, `<1ms` per alert  
    routes alerts to correct incident by proximity  

  - **ReconcilerAgent:**  
    merge/split/close rules, ReAct loop structure  
    deterministic, no LLM  
    closes stale incidents after 1200s inactivity  

**Technical depth:** Metric sources: `docs/evaluation_results.md` (training table); correlation **96.7%** on val **30** examples; demo incident confidence **0.91** on primary Valkey scenario (`CONTEXT.md`).

**Speaker note:** “We deliberately chose rule-based logic for triage and reconciliation — deterministic tasks where rules outperform LLMs in speed, cost, and reliability. LLMs are reserved for tasks requiring reasoning and language generation. This hybrid architecture is more production-ready than a pure LLM pipeline — and more honest about where AI adds genuine value.” Mention GPU trains, Mac runs **211** fast mocked tests.

---

## Slide 6 — Reward hacking discovery + fix

**Hook:** RL maximized the wrong signal—our **Communications** LLM “gamed” the rubric until we redesigned rewards (rule-based agents unaffected).

**Bullets:**
- **Symptom:** repeated “ACTION” / boilerplate lines to harvest keyword + readability scores
- **Root cause:** presence checks + Flesch–Kincaid band + **no repetition penalty** → classic reward hacking
- **Fix:** `advisory_reward()` now applies **repetition** (unique line ratio) + **length** tier penalties before returning score (`scripts/train_communications_rlvr.py`)

**Technical depth:** Communications RLVR run: train loss **−0.001**, **160** steps, **52 min** on **RTX 4090**; training reward ~**0.85–0.92** per doc note; compliance delta **0** (SFT already strong at **94.2%**).

**Speaker note:** This slide is your “PhD moment”—tie to RLHF in production. Mention **Ollama fallback** for clean demo output if GPU adapter misbehaves.

---

## Slide 7 — Live demo description

**Hook:** If it works on a real cascade, investors and engineers both lean in.

**Bullets:**
- **Stack:** OpenTelemetry demo app + Prometheus/Jaeger/Node Exporter (see runbook in `docs/REMINDERS.md`)
- **Fault:** stop **Valkey** container → cache failure cascade
- **Observe:** raw alerts → incident board → preliminary → confirmed advisory on thresholds

**Technical depth:** **7 alerts / 3 domains / 1 incident**; correlation confidence **0.91** on primary scenario (`CONTEXT.md`).

**Speaker note:** Pre-record a 60s clip as backup. Narrate one alert ID crossing dedupe + store upsert so the demo feels deterministic.

---

## Slide 8 — Results + metrics

**Hook:** We publish numbers—even where baseline heuristics look “too perfect.”

**Bullets:**
- **Correlation (DSPy):** optimized **96.7%** root-cause accuracy vs **100%** baseline heuristic on val (**30** examples); **8** bootstrap traces; model **gpt-oss-20b** on SV cluster
- **Normalizer:** SFT token accuracy **80.9%**; RLVR final train loss **0.034**
- **Communications:** SFT token accuracy **94.2%**; RLVR final compliance **0.8646** (same as baseline per table)

**Technical depth:** Latency table: end-to-end **TBD** but **target &lt; 2000 ms** (`evaluation_results.md`). Normalizer RLVR: **400** steps, **2** epochs.

**Speaker note:** Read the footnote from the doc aloud: **100% baseline** uses ground-truth-yoked heuristic; **96.7%** is the meaningful LLM number for demo day credibility.

---

## Slide 9 — Alert threshold calibration lesson

**Hook:** The best model fails if triggers fire at the wrong confidence—thresholds are part of the product.

**Bullets:**
- **Preliminary** gate: confidence **&gt; 0.50** + evidence counts (`CONTEXT.md`)
- **Confirmed** gate: confidence **&gt; 0.85**—aligns with “high trust” advisory copy
- **Lesson:** development vs production correlator modes trade interpretability vs strict DSPy path—calibrate demo script to the story you tell

**Technical depth:** Demo incident lands at **0.91** confidence—above confirmed bar with margin (`CONTEXT.md`).

**Speaker note:** Admit tuning is iterative: thresholds + dedupe window (**60 s** in streaming) shape what the NOC sees as “new” vs noise.

---

## Slide 10 — Lessons learned

**Hook:** Capstone value is in honest postmortems—not only green metrics.

**Bullets:**
- **Reward design = product quality** for RLVR advisories; SFT was already excellent (**94.2%**)
- **Evaluation honesty:** label where metrics are heuristic vs model-driven (`evaluation_results.md` correlation note)
- **Ops realism:** GPU time (e.g. Normalizer RLVR **77 min**) and token **max_length** during RLVR affected compliance readouts

**Technical depth:** Communications RLVR note: completions hit **max_length=256** during RLVR—truncation caveat in doc.

**Speaker note:** Close the arc from slide 6: detection + fix + retrain path is documented for the team after the hackathon.

---

## Slide 11 — Market + future work

**Hook:** This is a wedge into AIOps—start narrow (NOC correlation), expand to runbooks and ticketing.

**Bullets:**
- **Beachhead:** incident synthesis + advisory for hybrid cloud NOCs (every F500 digital unit)
- **Next:** second fault scenario (checkout cascade), architecture SVG in repo, full `run_evaluation.py` wiring off heuristics
- **GTM:** package as on-prem friendly (SQLite, YAML config, mock-first CI)

**Technical depth:** Roadmap anchors in repo: `docs/REMINDERS.md` (REMINDER-009 checkout, REMINDER-004 SVG, REMINDER-010 RLVR quality).

**Speaker note:** One sentence on **privacy**: keys in `.env`, no secrets in YAML—enterprise procurement cares.

---

## Slide 12 — Q&A

**Hook:** Open the floor—technical depth wins trust.

**Bullets:**
- **Bring:** link to repo, `evaluation_results.md`, demo runbook, one live terminal
- **Anticipate:** “Why not one giant LLM?” → **hybrid** design: rules for routing/reconcile; LLMs for classify/correlate/write; contracts, testability, cost, specialization
- **Anticipate:** “What breaks in prod?” → MCP availability, dedupe window, correlator mode

**Technical depth:** CI signal: **211** tests, fast suite (project standard)—mention as engineering hygiene.

**Speaker note:** Thank the team/cluster operators; invite collaboration on evaluation harness and second scenario. End on time.

---

## Timing cheat sheet (15 minutes)

| Slide | Suggested time |
|------|----------------|
| 1–2 | 2:00 |
| 3–5 | 4:30 |
| 6–7 | 3:30 |
| 8–10 | 3:30 |
| 11–12 | 1:30 |
| **Total** | **~15:00** |

---

*End of outline. Metrics and notes grounded in `docs/evaluation_results.md` as of file contents in repo.*
