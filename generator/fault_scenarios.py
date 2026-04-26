"""Fault scenario dataclass definitions for synthetic incident generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


_VALID_INITIATING_DOMAINS: set[str] = {
    "infrastructure",
    "service_mesh",
    "application",
    "dependency",
}
_VALID_TEMPORAL_PATTERNS: set[str] = {
    "simultaneous",
    "sequential",
    "gradual",
    "sudden_at_time_boundary",
    "gradual_then_sudden",
}
_ALERT_TEMPLATE_REQUIRED_KEYS: set[str] = {
    "domain",
    "severity",
    "device",
    "metric",
    "message_template",
    "value_range",
}


@dataclass
class FaultScenario:
    """Represents one synthetic fault scenario template."""

    scenario_id: str
    name: str
    initiating_fault_domain: str
    initiating_fault_type: str
    initiating_device: str
    cascade_chain: List[str]
    alert_templates: List[dict]
    temporal_pattern: str
    noise_alert_domains: List[str]
    ground_truth: dict

    def __post_init__(self) -> None:
        """Validate scenario fields and alert template shape."""
        if self.initiating_fault_domain not in _VALID_INITIATING_DOMAINS:
            raise ValueError(
                "initiating_fault_domain must be one of "
                f"{sorted(_VALID_INITIATING_DOMAINS)}."
            )

        if self.temporal_pattern not in _VALID_TEMPORAL_PATTERNS:
            raise ValueError(
                "temporal_pattern must be one of "
                f"{sorted(_VALID_TEMPORAL_PATTERNS)}."
            )

        if not isinstance(self.initiating_device, str) or not self.initiating_device.strip():
            raise ValueError("initiating_device must be a non-empty string.")

        if not isinstance(self.alert_templates, list) or len(self.alert_templates) == 0:
            raise ValueError("alert_templates must be a non-empty list.")

        for template in self.alert_templates:
            if not isinstance(template, dict):
                raise ValueError("each alert_template must be a dict.")
            missing = _ALERT_TEMPLATE_REQUIRED_KEYS - set(template.keys())
            if missing:
                raise ValueError(
                    "each alert_template dict must have keys "
                    f"{sorted(_ALERT_TEMPLATE_REQUIRED_KEYS)}."
                )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this scenario to a dictionary."""
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "initiating_fault_domain": self.initiating_fault_domain,
            "initiating_fault_type": self.initiating_fault_type,
            "initiating_device": self.initiating_device,
            "cascade_chain": list(self.cascade_chain),
            "alert_templates": [dict(template) for template in self.alert_templates],
            "temporal_pattern": self.temporal_pattern,
            "noise_alert_domains": list(self.noise_alert_domains),
            "ground_truth": dict(self.ground_truth),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FaultScenario:
        """Deserialize a scenario from dictionary data."""
        return cls(
            scenario_id=str(data["scenario_id"]),
            name=str(data["name"]),
            initiating_fault_domain=str(data["initiating_fault_domain"]),
            initiating_fault_type=str(data["initiating_fault_type"]),
            initiating_device=str(data["initiating_device"]),
            cascade_chain=[str(item) for item in data["cascade_chain"]],
            alert_templates=[dict(item) for item in data["alert_templates"]],
            temporal_pattern=str(data["temporal_pattern"]),
            noise_alert_domains=[str(item) for item in data["noise_alert_domains"]],
            ground_truth=dict(data["ground_truth"]),
        )


