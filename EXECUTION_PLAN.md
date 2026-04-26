# NOC Whisperer — Execution Plan

> One Cursor session per day. One file per session.
> Start every session with: `@CONTEXT.md @EXECUTION_PLAN.md`
> Then state: `Today is Session N. <task description>`
> Model: Claude Sonnet 4.6 for all code generation.
> Switch to Opus 4.7 only when Sonnet is genuinely stuck.

---

## Time Budget

```
Weekdays:  1 hour/day
Weekends:  2-3 hours/day
Total:     ~38 hours across 4 weeks
```

---

## How To Use This File In Cursor

```
Test scope rules by session type:
   Data prep scripts:    functional-but-light (max 5 examples)
   GPU training scripts: import + config validation only
   DSPy optimization:    config validation + mock-based only
   Agent/pipeline code:  full functional with mock MCP tools

Step 1: Open noc_whisperer/ workspace in Cursor
Step 2: New chat — model = Claude Sonnet 4.6
Step 3: Type exactly:
        @CONTEXT.md @EXECUTION_PLAN.md
        Today is Session N. [copy task description below]
Step 4: Cursor generates code
Step 5: Run pytest
        python3 -m pytest tests/test_<session_file>.py -v
        All tests must pass before committing
Step 6: Commit BOTH the implementation and the test file
        git add <module_file> tests/test_<module_file>
        git commit -m "feat: <description> + tests"
Step 7: Close session

Note: Never modify CONTEXT.md or EXECUTION_PLAN.md
      during implementation sessions.
```

---

## WEEK 13 — Foundation (Sun Apr 26–Sat May 2)

**Goal:** Data pipeline working. All 4 MCP tools independently testable. No agents yet.

---

### Session 1 — Fri Apr 24 — 1 hour
**Task:** Project scaffold + requirements + .cursorrules

```
Files to create:
  requirements.txt
  .gitignore
  .env.example
  .cursorrules
  README.md
  All empty __init__.py files for each package directory

.cursorrules content:
  "This project is NOC Whisperer. Always read @CONTEXT.md
   before writing any code. One file per session.
   Use mock MCP tools during development."

.env.example content:
  OPENAI_API_KEY=your-key-here
  ANTHROPIC_API_KEY=your-key-here
  ENVIRONMENT=development
  RECONCILER_MODE=demo

Acceptance test:
  Directory structure matches CONTEXT.md exactly.
  pip install -r requirements.txt succeeds.
  git init && git add . && git commit -m "Session 1: scaffold"
```

---

### Session 2 — Sat Apr 25 — 1 hour
**Task:** `adapters/canonical_alert.py` + `adapters/synthetic_adapter.py` + `config/thresholds.yaml`

```
Files to create:
  adapters/__init__.py
  adapters/canonical_alert.py
  adapters/synthetic_adapter.py
  config/thresholds.yaml

Must contain exactly three dataclasses:
  CanonicalAlert  — all fields as specified in CONTEXT.md
  TriageDecision  — all fields as specified in CONTEXT.md
  Incident        — all fields as specified in CONTEXT.md

Requirements:
  - Use Python dataclasses with type hints
  - All fields must have docstring comments
  - Include __post_init__ validation:
      domain must be in {infrastructure, service_mesh, application}
      severity must be in {critical, major, minor, warning}
      status must be in {open, resolved}
  - Include a to_dict() method on each dataclass
  - Include a from_dict() classmethod on each dataclass
  - Add `SyntheticAdapter` stub in `adapters/synthetic_adapter.py`:
      class SyntheticAdapter
      to_canonical(raw_dict: dict) -> CanonicalAlert
      (returns hardcoded test CanonicalAlert for now)
  - Set `config/thresholds.yaml` values exactly:
      compute.cpu_utilization_percent critical/major/minor = 90.0/80.0/70.0
      compute.memory_available_mb critical/major/minor = 500/1000/2000
      storage.disk_used_percent critical/major/minor = 90.0/80.0/70.0
      service_mesh.http_error_rate_per_min critical/major/minor = 20/10/5

Acceptance test:
  python -c "from adapters.canonical_alert import CanonicalAlert,
             TriageDecision, Incident; print('OK')"
  python -c "from adapters.synthetic_adapter import SyntheticAdapter; print('OK')"
  test -f config/thresholds.yaml
```

---

### Session 3 — Sat Apr 25 — 1 hour
**Task:** `topology/otel_demo_graph.json` + `mcp_tools/topology_mcp.py`

```
Files to create:
  topology/otel_demo_graph.json
  mcp_tools/__init__.py
  mcp_tools/topology_mcp.py
  mcp_tools/mocks/__init__.py
  mcp_tools/mocks/mock_topology_mcp.py

otel_demo_graph.json structure:
  {
    "device_name": {
      "type": "cache|database|business|infrastructure|message_queue",
      "domain": "infrastructure|service_mesh|application",
      "feeds_into": ["service1", "service2"],
      "depends_on": ["service3"],
      "criticality": "high|medium|low"
    }
  }
  Include all services from CONTEXT.md topology section.

topology_mcp.py must implement:
  get_downstream(device) -> List[str]
  get_upstream(device) -> List[str]
  are_related(device_a, device_b) -> bool  # BFS both directions
  get_cascade_chain(root_device) -> List[str]  # BFS downstream
  get_topology_context(devices) -> dict

mock_topology_mcp.py:
  Same interface. Returns hardcoded data for Valkey cascade scenario.
  are_related("valkey-cart", "cart") = True
  are_related("valkey-cart", "checkout") = True  (transitive)
  are_related("valkey-cart", "kafka") = False
  get_cascade_chain("valkey-cart") = ["valkey-cart", "cart",
                                       "checkout", "frontend",
                                       "frontend-proxy"]

Acceptance test:
  test_get_downstream_valkey_cart()
  test_get_upstream_cart()
  test_are_related_direct()
  test_are_related_transitive()
  test_are_related_unrelated()
  test_cascade_chain_valkey_cart()
  test_topology_context_returns_dict()
  test_mock_topology_mcp()
```

---

### Session 4 — Sat Apr 25 — Part 1 + Part 2
**Task:** `generator/fault_scenarios.py`

```
Files to create:
  generator/__init__.py
  generator/fault_scenarios.py

Must define:
  FaultScenario dataclass with fields:
    scenario_id: str
    name: str
    initiating_fault_domain: str
    initiating_fault_type: str
    initiating_device: str
    cascade_chain: List[str]
    alert_templates: List[dict]
    temporal_pattern: str  # simultaneous|sequential|gradual|
                           # sudden_at_time_boundary|gradual_then_sudden
    noise_alert_domains: List[str]
    ground_truth: dict

  ALL_SCENARIOS: List[FaultScenario]
    — All 12 scenarios from CONTEXT.md fully instantiated
    — Each alert_template dict has keys:
        domain, severity, device, metric, message_template, value_range

  VALKEY_CART_CASCADE_SCENARIO: FaultScenario
    — Scenario 1 — the primary demo scenario
    — Fully detailed with 7-8 alert templates
    — ground_truth: {root_cause_device: "valkey-cart",
                     initiating_domain: "infrastructure",
                     affected_services: ["cart", "checkout",
                                         "frontend", "frontend-proxy"],
                     cascade_type: "load_amplification",
                     correlation_window_seconds: 120}
  Device names in all alert_templates must exactly match keys in
  topology/otel_demo_graph.json. Valid names: valkey-cart, cart,
  checkout, frontend, frontend-proxy, payment, product-catalog,
  kafka, accounting, fraud-detection, shipping, currency, email,
  recommendation, ad, image-provider, flagd, quote

Acceptance test:
  from generator.fault_scenarios import ALL_SCENARIOS, VALKEY_CART_CASCADE_SCENARIO
  assert len(ALL_SCENARIOS) == 12
  assert VALKEY_CART_CASCADE_SCENARIO.ground_truth["root_cause_device"] == "valkey-cart"
  print("Fault scenarios OK")
```

