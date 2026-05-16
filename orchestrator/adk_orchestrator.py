from __future__ import annotations

import os

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import FunctionTool

from agents.adk_tools.communications_tools import generate_advisory
from agents.adk_tools.correlation_tools import correlate_alert
from agents.adk_tools.incident_tools import check_open_incidents, close_incident
from agents.adk_tools.normalizer_tools import normalize_alert
from agents.adk_tools.prometheus_tools import check_service_health, get_active_alerts
from agents.adk_tools.triage_tools import route_alert

NOC_INSTRUCTION = """
You are a NOC (Network Operations Center) orchestrator agent.
Your job is to monitor services and manage incidents.

Every monitoring cycle follow these steps STRICTLY IN ORDER:

STEP 1: Call get_active_alerts() to check for threshold breaches.
        If no alerts returned, skip to STEP 6.

STEP 2: For EACH alert in the list, call normalize_alert() with
        the alert's device, metric, value, source_system, message fields.

STEP 3: For EACH normalized alert, call route_alert() with the
        alert_id, device, domain, severity, metric, value, 
        confidence, source_system fields from normalize_alert().

STEP 4: For EACH routed alert, call correlate_alert() with all
        fields from route_alert() plus the original alert fields.

STEP 5: For EACH correlated incident:
        - If confidence > 0.85 AND alert_count >= 2 
          AND confirmed_advisory_sent is False:
          call generate_advisory(incident_id, 'confirmed')
        - If confidence > 0.50 AND alert_count >= 2
          AND preliminary_advisory_sent is False:
          call generate_advisory(incident_id, 'preliminary')

STEP 6: Call check_open_incidents() to get all open incidents.
        For EACH open incident:
        - Call check_service_health(root_cause_device)
        - If returns True: call close_incident(incident_id)
          then call generate_advisory(incident_id, 'resolution')
        - If returns False: leave incident open

Complete ALL steps every cycle. Never skip steps.
Be thorough — process every alert and every incident.
"""


def build_noc_orchestrator(model_name: str = "openai/gpt-oss-20b") -> LlmAgent:
    """Build and return the NOC LlmAgent orchestrator."""
    model = LiteLlm(model=model_name)

    tools = [
        FunctionTool(get_active_alerts),
        FunctionTool(normalize_alert),
        FunctionTool(route_alert),
        FunctionTool(correlate_alert),
        FunctionTool(generate_advisory),
        FunctionTool(check_open_incidents),
        FunctionTool(check_service_health),
        FunctionTool(close_incident),
    ]

    return LlmAgent(
        name="NOCOrchestrator",
        description="NOC orchestrator that monitors services and manages incidents",
        model=model,
        instruction=NOC_INSTRUCTION,
        tools=tools,
    )
