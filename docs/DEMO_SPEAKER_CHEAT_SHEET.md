## NOC Whisperer Demo Speaker Cheat Sheet

Use this as your 5-7 minute speaking guide for the May 30 demo.

---

## 1) Opening (20-30 seconds)

"NOC Whisperer is a multi-agent incident correlation system.  
When an infrastructure fault happens, it takes noisy alerts from multiple systems, normalizes them, routes them, correlates root cause, and generates NOC advisories in near real time."

---

## 2) Core Problem (30-45 seconds)

- In a real outage, alerts come from different sources and formats.
- Humans spend 15-20 minutes building the incident picture.
- NOC Whisperer compresses that to near-immediate incident synthesis.

Optional line:
"The model does not just classify one alert; it reasons over alert clusters plus service topology."

---

## 3) Agent Mental Model (60-90 seconds)

- **NormalizerAgent**: "Turn raw source-specific events into a clean canonical alert."
- **TriageAgent**: "Decide new incident vs append to existing incident."
- **CorrelationAgent**: "Synthesize root cause, affected services, confidence."
- **CommunicationsAgent**: "Generate operator-ready advisory text."
- **ADK Orchestrator**: "Calls tools in strict sequence each cycle."

Transition:
"Think of it as a pipeline: normalize -> route -> correlate -> advise."

---

## 4) Live Scenario Script (2-3 minutes)

### Pre-fault baseline

- Show dashboard panels:
  - RAW ALERT STREAM
  - INCIDENT BOARD
  - NOC ADVISORY
- Explain normal behavior: low/no critical incidents, stable board.

### Fault injection

- Stop valkey-cart (or run your prepared injection step).
- Narrate expected progression:
  1. Raw alerts appear.
  2. Incident board forms/updates one cart-rooted incident.
  3. Confidence rises as alerts append.
  4. Confirmed advisory fires once threshold is met.

### Recovery

- Restore service.
- Show health check path:
  - incident closes
  - service restored advisory generated

---

## 5) What Makes This Credible (45-60 seconds)

- Rule-based + model hybrid:
  - deterministic routing constraints
  - LLM for higher-order correlation and advisory generation
- Shared typed contracts (`CanonicalAlert`, `TriageDecision`, `Incident`)
- Guardrails added from rehearsal findings:
  - incident dedup robustness in correlation wrapper
  - advisory repetition controls in communications path

---

## 6) Known Questions You Can Pre-answer (30 seconds)

- "Is this just one prompt?" -> No, it is tool-orchestrated multi-agent flow.
- "Can it fail safely?" -> Yes, fallback paths and guardrails exist in each layer.
- "What is persisted?" -> Incidents and flags in SQLite; advisory panel text is in dashboard runtime state.

---

## 7) Closing (15-20 seconds)

"NOC Whisperer turns multi-source alert noise into one coherent incident narrative and actionable guidance, quickly enough to support real-time NOC operations."

---

## Fast Recovery Lines (if anything goes wrong live)

- **If dashboard lags**: "Tool cycle is still processing; the board refreshes after each cycle."
- **If advisory is delayed**: "Advisory triggers are threshold-gated by confidence and alert count."
- **If duplicate incidents appear**: "This is exactly why we added dedup guardrails; we can inspect the decision path live."