---

### Session 5 — Sun Apr 26 — 1.5 hours
**Task:** `generator/synthetic_generator.py`

```
Files to create:
  generator/synthetic_generator.py

Must implement:
  class ScenarioDrivenGenerator:

    def generate_storm(
        self,
        scenario: FaultScenario,
        noise_ratio: float = 0.3,
        base_time: datetime = None
    ) -> dict:
      # Returns: {
      #   "alerts": List[CanonicalAlert],  # sorted by timestamp
      #   "ground_truth": dict,
      #   "scenario_name": str,
      #   "incident_id": str  # UUID embedded in all non-noise alerts
      # }

    def generate_dataset(
        self,
        num_incidents: int,
        noise_ratio: float,
        scenarios: List[FaultScenario] = None,  # default ALL_SCENARIOS
        random_seed: int = 42
    ) -> List[dict]:
      # Returns list of storms

    def _apply_temporal_pattern(
        self,
        base_time: datetime,
        alert_index: int,
        pattern: str
    ) -> datetime:
      # Implements all 5 temporal patterns

    def _generate_noise_alert(self, base_time: datetime) -> CanonicalAlert:
      # Random alert unrelated to the scenario
      # Different device, plausible but unrelated metric

Requirements:
  - Set random.seed(random_seed) before any generation
  - Noise alerts have incident_id = None
  - Correlated alerts share the same incident_id (UUID)
  - Timing jitter: add random.randint(0, 30) seconds to each alert
  - Device names must match topology/otel_demo_graph.json keys

Acceptance test:
  from generator.synthetic_generator import ScenarioDrivenGenerator
  from generator.fault_scenarios import VALKEY_CART_CASCADE_SCENARIO
  gen = ScenarioDrivenGenerator()
  storm = gen.generate_storm(VALKEY_CART_CASCADE_SCENARIO, noise_ratio=0.3)
  assert len(storm["alerts"]) >= 7
  assert storm["ground_truth"]["root_cause_device"] == "valkey-cart"
  correlated = [a for a in storm["alerts"] if a.incident_id is not None]
  assert len(correlated) >= 7
  print("Generator OK")
```

---

### Session 6 — Sun Apr 26 — 1 hour
**Task:** `scripts/generate_training_data.py` — run `.venv/bin/python3 scripts/generate_training_data.py` — commit data/

```
Files to create:
  scripts/__init__.py
  scripts/generate_training_data.py

Script must:
  1. Import ScenarioDrivenGenerator and ALL_SCENARIOS
  2. Set random seed = 42 (FIXED — never change)
  3. Generate train split: 100 incidents, noise_ratio=0.3
  4. Generate val split:   30  incidents, noise_ratio=0.3
  5. Generate test split:  20  incidents, noise_ratio=0.4
  6. Save each to data/train.json, data/val.json, data/test.json
  7. Print summary:
       "Train: 100 incidents, 4123 total alerts"
       "Val:   30  incidents, 1244 total alerts"
       "Test:  20  incidents, 856  total alerts"
  8. Verify ground truth is present in every incident

After generation:
  Add data/ to .gitignore
  Commit the script but NOT the data files

Acceptance test:
  .venv/bin/python3 scripts/generate_training_data.py
  # Must complete without errors
  # Must print summary
  import json
  train = json.load(open("data/train.json"))
  assert len(train) == 100
  assert "ground_truth" in train[0]
  assert "alerts" in train[0]
  print("Dataset generation OK")
```

---

### Session 7 — TBD (deferred — OTel VM setup)
**Task:** Clone and verify OpenTelemetry demo stack

```
CRITICAL PATH: Session 7 must be completed before Session 24.
Session 24 (integration testing) is scheduled for Sat May 10.
Session 7 (OTel VM setup) must be done by Fri May 9 at latest.
If corporate VM Docker access is not confirmed by Sun May 3,
immediately provision a cloud VM as backup:
  AWS t3.xlarge (16GB) or Digital Ocean 8GB Droplet or Hetzner CX31
  Estimated cost: $5-15 for two weeks
  Required ports: 9090, 16686, 9100, 3000, 8080
Do not let VM access delay block the demo.

This session produces NO code files.
It is a pure environment setup session.
The only commit is a notes file.

Steps (run in terminal — NOT inside noc_whisperer/ directory):

  1. Clone OTel demo OUTSIDE the noc_whisperer project:
       cd ~
       git clone https://github.com/open-telemetry/opentelemetry-demo
       cd opentelemetry-demo

  2. Add Node Exporter to docker-compose.yml under services::
       node-exporter:
         image: prom/node-exporter:latest
         ports:
           - "9100:9100"
         volumes:
           - /proc:/host/proc:ro
           - /sys:/host/sys:ro
         command:
           - '--path.procfs=/host/proc'
           - '--path.sysfs=/host/sys'

  3. Start the stack:
       docker compose up -d
       # Wait 3-5 minutes for all services to stabilize

  4. Verify all three backends respond:
       curl http://localhost:9090/api/v1/query?query=up
       curl http://localhost:16686/api/services
       curl http://localhost:9100/metrics | head -20

  5. Verify valkey-cart is running:
       docker compose ps | grep valkey

  6. Test the demo failure scenario once:
       docker compose stop valkey-cart
       # Wait 30 seconds
       curl http://localhost:9090/api/v1/query?query=up
       docker compose start valkey-cart
       # Verify valkey-cart recovers

  7. Back inside noc_whisperer/ — create docs/otel_setup_notes.md:
     Document:
       - docker compose ps output
       - Which ports confirmed active
       - OTel demo directory path on your machine
       - Any issues encountered and how resolved
       - Confirmation valkey-cart stop/start cycle works

Acceptance criteria:
  □ All three curl commands return valid responses
  □ valkey-cart appears in docker compose ps
  □ valkey-cart stop/start cycle completes without errors
  □ docs/otel_setup_notes.md exists and is committed

Commit (from inside noc_whisperer/):
  git add docs/otel_setup_notes.md
  git commit -m "infra: OTel demo stack verified — valkey-cart cascade confirmed"

Note: OTel demo directory lives OUTSIDE noc_whisperer/.
Never clone it inside the project directory.
Sessions 8 onward assume localhost:9090, localhost:16686,
and localhost:9100 are always available.
```

