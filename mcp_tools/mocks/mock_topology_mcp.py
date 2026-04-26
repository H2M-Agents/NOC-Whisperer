"""Mock topology MCP tool with hardcoded cascade behavior."""

from __future__ import annotations

from typing import Dict, List


class MockTopologyMCP:
    """Mocked topology API for deterministic agent testing."""

    def __init__(self) -> None:
        """Initialize static mock topology data."""
        self._context = {
            "valkey-cart": {
                "feeds_into": ["cart"],
                "depends_on": [],
            },
            "cart": {
                "feeds_into": ["checkout", "frontend"],
                "depends_on": ["valkey-cart"],
            },
        }

    def get_downstream(self, device: str) -> List[str]:
        """Return hardcoded downstream services."""
        if device == "valkey-cart":
            return ["cart"]
        return list(self._context.get(device, {}).get("feeds_into", []))

    def get_upstream(self, device: str) -> List[str]:
        """Return hardcoded upstream dependencies."""
        if device == "cart":
            return ["valkey-cart"]
        return list(self._context.get(device, {}).get("depends_on", []))

    def are_related(self, device_a: str, device_b: str) -> bool:
        """Return hardcoded relationship answers."""
        if (device_a, device_b) == ("valkey-cart", "cart"):
            return True
        if (device_a, device_b) == ("valkey-cart", "checkout"):
            return True
        if (device_a, device_b) == ("valkey-cart", "kafka"):
            return False
        if (device_a, device_b) == ("valkey-cart", "product-catalog"):
            return False
        return False

    def get_cascade_chain(self, root_device: str) -> List[str]:
        """Return hardcoded cascade chain from valkey-cart."""
        if root_device == "valkey-cart":
            return [
                "valkey-cart",
                "cart",
                "checkout",
                "frontend",
                "frontend-proxy",
            ]
        return [root_device]

    def get_topology_context(self, devices: List[str]) -> dict:
        """Return hardcoded context for valkey-cart/cart input."""
        if devices == ["valkey-cart", "cart"]:
            return self._context

        context: Dict[str, Dict[str, List[str]]] = {}
        for device in devices:
            context[device] = {
                "feeds_into": self.get_downstream(device),
                "depends_on": self.get_upstream(device),
            }
        return context

    def health_check(self) -> bool:
        """Always return healthy for mock tool."""
        return True
