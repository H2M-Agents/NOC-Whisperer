---

# NOC Whisperer — Demo Q&A Cheat Sheet
# Capstone Presentation — May 30, 2026

---

## THEME 1: LLM vs Rule-based

**Q: Your baseline heuristic scored 100% and beat DSPy at 96.7%. Why use an LLM for correlation at all?**

A: The eval set was 30 examples — small enough that a well-tuned
heuristic can memorize the patterns. The LLM advantage shows up
in two places the eval doesn't measure: confidence calibration
(the heuristic always returns 0.55; DSPy returns 0.90-0.95
reflecting genuine evidence strength) and handling novel alert
combinations the heuristic wasn't designed for. For the demo
scenario specifically, DSPy is what drives the CONFIRMED advisory
to fire.

---

**Q: If TriageAgent is rule-based and health checks are rule-based, what's actually agentic about this?**

A: The agent decides which advisory to generate and when —
preliminary vs confirmed vs resolution — based on live state it
reads from multiple tool outputs each cycle. It also handles
ambiguity: when three alerts arrive in one cycle, the LLM
correctly maps each to the right incident rather than a hardcoded
sequential processor doing it mechanically. The agentic value is
context-sensitive coordination across tools, not replacing
deterministic components that should be deterministic.

---

**Q: Why use DSPy for correlation instead of fine-tuning like the other two agents?**

A: Correlation requires multi-step reasoning over a cluster of
alerts plus a topology graph — better fit for chain-of-thought
prompting and DSPy optimization than SFT on input-output pairs.
Fine-tuning works well for format learning (normalization) and
style learning (advisory text). Reasoning over structured
evidence is where DSPy compiled programs add more value.

---

## THEME 2: Architecture decisions

**Q: Why SQLite? A real NOC system would need a proper database.**

A: In-memory SQLite is the right choice for a demo that runs as
a single process for 10-15 minutes. For production, the
IncidentStore abstraction already has both sync and async methods
— swapping the backend to PostgreSQL or Redis doesn't touch any
agent code. The abstraction was deliberately designed for this.

---

**Q: You fine-tuned on 200 and 80 examples. Isn't that too small to generalize?**

A: For the specific task — normalizing alerts into a canonical
schema and generating NOC advisory text — these datasets are
domain-complete. The schema has fixed fields; the advisory format
has a fixed structure. You don't need millions of examples to
learn a consistent format. The 80.9% and 94.2% accuracy numbers
reflect that the tasks are well-bounded.

---

**Q: What does RLVR add over SFT for the communications agent?**

A: SFT teaches the model to mimic training examples. RLVR
additionally rewards outputs that satisfy specific NOC advisory
criteria — correct severity labeling, correct service
attribution, actionable remediation steps — even when the exact
wording differs from training data. It reduced mode instability
in advisory generation.

---

**Q: How does the topology graph work? Who maintains it?**

A: It is a JSON file (otel_demo_graph.json) with directed edges:
feeds_into and depends_on for each service. For the OTel demo it
was hand-crafted. In a real deployment this would be generated
from service mesh telemetry or a CMDB. The graph drives two
things: triage routing (are two devices related?) and correlation
context (what depends on what?).

---

## THEME 3: Reliability and robustness

**Q: What happens if the LLM doesn't follow the 6-step instruction?**

A: We saw this during development. The solution was to move
invariants out of the prompt and into code — the advisory guard
in communications_tools.py, the duplicate incident guard in
correlation_tools.py, and the device relabeling in
prometheus_mcp.py. The LLM can go off-script; the tools enforce
correct behavior regardless. That is one of the key lessons from
the project.

---

**Q: What if the SV cluster LLM endpoint goes down?**

A: DSPyCorrelator falls back to BaselineCorrelator — the
rule-based heuristic. CommunicationsAgent falls back to Ollama
qwen3:8b locally. The system degrades gracefully: confidence
scores revert to 0.55 and advisory text becomes more generic,
but the pipeline keeps running.

---

**Q: How do you handle false positives — alerts that fire when nothing is actually wrong?**

A: The ad service crash-loop in the demo is exactly this. The
fix was to relabel those alerts at the Prometheus ingestion layer
— device=ad instead of device=frontend — so the topology graph
correctly isolates them from the valkey-cart cascade. In a real
system this would be handled by alert threshold tuning and
topology-aware filtering at the MCP tool layer.

---

## THEME 4: Real-world applicability

**Q: Your detection takes 60-90 seconds. A real NOC needs faster than that.**

A: The 60-90 seconds is driven by Prometheus's 5-minute rate
window in the breach queries. Reducing that window to 1 minute
brings detection under 90 seconds for latency-based signals. For
container-down events, the up{job=~"opentelemetry-demo/.*"} == 0
query fires within one scrape interval — 15 seconds. This is a
configuration choice, not an architectural constraint.

---

**Q: How does this scale beyond 25 OTel demo services?**

A: The three scaling points are: the topology graph (grows with
services but is static), the SQLite store (in-memory; production
would use a persistent backend), and the Prometheus queries
(adding new service metrics means adding PromQL queries to
prometheus_mcp.py). The agent pipeline itself is service-count
agnostic — it processes whatever alerts Prometheus returns.

---

**Q: What is the MTTR improvement?**

A: We have not measured this against a baseline in the OTel demo
environment. What we can say: the system goes from fault
injection to CONFIRMED root cause advisory in 2-3 minutes. Human
L1 triage for a 7-service cascade is typically 15-30 minutes
based on industry benchmarks.

---

## THEME 5: Demo specifics

**Q: The ad service is crash-looping in the background. Doesn't that undermine confidence in the demo?**

A: It actually demonstrates the system's noise isolation
capability. The ad crash-loop generates persistent frontend 500
errors. The system correctly attributes these to the ad service
— not frontend — and keeps them in a separate incident that does
not contaminate the valkey-cart cascade story. A system that only
works in a noise-free environment is not production-ready.

---

**Q: What would you do differently next time?**

A: Choose the agentic framework first, design state management
from day one, establish the baseline before fine-tuning, and run
the demo scenario weekly during development to catch integration
issues early. See Slide 9 for the full list.

---

## ONE-LINE ANSWERS (if time is short)

**"Is it really agentic or just a pipeline?"**
The LLM coordinates; the specialist tools decide. That is the
correct division of responsibility.

**"Why not just use a rules engine for all of it?"**
Rules cannot generate natural language advisories or calibrate
confidence from evidence. LLM handles what rules cannot; rules
handle what LLMs should not.

**"What is the most impressive technical result?"**
The system correctly separates two concurrent failure modes —
ad noise and valkey-cart cascade — using topology graph
isolation. That is not trivial.

---

*Ground truth: docs/REMINDERS.md, CONTEXT.md, scripts/run_demo_adk.py*
*Test suite: 299 tests as of May 20 2026*
*Demo host: gho-gpu-vm | OTel stack: gho-vm-1*

---
