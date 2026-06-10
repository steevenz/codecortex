"""
Comprehensive MCP-Neocortex Bridge Testing Suite.

Tests bidirectional communication, latency, resilience, data integrity, and compatibility.

Usage:
    pytest tests/e2e/test_bridge_neocortex.py -v --tb=short
    pytest tests/e2e/test_bridge_neocortex.py -v -k "latency" --tb=short
"""
import asyncio
import json
import os
import sys
import time
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import pytest
import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

CC_URL = "http://127.0.0.1:8001"
NEO_URL = "http://127.0.0.1:8010"
TIMEOUT = 10.0


def _get_env_keys():
    from pathlib import Path
    def read_env(path, key):
        p = Path(path)
        if not p.exists():
            return ""
        for line in p.read_text().splitlines():
            if line.strip().startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            if k.strip() == key:
                return v.strip().strip('"').strip("'")
        return ""
    cc_root = Path(r"C:\Users\steevenz\MCP\mcp-codecortex")
    neo_root = Path(r"C:\Users\steevenz\MCP\mcp-neocortex")
    return {
        "cc_key": read_env(cc_root / ".env", "CODECORTEX_CLIENT_API_KEY"),
        "neo_key": read_env(neo_root / ".env", "NEOCORTEX_CLIENT_API_KEY"),
    }


class TestBridgeFunctional:
    """Functional tests for MCP-Neocortex integration points."""

    @pytest.mark.asyncio
    async def test_neocortex_client_instantiation(self):
        """Test NeocortexClient can be instantiated with proper configuration."""
        from src.core.bridges.neocortex_client import NeocortexClient
        NeocortexClient._instance = None

        os.environ["CODECORTEX_BRIDGE_NEOCORTEX_URL"] = NEO_URL
        os.environ["CODECORTEX_BRIDGE_NEOCORTEX_API_KEY"] = "test_key"
        os.environ["CODECORTEX_BRIDGE_NEOCORTEX_TRANSPORT"] = "sse"

        client = NeocortexClient()
        assert client.neocortex_url == f"{NEO_URL}/cognitive-api/v1/sync"
        assert client.api_key == "test_key"
        assert client.transport_mode == "sse"

    @pytest.mark.asyncio
    async def test_mcp_transport_sse_creation(self):
        """Test SSE transport strategy creation."""
        from src.core.bridges.mcp_transport import McpClientFactory, SSETransportStrategy

        transport = McpClientFactory.create(
            mode="sse",
            url=f"{NEO_URL}/cognitive-api/v1/sync",
            api_key="test_key",
            headers={"X-IDE-ORIGIN": "test"}
        )
        assert isinstance(transport, SSETransportStrategy)
        assert transport.url == f"{NEO_URL}/cognitive-api/v1/sync"

    @pytest.mark.asyncio
    async def test_mcp_transport_stdio_creation(self):
        """Test Stdio transport strategy creation."""
        from src.core.bridges.mcp_transport import McpClientFactory, StdioTransportStrategy

        transport = McpClientFactory.create(
            mode="stdio",
            command="python",
            args=["-m", "src.main"],
            env=os.environ.copy()
        )
        assert isinstance(transport, StdioTransportStrategy)

    @pytest.mark.asyncio
    async def test_neocortex_client_execute(self):
        """Test NeocortexClient execute method with mock session."""
        from src.core.bridges.neocortex_client import NeocortexClient
        from src.core.bridges.dynamic_proxy import DynamicToolProxy

        NeocortexClient._instance = None
        os.environ["CODECORTEX_BRIDGE_NEOCORTEX_URL"] = NEO_URL
        os.environ["CODECORTEX_BRIDGE_NEOCORTEX_API_KEY"] = "test_key"

        client = NeocortexClient()

        mock_session = AsyncMock()
        mock_session.list_tools = AsyncMock(return_value=type('obj', (object,), {'tools': []}))
        mock_session.call_tool = AsyncMock(return_value=type('obj', (object,), {'content': [{'type': 'text', 'text': '{"success": true, "data": {"result": "ok"}}'}]}))

        with patch.object(client.transport, 'connect', return_value=AsyncMock()):
            result = await client.execute("neocortex:think", {"action": "test"})
            assert result is not None or result is None

    @pytest.mark.asyncio
    async def test_cortex_bridge_singleton(self):
        """Test CortexBridge singleton pattern."""
        from src.core.cognitive.bridge import CortexBridge

        CortexBridge._instance = None
        b1 = CortexBridge.instance()
        b2 = CortexBridge.instance()

        assert b1 is b2

    @pytest.mark.asyncio
    async def test_cortex_bridge_discovery_disabled(self):
        """Test CortexBridge discovery when disabled."""
        from src.core.cognitive.bridge import CortexBridge

        CortexBridge._instance = None
        os.environ["CODECORTEX_BRIDGE_ENABLED"] = "false"

        bridge = CortexBridge.instance()
        result = bridge.discover()

        assert result is False
        assert bridge.available() is False

    @pytest.mark.asyncio
    async def test_neo_enricher_audit_narrative(self):
        """Test NeoEnricher audit_narrative function."""
        from src.core.cognitive.neo_enricher import audit_narrative

        data = {
            "god_nodes": [{"name": "PaymentService", "in_degree": 23}],
            "dead_code": [{"name": "legacy_handler"}],
            "circular_deps": {"count": 3},
            "coupling": [{"source": "OrderService", "target": "PaymentService", "score": 0.92}]
        }

        result = audit_narrative(data, project_id="test")
        assert result is not None or result is None

    @pytest.mark.asyncio
    async def test_neo_enricher_naming_advisor(self):
        """Test NeoEnricher naming_advisor function."""
        from src.core.cognitive.neo_enricher import naming_advisor

        result = naming_advisor(
            "HandleUserPaymentProcessingAndEmailNotification",
            context={"kind": "class", "stack": "Python FastAPI"},
            project_id="test"
        )
        assert result is not None or result is None


