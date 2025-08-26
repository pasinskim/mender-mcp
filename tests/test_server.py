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


def test_format_device_types_empty():
    """Test device types formatting with empty list."""
    with patch('mcp_server_mender.server.MenderAPIClient') as mock_client:
        server = MenderMCPServer("https://hosted.mender.io", "test_token")
        
        output = server._format_device_types([])
        
        assert output == ""


def test_format_device_types_few():
    """Test device types formatting with 3 or fewer types (inline format)."""
    with patch('mcp_server_mender.server.MenderAPIClient') as mock_client:
        server = MenderMCPServer("https://hosted.mender.io", "test_token")
        
        # Test with 1 device type
        output = server._format_device_types(["beaglebone"])
        assert output == "    Device Types: beaglebone\n"
        
        # Test with 3 device types
        device_types = ["beaglebone", "beaglebone-yocto", "raspberry-pi"]
        output = server._format_device_types(device_types)
        expected = "    Device Types: beaglebone, beaglebone-yocto, raspberry-pi\n"
        assert output == expected


def test_format_device_types_many():
    """Test device types formatting with more than 3 types (bullet format)."""
    with patch('mcp_server_mender.server.MenderAPIClient') as mock_client:
        server = MenderMCPServer("https://hosted.mender.io", "test_token")
        
        device_types = [
            "beaglebone", 
            "beaglebone-yocto", 
            "beaglebone-yocto-grub",
            "raspberry-pi",
            "raspberry-pi-4"
        ]
        
        output = server._format_device_types(device_types)
        
        # Should include header with count
        assert "Device Types (5):" in output
        
        # Should include all device types as bullet points
        assert "• beaglebone\n" in output
        assert "• beaglebone-yocto\n" in output
        assert "• beaglebone-yocto-grub\n" in output
        assert "• raspberry-pi\n" in output
        assert "• raspberry-pi-4\n" in output
        
        # Should not truncate or show "+X more"
        assert "+1 more" not in output
        assert "+2 more" not in output


def test_format_device_types_long_names():
    """Test device types formatting with long device type names."""
    with patch('mcp_server_mender.server.MenderAPIClient') as mock_client:
        server = MenderMCPServer("https://hosted.mender.io", "test_token")
        
        # Create a very long device type name that exceeds 64 chars
        long_device_type = "very-long-device-type-name-that-exceeds-sixty-four-characters-limit"
        device_types = ["beaglebone", long_device_type, "raspberry-pi", "short-name"]
        
        output = server._format_device_types(device_types)
        
        # Should include header
        assert "Device Types (4):" in output
        
        # Should include normal device types
        assert "• beaglebone\n" in output
        assert "• raspberry-pi\n" in output
        assert "• short-name\n" in output
        
        # Long device type should be truncated with "..."
        assert "• very-long-device-type-name-that-exceeds-sixty-four-ch..." in output


def test_format_device_types_line_length():
    """Test that device type lines don't exceed 64 characters."""
    with patch('mcp_server_mender.server.MenderAPIClient') as mock_client:
        server = MenderMCPServer("https://hosted.mender.io", "test_token")
        
        # Test with various device type lengths
        device_types = [
            "short",
            "medium-length-device-type", 
            "very-long-device-type-name-that-would-exceed-the-limit",
            "x" * 100  # Extremely long name
        ]
        
        output = server._format_device_types(device_types)
        
        # Check each line doesn't exceed 64 characters
        lines = output.split('\n')
        for line in lines:
            if line.strip():  # Skip empty lines
                assert len(line) <= 64, f"Line exceeds 64 chars: '{line}' (length: {len(line)})"