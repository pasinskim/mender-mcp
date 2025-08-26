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
                tags = [f"{t.get('key', 'N/A')}:{t.get('value', 'N/A')}" for t in release.tags[:2]]
                output += f"  Tags: {', '.join(tags)}"
                if len(release.tags) > 2:
                    output += f" (+{len(release.tags) - 2} more)"
                output += "\n"
            # Show first artifact info if available
            if release.artifacts and len(release.artifacts) > 0:
                artifact = release.artifacts[0]
                if artifact.get('size'):
                    size_mb = artifact.get('size') / (1024*1024)
                    output += f"  Size: {size_mb:.1f} MB\n"
                output += f"  Signed: {artifact.get('signed', False)}\n"
            output += "\n"

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