---

### Session 8 — Sun Apr 26 — 1 hour
**Task:** `mcp_tools/prometheus_mcp.py` + `mcp_tools/mocks/mock_prometheus_mcp.py`

Files to create:
  mcp_tools/prometheus_mcp.py
  mcp_tools/mocks/mock_prometheus_mcp.py

prometheus_mcp.py must implement:
  class PrometheusMCP:
    def __init__(self, base_url: str, thresholds_path: str = "config/thresholds.yaml"):
      # Load thresholds from yaml
      # Store base_url

    def get_threshold_breaches(self) -> List[CanonicalAlert]:
      # Query Prometheus API for metric threshold breaches
      # Queries:
      #   rate(http_server_duration_milliseconds_count{status_code=~"5.."}[1m]) > 0.1
      #   valkey_cache_miss_ratio > 0.9
      #   cart_connections_active / cart_connections_max > 0.9
      # Returns List[CanonicalAlert] — empty list on connection failure

    def query(self, promql: str) -> dict:
      # GET {base_url}/api/v1/query?query={promql}
      # Returns raw API response dict
      # Returns {} on connection failure

    def get_alerts_since(self, seconds: int = 30) -> List[CanonicalAlert]:
      # Query for alerts fired in last N seconds
      # Returns List[CanonicalAlert]

    def health_check(self) -> bool:
      # GET {base_url}/api/v1/query?query=up
      # Returns True if response is valid, False otherwise

    def _to_canonical(self, metric_result: dict) -> CanonicalAlert:
      # Convert Prometheus metric result to CanonicalAlert
      # Load severity from thresholds.yaml
      # domain = "service_mesh"
      # source_system = "prometheus"

mock_prometheus_mcp.py must implement:
  class MockPrometheusMCP:
    def __init__(self, scenario_alerts: List[CanonicalAlert] = None):
      self.scenario_alerts = scenario_alerts or []

    def get_threshold_breaches(self) -> List[CanonicalAlert]:
      return self.scenario_alerts

    def query(self, promql: str) -> dict:
      return {"status": "success", "data": {"result": []}}

    def get_alerts_since(self, seconds: int = 30) -> List[CanonicalAlert]:
      return self.scenario_alerts

    def health_check(self) -> bool:
      return True

Acceptance test — tests/test_prometheus_mcp.py:
  test_import()
  test_mock_returns_empty_by_default()
  test_mock_returns_injected_alerts()
  test_mock_health_check_true()
  test_mock_get_alerts_since()
  test_live_health_check_fails_gracefully()
    # With base_url="http://localhost:1", health_check() must return False
    # Must not raise an exception
  test_live_get_threshold_breaches_fails_gracefully()
    # With base_url="http://localhost:1", get_threshold_breaches() must return []
    # Must not raise an exception

Run: .venv/bin/python3 -m pytest tests/test_prometheus_mcp.py -v
All 7 tests must pass.
Run: .venv/bin/python3 -m pytest tests/ -v
Full suite must pass.

Commit: "feat: prometheus MCP tool + mock + tests"

---

### Session 9 — Sun Apr 26 — 1 hour
**Task:** `mcp_tools/jaeger_mcp.py` + `mcp_tools/mocks/mock_jaeger_mcp.py`

Files to create:
  mcp_tools/jaeger_mcp.py
  mcp_tools/mocks/mock_jaeger_mcp.py
  tests/test_jaeger_mcp.py

jaeger_mcp.py must implement:
  class JaegerMCP:
    def __init__(self, base_url: str):
      self.base_url = base_url

    def get_error_spans(self, since_seconds: int = 30) -> List[CanonicalAlert]:
      # GET {base_url}/api/traces?service=all&tags={"error":"true"}
      #     &lookback={since_seconds}s&limit=100
      # Convert error spans to CanonicalAlert
      # domain = "application"
      # source_system = "jaeger"
      # Returns [] on connection failure

    def health_check(self) -> bool:
      # GET {base_url}/api/services
      # Returns True if valid response, False otherwise

    def _span_to_canonical(self, span: dict) -> CanonicalAlert:
      # Convert Jaeger span to CanonicalAlert
      # Extract: service name → device
      # Extract: error type → metric
      # severity = "major" for error spans
      # domain = "application"

mock_jaeger_mcp.py must implement:
  class MockJaegerMCP:
    def __init__(self, scenario_alerts: List[CanonicalAlert] = None):
      self.scenario_alerts = scenario_alerts or []

    def get_error_spans(self, since_seconds: int = 30) -> List[CanonicalAlert]:
      return self.scenario_alerts

    def health_check(self) -> bool:
      return True

Acceptance test — tests/test_jaeger_mcp.py:
  test_import()
  test_mock_returns_empty_by_default()
  test_mock_returns_injected_alerts()
  test_mock_health_check_true()
  test_live_health_check_fails_gracefully()
    # base_url="http://localhost:1" must return False not raise
  test_live_get_error_spans_fails_gracefully()
    # base_url="http://localhost:1" must return [] not raise

Run: .venv/bin/python3 -m pytest tests/test_jaeger_mcp.py -v
All 6 tests must pass.
Run: .venv/bin/python3 -m pytest tests/ -v
Full suite must pass.

Commit: "feat: jaeger MCP tool + mock + tests"

---

### Session 10 — Mon Apr 27 — 1 hour
**Task:** `mcp_tools/node_exporter_mcp.py` + `mcp_tools/mocks/mock_node_exporter_mcp.py`

Files to create:
  mcp_tools/node_exporter_mcp.py
  mcp_tools/mocks/mock_node_exporter_mcp.py
  tests/test_node_exporter_mcp.py

node_exporter_mcp.py must implement:
  class NodeExporterMCP:
    def __init__(self, prometheus_base_url: str,
                 thresholds_path: str = "config/thresholds.yaml"):
      # Node Exporter metrics are scraped via Prometheus
      # Store prometheus_base_url
      # Load thresholds from yaml

    def get_host_alerts(self) -> List[CanonicalAlert]:
      # Query Prometheus for Node Exporter metrics:
      #   CPU:    100-(avg(rate(node_cpu_seconds_total{mode="idle"}[2m]))*100) > 90
      #   Memory: node_memory_MemAvailable_bytes < 524288000
      #   Disk:   (node_filesystem_size_bytes-node_filesystem_free_bytes)
      #             /node_filesystem_size_bytes > 0.90
      # domain = "infrastructure"
      # source_system = "node_exporter"
      # Returns [] on connection failure

    def health_check(self) -> bool:
      # Query Prometheus for node_exporter up metric:
      #   up{job="node"} == 1
      # Returns True if result non-empty, False otherwise

    def _to_canonical(self, metric_result: dict,
                      metric_name: str) -> CanonicalAlert:
      # Convert Node Exporter metric to CanonicalAlert
      # domain = "infrastructure"
      # Load severity from thresholds.yaml

mock_node_exporter_mcp.py must implement:
  class MockNodeExporterMCP:
    def __init__(self, scenario_alerts: List[CanonicalAlert] = None):
      self.scenario_alerts = scenario_alerts or []

    def get_host_alerts(self) -> List[CanonicalAlert]:
      return self.scenario_alerts

    def health_check(self) -> bool:
      return True

