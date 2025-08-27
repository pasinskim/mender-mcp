"""Tests for Mender MCP Server."""

from unittest.mock import patch, Mock

import pytest

from mcp_server_mender.mender_api import (
    MenderAPIClient, 
    MenderDevice, 
    MenderInventoryItem,
    MenderDeviceInventory,
    MenderDeploymentLogEntry,
    MenderDeploymentLog
)
from mcp_server_mender.server import MenderMCPServer
from mcp_server_mender.security import SecurityLogger


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


# Inventory Tests

def test_mender_inventory_item_model():
    """Test MenderInventoryItem model validation."""
    item = MenderInventoryItem(name="device_type", value="beaglebone")
    assert item.name == "device_type"
    assert item.value == "beaglebone"
    assert item.description is None


def test_mender_device_inventory_model():
    """Test MenderDeviceInventory model validation."""
    attributes = [
        MenderInventoryItem(name="device_type", value="beaglebone"),
        MenderInventoryItem(name="os", value="linux")
    ]
    
    inventory = MenderDeviceInventory(
        device_id="test-device",
        attributes=attributes
    )
    
    assert inventory.device_id == "test-device"
    assert len(inventory.attributes) == 2
    assert inventory.attributes[0].name == "device_type"
    assert inventory.updated_ts is None


@pytest.fixture
def mock_inventory():
    """Mock device inventory for testing."""
    return MenderDeviceInventory(
        device_id="test-device-123",
        attributes=[
            MenderInventoryItem(name="device_type", value="beaglebone"),
            MenderInventoryItem(name="kernel", value="Linux 5.4.0"),
            MenderInventoryItem(name="mem_total_kB", value="512000"),
            MenderInventoryItem(name="mac_address", value="aa:bb:cc:dd:ee:ff"),
            MenderInventoryItem(name="serial_number", value="ABC123DEF456")
        ],
        updated_ts="2023-10-01T12:00:00Z"
    )


@pytest.fixture 
def mock_inventories():
    """Mock multiple device inventories for testing."""
    return [
        MenderDeviceInventory(
            device_id="device1",
            attributes=[
                MenderInventoryItem(name="device_type", value="beaglebone"),
                MenderInventoryItem(name="os", value="linux")
            ]
        ),
        MenderDeviceInventory(
            device_id="device2", 
            attributes=[
                MenderInventoryItem(name="device_type", value="raspberry-pi"),
                MenderInventoryItem(name="os", value="linux"),
                MenderInventoryItem(name="cpu_model", value="ARM Cortex-A72"),
                MenderInventoryItem(name="mem_total_kB", value="1024000")
            ]
        )
    ]


def test_format_device_inventory_output(mock_inventory):
    """Test device inventory output formatting."""
    with patch('mcp_server_mender.server.MenderAPIClient') as mock_client:
        server = MenderMCPServer("https://hosted.mender.io", "test_token")
        
        # Mock the get_device_group method to avoid API calls
        server.mender_client.get_device_group.return_value = "production"
        
        output = server._format_device_inventory_output(mock_inventory)
        
        assert "Device ID: test-device-123" in output
        assert "Last Updated: 2023-10-01 12:00:00+00:00" in output
        assert "Group: production" in output
        assert "Inventory Attributes (5):" in output
        assert "• device_type: beaglebone" in output
        assert "• kernel: Linux 5.4.0" in output
        assert "• mem_total_kB: 512000" in output
        assert "• mac_address: aa:bb:cc:dd:ee:ff" in output
        assert "• serial_number: ABC123DEF456" in output


def test_format_device_inventory_output_no_attributes():
    """Test device inventory output with no attributes."""
    empty_inventory = MenderDeviceInventory(
        device_id="empty-device",
        attributes=[]
    )
    
    with patch('mcp_server_mender.server.MenderAPIClient') as mock_client:
        server = MenderMCPServer("https://hosted.mender.io", "test_token")
        
        output = server._format_device_inventory_output(empty_inventory)
        
        assert "Device ID: empty-device" in output
        assert "No inventory attributes found." in output


