# Mender MCP Server

Model Context Protocol (MCP) server for Mender IoT platform integration.

## Overview

This project provides an MCP server that enables AI assistants like Claude Code to interact with Mender platform services for device management, deployment tracking, and system monitoring.

## Features

- **Device Management**: List devices, check device status, filter by device type
- **Deployment Tracking**: Monitor deployment status, list deployments, check deployment details
- **Artifact Information**: View available artifacts and their compatibility
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
- "What artifacts are available?"

### Available Tools

The server provides these tools:

- **get_device_status**: Get current status of a specific device
- **list_devices**: List devices with optional filtering (status, device type, limit)
- **get_deployment_status**: Check deployment progress and details
- **list_deployments**: List deployments with optional filtering (status, limit)

### Available Resources

The server provides these resources:

- **mender://devices**: Complete device inventory
- **mender://deployments**: All deployments 
- **mender://artifacts**: Available artifacts
- **mender://devices/{device_id}**: Specific device details
- **mender://deployments/{deployment_id}**: Specific deployment details

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

## Limitations

- **Read-only**: No device control or deployment creation
- **Rate Limits**: Subject to Mender API rate limits
- **No Caching**: Always fetches fresh data (planned for iteration 2)
- **Single Tenant**: One Mender organization per server instance

## License

MIT License - see LICENSE file for details.