Acceptance test — tests/test_node_exporter_mcp.py:
  test_import()
  test_mock_returns_empty_by_default()
  test_mock_returns_injected_alerts()
  test_mock_health_check_true()
  test_live_health_check_fails_gracefully()
    # prometheus_base_url="http://localhost:1" must return False not raise
  test_live_get_host_alerts_fails_gracefully()
    # prometheus_base_url="http://localhost:1" must return [] not raise

Run: .venv/bin/python3 -m pytest tests/test_node_exporter_mcp.py -v
All 6 tests must pass.
Run: .venv/bin/python3 -m pytest tests/ -v
Full suite must pass.

Commit: "feat: node exporter MCP tool + mock + tests"

---

## WEEK 14 — Models and Agents (Sun May 3–Sat May 9)

**Goal:** Both fine-tuned models locked. All five agents implemented. Pipeline wired.

---

### Session 11 — Tue Apr 28 — 1 hour
**Task:** `scripts/prepare_normalizer_sft.py`

```
Files to create:
  scripts/prepare_normalizer_sft.py
  tests/test_prepare_normalizer_sft.py

Script must:
  1. Load data/train.json
  2. For each alert in each incident:
     - Format as (prompt, completion) pair
     - Prompt: "Raw metric event from {source_system}:\n{json.dumps(alert_fields)}\n
                Classify domain and severity."
     - Completion: "domain: {domain}\nseverity: {severity}\n
                    reasoning: {reason}\nconfidence: {confidence}"
  3. Generate 200 examples total
     (sample from training alerts, weight toward ambiguous cases)
  4. Save to data/normalizer_sft_train.jsonl (one JSON per line)
  5. Print: "Generated 200 SFT examples"

Spot-check requirement:
  Print 3 random examples to stdout for manual review.

Acceptance test:
  python scripts/prepare_normalizer_sft.py
  # Verify 200 lines in output file
  wc -l data/normalizer_sft_train.jsonl  # should print 200
```

---

### Session 12 — Wed Apr 29 — 1 hour
**Task:** `scripts/train_normalizer_sft.py` — submit to GPU

```
Files to create:
  scripts/train_normalizer_sft.py
  tests/test_train_normalizer_sft.py

tests/test_train_normalizer_sft.py:
  Import and config validation only — no GPU execution.
  Tests must verify:
    - Script imports without error
    - LoRA config object is constructed correctly
    - SFTConfig parameters match CONTEXT.md specs
    - Output path is correctly configured
    - Script has if __name__ == '__main__' guard
  Tests must NOT execute any training.

Script must:
  1. Load Qwen/Qwen2.5-7B-Instruct with LoRA config from CONTEXT.md
  2. Load data/normalizer_sft_train.jsonl
  3. Run SFTTrainer with config from CONTEXT.md
  4. Log loss per epoch to logs/normalizer_sft_loss.txt
  5. Save to checkpoints/normalizer_sft_final/
  6. Print: "SFT training complete. Loss: {final_loss}"

Requires GPU. Submit as background job:
  nohup python scripts/train_normalizer_sft.py > logs/normalizer_sft.log 2>&1 &
  echo $! > pids/normalizer_sft.pid

While job runs: write agents/normalizer_agent.py (stub version)

normalizer_agent.py stub:
  - load_model(model_path) — loads from path or Ollama if path doesn't exist
  - process(raw_payload, source_system) -> CanonicalAlert
  - Uses Ollama/llama3.1:8b if model not yet trained
  - Switches to fine-tuned model when models/normalizer_final_locked exists

Acceptance test (stub):
  from agents.normalizer_agent import NormalizerAgent
  agent = NormalizerAgent(model_path=None)  # uses Ollama
  # Verify import succeeds
  print("Normalizer agent stub OK")
```

---

### Session 13 — Thu Apr 30 — 1 hour
**Task:** Check SFT results + `agents/triage_agent.py`

```
Morning check:
  cat logs/normalizer_sft.log | tail -20
  # Verify: loss decreasing, no OOM errors, checkpoint saved

Files to create:
  agents/__init__.py
  agents/triage_agent.py
  tests/test_triage_agent.py

triage_agent.py must implement:
  class TriageAgent:
    def __init__(self, topology_mcp, incident_store):
      self.topology = topology_mcp
      self.store = incident_store
      self.time_window_seconds = 300

    def route(self, alert: CanonicalAlert) -> TriageDecision:
      # 1. Get open incidents from store
      # 2. For each: check temporal + topological proximity
      # 3. Return TriageDecision

    def _is_temporally_proximate(
        self, alert: CanonicalAlert, incident: Incident
    ) -> bool:
      # alert.timestamp within self.time_window_seconds of incident.updated_at

    def _is_topologically_proximate(
        self, alert: CanonicalAlert, incident: Incident
    ) -> bool:
      # topology_mcp.are_related(alert.device, incident.root_cause_device)

Acceptance test:
  from agents.triage_agent import TriageAgent
  from mcp_tools.mocks.mock_topology_mcp import MockTopologyMCP
  # Create mock incident store with one open incident
  # Feed related alert — should get action="append"
  # Feed unrelated alert — should get action="new"
  print("Triage agent tests passed")
```

---

### Session 14 — Fri May 1 — 1 hour
**Task:** `scripts/train_normalizer_rlvr.py` — submit + `dspy_programs/alerts_to_incident.py`

```
Files to create:
  scripts/train_normalizer_rlvr.py
  dspy_programs/__init__.py
  dspy_programs/alerts_to_incident.py
  tests/test_alerts_to_incident.py

train_normalizer_rlvr.py must:
  1. Load from checkpoints/normalizer_sft_final (warm start)
  2. Implement normalizer_reward() from CONTEXT.md exactly
  3. Run GRPOTrainer: G=8, 2 epochs
  4. Log reward per epoch to logs/normalizer_rlvr_rewards.txt
  5. Save to models/normalizer_final_locked/
  6. Print baseline accuracy, final accuracy, delta

Submit as background job (same pattern as Session 9)

alerts_to_incident.py must:
  - Define AlertsToIncident signature (all fields from CONTEXT.md)
  - Implement baseline hand-written prompt (no DSPy optimization yet):
      class BaselineCorrelator:
        def predict(self, alert_cluster, topology_context) -> dict
        # Uses direct LLM call with hand-written prompt
        # Returns dict with all 5 output fields
  - Implement DSPy-based correlator (stub — loads compiled.json when available):
      class DSPyCorrelator:
        def predict(self, alert_cluster, topology_context) -> dict

Acceptance test:
  from dspy_programs.alerts_to_incident import AlertsToIncident
  import dspy
  prog = dspy.ChainOfThought(AlertsToIncident)
  print("DSPy signature OK")
```

---

### Session 15 — Sat May 2 — 1.5 hours
**Task:** Check RLVR results + lock model + `agents/correlation_agent.py`

