"""Mender MCP Server - Main server implementation."""

import asyncio
import os
import sys
from typing import Any, Dict, List, Optional

import click
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, TextContent, Tool
from pydantic import AnyUrl

from .mender_api import MenderAPIClient, MenderAPIError


class MenderMCPServer:
    """Mender MCP Server implementation."""

    def __init__(self, server_url: str, access_token: str):
        """Initialize the server with Mender API client."""
        self.mender_client = MenderAPIClient(server_url, access_token)
        self.server = Server("mender")
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Set up MCP server handlers."""

        @self.server.list_resources()
        async def list_resources() -> List[Resource]:
            """List available resources."""
            return [
                Resource(
                    uri=AnyUrl("mender://devices"),
                    name="Devices",
                    description="List of all Mender devices",
                    mimeType="application/json",
                ),
                Resource(
                    uri=AnyUrl("mender://deployments"),
                    name="Deployments",
                    description="List of all Mender deployments",
                    mimeType="application/json",
                ),
                Resource(
                    uri=AnyUrl("mender://artifacts"),
                    name="Artifacts",
                    description="List of all Mender artifacts",
                    mimeType="application/json",
                ),
                Resource(
                    uri=AnyUrl("mender://releases"),
                    name="Releases",
                    description="List of all Mender releases",
                    mimeType="application/json",
                ),
                Resource(
                    uri=AnyUrl("mender://inventory"),
                    name="Device Inventory",
                    description="Complete device inventory with all attributes",
                    mimeType="application/json",
                ),
                Resource(
                    uri=AnyUrl("mender://inventory-groups"),
                    name="Inventory Groups",
                    description="Device grouping information",
                    mimeType="application/json",
                ),
            ]

        @self.server.read_resource()
        async def read_resource(uri: AnyUrl) -> str:
            """Read a specific resource."""
            uri_str = str(uri)

            try:
                if uri_str == "mender://devices":
                    devices = self.mender_client.get_devices()
                    return self._format_devices_output(devices)

                elif uri_str == "mender://deployments":
                    deployments = self.mender_client.get_deployments()
                    return self._format_deployments_output(deployments)

                elif uri_str == "mender://artifacts":
                    artifacts = self.mender_client.get_artifacts()
                    return self._format_artifacts_output(artifacts)

                elif uri_str == "mender://releases":
                    releases = self.mender_client.get_releases()
                    return self._format_releases_output(releases)

                elif uri_str.startswith("mender://devices/"):
                    device_id = uri_str.split("/")[-1]
                    device = self.mender_client.get_device(device_id)
                    return self._format_device_output(device)

                elif uri_str.startswith("mender://deployments/"):
                    deployment_id = uri_str.split("/")[-1]
                    deployment = self.mender_client.get_deployment(deployment_id)
                    return self._format_deployment_output(deployment)

                elif uri_str.startswith("mender://releases/"):
                    release_name = uri_str.split("/")[-1]
                    release = self.mender_client.get_release(release_name)
                    return self._format_release_output(release)

                elif uri_str == "mender://inventory":
                    inventories = self.mender_client.get_devices_inventory()
                    return self._format_inventories_output(inventories)

                elif uri_str.startswith("mender://inventory/"):
                    device_id = uri_str.split("/")[-1]
                    inventory = self.mender_client.get_device_inventory(device_id)
                    return self._format_device_inventory_output(inventory)

                elif uri_str == "mender://inventory-groups":
                    groups = self.mender_client.get_inventory_groups()
                    return self._format_inventory_groups_output(groups)

                else:
                    raise ValueError(f"Unknown resource: {uri}")

            except MenderAPIError as e:
                return f"Error accessing Mender API: {e.message}"
            except Exception as e:
                return f"Unexpected error: {str(e)}"

        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available tools."""
            return [
                Tool(
                    name="get_device_status",
                    description="Get the current status of a specific device",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {
                                "type": "string",
                                "description": "The ID of the device to check"
                            }
                        },
                        "required": ["device_id"]
                    }
                ),
                Tool(
                    name="list_devices",
                    description="List devices with optional filtering",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "status": {
                                "type": "string",
                                "description": "Filter by device status (accepted, rejected, pending, etc.)",
                                "enum": ["accepted", "rejected", "pending", "noauth"]
                            },
                            "device_type": {
                                "type": "string",
                                "description": "Filter by device type"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of devices to return",
                                "minimum": 1,
                                "maximum": 500,
                                "default": 20
                            }
                        }
                    }
                ),
                Tool(
                    name="get_deployment_status",
                    description="Get the status and details of a specific deployment",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "deployment_id": {
                                "type": "string",
                                "description": "The ID of the deployment to check"
                            }
                        },
                        "required": ["deployment_id"]
                    }
                ),
                Tool(
                    name="list_deployments",
                    description="List deployments with optional filtering",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "status": {
                                "type": "string",
                                "description": "Filter by deployment status",
                                "enum": ["inprogress", "finished", "pending"]
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of deployments to return",
                                "minimum": 1,
                                "maximum": 100,
                                "default": 10
                            }
                        }
                    }
                ),
                Tool(
                    name="list_releases",
                    description="List releases with optional filtering",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Filter by release name"
                            },
                            "tag": {
                                "type": "string",
                                "description": "Filter by release tag"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of releases to return",
                                "minimum": 1,
                                "maximum": 100,
                                "default": 20
                            }
                        }
                    }
                ),
                Tool(
                    name="get_release_status",
                    description="Get the details of a specific release",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "release_name": {
                                "type": "string",
                                "description": "The name of the release to check"
                            }
                        },
                        "required": ["release_name"]
                    }
                ),
                Tool(
                    name="get_device_inventory",
                    description="Get complete inventory attributes for a specific device",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {
                                "type": "string",
                                "description": "The ID of the device to get inventory for"
                            }
                        },
                        "required": ["device_id"]
                    }
                ),
                Tool(
                    name="list_device_inventory",
                    description="List device inventories with optional filtering",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of device inventories to return",
                                "minimum": 1,
                                "maximum": 500,
                                "default": 20
                            },
                            "has_attribute": {
                                "type": "string",
                                "description": "Filter devices that have a specific attribute name"
                            }
                        }
                    }
                ),
                Tool(
                    name="get_inventory_groups",
                    description="Get all device inventory groups",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="get_deployment_device_log",
                    description="Get deployment logs for a specific device in a deployment",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "deployment_id": {
                                "type": "string",
                                "description": "The deployment ID"
                            },
                            "device_id": {
                                "type": "string",
                                "description": "The device ID"
                            }
                        },
                        "required": ["deployment_id", "device_id"]
                    }
                ),
                Tool(
                    name="get_deployment_logs",
                    description="Get deployment logs for all devices in a deployment",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "deployment_id": {
                                "type": "string",
                                "description": "The deployment ID"
                            }
                        },
                        "required": ["deployment_id"]
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls."""
            try:
                if name == "get_device_status":
                    device_id = arguments["device_id"]
                    device = self.mender_client.get_device(device_id)
                    result = self._format_device_output(device)

                elif name == "list_devices":
                    status = arguments.get("status")
                    device_type = arguments.get("device_type")
                    limit = arguments.get("limit", 20)

                    devices = self.mender_client.get_devices(
                        status=status,
                        device_type=device_type,
                        limit=limit
                    )
                    result = self._format_devices_output(devices)

                elif name == "get_deployment_status":
                    deployment_id = arguments["deployment_id"]
                    deployment = self.mender_client.get_deployment(deployment_id)
                    result = self._format_deployment_output(deployment)

                elif name == "list_deployments":
                    status = arguments.get("status")
                    limit = arguments.get("limit", 10)

                    deployments = self.mender_client.get_deployments(
                        status=status,
                        limit=limit
                    )
                    result = self._format_deployments_output(deployments)

                elif name == "list_releases":
                    name_filter = arguments.get("name")
                    tag = arguments.get("tag")
                    limit = arguments.get("limit", 20)

                    releases = self.mender_client.get_releases(
                        name=name_filter,
                        tag=tag,
                        limit=limit
                    )
                    result = self._format_releases_output(releases)

                elif name == "get_release_status":
                    release_name = arguments["release_name"]
                    release = self.mender_client.get_release(release_name)
                    result = self._format_release_output(release)

                elif name == "get_device_inventory":
                    device_id = arguments["device_id"]
                    inventory = self.mender_client.get_device_inventory(device_id)
                    result = self._format_device_inventory_output(inventory)

                elif name == "list_device_inventory":
                    limit = arguments.get("limit", 20)
                    has_attribute = arguments.get("has_attribute")
                    
                    inventories = self.mender_client.get_devices_inventory(
                        limit=limit,
                        has_attribute=has_attribute
                    )
                    result = self._format_inventories_output(inventories)

                elif name == "get_inventory_groups":
                    groups = self.mender_client.get_inventory_groups()
                    result = self._format_inventory_groups_output(groups)

                elif name == "get_deployment_device_log":
                    deployment_id = arguments["deployment_id"]
                    device_id = arguments["device_id"]
                    log = self.mender_client.get_deployment_device_log(deployment_id, device_id)
                    result = self._format_deployment_log_output(log)

                elif name == "get_deployment_logs":
                    deployment_id = arguments["deployment_id"]
                    logs = self.mender_client.get_deployment_logs(deployment_id)
                    result = self._format_deployment_logs_output(logs)

                else:
                    result = f"Unknown tool: {name}"

                return [TextContent(type="text", text=result)]

            except MenderAPIError as e:
                error_msg = f"Mender API Error: {e.message}"
                if e.status_code:
                    error_msg += f" (HTTP {e.status_code})"
                return [TextContent(type="text", text=error_msg)]
            except Exception as e:
                return [TextContent(type="text", text=f"Unexpected error: {str(e)}")]

    def _format_device_output(self, device) -> str:
        """Format device information for output."""
        output = f"Device ID: {device.id}\n"
        output += f"Status: {device.status}\n"

        if device.device_type:
            output += f"Device Type: {device.device_type}\n"

        if device.created_ts:
            output += f"Created: {device.created_ts}\n"

        if device.updated_ts:
            output += f"Last Updated: {device.updated_ts}\n"

        output += f"Decommissioning: {device.decommissioning}\n"

        if device.attributes:
            output += "Attributes:\n"
            for attr in device.attributes:
                output += f"  - {attr.get('name', 'N/A')}: {attr.get('value', 'N/A')}\n"

        return output

    def _format_devices_output(self, devices) -> str:
        """Format devices list for output."""
        if not devices:
            return "No devices found."

        output = f"Found {len(devices)} device(s):\n\n"

        for device in devices:
            output += f"• {device.id}\n"
            output += f"  Status: {device.status}\n"
            if device.device_type:
                output += f"  Type: {device.device_type}\n"
            if device.updated_ts:
                output += f"  Last Updated: {device.updated_ts}\n"
            output += "\n"

        return output

    def _format_deployment_output(self, deployment) -> str:
        """Format deployment information for output."""
        output = f"Deployment ID: {deployment.id}\n"
        output += f"Name: {deployment.name}\n"
        output += f"Artifact: {deployment.artifact_name}\n"
        output += f"Status: {deployment.status}\n"

        if deployment.created:
            output += f"Created: {deployment.created}\n"

        if deployment.finished:
            output += f"Finished: {deployment.finished}\n"

        if deployment.device_count:
            output += f"Device Count: {deployment.device_count}\n"

        if deployment.statistics:
            output += "Statistics:\n"
            for key, value in deployment.statistics.items():
                output += f"  {key}: {value}\n"

        return output

    def _format_deployments_output(self, deployments) -> str:
        """Format deployments list for output."""
        if not deployments:
            return "No deployments found."

        output = f"Found {len(deployments)} deployment(s):\n\n"

        for deployment in deployments:
            output += f"• {deployment.name} (ID: {deployment.id})\n"
            output += f"  Status: {deployment.status}\n"
            output += f"  Artifact: {deployment.artifact_name}\n"
            if deployment.created:
                output += f"  Created: {deployment.created}\n"
            output += "\n"

        return output

    def _format_artifacts_output(self, artifacts) -> str:
        """Format artifacts list for output."""
        if not artifacts:
            return "No artifacts found."

        output = f"Found {len(artifacts)} artifact(s):\n\n"

        for artifact in artifacts:
            output += f"• {artifact.name} (ID: {artifact.id})\n"
            if artifact.description:
                output += f"  Description: {artifact.description}\n"
            if artifact.device_types_compatible:
                output += f"  Compatible Types: {', '.join(artifact.device_types_compatible)}\n"
            if artifact.size:
                output += f"  Size: {artifact.size} bytes\n"
            output += "\n"

        return output

    def _format_release_output(self, release) -> str:
        """Format release information for output."""
        output = f"Release Name: {release.name}\n"
        
        if release.modified:
            output += f"Last Modified: {release.modified}\n"

        if release.artifacts_count:
            output += f"Artifacts Count: {release.artifacts_count}\n"

        if release.notes:
            output += f"Notes: {release.notes}\n"

        if release.tags:
            output += "Tags:\n"
            for tag in release.tags:
                output += f"  - {tag.get('key', 'N/A')}: {tag.get('value', 'N/A')}\n"

        if release.artifacts:
            output += f"Artifacts ({len(release.artifacts)}):\n"
            for artifact in release.artifacts:
                output += f"  • {artifact.get('name', 'N/A')}\n"
                if artifact.get('id'):
                    output += f"    ID: {artifact.get('id')}\n"
                if artifact.get('size'):
                    size_mb = artifact.get('size') / (1024*1024)
                    output += f"    Size: {size_mb:.1f} MB\n"
                output += f"    Signed: {artifact.get('signed', False)}\n"
                if artifact.get('device_types_compatible'):
                    device_types = artifact.get('device_types_compatible', [])
                    output += self._format_device_types(device_types)
                output += "\n"

        return output

    def _format_device_types(self, device_types) -> str:
        """Format device types list with bullet points and 64-char line wrapping."""
        if not device_types:
            return ""
        
        if len(device_types) <= 3:
            # For 3 or fewer types, use inline format
            return f"    Device Types: {', '.join(device_types)}\n"
        
        # For more than 3 types, use bullet point format
        output = f"    Device Types ({len(device_types)}):\n"
        
        for device_type in device_types:
            # Format each device type as a bullet point
            prefix = "      • "  # 8 characters
            max_device_type_length = 64 - len(prefix) - 3  # 3 for "..."
            
            if len(prefix + device_type) <= 64:
                output += f"{prefix}{device_type}\n"
            else:
                # Wrap long device type names - truncate to fit within 64 chars
                truncated = device_type[:max_device_type_length]
                output += f"{prefix}{truncated}...\n"
        
        return output

    def _format_tags(self, tags) -> str:
        """Format tags list with bullet points and 64-char line wrapping."""
        if not tags:
            return ""
        
        # Convert tags to formatted strings
        tag_strings = []
        for tag in tags:
            key = tag.get('key', 'N/A')
            value = tag.get('value', 'N/A')
            tag_strings.append(f"{key}:{value}")
        
        if len(tag_strings) <= 3:
            # For 3 or fewer tags, use inline format
            return f"  Tags: {', '.join(tag_strings)}\n"
        
        # For more than 3 tags, use bullet point format
        output = f"  Tags ({len(tag_strings)}): \n"
        
        for tag_string in tag_strings:
            # Format each tag as a bullet point
            prefix = "    • "  # 6 characters
            max_tag_length = 64 - len(prefix) - 3  # 3 for "..."
            
            if len(prefix + tag_string) <= 64:
                output += f"{prefix}{tag_string}\n"
            else:
                # Wrap long tag names - truncate to fit within 64 chars
                truncated = tag_string[:max_tag_length]
                output += f"{prefix}{truncated}...\n"
        
        return output

    def _format_releases_output(self, releases) -> str:
        """Format releases list for output."""
        if not releases:
            return "No releases found."

        output = f"Found {len(releases)} release(s):\n\n"

        for release in releases:
            output += f"• {release.name}\n"
            if release.modified:
                output += f"  Last Modified: {release.modified}\n"
            if release.artifacts_count:
                output += f"  Artifacts: {release.artifacts_count}\n"
            if release.notes:
                output += f"  Notes: {release.notes}\n"
            if release.tags:
                output += self._format_tags(release.tags)
            # Show first artifact info if available
            if release.artifacts and len(release.artifacts) > 0:
                artifact = release.artifacts[0]
                if artifact.get('size'):
                    size_mb = artifact.get('size') / (1024*1024)
                    output += f"  Size: {size_mb:.1f} MB\n"
                output += f"  Signed: {artifact.get('signed', False)}\n"
            output += "\n"

        return output

    def _format_device_inventory_output(self, inventory) -> str:
        """Format complete device inventory for display."""
        output = f"Device ID: {inventory.device_id}\n"
        
        if inventory.updated_ts:
            output += f"Last Updated: {inventory.updated_ts}\n"
        
        # Get group information if available
        try:
            group = self.mender_client.get_device_group(inventory.device_id)
            if group:
                output += f"Group: {group}\n"
        except Exception:
            # Ignore group errors to avoid breaking inventory display
            pass
        
        if not inventory.attributes:
            output += "No inventory attributes found.\n"
            return output
        
        output += f"\nInventory Attributes ({len(inventory.attributes)}):\n"
        
        for attr in inventory.attributes:
            attr_name = attr.name
            attr_value = str(attr.value)
            
            # Truncate long values for readability
            if len(attr_value) > 60:
                attr_value = attr_value[:57] + "..."
            
            output += f"  • {attr_name}: {attr_value}\n"
        
        return output

    def _format_inventories_output(self, inventories) -> str:
        """Format device inventories list for display."""
        if not inventories:
            return "No device inventories found."

        output = f"Found {len(inventories)} device inventories:\n\n"

        for inventory in inventories:
            output += f"• {inventory.device_id}\n"
            if inventory.updated_ts:
                output += f"  Last Updated: {inventory.updated_ts}\n"
            
            attr_count = len(inventory.attributes)
            if attr_count > 0:
                output += f"  Attributes: {attr_count}\n"
                
                # Show first few attributes as preview
                preview_attrs = inventory.attributes[:3]
                for attr in preview_attrs:
                    attr_value = str(attr.value)
                    if len(attr_value) > 30:
                        attr_value = attr_value[:27] + "..."
                    output += f"    - {attr.name}: {attr_value}\n"
                
                if attr_count > 3:
                    output += f"    ... and {attr_count - 3} more\n"
            else:
                output += "  No attributes\n"
            
            output += "\n"

        return output

    def _format_inventory_groups_output(self, groups) -> str:
        """Format inventory groups information."""
        if not groups:
            return "No inventory groups found."

        output = f"Found {len(groups)} inventory groups:\n\n"

        for group in groups:
            group_name = group.get("group", "Unknown")
            device_count = group.get("device_count", 0)
            
            output += f"• {group_name}\n"
            if device_count > 0:
                output += f"  Devices: {device_count}\n"
            else:
                output += "  No devices\n"
            
            # Show group attributes if available
            if "attributes" in group and group["attributes"]:
                attrs = group["attributes"]
                output += f"  Group Attributes: {len(attrs)}\n"
                for key, value in attrs.items():
                    value_str = str(value)
                    if len(value_str) > 40:
                        value_str = value_str[:37] + "..."
                    output += f"    - {key}: {value_str}\n"
            
            output += "\n"

        return output

    def _format_deployment_log_output(self, log) -> str:
        """Format deployment log for specific device."""
        from .mender_api import MenderDeploymentLog
        
        if not isinstance(log, MenderDeploymentLog):
            return f"Invalid deployment log data: {str(log)}"
        
        output = f"Deployment Log\n"
        output += f"================\n"
        output += f"Deployment ID: {log.deployment_id}\n"
        output += f"Device ID: {log.device_id}\n"
        
        if log.retrieved_at:
            output += f"Retrieved: {log.retrieved_at}\n"
        
        output += f"Log Entries: {len(log.entries)}\n\n"
        
        if not log.entries:
            output += "No log entries found.\n"
            output += "Note: Deployment logs may only be available for failed deployments\n"
            output += "or may not be enabled for this Mender configuration.\n"
            return output
        
        output += "Log Details:\n"
        output += "------------\n"
        
        for entry in log.entries:
            # Format timestamp
            timestamp_str = ""
            if entry.timestamp:
                timestamp_str = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            
            # Format level
            level_str = ""
            if entry.level:
                level_str = f"[{entry.level}] "
            
            # Format message with truncation if too long
            message = entry.message
            if len(message) > 200:
                message = message[:197] + "..."
            
            if timestamp_str:
                output += f"{timestamp_str} {level_str}{message}\n"
            else:
                output += f"{level_str}{message}\n"
        
        return output

    def _format_deployment_logs_output(self, logs) -> str:
        """Format deployment logs for all devices."""
        from .mender_api import MenderDeploymentLog
        
        if not logs:
            return "No deployment logs found.\n" \
                   "Note: Deployment logs may only be available for failed deployments\n" \
                   "or may not be enabled for this Mender configuration."
        
        output = f"Deployment Logs Summary\n"
        output += f"======================\n"
        output += f"Found logs for {len(logs)} device(s):\n\n"
        
        for log in logs:
            if not isinstance(log, MenderDeploymentLog):
                continue
                
            output += f"• Device: {log.device_id}\n"
            output += f"  Log Entries: {len(log.entries)}\n"
            
            if log.entries:
                # Show first few log entries as preview
                preview_entries = log.entries[:3]
                for entry in preview_entries:
                    level_str = f"[{entry.level}] " if entry.level else ""
                    message = entry.message
                    if len(message) > 80:
                        message = message[:77] + "..."
                    output += f"    {level_str}{message}\n"
                
                if len(log.entries) > 3:
                    output += f"    ... and {len(log.entries) - 3} more entries\n"
            else:
                output += "    No log entries\n"
            
            output += "\n"
        
        output += "Use 'get_deployment_device_log' for complete logs of specific devices.\n"
        
        return output

    async def run(self) -> None:
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


@click.command()
@click.option(
    "--server-url",
    required=False,
    help="Mender server URL (default: https://hosted.mender.io)",
    default="https://hosted.mender.io"
)
@click.option(
    "--access-token",
    required=False,
    help="Personal Access Token for authentication"
)
@click.option(
    "--token-file",
    required=False,
    help="File containing the Personal Access Token"
)
def main(server_url: str, access_token: Optional[str], token_file: Optional[str]) -> None:
    """Run the Mender MCP server."""

    # Get access token from various sources
    token = None

    if access_token:
        token = access_token
    elif token_file:
        try:
            with open(os.path.expanduser(token_file)) as f:
                token = f.read().strip()
        except FileNotFoundError:
            click.echo(f"Error: Token file not found: {token_file}", err=True)
            sys.exit(1)
        except Exception as e:
            click.echo(f"Error reading token file: {e}", err=True)
            sys.exit(1)
    else:
        # Try environment variable
        token = os.getenv("MENDER_ACCESS_TOKEN")

    if not token:
        click.echo(
            "Error: No access token provided. Use --access-token, --token-file, "
            "or set MENDER_ACCESS_TOKEN environment variable.",
            err=True
        )
        sys.exit(1)

    # Create and run server
    server = MenderMCPServer(server_url, token)

    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        click.echo("\nServer stopped by user.", err=True)
    except Exception as e:
        click.echo(f"Server error: {e}", err=True)
        sys.exit(1)
    finally:
        server.mender_client.close()


if __name__ == "__main__":
    main()
