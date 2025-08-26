"""Tests for Mender MCP Server."""

from unittest.mock import patch

import pytest

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


def test_format_tags_empty():
    """Test tags formatting with empty list."""
    with patch('mcp_server_mender.server.MenderAPIClient') as mock_client:
        server = MenderMCPServer("https://hosted.mender.io", "test_token")

        output = server._format_tags([])

        assert output == ""


def test_format_tags_few():
    """Test tags formatting with 3 or fewer tags (inline format)."""
    with patch('mcp_server_mender.server.MenderAPIClient') as mock_client:
        server = MenderMCPServer("https://hosted.mender.io", "test_token")

        # Test with 1 tag
        tags = [{"key": "version", "value": "1.0.0"}]
        output = server._format_tags(tags)
        assert output == "  Tags: version:1.0.0\n"

        # Test with 3 tags
        tags = [
            {"key": "version", "value": "1.0.0"},
            {"key": "env", "value": "prod"},
            {"key": "team", "value": "backend"}
        ]
        output = server._format_tags(tags)
        expected = "  Tags: version:1.0.0, env:prod, team:backend\n"
        assert output == expected


def test_format_tags_many():
    """Test tags formatting with more than 3 tags (bullet format)."""
    with patch('mcp_server_mender.server.MenderAPIClient') as mock_client:
        server = MenderMCPServer("https://hosted.mender.io", "test_token")

        tags = [
            {"key": "version", "value": "1.0.0"},
            {"key": "env", "value": "production"},
            {"key": "team", "value": "backend"},
            {"key": "region", "value": "us-east-1"},
            {"key": "stage", "value": "stable"}
        ]

        output = server._format_tags(tags)

        # Should include header with count
        assert "Tags (5):" in output

        # Should include all tags as bullet points
        assert "• version:1.0.0\n" in output
        assert "• env:production\n" in output
        assert "• team:backend\n" in output
        assert "• region:us-east-1\n" in output
        assert "• stage:stable\n" in output

        # Should not truncate or show "+X more"
        assert "+1 more" not in output
        assert "+2 more" not in output


def test_format_tags_malformed():
    """Test tags formatting with malformed tags (missing key/value)."""
    with patch('mcp_server_mender.server.MenderAPIClient') as mock_client:
        server = MenderMCPServer("https://hosted.mender.io", "test_token")

        # Test with missing key
        tags = [
            {"value": "1.0.0"},
            {"key": "env", "value": "prod"},
            {"key": "team"}  # Missing value
        ]

        output = server._format_tags(tags)

        # Should handle missing key/value gracefully with N/A
        assert "N/A:1.0.0" in output
        assert "team:N/A" in output
        assert "env:prod" in output


def test_format_tags_long_names():
    """Test tags formatting with long tag key:value pairs."""
    with patch('mcp_server_mender.server.MenderAPIClient') as mock_client:
        server = MenderMCPServer("https://hosted.mender.io", "test_token")

        # Create a very long tag that exceeds 64 chars
        long_tag = {
            "key": "very-long-deployment-environment-identifier-key",
            "value": "very-long-deployment-environment-identifier-value-that-exceeds-limits"
        }
        tags = [
            {"key": "version", "value": "1.0.0"},
            long_tag,
            {"key": "team", "value": "backend"},
            {"key": "short", "value": "val"}
        ]

        output = server._format_tags(tags)

        # Should include header
        assert "Tags (4):" in output

        # Should include normal tags
        assert "• version:1.0.0\n" in output
        assert "• team:backend\n" in output
        assert "• short:val\n" in output

        # Long tag should be truncated with "..."
        assert "very-long-deployment-environment-identifier-key:very-lo..." in output


def test_format_tags_line_length():
    """Test that tag lines don't exceed 64 characters."""
    with patch('mcp_server_mender.server.MenderAPIClient') as mock_client:
        server = MenderMCPServer("https://hosted.mender.io", "test_token")

        # Test with various tag lengths
        tags = [
            {"key": "short", "value": "val"},
            {"key": "medium-length-tag-key", "value": "medium-length-value"},
            {"key": "very-long-tag-key-that-would-exceed", "value": "very-long-tag-value-that-would-exceed-the-limit"},
            {"key": "x" * 50, "value": "y" * 50}  # Extremely long key:value
        ]

        output = server._format_tags(tags)

        # Check each line doesn't exceed 64 characters
        lines = output.split('\n')
        for line in lines:
            if line.strip():  # Skip empty lines
                assert len(line) <= 64, f"Line exceeds 64 chars: '{line}' (length: {len(line)})"