def test_format_device_inventory_output_long_values():
    """Test device inventory output with long attribute values."""
    long_value = "a" * 100  # Very long value
    inventory = MenderDeviceInventory(
        device_id="test-device",
        attributes=[
            MenderInventoryItem(name="long_attribute", value=long_value),
            MenderInventoryItem(name="short_attr", value="short")
        ]
    )
    
    with patch('mcp_server_mender.server.MenderAPIClient') as mock_client:
        server = MenderMCPServer("https://hosted.mender.io", "test_token")
        
        output = server._format_device_inventory_output(inventory)
        
        # Long value should be truncated
        assert "• long_attribute: " + "a" * 57 + "..." in output
        # Short value should not be truncated  
        assert "• short_attr: short" in output


def test_format_inventories_output(mock_inventories):
    """Test multiple inventories output formatting."""
    with patch('mcp_server_mender.server.MenderAPIClient') as mock_client:
        server = MenderMCPServer("https://hosted.mender.io", "test_token")
        
        output = server._format_inventories_output(mock_inventories)
        
        assert "Found 2 device inventories:" in output
        assert "• device1" in output
        assert "• device2" in output
        assert "Attributes: 2" in output
        assert "Attributes: 4" in output
        assert "- device_type: beaglebone" in output
        assert "- device_type: raspberry-pi" in output
        assert "... and 1 more" in output  # device2 has 4 attrs, shows 3 + "1 more"


def test_format_inventories_output_empty():
    """Test inventories output with empty list."""
    with patch('mcp_server_mender.server.MenderAPIClient') as mock_client:
        server = MenderMCPServer("https://hosted.mender.io", "test_token")
        
        output = server._format_inventories_output([])
        
        assert output == "No device inventories found."


def test_format_inventory_groups_output():
    """Test inventory groups output formatting."""
    groups = [
        {
            "group": "production",
            "device_count": 5,
            "attributes": {
                "environment": "prod",
                "region": "us-east-1"
            }
        },
        {
            "group": "testing", 
            "device_count": 2,
            "attributes": {}
        },
        {
            "group": "empty-group",
            "device_count": 0
        }
    ]
    
    with patch('mcp_server_mender.server.MenderAPIClient') as mock_client:
        server = MenderMCPServer("https://hosted.mender.io", "test_token")
        
        output = server._format_inventory_groups_output(groups)
        
        assert "Found 3 inventory groups:" in output
        assert "• production" in output
        assert "Devices: 5" in output
        assert "Group Attributes: 2" in output
        assert "- environment: prod" in output
        assert "- region: us-east-1" in output
        assert "• testing" in output
        assert "• empty-group" in output
        assert "No devices" in output


def test_format_inventory_groups_output_empty():
    """Test inventory groups output with empty list."""
    with patch('mcp_server_mender.server.MenderAPIClient') as mock_client:
        server = MenderMCPServer("https://hosted.mender.io", "test_token")
        
        output = server._format_inventory_groups_output([])
        
        assert output == "No inventory groups found."


def test_mender_deployment_log_entry_model():
    """Test MenderDeploymentLogEntry model validation."""
    from datetime import datetime
    
    entry_data = {
        "timestamp": datetime(2023, 8, 27, 12, 30, 45),
        "level": "INFO",
        "message": "Deployment started successfully"
    }
    
    entry = MenderDeploymentLogEntry(**entry_data)
    assert entry.timestamp == datetime(2023, 8, 27, 12, 30, 45)
    assert entry.level == "INFO"
    assert entry.message == "Deployment started successfully"


def test_mender_deployment_log_model():
    """Test MenderDeploymentLog model validation."""
    from datetime import datetime
    
    log_data = {
        "deployment_id": "dep-123",
        "device_id": "dev-456",
        "entries": [
            MenderDeploymentLogEntry(
                timestamp=datetime(2023, 8, 27, 12, 30, 45),
                level="INFO",
                message="Starting deployment"
            ),
            MenderDeploymentLogEntry(
                timestamp=datetime(2023, 8, 27, 12, 31, 0),
                level="ERROR", 
                message="Deployment failed"
            )
        ],
        "retrieved_at": datetime(2023, 8, 27, 12, 35, 0)
    }
    
    log = MenderDeploymentLog(**log_data)
    assert log.deployment_id == "dep-123"
    assert log.device_id == "dev-456"
    assert len(log.entries) == 2
    assert log.entries[0].level == "INFO"
    assert log.entries[1].level == "ERROR"