```
Morning check:
  cat logs/normalizer_rlvr_rewards.log | tail -20
  # Record: baseline accuracy, SFT accuracy, RLVR accuracy
  # Write these numbers to docs/evaluation_results.md

Lock model:
  # Verify models/normalizer_final_locked/ exists
  # Add to .gitignore if not already there
  ls -la models/normalizer_final_locked/

Files to create:
  agents/correlation_agent.py
  tests/test_correlation_agent.py

correlation_agent.py must implement:
  class CorrelationAgent:
    def __init__(self, topology_mcp, incident_store,
                 window_seconds=180, mode="development"):
      self.topology = topology_mcp
      self.store = incident_store
      self.window = window_seconds
      self.alert_buffer = []  # sliding window — in memory
      self.correlator = self._load_correlator(mode)

    def correlate(self, decision: TriageDecision) -> Incident:
      # 1. Add alert to buffer, prune old alerts
      # 2. Assemble cluster (append or new mode)
      # 3. Get topology context
      # 4. Run DSPy program
      # 5. Return Incident

    def _assemble_cluster(self, decision: TriageDecision) -> List[CanonicalAlert]:
      # append: existing_incident.alerts + [new_alert]
      # new:    self.alert_buffer + [new_alert]

    def _load_correlator(self, mode: str):
      # development: BaselineCorrelator (Ollama)
      # production: DSPyCorrelator (compiled program)

Acceptance test:
  from agents.correlation_agent import CorrelationAgent
  from mcp_tools.mocks.mock_topology_mcp import MockTopologyMCP
  agent = CorrelationAgent(MockTopologyMCP(), mock_store, mode="development")
  # Feed a TriageDecision with action="new"
  # Verify returns an Incident with all fields populated
  print("Correlation agent OK")
```

---

### Session 16 — Sun May 3 — 1.5 hours
**Task:** `scripts/prepare_communications_sft.py` + `scripts/train_communications_sft.py`

```
Files to create:
  scripts/prepare_communications_sft.py
  scripts/train_communications_sft.py
  tests/test_prepare_communications_sft.py
  tests/test_train_communications_sft.py

tests/test_prepare_communications_sft.py:
  functional-but-light, 5 examples maximum
tests/test_train_communications_sft.py:
  import and config validation only — no GPU execution

prepare_communications_sft.py must:
  Generate 80 (incident, advisory) training pairs:
  - 40 preliminary advisories (incident confidence 0.50-0.84)
  - 40 confirmed advisories (incident confidence 0.85-1.00)

  Preliminary advisory template:
    NOC ADVISORY — {time} PST
    STATUS: PRELIMINARY — INVESTIGATING
    SUSPECTED: {root_cause_device} failure
    AFFECTED: {affected_services}
    CONFIDENCE: {confidence:.0%} — under investigation
    ACTION: Monitor {primary_affected_service} error rates
    Next update: 60 seconds

  Confirmed advisory template:
    NOC ADVISORY — {time} PST
    INCIDENT: {incident_title}
    ROOT CAUSE: {root_cause_device} confirmed
    AFFECTED: {affected_services}
    SEVERITY: {severity} — {duration} minutes duration
    ACTION REQUIRED:
      NOC L2: {recommended_action}
      Platform: Monitor {primary_affected_service} recovery
    Next update: On status change

  Save to data/communications_sft_train.jsonl

train_communications_sft.py:
  Same pattern as train_normalizer_sft.py
  Output: checkpoints/communications_sft_final/
  Submit as background job

Acceptance test:
  python scripts/prepare_communications_sft.py
  wc -l data/communications_sft_train.jsonl  # should print 80
```

---

### Session 17 — Sun May 3 — 1 hour
**Task:** `orchestrator/incident_store.py`

```
Files to create:
  orchestrator/__init__.py
  orchestrator/incident_store.py
  tests/test_incident_store.py

incident_store.py must implement:
  class IncidentStore:
    def __init__(self, db_path: str = "incidents.db"):
      # Initialize SQLite connection
      # Create tables if not exist
      # Use asyncio.Lock for thread safety

    async def upsert(self, incident: Incident) -> None:
      # Insert or replace incident
      # Serialize alerts list to JSON

    def get_open_incidents(self) -> List[Incident]:
      # Return all incidents with status="open"

    def get_incident(self, incident_id: str) -> Optional[Incident]:
      # Return specific incident by ID

    async def mark_advisory_sent(
        self, incident_id: str, advisory_type: str
    ) -> None:
      # advisory_type: "preliminary" | "confirmed"
      # Set the appropriate boolean flag

    def get_recent_resolved(self, hours: int = 24) -> List[Incident]:
      # Return incidents resolved in last N hours
      # Used by Reconciler for pattern matching

Schema:
  CREATE TABLE IF NOT EXISTS incidents (
    incident_id TEXT PRIMARY KEY,
    created_at TEXT,
    updated_at TEXT,
    status TEXT,
    root_cause_device TEXT,
    incident_title TEXT,
    affected_services TEXT,  -- JSON array
    confidence REAL,
    recommended_action TEXT,
    alerts TEXT,             -- JSON array of CanonicalAlert dicts
    preliminary_advisory_sent INTEGER DEFAULT 0,
    confirmed_advisory_sent INTEGER DEFAULT 0
  )

Acceptance test:
  import asyncio
  from orchestrator.incident_store import IncidentStore
  store = IncidentStore(":memory:")  # in-memory for testing
  # Create a test incident, upsert it, retrieve it
  # Verify all fields round-trip correctly
  print("Incident store OK")
```

---

### Session 18 — Mon May 4 — 1 hour
**Task:** Check Communications SFT + `scripts/train_communications_rlvr.py`

```
Morning check:
  cat logs/communications_sft.log | tail -20
  # Verify checkpoint saved

Files to create:
  scripts/train_communications_rlvr.py
  tests/test_train_communications_rlvr.py

tests/test_train_communications_rlvr.py:
  Import and config validation only — no GPU execution.
  Tests must verify:
    - Script imports without error
    - advisory_reward() function exists and returns float in [0,1]
    - GRPOConfig parameters match CONTEXT.md specs (G=8)
    - Reward function returns 1.0 for a perfect advisory
    - Reward function returns 0.0 for an empty string
    - Script has if __name__ == '__main__' guard
  Tests must NOT execute any GRPO training.

Must:
  1. Load from checkpoints/communications_sft_final (warm start)
  2. Implement advisory_reward() from CONTEXT.md exactly
     (include KNOWN_SERVICES list from CONTEXT.md)
  3. Run GRPOTrainer: G=8, 2 epochs
  4. Log reward per epoch
  5. Save to models/communications_final_locked/
  6. Print baseline compliance, final compliance, delta

Submit as background job.

Also create: communications/__init__.py
             communications/communications_agent.py (stub)

communications_agent.py stub:
  class CommunicationsAgent:
    def __init__(self, model_path=None):
      # Load locked model or Ollama fallback

    def generate(self, incident: Incident,
                 advisory_type: str = "preliminary") -> str:
      # Format prompt with incident fields
      # Run inference
      # Return advisory string

    def _format_prompt(self, incident: Incident,
                       advisory_type: str) -> str:
      # preliminary: emphasize "investigating", "suspected"
      # confirmed: emphasize "confirmed", imperative actions

Acceptance test:
  from communications.communications_agent import CommunicationsAgent
  agent = CommunicationsAgent(model_path=None)  # Ollama fallback
  print("Communications agent stub OK")
```