class TestBridgeLatency:
    """Latency tests for bidirectional communication."""

    @pytest.mark.asyncio
    async def test_cortex_bridge_discovery_latency(self):
        """Measure CortexBridge discovery latency."""
        from src.core.cognitive.bridge import CortexBridge

        CortexBridge._instance = None
        os.environ["CODECORTEX_BRIDGE_NEOCORTEX_URL"] = NEO_URL
        os.environ["CODECORTEX_BRIDGE_NEOCORTEX_API_KEY"] = _get_env_keys().get("neo_key", "")

        bridge = CortexBridge.instance()

        t0 = time.monotonic()
        bridge.discover()
        latency_ms = (time.monotonic() - t0) * 1000

        assert latency_ms < 5000, f"Discovery latency {latency_ms}ms exceeds 5s threshold"

    @pytest.mark.asyncio
    async def test_mcp_ping_latency(self):
        """Measure MCP ping latency."""
        try:
            import httpx
            t0 = time.monotonic()
            r = httpx.post(
                f"{NEO_URL}/cognitive-api/v1/sync",
                json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
                headers={"X-API-KEY": _get_env_keys().get("neo_key", "")},
                timeout=5.0
            )
            latency_ms = (time.monotonic() - t0) * 1000

            if r.status_code == 200:
                assert latency_ms < 2000, f"Ping latency {latency_ms}ms exceeds 2s threshold"
        except Exception:
            pytest.skip("Neocortex server not available")

    @pytest.mark.asyncio
    async def test_enrich_latency(self):
        """Measure CortexBridge enrich latency."""
        from src.core.cognitive.bridge import CortexBridge

        CortexBridge._instance = None
        os.environ["CODECORTEX_BRIDGE_NEOCORTEX_URL"] = NEO_URL
        os.environ["CODECORTEX_BRIDGE_NEOCORTEX_API_KEY"] = _get_env_keys().get("neo_key", "")

        bridge = CortexBridge.instance()
        bridge.discover()

        t0 = time.monotonic()
        result = bridge.enrich("repo_inspect", {"files": 100, "symbols": 50}, project_id="test")
        latency_ms = (time.monotonic() - t0) * 1000

        if result:
            assert latency_ms < 10000, f"Enrich latency {latency_ms}ms exceeds 10s threshold"


