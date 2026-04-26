"""Unit tests for live and mock topology MCP implementations."""

from mcp_tools.mocks.mock_topology_mcp import MockTopologyMCP
from mcp_tools.topology_mcp import TopologyMCP


def _live_topology() -> TopologyMCP:
    """Return a live topology MCP instance backed by graph JSON."""
    return TopologyMCP("topology/otel_demo_graph.json")


def test_import() -> None:
    """Verify required classes are importable."""
    from mcp_tools.mocks.mock_topology_mcp import MockTopologyMCP as _MockTopologyMCP
    from mcp_tools.topology_mcp import TopologyMCP as _TopologyMCP

    assert _TopologyMCP is not None
    assert _MockTopologyMCP is not None


def test_get_downstream_valkey_cart() -> None:
    t = _live_topology()
    assert "cart" in t.get_downstream("valkey-cart")
    assert "checkout" not in t.get_downstream("valkey-cart")


def test_get_upstream_cart() -> None:
    t = _live_topology()
    assert "valkey-cart" in t.get_upstream("cart")


def test_get_upstream_checkout() -> None:
    t = _live_topology()
    assert "cart" in t.get_upstream("checkout")
    assert "kafka" in t.get_upstream("checkout")
    assert "payment" in t.get_upstream("checkout")


def test_are_related_direct() -> None:
    t = _live_topology()
    assert t.are_related("valkey-cart", "cart") is True


def test_are_related_transitive() -> None:
    t = _live_topology()
    assert t.are_related("valkey-cart", "checkout") is True
    assert t.are_related("valkey-cart", "frontend") is True


def test_are_related_unrelated() -> None:
    t = _live_topology()
    assert t.are_related("valkey-cart", "kafka") is False
    assert t.are_related("valkey-cart", "flagd") is False


def test_are_related_siblings_not_related() -> None:
    t = _live_topology()
    assert t.are_related("valkey-cart", "kafka") is False


def test_cascade_chain_valkey_cart() -> None:
    t = _live_topology()
    chain = t.get_cascade_chain("valkey-cart")
    assert chain[0] == "valkey-cart"
    assert "cart" in chain
    assert "checkout" in chain
    assert "frontend" in chain
    assert "kafka" not in chain
    assert "product-catalog" not in chain


def test_cascade_chain_ordering() -> None:
    t = _live_topology()
    chain = t.get_cascade_chain("valkey-cart")
    assert chain.index("valkey-cart") < chain.index("cart")
    assert chain.index("cart") < chain.index("checkout")


def test_topology_context_structure() -> None:
    t = _live_topology()
    context = t.get_topology_context(["valkey-cart", "cart"])
    assert "valkey-cart" in context
    assert "cart" in context
    assert "feeds_into" in context["valkey-cart"]
    assert "depends_on" in context["valkey-cart"]
    assert "cart" in context["valkey-cart"]["feeds_into"]


def test_unknown_device_returns_empty() -> None:
    t = _live_topology()
    assert t.get_downstream("nonexistent") == []
    assert t.get_upstream("nonexistent") == []
    assert t.are_related("valkey-cart", "nonexistent") is False


def test_health_check() -> None:
    t = _live_topology()
    assert t.health_check() is True


def test_mock_basic() -> None:
    mock = MockTopologyMCP()
    assert mock.are_related("valkey-cart", "cart") is True
    assert mock.are_related("valkey-cart", "kafka") is False
    assert mock.health_check() is True


def test_mock_cascade_chain() -> None:
    mock = MockTopologyMCP()
    chain = mock.get_cascade_chain("valkey-cart")
    assert chain[0] == "valkey-cart"
    assert "cart" in chain
    assert "frontend" in chain
    assert "kafka" not in chain


def test_mock_topology_context() -> None:
    mock = MockTopologyMCP()
    context = mock.get_topology_context(["valkey-cart", "cart"])
    assert "valkey-cart" in context
    assert "cart" in context["valkey-cart"]["feeds_into"]
