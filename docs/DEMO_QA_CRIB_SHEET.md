## NOC Whisperer Demo Q&A Crib Sheet

Short, high-confidence answers for likely demo questions.

---

## Architecture and Agent Roles

### Q: Is this one LLM prompt, or a real pipeline?

**A:** It is a real multi-agent tool pipeline.  
The orchestrator calls tools in order: `get_active_alerts -> normalize_alert -> route_alert -> correlate_alert -> generate_advisory`, then health/close checks.

### Q: Which parts are rule-based vs model-based?

**A:**  
- Rule-based: Triage routing, health checks, closure logic, store operations.  
- Model-based: Normalizer classification (with fallback), DSPy correlation synthesis, Communications advisory generation.

### Q: What are the shared data contracts?

**A:** `CanonicalAlert`, `TriageDecision`, and `Incident`.  
All core steps pass through those typed structures.

---

## Correlation and Confidence

### Q: How does root cause get chosen?

**A:** The correlation agent evaluates clustered alerts with topology context and outputs `root_cause_device`, `affected_services`, `incident_title`, `confidence`, and recommended action.

### Q: Why does confidence increase over time?

**A:** As more related alerts append to the same incident, the evidence cluster gets stronger, which typically increases correlation confidence.

### Q: What happens if correlation model fails?

**A:** The DSPy correlator has a fallback baseline path so the system can still produce incident output.

---

## Incident Dedup and Guardrails

### Q: How do you prevent duplicate incidents?

**A:** Two layers:  
1) Triage routes to existing incidents based on time + topology relation.  
2) Correlation wrapper runs dedup guard logic before final correlation decision, including valid-id checks and known alias matching (`cart` <-> `valkey-cart`).

### Q: What if the orchestrator passes a bad `incident_id`?

**A:** The correlation wrapper resolves by open-incident matching so invalid append IDs do not create accidental new incidents in normal operation.

### Q: Is `ad` noise merged into cart incidents?

**A:** No. The matching logic is intentionally narrow to avoid broad topology merges that would contaminate cart incident tracking.

---

## Advisory Generation

### Q: When does a confirmed advisory fire?

**A:** In the ADK instruction path, when confidence is above threshold and alert_count condition is met, and the confirmed advisory flag is still false.

### Q: How did you address repeated advisory text seen in rehearsal?

**A:** We added prompt tightening and local inference post-processing caps to reduce repetitive `ACTION REQUIRED` patterns for demo stability.

### Q: Is advisory text persisted in SQLite?

**A:** Incident/advisory flags are persisted. The live advisory panel text itself is held in dashboard runtime state.

---

## Data, Storage, and Dashboard

### Q: What is stored in SQLite?

**A:** The `incidents` table: IDs, timestamps, status, root cause, affected services, confidence, recommended action, alert history JSON, and advisory flags.

### Q: Where do dashboard panels get data?

**A:**  
- Raw stream: normalized alerts pushed into dashboard memory.  
- Incident board: open incidents refreshed from store each cycle.  
- Advisory panel: latest generated advisory text in dashboard memory.

### Q: Is this production UI?

**A:** Current demo uses a Rich terminal dashboard. A web GUI path is feasible as a near-term enhancement without changing core agent logic.

---

## Reliability and Fallback Questions

### Q: What if model loading fails?

**A:** Both normalizer and communications have fallbacks (rule-based or Ollama path), so demo flow can continue.

### Q: What if a cycle errors?

**A:** The run loop catches cycle exceptions, logs them, and continues to next cycle instead of terminating the session.

### Q: What prevents stale advisories from re-firing every cycle?

**A:** Advisory sent flags are persisted and checked before generation; confirmed path also handles preliminary flag consistency.

---

## Performance and Demo Narrative

### Q: Why is this better than rule-only alerting?

**A:** It combines deterministic safety rails with model-based correlation across alerts and topology, producing a coherent incident narrative and operator guidance.

### Q: What should the audience watch for?

**A:**  
1) Alert burst appears.  
2) One coherent cart incident forms and confidence rises.  
3) Confirmed advisory appears.  
4) After restore, incident closes and resolution advisory appears.

### Q: What is the single takeaway?

**A:** NOC Whisperer converts fragmented alert noise into a unified, actionable incident view fast enough for live NOC operations.