VALKEY_CART_CASCADE_SCENARIO = FaultScenario(
    scenario_id="scenario_01",
    name="Valkey cache failure causing cart and checkout cascade",
    initiating_fault_domain="infrastructure",
    initiating_fault_type="cache_failure",
    initiating_device="valkey-cart",
    cascade_chain=["valkey-cart", "cart", "checkout", "frontend", "frontend-proxy"],
    temporal_pattern="sequential",
    noise_alert_domains=["infrastructure", "application"],
    ground_truth={
        "root_cause_device": "valkey-cart",
        "initiating_domain": "infrastructure",
        "affected_services": ["cart", "checkout", "frontend", "frontend-proxy"],
        "cascade_type": "load_amplification",
        "correlation_window_seconds": 120,
    },
    alert_templates=[
        {
            "domain": "infrastructure",
            "severity": "critical",
            "device": "valkey-cart",
            "metric": "container_up",
            "message_template": "valkey-cart container is down",
            "value_range": [0.0, 0.0],
        },
        {
            "domain": "infrastructure",
            "severity": "critical",
            "device": "valkey-cart",
            "metric": "valkey_cache_miss_ratio",
            "message_template": "Valkey cache miss ratio at {value:.0%}",
            "value_range": [0.95, 1.0],
        },
        {
            "domain": "service_mesh",
            "severity": "critical",
            "device": "cart",
            "metric": "http_error_rate_per_min",
            "message_template": "cart HTTP error rate {value:.0f}/min",
            "value_range": [25.0, 50.0],
        },
        {
            "domain": "service_mesh",
            "severity": "major",
            "device": "cart",
            "metric": "http_latency_seconds",
            "message_template": "cart response latency {value:.1f}s",
            "value_range": [3.0, 8.0],
        },
        {
            "domain": "service_mesh",
            "severity": "major",
            "device": "checkout",
            "metric": "http_error_rate_per_min",
            "message_template": "checkout HTTP error rate {value:.0f}/min",
            "value_range": [15.0, 35.0],
        },
        {
            "domain": "application",
            "severity": "major",
            "device": "frontend",
            "metric": "http_error_rate_per_min",
            "message_template": "frontend HTTP error rate {value:.0f}/min",
            "value_range": [10.0, 25.0],
        },
        {
            "domain": "application",
            "severity": "minor",
            "device": "frontend-proxy",
            "metric": "http_latency_seconds",
            "message_template": "frontend-proxy latency {value:.1f}s",
            "value_range": [1.5, 4.0],
        },
    ],
)

SCENARIO_02_DISK_FULL_CHECKOUT = FaultScenario(
    scenario_id="scenario_02",
    name="Disk full causing checkout read errors",
    initiating_fault_domain="application",
    initiating_fault_type="disk_full",
    initiating_device="checkout",
    cascade_chain=["checkout", "frontend", "frontend-proxy"],
    temporal_pattern="gradual_then_sudden",
    noise_alert_domains=["application", "service_mesh"],
    ground_truth={
        "root_cause_device": "checkout",
        "initiating_domain": "application",
        "affected_services": ["checkout", "frontend", "frontend-proxy"],
        "cascade_type": "capacity_exhaustion",
        "correlation_window_seconds": 180,
    },
    alert_templates=[
        {
            "domain": "infrastructure",
            "severity": "major",
            "device": "checkout",
            "metric": "disk_used_percent",
            "message_template": "checkout disk usage at {value:.1f}%",
            "value_range": [88.0, 98.0],
        },
        {
            "domain": "service_mesh",
            "severity": "critical",
            "device": "checkout",
            "metric": "http_error_rate_per_min",
            "message_template": "checkout write path errors {value:.0f}/min",
            "value_range": [20.0, 40.0],
        },
        {
            "domain": "application",
            "severity": "major",
            "device": "frontend",
            "metric": "http_error_rate_per_min",
            "message_template": "frontend checkout failures {value:.0f}/min",
            "value_range": [10.0, 30.0],
        },
    ],
)

SCENARIO_03_IO_LATENCY_PRODUCT_CATALOG = FaultScenario(
    scenario_id="scenario_03",
    name="I/O latency causing product-catalog slowdown",
    initiating_fault_domain="application",
    initiating_fault_type="io_latency",
    initiating_device="product-catalog",
    cascade_chain=["product-catalog", "checkout", "frontend"],
    temporal_pattern="gradual",
    noise_alert_domains=["application", "infrastructure"],
    ground_truth={
        "root_cause_device": "product-catalog",
        "initiating_domain": "application",
        "affected_services": ["product-catalog", "checkout", "frontend"],
        "cascade_type": "latency_cascade",
        "correlation_window_seconds": 180,
    },
    alert_templates=[
        {
            "domain": "application",
            "severity": "major",
            "device": "product-catalog",
            "metric": "http_latency_seconds",
            "message_template": "product-catalog latency {value:.1f}s",
            "value_range": [1.5, 5.0],
        },
        {
            "domain": "service_mesh",
            "severity": "major",
            "device": "checkout",
            "metric": "http_latency_seconds",
            "message_template": "checkout dependency latency {value:.1f}s",
            "value_range": [2.0, 6.0],
        },
        {
            "domain": "application",
            "severity": "minor",
            "device": "frontend",
            "metric": "http_latency_seconds",
            "message_template": "frontend page latency {value:.1f}s",
            "value_range": [1.0, 3.5],
        },
    ],
)

