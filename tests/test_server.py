"""Tests for Mender MCP Server."""

import pytest
from unittest.mock import Mock, patch

from mcp_server_mender.mender_api import MenderAPIClient, MenderDevice
from mcp_server_mender.server import MenderMCPServer


def test_mender_api_client_init():
    """Test MenderAPIClient initialization."""
    client = MenderAPIClient("https://hosted.mender.io", "test_token")
    
    assert client.server_url == "https://hosted.mender.io"
    assert client.access_token == "test_token"
    assert "Bearer test_token" in client.client.headers["Authorization"]


def test_mender_device_model():
    """Test MenderDevice model validation."""
    device_data = {
        "id": "test-device-id",
        "status": "accepted",
        "device_type": "test-device",
        "attributes": []
    }
    
    device = MenderDevice(**device_data)
    assert device.id == "test-device-id"
    assert device.status == "accepted"
    assert device.device_type == "test-device"


def test_mender_mcp_server_init():
    """Test MenderMCPServer initialization."""
    with patch('mcp_server_mender.server.MenderAPIClient') as mock_client:
        server = MenderMCPServer("https://hosted.mender.io", "test_token")
        
        assert server.server.name == "mender"
        mock_client.assert_called_once_with("https://hosted.mender.io", "test_token")


@pytest.fixture
def mock_devices():
    """Mock devices for testing."""
    return [
        MenderDevice(id="device1", status="accepted"),
        MenderDevice(id="device2", status="pending")
    ]


def test_format_devices_output(mock_devices):
    """Test device output formatting."""
    with patch('mcp_server_mender.server.MenderAPIClient') as mock_client:
        server = MenderMCPServer("https://hosted.mender.io", "test_token")
        
        output = server._format_devices_output(mock_devices)
        
        assert "Found 2 device(s)" in output
        assert "device1" in output
        assert "device2" in output
        assert "accepted" in output
        assert "pending" in output


def test_format_devices_output_empty():
    """Test device output formatting with empty list."""
    with patch('mcp_server_mender.server.MenderAPIClient') as mock_client:
        server = MenderMCPServer("https://hosted.mender.io", "test_token")
        
        output = server._format_devices_output([])
        
        assert output == "No devices found."