---

### Session 19 — Tue May 5 — 1 hour
**Task:** `orchestrator/streaming_pipeline.py`

```
Files to create:
  orchestrator/streaming_pipeline.py
  tests/test_streaming_pipeline.py

Must implement:
  class StreamingPipeline:
    def __init__(self, mcp_tools, normalizer, triage,
                 correlation, communications, incident_store, dashboard):
      self.mcp_tools = mcp_tools  # list of 4 tools
      self.normalizer = normalizer
      self.triage = triage
      self.correlation = correlation
      self.communications = communications
      self.store = incident_store
      self.dashboard = dashboard
      self.seen_alert_ids = set()  # deduplication

    async def streaming_loop(self):
      while True:
        raw_alerts = []
        for tool in self.mcp_tools:
          raw_alerts.extend(tool.get_alerts())

        new_alerts = [a for a in raw_alerts
                      if a.alert_id not in self.seen_alert_ids]

        for alert in new_alerts:
          self.seen_alert_ids.add(alert.alert_id)
          await self.process_alert(alert)

        await asyncio.sleep(15)

    async def process_alert(self, raw_alert):
      canonical  = self.normalizer.process(raw_alert)
      decision   = self.triage.route(canonical)
      incident   = self.correlation.correlate(decision)
      await self.store.upsert(incident)
      self.dashboard.update_alert_stream(canonical)
      self.dashboard.update_incident_board(incident)
      await self.check_advisory_triggers(incident)

    async def check_advisory_triggers(self, incident: Incident):
      # Implement advisory trigger logic from CONTEXT.md exactly

Acceptance test:
  # Run streaming pipeline with all mock tools for 5 seconds
  # Feed valkey-cart cascade alerts via mock tools
  # Verify incidents appear in incident_store
  # Verify advisory fires when confidence threshold crossed
  print("Streaming pipeline OK")
```

---

## WEEK 15 — Integration and Optimization (Sun May 10–Sat May 16)

**Goal:** DSPy delta measured. Reconciler working. Full evaluation numbers in hand. Demo rehearsed.

---

### Session 20 — Wed May 6 — 1 hour
**Task:** `agents/reconciler_agent.py`

```
Files to create:
  agents/reconciler_agent.py
  tests/test_reconciler_agent.py

Must implement:
  @dataclass
  class ReconcilerDecision:
    action: str           # merge | split | close | keep
    primary_incident_id: str
    secondary_incident_id: Optional[str]  # for merge only
    reasoning: str

  class ReconcilerAgent:
    def __init__(self, topology_mcp, prometheus_mcp,
                 max_iterations: int = 3):

    def reconcile(
        self, open_incidents: List[Incident]
    ) -> List[ReconcilerDecision]:
      decisions = []
      for i, inc_a in enumerate(open_incidents):
        for inc_b in open_incidents[i+1:]:
          decision = self._evaluate_pair(inc_a, inc_b)
          if decision.action != "keep":
            decisions.append(decision)

      for incident in open_incidents:
        if self._should_close(incident):
          decisions.append(ReconcilerDecision(
            action="close",
            primary_incident_id=incident.incident_id,
            reasoning="No new alerts for 20 minutes"
          ))
      return decisions

    def _evaluate_pair(
        self, inc_a: Incident, inc_b: Incident
    ) -> ReconcilerDecision:
      # ReAct loop — max self.max_iterations iterations
      # THINK: are these the same root cause?
      # ACT: topology_mcp.are_related() + prometheus_mcp.query()
      # OBSERVE: evidence
      # DECIDE: merge | keep

    def _should_close(self, incident: Incident) -> bool:
      # No new alerts for close_inactivity_seconds (from config)

Acceptance test:
  # Two related incidents → should merge
  # Two unrelated incidents → should keep
  # Stale incident → should close
  print("Reconciler agent OK")
```

---

### Session 21 — Thu May 7 — 1 hour
**Task:** `orchestrator/master_orchestrator.py` + `orchestrator/batch_reconciler.py`

```
Files to create:
  orchestrator/batch_reconciler.py
  orchestrator/master_orchestrator.py
  tests/test_master_orchestrator.py

batch_reconciler.py must implement:
  class BatchReconciler:
    def __init__(self, reconciler_agent, communications_agent,
                 incident_store, dashboard, mode="demo"):
      self.interval = reconciler_config[mode]  # 30s or 900s

    async def batch_loop(self):
      while True:
        await asyncio.sleep(self.interval)
        open_incidents = self.store.get_open_incidents()
        decisions = self.reconciler.reconcile(open_incidents)
        for decision in decisions:
          await self._execute_decision(decision)

    async def _execute_decision(self, decision: ReconcilerDecision):
      # merge: combine alerts from both incidents, re-run correlation
      # split: create two new incidents from one
      # close: set status="resolved", set updated_at=now
      # After execution: check_advisory_triggers on updated incident

master_orchestrator.py must implement:
  class MasterOrchestrator:
    def __init__(self, streaming_pipeline, batch_reconciler):

    async def run(self):
      await asyncio.gather(
        self.streaming.streaming_loop(),
        self.batch.batch_loop()
      )

    def start(self):
      asyncio.run(self.run())

Acceptance test:
  # Run full orchestrator with all mocks for 35 seconds
  # Feed valkey-cart cascade alerts at T=0
  # Verify: incidents created by streaming at T~15s
  # Verify: reconciler fires at T~30s, merges incidents
  # Verify: confirmed advisory fires after merge
  print("Master orchestrator OK")
```

---

### Session 22 — Fri May 8 — 1 hour
**Task:** `scripts/optimize_dspy.py` — THE most important session of Week 15

```
Files to create:
  scripts/optimize_dspy.py
  tests/test_optimize_dspy.py

tests/test_optimize_dspy.py:
  Config validation and mock-based only — no live API calls.
  Tests must verify:
    - Script imports without error
    - root_cause_accuracy metric function exists
    - Metric returns True when prediction matches ground truth
    - Metric returns False when prediction does not match
    - Dataset loading function works with data/val.json
    - Script has if __name__ == '__main__' guard
  Tests must NOT make any OpenAI API calls.

Script must:
  1. Load val set: data/val.json (30 incidents)
  2. Configure DSPy LM:
       lm = dspy.OpenAI(model="gpt-4o-mini",
                        api_key=os.environ["OPENAI_API_KEY"])
       dspy.settings.configure(lm=lm, cache=True)

  3. Define metric:
       def root_cause_accuracy(example, prediction, trace=None):
         return (prediction.root_cause_device.lower() ==
                 example.ground_truth["root_cause_device"].lower())

  4. Run BASELINE (hand-written prompt):
       baseline = dspy.Predict(AlertsToIncident)
       baseline_score = evaluate(baseline, val_set, metric=root_cause_accuracy)
       print(f"Baseline accuracy: {baseline_score:.1%}")

  5. Run OPTIMIZER:
       optimizer = dspy.BootstrapFewShot(
           metric=root_cause_accuracy,
           max_bootstrapped_demos=8,
           max_labeled_demos=20
       )
       optimized = optimizer.compile(
           dspy.ChainOfThought(AlertsToIncident),
           trainset=train_set[:50]  # 50 examples sufficient
       )
       optimized_score = evaluate(optimized, val_set, metric=root_cause_accuracy)
       print(f"Optimized accuracy: {optimized_score:.1%}")
       print(f"Delta: +{(optimized_score-baseline_score):.1%}")

  6. Save:
       optimized.save("dspy_programs/alerts_to_incident_compiled.json")
       print("Compiled program saved.")

  7. Update CorrelationAgent to load compiled program

CRITICAL:
  Run this script ONCE.
  Record both numbers in docs/evaluation_results.md.
  Estimated cost: ~$5 on GPT-4o-mini.
  DSPy caching is ON — repeated runs cost $0.

Acceptance test:
  python scripts/optimize_dspy.py
  # Must print baseline, optimized, delta
  # compiled.json must exist after run
  ls -la dspy_programs/alerts_to_incident_compiled.json
```