SCENARIO_04_OOM_PAYMENT = FaultScenario(
    scenario_id="scenario_04",
    name="OOM kill causing payment service death",
    initiating_fault_domain="application",
    initiating_fault_type="oom_kill",
    initiating_device="payment",
    cascade_chain=["payment", "checkout", "frontend"],
    temporal_pattern="sudden_at_time_boundary",
    noise_alert_domains=["infrastructure", "application"],
    ground_truth={
        "root_cause_device": "payment",
        "initiating_domain": "application",
        "affected_services": ["payment", "checkout", "frontend"],
        "cascade_type": "hard_failure",
        "correlation_window_seconds": 120,
    },
    alert_templates=[
        {
            "domain": "infrastructure",
            "severity": "critical",
            "device": "payment",
            "metric": "oom_kill_count",
            "message_template": "payment OOM kill count {value:.0f}",
            "value_range": [1.0, 3.0],
        },
        {
            "domain": "service_mesh",
            "severity": "critical",
            "device": "checkout",
            "metric": "http_error_rate_per_min",
            "message_template": "checkout payment failures {value:.0f}/min",
            "value_range": [15.0, 40.0],
        },
        {
            "domain": "application",
            "severity": "major",
            "device": "frontend",
            "metric": "http_error_rate_per_min",
            "message_template": "frontend payment errors {value:.0f}/min",
            "value_range": [8.0, 20.0],
        },
    ],
)

SCENARIO_05_CPU_STARVATION_RECOMMENDATION = FaultScenario(
    scenario_id="scenario_05",
    name="CPU starvation causing recommendation latency",
    initiating_fault_domain="application",
    initiating_fault_type="cpu_starvation",
    initiating_device="recommendation",
    cascade_chain=["recommendation", "frontend", "frontend-proxy"],
    temporal_pattern="simultaneous",
    noise_alert_domains=["application", "infrastructure"],
    ground_truth={
        "root_cause_device": "recommendation",
        "initiating_domain": "application",
        "affected_services": ["recommendation", "frontend", "frontend-proxy"],
        "cascade_type": "resource_contention",
        "correlation_window_seconds": 150,
    },
    alert_templates=[
        {
            "domain": "infrastructure",
            "severity": "major",
            "device": "recommendation",
            "metric": "cpu_utilization_percent",
            "message_template": "recommendation CPU at {value:.1f}%",
            "value_range": [90.0, 99.0],
        },
        {
            "domain": "application",
            "severity": "major",
            "device": "recommendation",
            "metric": "http_latency_seconds",
            "message_template": "recommendation latency {value:.1f}s",
            "value_range": [2.0, 6.0],
        },
        {
            "domain": "application",
            "severity": "minor",
            "device": "frontend",
            "metric": "http_latency_seconds",
            "message_template": "frontend recommendation latency {value:.1f}s",
            "value_range": [1.0, 3.0],
        },
    ],
)

SCENARIO_06_CONTAINER_THROTTLING_SHIPPING = FaultScenario(
    scenario_id="scenario_06",
    name="Container throttling causing shipping slowdown",
    initiating_fault_domain="application",
    initiating_fault_type="container_throttling",
    initiating_device="shipping",
    cascade_chain=["shipping", "checkout", "frontend"],
    temporal_pattern="gradual",
    noise_alert_domains=["service_mesh", "application"],
    ground_truth={
        "root_cause_device": "shipping",
        "initiating_domain": "application",
        "affected_services": ["shipping", "checkout", "frontend"],
        "cascade_type": "throughput_degradation",
        "correlation_window_seconds": 180,
    },
    alert_templates=[
        {
            "domain": "infrastructure",
            "severity": "major",
            "device": "shipping",
            "metric": "cpu_throttle_ratio",
            "message_template": "shipping throttle ratio {value:.2f}",
            "value_range": [0.7, 0.98],
        },
        {
            "domain": "service_mesh",
            "severity": "major",
            "device": "checkout",
            "metric": "http_latency_seconds",
            "message_template": "checkout shipping latency {value:.1f}s",
            "value_range": [1.5, 5.0],
        },
        {
            "domain": "application",
            "severity": "minor",
            "device": "frontend",
            "metric": "http_latency_seconds",
            "message_template": "frontend shipping delay {value:.1f}s",
            "value_range": [1.0, 3.5],
        },
    ],
)