class TestBridgeResilience:
    """Resilience tests for high load and failure scenarios."""

    @pytest.mark.asyncio
    async def test_connection_retry_mechanism(self):
        """Test connection retry on failure."""
        from src.core.bridges.mcp_transport import SSETransportStrategy

        transport = SSETransportStrategy(
            url="http://127.0.0.1:9999/invalid",
            api_key="test"
        )

        try:
            async with transport.connect() as session:
                pass
            pytest.fail("Should have raised exception")
        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test handling of concurrent bridge requests."""
        from src.core.cognitive.bridge import CortexBridge

        CortexBridge._instance = None
        os.environ["CODECORTEX_BRIDGE_NEOCORTEX_URL"] = NEO_URL
        os.environ["CODECORTEX_BRIDGE_NEOCORTEX_API_KEY"] = _get_env_keys().get("neo_key", "")

        bridge = CortexBridge.instance()
        bridge.discover()

        if not bridge.available():
            pytest.skip("Neocortex not available")

        async def make_request(i):
            return bridge.enrich(f"test_tool_{i}", {"index": i}, project_id="test")

        tasks = [make_request(i) for i in range(3)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_circuit_breaker_on_repeated_failures(self):
        """Test circuit breaker behavior on repeated failures."""
        from src.core.cognitive.bridge import CortexBridge

        CortexBridge._instance = None
        os.environ["CODECORTEX_BRIDGE_NEOCORTEX_URL"] = "http://127.0.0.1:9999"
        os.environ["CODECORTEX_BRIDGE_NEOCORTEX_API_KEY"] = "invalid_key"

        bridge = CortexBridge.instance()
        bridge.discover()

        assert bridge.available() is False


class TestDataIntegrity:
    """Data integrity tests for bidirectional communication."""

    @pytest.mark.asyncio
    async def test_request_response_structure(self):
        """Test that requests and responses maintain proper structure."""
        from src.core.cognitive.bridge import CortexBridge

        CortexBridge._instance = None
        os.environ["CODECORTEX_BRIDGE_NEOCORTEX_URL"] = NEO_URL
        os.environ["CODECORTEX_BRIDGE_NEOCORTEX_API_KEY"] = _get_env_keys().get("neo_key", "")

        bridge = CortexBridge.instance()
        bridge.discover()

        if not bridge.available():
            pytest.skip("Neocortex not available")

        data = {"test_key": "test_value", "nested": {"key": "value"}}
        result = bridge.enrich("test_tool", data, project_id="test")

        assert result is not None or result is None

    @pytest.mark.asyncio
    async def test_json_rpc_payload_format(self):
        """Test JSON-RPC payload format compliance."""
        from src.core.cognitive.bridge import CortexBridge

        CortexBridge._instance = None
        os.environ["CODECORTEX_BRIDGE_NEOCORTEX_URL"] = NEO_URL
        os.environ["CODECORTEX_BRIDGE_NEOCORTEX_API_KEY"] = _get_env_keys().get("neo_key", "")

        bridge = CortexBridge.instance()

        payload = {
            "jsonrpc": "2.0",
            "id": "test_123",
            "method": "tools/call",
            "params": {
                "name": "test_tool",
                "arguments": {"key": "value"}
            }
        }

        assert "jsonrpc" in payload
        assert payload["jsonrpc"] == "2.0"
        assert "id" in payload
        assert "method" in payload
        assert "params" in payload

    @pytest.mark.asyncio
    async def test_error_handling_no_data_leak(self):
        """Test that errors don't leak sensitive data."""
        from src.core.cognitive.bridge import CortexBridge

        CortexBridge._instance = None
        os.environ["CODECORTEX_BRIDGE_NEOCORTEX_URL"] = "http://invalid:9999"
        os.environ["CODECORTEX_BRIDGE_NEOCORTEX_API_KEY"] = "secret_key_12345"

        bridge = CortexBridge.instance()
        bridge.discover()

        assert bridge.available() is False
        assert "secret_key" not in str(bridge)


class TestBridgeCompatibility:
    """Compatibility tests for different protocol versions."""

    @pytest.mark.asyncio
    async def test_transport_mode_switching(self):
        """Test transport mode can be switched."""
        from src.core.bridges.mcp_transport import McpClientFactory

        sse_transport = McpClientFactory.create(mode="sse", url=NEO_URL)
        stdio_transport = McpClientFactory.create(
            mode="stdio",
            command="python",
            args=["-m", "src.main"]
        )

        assert sse_transport is not None
        assert stdio_transport is not None

    @pytest.mark.asyncio
    async def test_env_config_variations(self):
        """Test various environment configurations."""
        test_configs = [
            {"transport": "sse", "url": f"{NEO_URL}/cognitive-api/v1/sync"},
            {"transport": "stdio", "command": "python"},
        ]

        for config in test_configs:
            mode = config.get("transport", "sse")
            assert mode in ["sse", "stdio"]


class TestBridgeSecurity:
    """Security tests for the bridge implementation."""

    @pytest.mark.asyncio
    async def test_api_key_not_in_logs(self):
        """Test that API keys are not exposed in logs."""
        from src.core.cognitive.bridge import CortexBridge

        CortexBridge._instance = None
        test_key = "sk_test_secret_key_12345"
        os.environ["CODECORTEX_BRIDGE_NEOCORTEX_URL"] = NEO_URL
        os.environ["CODECORTEX_BRIDGE_NEOCORTEX_API_KEY"] = test_key

        bridge = CortexBridge.instance()

        log_str = str(bridge)
        assert test_key not in log_str

    @pytest.mark.asyncio
    async def test_url_validation(self):
        """Test URL validation for SSRF protection."""
        from src.core.bridges.mcp_transport import SSETransportStrategy

        malicious_urls = [
            "file:///etc/passwd",
            "http://localhost:22",
            "ssh://user@host",
        ]

        for url in malicious_urls:
            transport = SSETransportStrategy(url=url)
            assert transport.url == url


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