def test_parse_log_line_with_timestamp_and_level():
    """Test parsing log line with timestamp and level."""
    client = MenderAPIClient("https://hosted.mender.io", "test_token")
    
    line = "2023-08-27T12:30:45Z INFO: Starting deployment process"
    entry = client._parse_log_line(line)
    
    assert entry.timestamp is not None
    assert entry.level == "INFO"
    assert entry.message == "Starting deployment process"


def test_parse_log_line_with_level_only():
    """Test parsing log line with level only."""
    client = MenderAPIClient("https://hosted.mender.io", "test_token")
    
    line = "ERROR: Failed to download artifact"
    entry = client._parse_log_line(line)
    
    assert entry.timestamp is None
    assert entry.level == "ERROR"
    assert entry.message == "Failed to download artifact"


def test_parse_log_line_plain_message():
    """Test parsing plain log line without timestamp or level."""
    client = MenderAPIClient("https://hosted.mender.io", "test_token")
    
    line = "This is a plain log message"
    entry = client._parse_log_line(line)
    
    assert entry.timestamp is None
    assert entry.level is None
    assert entry.message == "This is a plain log message"


def test_parse_deployment_log_response_string():
    """Test parsing deployment log response as string."""
    client = MenderAPIClient("https://hosted.mender.io", "test_token")
    
    log_text = """2023-08-27T12:30:45Z INFO: Starting deployment
2023-08-27T12:31:00Z ERROR: Download failed
Plain message without timestamp"""
    
    log = client._parse_deployment_log_response(log_text, "dep-123", "dev-456")
    
    assert log.deployment_id == "dep-123"
    assert log.device_id == "dev-456"
    assert len(log.entries) == 3
    assert log.entries[0].level == "INFO"
    assert log.entries[1].level == "ERROR"
    assert log.entries[2].message == "Plain message without timestamp"


def test_parse_deployment_log_response_json_array():
    """Test parsing deployment log response as JSON array."""
    client = MenderAPIClient("https://hosted.mender.io", "test_token")
    
    log_data = [
        {"timestamp": "2023-08-27T12:30:45Z", "level": "INFO", "message": "Starting deployment"},
        {"timestamp": "2023-08-27T12:31:00Z", "level": "ERROR", "message": "Download failed"}
    ]
    
    log = client._parse_deployment_log_response(log_data, "dep-123", "dev-456")
    
    assert log.deployment_id == "dep-123"
    assert log.device_id == "dev-456"
    assert len(log.entries) == 2
    assert log.entries[0].level == "INFO"
    assert log.entries[1].level == "ERROR"


def test_parse_deployment_log_response_json_object():
    """Test parsing deployment log response as JSON object."""
    client = MenderAPIClient("https://hosted.mender.io", "test_token")
    
    log_data = {
        "entries": [
            {"timestamp": "2023-08-27T12:30:45Z", "level": "INFO", "message": "Starting deployment"},
            {"timestamp": "2023-08-27T12:31:00Z", "level": "ERROR", "message": "Download failed"}
        ]
    }
    
    log = client._parse_deployment_log_response(log_data, "dep-123", "dev-456")
    
    assert log.deployment_id == "dep-123"
    assert log.device_id == "dev-456"
    assert len(log.entries) == 2
    assert log.entries[0].level == "INFO"
    assert log.entries[1].level == "ERROR"