---

### Session 23 — Sat May 9 — 2-3 hours
**Task:** `ui/noc_dashboard.py`

```
Files to create:
  ui/__init__.py
  ui/noc_dashboard.py
  tests/test_noc_dashboard.py

Must implement using rich library:
  class NOCDashboard:
    def __init__(self):
      self.alert_stream = []   # last 10 alerts
      self.open_incidents = [] # current open incidents
      self.latest_advisory = ""

    def update_alert_stream(self, alert: CanonicalAlert):
      self.alert_stream.append(alert)
      self.alert_stream = self.alert_stream[-10:]  # keep last 10

    def update_incident_board(self, incident: Incident):
      # Update or insert incident in open_incidents list

    def update_advisory(self, advisory_text: str):
      self.latest_advisory = advisory_text

    def generate_display(self) -> Columns:
      # Panel 1: Raw Alert Stream table (border=red)
      #   Columns: Time | Source | Device | Signal
      # Panel 2: Incident Board table (border=yellow)
      #   Columns: ID | Root Cause | Affected | Conf | Status
      # Panel 3: NOC Advisory panel (border=green)
      #   Latest advisory text
      return Columns([panel1, panel2, panel3])

    def run(self):
      with Live(self.generate_display(), refresh_per_second=2) as live:
        while True:
          live.update(self.generate_display())
          time.sleep(0.5)

Acceptance test:
  from ui.noc_dashboard import NOCDashboard
  dash = NOCDashboard()
  # Add some test alerts and an incident
  # Verify generate_display() returns without error
  print("Dashboard OK")
```

---

### Session 24 — Sun May 10 — 2-3 hours
**Task:** Full evaluation — all metrics on held-out test set

```
Files to create:
  evaluation/__init__.py
  evaluation/root_cause_accuracy.py
  evaluation/domain_classification.py
  evaluation/advisory_compliance.py
  evaluation/latency_monitor.py
  docs/evaluation_results.md
  tests/test_evaluation_suite.py

Each evaluation script must:
  - Load data/test.json (FIRST TIME this file is used)
  - Run the relevant agent/model
  - Print results clearly
  - Write results to docs/evaluation_results.md

root_cause_accuracy.py:
  - Run CorrelationAgent on each test incident
  - Measure: does root_cause_device match ground_truth?
  - Report: baseline % and DSPy-optimized %
  - Report: delta

domain_classification.py:
  - Run NormalizerAgent on each alert in test set
  - Measure: domain accuracy, severity accuracy
  - Report: base model %, SFT %, RLVR %

advisory_compliance.py:
  - Run CommunicationsAgent on each test incident
  - Score all 6 criteria per advisory
  - Report: mean compliance score base vs RLVR

latency_monitor.py:
  - Time each pipeline stage for 20 alerts
  - Report: normalize_ms, triage_ms, correlate_ms, store_ms, total_ms
  - Assert total < 2000ms

docs/evaluation_results.md format:
  # Evaluation Results — Week 15

  ## Normalizer Agent
  | Metric | Base | SFT | RLVR |
  |---|---|---|---|
  | Domain accuracy | X% | Y% | Z% |
  | Severity accuracy | X% | Y% | Z% |

  ## Correlation Agent
  | Metric | Baseline | DSPy Optimized |
  |---|---|---|
  | Root cause accuracy | X% | Y% |

  ## Communications Agent
  | Metric | Base | RLVR |
  |---|---|---|
  | Advisory compliance | X% | Y% |

  ## Latency
  | Stage | Mean ms |
  |---|---|
  | Normalize | X |
  | End-to-end | X |
```

---

### Session 25 — Mon May 11 — 1 hour
**Task:** Live OTel demo integration + rehearsal

```
No new files — integration and testing session.

Steps:
  1. Verify OTel stack running:
       docker compose ps
     If not running: docker compose up -d

  2. Verify Node Exporter added and running:
       curl http://localhost:9100/metrics | grep node_cpu

  3. Switch to live MCP tools (not mocks):
       Set ENVIRONMENT=production in .env

  4. Run full system:
       python -m orchestrator.master_orchestrator

  5. In separate terminal — run demo:
       bash demo/inject_failure.sh  (docker compose stop valkey-cart)

  6. Watch dashboard for:
       □ 7+ alerts arriving in Panel 1
       □ 1-2 incidents created in Panel 2
       □ Preliminary advisory in Panel 3 within 90 seconds
       □ Reconciler fires at 30s mark — incidents merge
       □ Confirmed advisory in Panel 3 within 3 minutes

  7. Restore: docker compose start valkey-cart

  8. Repeat 3 times — verify reproducibility

  9. Time the full sequence — note in docs/demo_notes.md

  10. Create demo/inject_failure.sh:
        #!/bin/bash
        echo "=== NOC WHISPERER DEMO ==="
        echo "Stopping Redis at $(date)"
        cd /path/to/opentelemetry-demo
        docker compose stop valkey-cart
        echo "Redis stopped. Watch the dashboard."

  11. Create demo/run_demo.py — narrated script version

Fix anything that breaks. Document in docs/demo_notes.md.
```

---

### Session 26 — Tue May 12 — 1 hour
**Task:** Bug fixes + polish + backup plan

```
Priority order:
  1. Fix top 3 issues from Saturday rehearsal
  2. Add graceful degradation to all MCP tools:
       If tool times out after 5s: log warning, return []
       System continues — does not crash
  3. Add structured logging throughout pipeline:
       import logging
       logging.basicConfig(level=logging.INFO,
                           format='%(asctime)s %(name)s %(message)s',
                           filename='logs/noc_whisperer.log')
  4. Create backup recording:
       Install asciinema: pip install asciinema
       asciinema rec docs/demo_backup.cast
       # Run the full demo sequence
       # Stop recording
       # This is your fallback if live demo fails

  5. Final end-to-end run — all real components, no mocks
  6. git tag v0.9-week15-complete
  7. git push
```

---

## WEEK 16 — Demo and Hackathon (Sun May 17 — demo day)