SCENARIO_07_NETWORK_PARTITION_KAFKA = FaultScenario(
    scenario_id="scenario_07",
    name="Network partition causing kafka unreachable",
    initiating_fault_domain="infrastructure",
    initiating_fault_type="network_partition",
    initiating_device="kafka",
    cascade_chain=["kafka", "checkout", "accounting", "fraud-detection"],
    temporal_pattern="simultaneous",
    noise_alert_domains=["infrastructure", "application"],
    ground_truth={
        "root_cause_device": "kafka",
        "initiating_domain": "infrastructure",
        "affected_services": ["checkout", "accounting", "fraud-detection"],
        "cascade_type": "network_isolation",
        "correlation_window_seconds": 120,
    },
    alert_templates=[
        {
            "domain": "infrastructure",
            "severity": "critical",
            "device": "kafka",
            "metric": "broker_reachable",
            "message_template": "kafka broker unreachable",
            "value_range": [0.0, 0.0],
        },
        {
            "domain": "service_mesh",
            "severity": "major",
            "device": "checkout",
            "metric": "http_error_rate_per_min",
            "message_template": "checkout kafka dependency errors {value:.0f}/min",
            "value_range": [10.0, 30.0],
        },
        {
            "domain": "application",
            "severity": "major",
            "device": "accounting",
            "metric": "consumer_lag",
            "message_template": "accounting consumer lag {value:.0f}",
            "value_range": [500.0, 5000.0],
        },
    ],
)

SCENARIO_08_DNS_FAILURE_CURRENCY = FaultScenario(
    scenario_id="scenario_08",
    name="DNS failure causing currency service errors",
    initiating_fault_domain="dependency",
    initiating_fault_type="dns_failure",
    initiating_device="currency",
    cascade_chain=["currency", "checkout", "frontend"],
    temporal_pattern="gradual",
    noise_alert_domains=["application", "dependency"],
    ground_truth={
        "root_cause_device": "currency",
        "initiating_domain": "dependency",
        "affected_services": ["currency", "checkout", "frontend"],
        "cascade_type": "name_resolution_failure",
        "correlation_window_seconds": 180,
    },
    alert_templates=[
        {
            "domain": "application",
            "severity": "major",
            "device": "currency",
            "metric": "dns_lookup_failures_per_min",
            "message_template": "currency DNS lookup failures {value:.0f}/min",
            "value_range": [10.0, 40.0],
        },
        {
            "domain": "service_mesh",
            "severity": "major",
            "device": "checkout",
            "metric": "http_error_rate_per_min",
            "message_template": "checkout currency dependency errors {value:.0f}/min",
            "value_range": [8.0, 25.0],
        },
        {
            "domain": "application",
            "severity": "minor",
            "device": "frontend",
            "metric": "http_error_rate_per_min",
            "message_template": "frontend currency conversion errors {value:.0f}/min",
            "value_range": [4.0, 12.0],
        },
    ],
)

SCENARIO_09_LB_FAILURE_FRONTEND_PROXY = FaultScenario(
    scenario_id="scenario_09",
    name="Load balancer failure causing frontend-proxy errors",
    initiating_fault_domain="infrastructure",
    initiating_fault_type="load_balancer_failure",
    initiating_device="frontend-proxy",
    cascade_chain=["frontend-proxy", "frontend"],
    temporal_pattern="gradual_then_sudden",
    noise_alert_domains=["infrastructure", "application"],
    ground_truth={
        "root_cause_device": "frontend-proxy",
        "initiating_domain": "infrastructure",
        "affected_services": ["frontend-proxy", "frontend"],
        "cascade_type": "edge_routing_failure",
        "correlation_window_seconds": 150,
    },
    alert_templates=[
        {
            "domain": "infrastructure",
            "severity": "critical",
            "device": "frontend-proxy",
            "metric": "backend_connection_failures",
            "message_template": "frontend-proxy backend connection failures {value:.0f}/min",
            "value_range": [20.0, 60.0],
        },
        {
            "domain": "application",
            "severity": "major",
            "device": "frontend",
            "metric": "http_error_rate_per_min",
            "message_template": "frontend gateway errors {value:.0f}/min",
            "value_range": [10.0, 35.0],
        },
        {
            "domain": "application",
            "severity": "minor",
            "device": "frontend",
            "metric": "http_latency_seconds",
            "message_template": "frontend response latency {value:.1f}s",
            "value_range": [1.0, 4.0],
        },
    ],
)