def test_format_deployment_log_output():
    """Test deployment log output formatting."""
    from datetime import datetime
    
    with patch('mcp_server_mender.server.MenderAPIClient') as mock_client:
        server = MenderMCPServer("https://hosted.mender.io", "test_token")
        
        log = MenderDeploymentLog(
            deployment_id="dep-123",
            device_id="dev-456",
            entries=[
                MenderDeploymentLogEntry(
                    timestamp=datetime(2023, 8, 27, 12, 30, 45),
                    level="INFO",
                    message="Starting deployment"
                ),
                MenderDeploymentLogEntry(
                    timestamp=datetime(2023, 8, 27, 12, 31, 0),
                    level="ERROR", 
                    message="Download failed"
                )
            ],
            retrieved_at=datetime(2023, 8, 27, 12, 35, 0)
        )
        
        output = server._format_deployment_log_output(log)
        
        assert "Deployment Log" in output
        assert "Deployment ID: dep-123" in output
        assert "Device ID: dev-456" in output
        assert "Log Entries: 2" in output
        assert "2023-08-27 12:30:45 [INFO] Starting deployment" in output
        assert "2023-08-27 12:31:00 [ERROR] Download failed" in output


def test_format_deployment_log_output_no_entries():
    """Test deployment log output formatting with no entries."""
    from datetime import datetime
    
    with patch('mcp_server_mender.server.MenderAPIClient') as mock_client:
        server = MenderMCPServer("https://hosted.mender.io", "test_token")
        
        log = MenderDeploymentLog(
            deployment_id="dep-123",
            device_id="dev-456",
            entries=[],
            retrieved_at=datetime(2023, 8, 27, 12, 35, 0)
        )
        
        output = server._format_deployment_log_output(log)
        
        assert "Deployment ID: dep-123" in output
        assert "Device ID: dev-456" in output
        assert "Log Entries: 0" in output
        assert "No log entries found" in output
        assert "may only be available for failed deployments" in output


def test_format_deployment_log_output_long_message():
    """Test deployment log output formatting with long message truncation."""
    from datetime import datetime
    
    with patch('mcp_server_mender.server.MenderAPIClient') as mock_client:
        server = MenderMCPServer("https://hosted.mender.io", "test_token")
        
        long_message = "This is a very long log message that should be truncated " * 10
        
        log = MenderDeploymentLog(
            deployment_id="dep-123",
            device_id="dev-456",
            entries=[
                MenderDeploymentLogEntry(
                    timestamp=datetime(2023, 8, 27, 12, 30, 45),
                    level="INFO",
                    message=long_message
                )
            ]
        )
        
        output = server._format_deployment_log_output(log)
        
        assert "..." in output  # Message should be truncated
        assert len(output.split('\n')[-2]) < 250  # Line should be reasonable length


def test_format_deployment_logs_output():
    """Test deployment logs summary output formatting."""
    from datetime import datetime
    
    with patch('mcp_server_mender.server.MenderAPIClient') as mock_client:
        server = MenderMCPServer("https://hosted.mender.io", "test_token")
        
        logs = [
            MenderDeploymentLog(
                deployment_id="dep-123",
                device_id="dev-456",
                entries=[
                    MenderDeploymentLogEntry(level="INFO", message="Starting deployment"),
                    MenderDeploymentLogEntry(level="ERROR", message="Download failed")
                ]
            ),
            MenderDeploymentLog(
                deployment_id="dep-123",
                device_id="dev-789",
                entries=[
                    MenderDeploymentLogEntry(level="INFO", message="Deployment successful")
                ]
            )
        ]
        
        output = server._format_deployment_logs_output(logs)
        
        assert "Deployment Logs Summary" in output
        assert "Found logs for 2 device(s)" in output
        assert "• Device: dev-456" in output
        assert "• Device: dev-789" in output
        assert "Log Entries: 2" in output
        assert "Log Entries: 1" in output
        assert "[INFO] Starting deployment" in output
        assert "[ERROR] Download failed" in output
        assert "get_deployment_device_log" in output


def test_format_deployment_logs_output_empty():
    """Test deployment logs output with empty list."""
    with patch('mcp_server_mender.server.MenderAPIClient') as mock_client:
        server = MenderMCPServer("https://hosted.mender.io", "test_token")
        
        output = server._format_deployment_logs_output([])
        
        assert "No deployment logs found" in output
        assert "may only be available for failed deployments" in output