**Goal:** Polished, rehearsed, defensible. No new features.

---

### Session 27 — Wed May 13 — 1 hour
**Task:** Fix top 3 failure modes from Week 15

```
From docs/demo_notes.md — address the top 3 issues only.
No new features. No scope creep.
Commit each fix separately with descriptive message.
```

---

### Session 28 — Thu May 14 — 1 hour
**Task:** Presentation assets

```
Files to create:
  docs/presentation_notes.md
  docs/evaluation_results_final.md  # clean version of eval results

presentation_notes.md outline:
  0:00-1:00  Problem statement
    "47 alerts. 3 systems. No unified picture.
     A senior engineer takes 20 minutes.
     Our system takes 2 seconds."

  1:00-3:00  Architecture walkthrough (2 minutes)
    Reference: docs/architecture/noc_whisperer_system_architecture.svg
    Walk through each component in 15 seconds max.
    Emphasize: 4 MCP tools, 5 agents, 2 fine-tuned models, DSPy.

  3:00-8:00  Live demo (5 minutes)
    Run: bash demo/inject_failure.sh
    Narrate each panel as alerts arrive.
    Call out preliminary advisory at ~90s.
    Call out reconciler merge at ~2:30.
    Call out confirmed advisory at ~3:00.

  8:00-11:00  Evaluation results (3 minutes)
    Show evaluation_results_final.md as table.
    Call out each delta explicitly.
    Be honest about any metric that missed target.

  11:00-13:00  Reflection (2 minutes)
    What worked exactly as planned?
    What surprised you?
    What are the top 3 known limitations?

  13:00-15:00  Q&A begins

Prepare for likely Q&A questions:
  Q: Why synthetic data and not real NOC data?
  A: Ground truth is embedded — perfect labels. Real data needs annotation.

  Q: How does this scale to thousands of alerts?
  A: Sliding window + incident store prevent unbounded growth.
     Reconciler closes stale incidents. Current design handles ~500 alerts/min.

  Q: What happens if an MCP tool goes down?
  A: Graceful degradation — returns [], logs warning, system continues.

  Q: Why GPT-4o-mini for DSPy and not a larger model?
  A: Deliberately weak model proves intelligence is in the architecture,
     not in expensive compute. $5 total for optimization run.
```

---

### Session 29 — Fri May 15 — 1 hour
**Task:** Timed dress rehearsal

```
Run the complete 15-minute presentation solo.
Use a stopwatch. Record actual times for each section.
Adjust notes where you overrun.

Run live demo 3 times consecutively:
  1. Stop valkey-cart — run through — restore valkey-cart
  2. Stop valkey-cart — run through — restore valkey-cart
  3. Stop valkey-cart — run through — restore valkey-cart

Verify demo is reproducible every time.
Check: does the architecture SVG display clearly when zoomed?
Check: do evaluation tables print clearly in terminal?

Document any remaining issues in docs/demo_notes.md.
Fix only if critical.
```

---

### Session 30 — Sat May 16 — 1 hour
**Task:** Final fixes + v1.0 tag

```
Fix only what is critical from Wednesday rehearsal.
No new features. No refactoring.

Final checklist:
  □ docker compose up — all services healthy
  □ python -m orchestrator.master_orchestrator — starts cleanly
  □ bash demo/inject_failure.sh — works correctly
  □ Preliminary advisory fires within 90 seconds
  □ Confirmed advisory fires within 3 minutes
  □ All evaluation numbers documented in docs/
  □ Architecture SVG committed to docs/architecture/
  □ asciinema backup recording available
  □ No API keys in any committed file
  □ .env not committed

git tag v1.0-hackathon-ready
git push --tags
```

---

### Session 31 — Sun May 17 — Hackathon demo day
**Task:** Contingency + rest

```
If everything went well Thursday:
  Rest. Do not touch the code.
  Review your presentation notes once.
  Get a good night's sleep.

If something is still broken:
  Fix ONE thing only — the most critical blocking issue.
  Accept that imperfect is fine. Ship what works.
```

---

### Hackathon Day — Sat/Sun May 17-18

```
Arrive with:
  □ Laptop + charger
  □ .env file (NOT committed — bring it separately)
  □ asciinema backup recording playable offline

30 minutes before your slot:
  docker compose up  (takes 2-3 minutes to stabilize)
  python -m orchestrator.master_orchestrator  (verify it starts)
  curl http://localhost:9090/api/v1/query?query=up  (verify Prometheus)

During presentation:
  Start with problem statement — no technical setup visible
  Run inject_failure.sh at the 3-minute mark
  If live demo fails: switch to asciinema backup immediately, keep talking

After presentation:
  docker compose down
  Celebrate.
```

---

## Commit Message Convention

```
Session 1:  "scaffold: project structure and requirements"
Session 2:  "feat: canonical alert dataclasses"
Session 3:  "feat: topology graph and MCP tool"
Session 4:  "feat: fault scenario definitions"
Session 5:  "feat: synthetic alert generator"
Session 6:  "feat: training dataset generation script"
Session 7:  "infra: OTel demo stack verified — valkey-cart cascade confirmed"
Session 8:  "feat: prometheus MCP tool + mock + tests"
Session 9:  "feat: jaeger MCP tool + mock + tests"
Session 10: "feat: node exporter MCP tool + mock + tests"
Session 11: "data: normalizer SFT training data preparation"
Session 12: "train: submit normalizer SFT job"
Session 13: "feat: triage agent implementation"
Session 14: "train: submit normalizer RLVR job + DSPy signature"
Session 15: "feat: correlation agent + lock normalizer model"
Session 16: "train: communications SFT data + submit job"
Session 17: "feat: incident store SQLite implementation"
Session 18: "train: submit communications RLVR job + comms agent stub"
Session 19: "feat: streaming pipeline orchestration"
Session 20: "feat: reconciler agent ReAct loop"
Session 21: "feat: master orchestrator two concurrent loops"
Session 22: "optimize: DSPy BootstrapFewShot — baseline X% → optimized Y%"
Session 23: "feat: three-panel rich terminal dashboard"
Session 24: "eval: full evaluation on held-out test set"
Session 25: "integration: live OTel demo rehearsal"
Session 26: "polish: graceful degradation + structured logging + backup recording"
Session 27: "fix: top 3 failure modes from Week 15"
Session 28: "docs: presentation notes and evaluation results"
Session 29: "rehearsal: timed dress rehearsal — no code changes"
Session 30: "release: v1.0-hackathon-ready"
Session 31: "contingency: final fixes if needed"
```

---

## Quick Reference — Model Usage In Cursor

| When | Model | Why |
|---|---|---|
| Writing code (most sessions) | Claude Sonnet 4.6 | Fast, cheap, capable for code gen |
| Genuinely stuck on architecture | Claude Opus 4.7 | Only when Sonnet can't figure it out |
| Quick stubs and boilerplate | Claude Haiku 4.5 | Cheapest — for simple repetitive code |

**Rule:** Start every session with Sonnet 4.6.
Switch to Opus 4.7 only if you've tried twice and Sonnet still gets it wrong.
Switch back to Sonnet 4.6 immediately after.
