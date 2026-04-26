"""Topology MCP tool for service dependency graph queries."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Dict, List


class TopologyMCP:
    """Query helper for downstream/upstream topology relationships."""

    def __init__(self, graph_path: str):
        """Load topology graph from JSON file path."""
        graph_file = Path(graph_path)
        if not graph_file.exists():
            raise FileNotFoundError(f"Topology graph file not found: {graph_path}")
        with graph_file.open("r", encoding="utf-8") as f:
            self.graph: Dict[str, Dict[str, object]] = json.load(f)

    def get_downstream(self, device: str) -> List[str]:
        """Return direct downstream services for a device."""
        if device not in self.graph:
            return []
        feeds_into = self.graph[device].get("feeds_into", [])
        return list(feeds_into) if isinstance(feeds_into, list) else []

    def get_upstream(self, device: str) -> List[str]:
        """Return direct upstream dependencies for a device."""
        if device not in self.graph:
            return []
        depends_on = self.graph[device].get("depends_on", [])
        return list(depends_on) if isinstance(depends_on, list) else []

    def are_related(self, device_a: str, device_b: str) -> bool:
        """Check relation by BFS from device_a with directed edges only."""
        if device_a not in self.graph or device_b not in self.graph:
            return False
        if device_a == device_b:
            return True

        for neighbors_fn in (self.get_downstream, self.get_upstream):
            visited = {device_a}
            queue: deque[str] = deque([device_a])

            while queue:
                current = queue.popleft()
                for neighbor in neighbors_fn(current):
                    if neighbor == device_b:
                        return True
                    if neighbor in self.graph and neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)
        return False

    def get_cascade_chain(self, root_device: str) -> List[str]:
        """Return BFS-ordered downstream cascade chain starting at root."""
        if root_device not in self.graph:
            return []

        chain: List[str] = []
        visited = {root_device}
        queue: deque[str] = deque([root_device])

        while queue:
            current = queue.popleft()
            chain.append(current)
            for downstream in self.get_downstream(current):
                if downstream in self.graph and downstream not in visited:
                    visited.add(downstream)
                    queue.append(downstream)
        return chain

    def get_topology_context(self, devices: List[str]) -> dict:
        """Return feeds_into and depends_on context for requested devices."""
        context: Dict[str, Dict[str, List[str]]] = {}
        for device in devices:
            context[device] = {
                "feeds_into": self.get_downstream(device),
                "depends_on": self.get_upstream(device),
            }
        return context

    def health_check(self) -> bool:
        """Return True when graph is loaded."""
        return bool(self.graph)