def test_format_deployment_logs_output_many_entries():
    """Test deployment logs output with many entries shows preview."""
    from datetime import datetime
    
    with patch('mcp_server_mender.server.MenderAPIClient') as mock_client:
        server = MenderMCPServer("https://hosted.mender.io", "test_token")
        
        # Create log with 5 entries
        entries = [
            MenderDeploymentLogEntry(level="INFO", message=f"Log entry {i}")
            for i in range(5)
        ]
        
        logs = [
            MenderDeploymentLog(
                deployment_id="dep-123",
                device_id="dev-456",
                entries=entries
            )
        ]
        
        output = server._format_deployment_logs_output(logs)
        
        assert "Log Entries: 5" in output
        assert "Log entry 0" in output
        assert "Log entry 1" in output
        assert "Log entry 2" in output
        assert "... and 2 more entries" in output  # Should show preview of first 3


def test_make_logs_request_handles_plain_text():
    """Test that _make_logs_request handles plain text responses correctly."""
    from unittest.mock import Mock
    
    client = MenderAPIClient("https://hosted.mender.io", "test_token")
    
    # Mock response with plain text content
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/plain"}
    mock_response.content = b"2025-08-27T12:30:45Z INFO: Starting deployment\nLog entry 2"
    mock_response.text = "2025-08-27T12:30:45Z INFO: Starting deployment\nLog entry 2"
    mock_response.raise_for_status.return_value = None
    
    # Mock the client request method
    client.client.request = Mock(return_value=mock_response)
    
    result = client._make_logs_request("GET", "/test/endpoint")
    
    assert isinstance(result, str)
    assert "Starting deployment" in result
    assert "Log entry 2" in result


def test_make_logs_request_handles_json_fallback():
    """Test that _make_logs_request falls back to JSON parsing when content-type is wrong."""
    from unittest.mock import Mock
    import json
    
    client = MenderAPIClient("https://hosted.mender.io", "test_token")
    
    # Mock response with JSON content but wrong content-type
    json_data = {"entries": [{"message": "test log"}]}
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/octet-stream"}  # Wrong content type
    mock_response.content = json.dumps(json_data).encode()
    mock_response.json.return_value = json_data
    mock_response.raise_for_status.return_value = None
    
    # Mock the client request method
    client.client.request = Mock(return_value=mock_response)
    
    result = client._make_logs_request("GET", "/test/endpoint")
    
    assert isinstance(result, dict)
    assert "entries" in result
    assert result["entries"][0]["message"] == "test log"


# Security Integration Tests

def test_mender_api_client_token_masking():
    """Test that tokens are masked in MenderAPIClient logs."""
    # Test the actual token masking functionality without mocking
    from mcp_server_mender.security import SecurityLogger
    
    test_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_payload_here"
    masked = SecurityLogger.mask_token(test_token)
    
    # Verify the token is properly masked
    assert "eyJhbGci" in masked      # First 8 chars should be visible
    assert "here" in masked          # Last 8 chars should be visible  
    assert "*" in masked             # Should contain masking asterisks
    assert len(masked) == len(test_token)  # Should be same length
    
    # Verify original token is not fully exposed
    assert masked != test_token      # Should be different from original
        

def test_mcp_server_security_logging():
    """Test that MCP server initializes security logging."""
    with patch('mcp_server_mender.server.SecurityLogger') as mock_security_logger:
        with patch('mcp_server_mender.mender_api.MenderAPIClient'):
            mock_logger_instance = Mock()
            mock_security_logger.return_value = mock_logger_instance
            
            server = MenderMCPServer("https://hosted.mender.io", "test_token")
            
            # Verify SecurityLogger was instantiated for server
            mock_security_logger.assert_called_with("mender_mcp_server")
            # Verify initialization was logged
            mock_logger_instance.log_secure.assert_called()


