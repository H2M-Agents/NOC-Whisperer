# NOC Whisperer — Presentation Outline (Hybrid VC + Technical Capstone)

**Format:** 12 slides · **15 minutes** total (~75s/slide average; compress slides 1–2 and 12 for buffer)  
**Sources:** `CONTEXT.md`, `docs/evaluation_results.md`  
**Session:** 28 · **Date:** Tue May 12, 2026

---

## 30-second elevator pitch

NOC Whisperer turns a flood of incompatible observability alerts into **one correlated incident** and **operator-ready advisories** in **under two seconds**, using a **five-agent pipeline** with **fine-tuned Qwen models** and **DSPy-optimized correlation**. We ship a **live OpenTelemetry demo** (Valkey cascade) and measured **~97% DSPy root-cause accuracy** on a held-out val set—while learning hard lessons about **RL reward hacking** in advisory training and fixing the reward function.

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

**Hook:** One pipeline replaces tribal knowledge with repeatable machine reasoning.

**Bullets:**
1. **Normalizer** — RLVR Qwen+LoRA: domain + severity  
2. **Triage** — rules: new vs append  
3. **Correlation** — DSPy: incident fields + confidence  
4. **Reconciler** — ReAct: merge/split/close  
5. **Communications** — RLVR Qwen+LoRA: preliminary / confirmed advisories  

**Technical depth:** Advisory triggers: **confidence &gt; 0.50** preliminary, **&gt; 0.85** confirmed (`CONTEXT.md`).

**Speaker note:** Emphasize **typed contracts** (CanonicalAlert → Incident) and **two loops** (streaming + batch)—shows engineering maturity, not a single LLM call.

---

## Slide 4 — Architecture (4 pillars)

**Hook:** Production-shaped design: ingest, reason, persist, and show—not just a chatbot.

**Bullets:**
- **Pillar 1 — Ingest:** 4 MCP tools, each canonicalizes to `List[CanonicalAlert]`
- **Pillar 2 — Reason:** five-agent sequential pipeline + DSPy program artifact
- **Pillar 3 — Orchestrate:** asyncio streaming (15s poll) + batch reconciler; **SQLite** source of truth
- **Pillar 4 — Operate:** Rich terminal dashboard (raw stream, incident board, advisory)

**Technical depth:** DSPy compiled program path: `dspy_programs/alerts_to_incident_compiled.json` (`evaluation_results.md`).

**Speaker note:** One diagram if available (architecture SVG); otherwise read the four pillars as a checklist live ops teams recognize.

---

## Slide 5 — Training pipeline (SFT + RLVR + DSPy)

**Hook:** Three complementary training philosophies—supervision, reinforcement, and program optimization.

**Bullets:**
- **SFT → RLVR** on **Qwen2.5-7B-Instruct** + **4-bit NF4** LoRA for Normalizer + Communications
- **DSPy** for correlation: compile/save optimized `AlertsToIncident`
- **Separation:** GPU trains; Mac runs **fast mocked tests** (211 tests, CI-friendly)

**Technical depth:** Normalizer SFT: loss **3.896 → 0.541**, token accuracy **80.9%**, **7 min** on **RTX 4060 Ti** (`evaluation_results.md`). Communications SFT: loss **3.001 → 0.250**, token accuracy **94.2%**, **57 s** on **RTX 4090**.

**Speaker note:** Mention RLVR pass for Normalizer: final train loss **0.034**, **77 min**, reward **0.200 → 0.350**—shows the stack actually trains, not just imports.

---

## Slide 6 — Reward hacking discovery + fix

**Hook:** RL maximized the wrong signal—our advisory model “gamed” the rubric until we redesigned rewards.

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
- **Anticipate:** “Why not one giant LLM?” → contracts, testability, cost, specialization
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
