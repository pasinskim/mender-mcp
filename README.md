# Mender MCP Server

Model Context Protocol (MCP) server for Mender IoT platform integration.

## Overview

This project provides an MCP server that enables AI assistants like Claude Code to interact with Mender platform services for device management, deployment tracking, and system monitoring.

## Features

- **Device Management**: List devices, check device status, filter by device type
- **Deployment Tracking**: Monitor deployment status, list deployments, check deployment details
- **Deployment Logs**: Retrieve deployment logs for specific devices and deployments (when available)
- **Release Management**: List releases, check release details, view release artifacts and metadata
- **Artifact Information**: View available artifacts and their compatibility
- **Device Inventory**: Access complete device inventory with hardware specs and custom attributes
- **Read-only Operations**: Safe monitoring and status checking (no destructive operations)
- **Personal Access Token Authentication**: Secure API access using Mender PATs

## Installation

### Prerequisites

- Python 3.8 or higher
- Mender account with API access
- Personal Access Token from your Mender account

### Install from Source

1. Clone the repository:
```bash
git clone <repository-url>
cd mender-mcp
```

2. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the package:
```bash
pip install -e .
```

## Configuration

### Personal Access Token

You need a Personal Access Token from your Mender account:

1. Log in to your Mender account (https://hosted.mender.io)
2. Go to Settings → Personal Access Tokens
3. Create a new token with appropriate permissions
4. Save the token securely

### Claude Code Integration

Add the following to your Claude Code MCP configuration file:

```json
{
  "mcpServers": {
    "mender": {
      "command": "mcp-server-mender",
      "args": [
        "--server-url", "https://hosted.mender.io",
        "--access-token", "YOUR_PERSONAL_ACCESS_TOKEN"
      ]
    }
  }
}
```

Alternative configuration using token file:

```json
{
  "mcpServers": {
    "mender": {
      "command": "mcp-server-mender", 
      "args": [
        "--token-file", "~/.mender/token"
      ]
    }
  }
}
```

### Environment Variables

You can also set the access token via environment variable:

```bash
export MENDER_ACCESS_TOKEN=your_token_here
```

## Usage

Once configured, you can use Claude Code to interact with your Mender devices:

### Example Queries

- "List all my Mender devices"
- "Show me devices with status 'accepted'"
- "Check the status of device abc123"
- "What deployments are currently running?"
- "Show me the latest deployments"
- "What releases are available?"
- "Show me details for release mender-demo-artifact-3.8.2"  
- "List releases with 'demo' in the name"
- "What artifacts are available?"
- "Get deployment logs for device abc123 in deployment def456"
- "Show me deployment logs for the latest deployment"
- "What inventory information do you have for device abc123?"

### Available Tools

The server provides these tools:

- **get_device_status**: Get current status of a specific device
- **list_devices**: List devices with optional filtering (status, device type, limit 1-500, default 20)
- **get_deployment_status**: Check deployment progress and details  
- **list_deployments**: List deployments with optional filtering (status, limit 1-100, default 10)
- **get_deployment_device_log**: Get deployment logs for a specific device in a deployment (logs typically available only for failed deployments)
- **get_deployment_logs**: Get deployment logs for all devices in a deployment (provides summary view with preview of each device's logs)
- **get_release_status**: Get detailed information about a specific release
- **list_releases**: List releases with optional filtering (name, tag, limit 1-100, default 20)
- **get_device_inventory**: Get complete inventory attributes for a specific device
- **list_device_inventory**: List device inventories with optional filtering (limit 1-500, default 20)
- **get_inventory_groups**: Get all device inventory groups

### Available Resources

The server provides these resources:

- **mender://devices**: Complete device inventory
- **mender://deployments**: All deployments 
- **mender://artifacts**: Available artifacts
- **mender://releases**: Complete release catalog
- **mender://inventory**: Device inventory with hardware specs and custom attributes
- **mender://inventory-groups**: Device grouping information
- **mender://devices/{device_id}**: Specific device details
- **mender://deployments/{deployment_id}**: Specific deployment details
- **mender://releases/{release_name}**: Specific release details
- **mender://inventory/{device_id}**: Specific device inventory details

## Display Formatting

The server uses optimized display formatting for readability:

### Detail Views
- **Device Types**: Shows all device types in organized format (previously limited to 3)
- **Release Tags**: Shows all tags in organized format (previously limited to 2)
- **Artifact Details**: Full artifact information including ID, size, signing status
- **Deployment Logs**: Chronological display with timestamps, log levels, and smart message truncation
- **Device Inventory**: Organized by attribute categories with value truncation for long data

### List Views  
- **Release Lists**: Shows primary artifact size and signing status
- **Device Lists**: Compact format with key device information
- **Deployment Lists**: Summary with status and creation date

### API vs Display Limits
- **API Limits**: Control how many items are fetched from Mender (pagination)
- **Display Limits**: Control how many details are shown for readability (formatting)

## CLI Usage

You can also run the server directly:

```bash
# Using access token
mcp-server-mender --access-token YOUR_TOKEN

# Using token file
mcp-server-mender --token-file ~/.mender/token

# Custom server URL (for on-premise installations)
mcp-server-mender --server-url https://your-mender-server.com --access-token YOUR_TOKEN
```

## Development

### Running Tests

```bash
source venv/bin/activate
pip install pytest
pytest tests/
```

### Code Formatting

```bash
pip install black ruff
black src/
ruff check src/
```

## Security

- **Read-only**: This server only provides read-only access to Mender APIs
- **Token Security**: Personal Access Tokens are handled securely 
- **No Destructive Operations**: No device control or deployment creation capabilities
- **Fail Fast**: Clear error messages for authentication and API issues

## Troubleshooting

### Authentication Issues

- Verify your Personal Access Token is valid
- Check that the token has appropriate permissions
- Ensure your Mender account has access to the devices/deployments

### API Errors

- Confirm your Mender server URL is correct
- Check your network connectivity to the Mender server
- Verify API endpoints are accessible

### Claude Code Integration

- Ensure the mcp-server-mender command is in your PATH
- Verify your MCP configuration file syntax is correct
- Check Claude Code logs for connection errors

### Deployment Logs Issues

- **"No deployment logs found"**: This is normal for successful deployments - logs are typically only retained for failed deployments
- **HTTP 404 errors**: Deployment logs API endpoints may not be available in your Mender configuration or API version
- **Empty log responses**: Some Mender installations don't enable deployment logging by default

## Limitations

- **Read-only**: No device control or deployment creation
- **Rate Limits**: Subject to Mender API rate limits
- **No Caching**: Always fetches fresh data (planned for iteration 2)  
- **Single Tenant**: One Mender organization per server instance
- **Deployment Logs**: Available only for failed deployments or specific Mender configurations (successful deployment logs typically not retained)
- **No Artifacts Filtering**: `get_artifacts()` method doesn't support filtering parameters
- **API Version Dependencies**: Some features require specific Mender API versions (automatic fallback v2→v1)

## License

MIT License - see LICENSE file for details.