def test_api_error_sanitization():
    """Test that API errors are sanitized in ErrorSanitizer."""
    from mcp_server_mender.security import ErrorSanitizer
    
    # Test error sanitization directly
    error_response = "Authentication failed. Token eyJhbGciOiJIUzI1NiI invalid for user secret_user_id"
    sanitized = ErrorSanitizer.sanitize_http_error(401, error_response, "/api/test")
    
    # Verify error message is sanitized and helpful
    assert "Authentication failed" in sanitized  # Should contain helpful message
    assert "Personal Access Token" in sanitized  # Should provide guidance
    assert "eyJhbGci" not in sanitized           # Token should not be exposed
    
    # Test different error codes
    sanitized_404 = ErrorSanitizer.sanitize_http_error(404, "Not found", "/api/devices/123")
    assert "device ID may not exist" in sanitized_404
    
    sanitized_429 = ErrorSanitizer.sanitize_http_error(429, "Rate limited", "")
    assert "rate limit exceeded" in sanitized_429.lower()


def test_server_tool_input_validation():
    """Test that server tool calls validate input parameters."""
    # Test the input validation directly using the validation functions
    from mcp_server_mender.security import validate_input, DeviceIdInput, DeploymentIdInput
    
    # Test valid device ID input
    valid_data = {"device_id": "valid-device-123"}
    result = validate_input(DeviceIdInput, valid_data)
    assert result["device_id"] == "valid-device-123"
    
    # Test invalid input with path traversal (should fail at pattern level)
    with pytest.raises(ValueError, match="Input validation failed"):
        invalid_data = {"device_id": "../../../etc/passwd"}
        validate_input(DeviceIdInput, invalid_data)
        
    # Test invalid input with special characters
    with pytest.raises(ValueError, match="Input validation failed"):
        invalid_data = {"device_id": "device<script>alert(1)</script>"}
        validate_input(DeviceIdInput, invalid_data)
    
    # Test valid deployment ID
    valid_deployment = {"deployment_id": "deployment-456-abc"}
    result = validate_input(DeploymentIdInput, valid_deployment)
    assert result["deployment_id"] == "deployment-456-abc"
    
    # Test injection prevention
    with pytest.raises(ValueError, match="Input validation failed"):
        invalid_deployment = {"deployment_id": "deploy'; DROP TABLE devices;--"}
        validate_input(DeploymentIdInput, invalid_deployment)


def test_security_logger_message_sanitization():
    """Test that SecurityLogger properly sanitizes messages."""
    # Test JWT token sanitization
    message_with_jwt = "Request failed: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload"
    sanitized = SecurityLogger.sanitize_message(message_with_jwt)
    assert "eyJhbGci" not in sanitized
    assert "[JWT_TOKEN]" in sanitized
    
    # Test API key sanitization
    message_with_api_key = "API call with key: abcd1234567890abcd1234567890abcd"
    sanitized = SecurityLogger.sanitize_message(message_with_api_key)
    assert "abcd1234567890abcd1234567890abcd" not in sanitized
    assert "[API_KEY]" in sanitized or "[REDACTED]" in sanitized
    
    # Test password sanitization
    message_with_password = "Login failed: password=supersecret123"
    sanitized = SecurityLogger.sanitize_message(message_with_password)
    assert "supersecret123" not in sanitized
    assert "password=[REDACTED]" in sanitized


def test_token_masking_various_lengths():
    """Test token masking for various token lengths."""
    # Short token
    short_token = "abc"
    masked = SecurityLogger.mask_token(short_token)
    assert masked == "***"
    
    # Medium token (16 chars exactly - boundary case, returned as-is)
    medium_token = "abcdefghij123456"  # 16 chars - boundary case  
    masked = SecurityLogger.mask_token(medium_token)
    assert masked == medium_token  # 16 chars exactly - no masking applied
    
    # Long token (JWT-style)
    long_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    masked = SecurityLogger.mask_token(long_token)
    assert masked.startswith("eyJhbGci")  # First 8 chars
    assert masked.endswith("dQssw5c")    # Last 8 chars
    assert "*" in masked                  # Has masking
    assert len(masked) == len(long_token) # Same length
    
    # Empty token
    empty_masked = SecurityLogger.mask_token("")
    assert empty_masked == "*[EMPTY]*"