SCENARIO_10_CERT_EXPIRY_PAYMENT = FaultScenario(
    scenario_id="scenario_10",
    name="Certificate expiry causing payment TLS errors",
    initiating_fault_domain="dependency",
    initiating_fault_type="cert_expiry",
    initiating_device="payment",
    cascade_chain=["payment", "checkout", "frontend"],
    temporal_pattern="sudden_at_time_boundary",
    noise_alert_domains=["dependency", "application"],
    ground_truth={
        "root_cause_device": "payment",
        "initiating_domain": "dependency",
        "affected_services": ["payment", "checkout", "frontend"],
        "cascade_type": "authentication_failure",
        "correlation_window_seconds": 120,
    },
    alert_templates=[
        {
            "domain": "application",
            "severity": "critical",
            "device": "payment",
            "metric": "tls_handshake_failures_per_min",
            "message_template": "payment TLS handshake failures {value:.0f}/min",
            "value_range": [20.0, 70.0],
        },
        {
            "domain": "service_mesh",
            "severity": "major",
            "device": "checkout",
            "metric": "http_error_rate_per_min",
            "message_template": "checkout payment TLS failures {value:.0f}/min",
            "value_range": [10.0, 30.0],
        },
        {
            "domain": "application",
            "severity": "major",
            "device": "frontend",
            "metric": "http_error_rate_per_min",
            "message_template": "frontend payment authorization errors {value:.0f}/min",
            "value_range": [6.0, 20.0],
        },
    ],
)

SCENARIO_11_BAD_DEPLOYMENT_CHECKOUT = FaultScenario(
    scenario_id="scenario_11",
    name="Bad deployment causing checkout configuration errors",
    initiating_fault_domain="dependency",
    initiating_fault_type="bad_config",
    initiating_device="checkout",
    cascade_chain=["checkout", "frontend", "frontend-proxy"],
    temporal_pattern="gradual",
    noise_alert_domains=["application", "dependency"],
    ground_truth={
        "root_cause_device": "checkout",
        "initiating_domain": "dependency",
        "affected_services": ["checkout", "frontend", "frontend-proxy"],
        "cascade_type": "configuration_regression",
        "correlation_window_seconds": 180,
    },
    alert_templates=[
        {
            "domain": "application",
            "severity": "major",
            "device": "checkout",
            "metric": "config_validation_failures_per_min",
            "message_template": "checkout config validation failures {value:.0f}/min",
            "value_range": [8.0, 25.0],
        },
        {
            "domain": "service_mesh",
            "severity": "major",
            "device": "checkout",
            "metric": "http_error_rate_per_min",
            "message_template": "checkout bad config errors {value:.0f}/min",
            "value_range": [12.0, 35.0],
        },
        {
            "domain": "application",
            "severity": "minor",
            "device": "frontend",
            "metric": "http_error_rate_per_min",
            "message_template": "frontend checkout failures {value:.0f}/min",
            "value_range": [5.0, 15.0],
        },
    ],
)

SCENARIO_12_EXTERNAL_API_EMAIL = FaultScenario(
    scenario_id="scenario_12",
    name="External API degradation causing email service timeout",
    initiating_fault_domain="dependency",
    initiating_fault_type="external_api_degradation",
    initiating_device="email",
    cascade_chain=["email", "checkout", "frontend"],
    temporal_pattern="gradual",
    noise_alert_domains=["application", "dependency"],
    ground_truth={
        "root_cause_device": "email",
        "initiating_domain": "dependency",
        "affected_services": ["email", "checkout", "frontend"],
        "cascade_type": "third_party_degradation",
        "correlation_window_seconds": 180,
    },
    alert_templates=[
        {
            "domain": "application",
            "severity": "major",
            "device": "email",
            "metric": "external_api_latency_seconds",
            "message_template": "email provider latency {value:.1f}s",
            "value_range": [2.0, 8.0],
        },
        {
            "domain": "application",
            "severity": "major",
            "device": "email",
            "metric": "timeout_rate_per_min",
            "message_template": "email timeout rate {value:.0f}/min",
            "value_range": [8.0, 30.0],
        },
        {
            "domain": "service_mesh",
            "severity": "minor",
            "device": "checkout",
            "metric": "http_latency_seconds",
            "message_template": "checkout email workflow latency {value:.1f}s",
            "value_range": [1.0, 3.5],
        },
    ],
)

ALL_SCENARIOS: List[FaultScenario] = [
    VALKEY_CART_CASCADE_SCENARIO,
    SCENARIO_02_DISK_FULL_CHECKOUT,
    SCENARIO_03_IO_LATENCY_PRODUCT_CATALOG,
    SCENARIO_04_OOM_PAYMENT,
    SCENARIO_05_CPU_STARVATION_RECOMMENDATION,
    SCENARIO_06_CONTAINER_THROTTLING_SHIPPING,
    SCENARIO_07_NETWORK_PARTITION_KAFKA,
    SCENARIO_08_DNS_FAILURE_CURRENCY,
    SCENARIO_09_LB_FAILURE_FRONTEND_PROXY,
    SCENARIO_10_CERT_EXPIRY_PAYMENT,
    SCENARIO_11_BAD_DEPLOYMENT_CHECKOUT,
    SCENARIO_12_EXTERNAL_API_EMAIL,
]
