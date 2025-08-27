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
3. Create a new token with **appropriate permissions**:
   - **Required**: `Device Management` - Read device status, inventory, and attributes
   - **Required**: `Deployment Management` - Read deployment status and history
   - **Optional**: `Artifact Management` - View artifacts and releases
   - **Optional**: `Device Logs` - Access deployment logs (if enabled)
4. Save the token securely in a protected location
5. **Security Note**: Never commit tokens to version control or share in plain text

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
- **get_deployment_device_log**: Get deployment logs for a specific device in a deployment (✅ works with failed deployments)
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

### Token Security
- **Read-only Access**: This server only provides read-only access to Mender APIs
- **Token Protection**: Personal Access Tokens should be stored securely (environment variables, secure files)
- **No Destructive Operations**: No device control, deployment creation, or configuration changes
- **Minimal Permissions**: Use tokens with only necessary permissions (Device Management, Deployment Management)

### Security Best Practices
- **Environment Variables**: Store tokens in `MENDER_ACCESS_TOKEN` environment variable
- **Token Files**: Use `~/.mender/token` with restricted file permissions (600)
- **Regular Rotation**: Rotate Personal Access Tokens periodically
- **Network Security**: All API communication uses HTTPS only
- **Error Sanitization**: Error messages avoid exposing sensitive token data

### Token Permissions Required

| Feature | Required Permission | Optional Permission |
|---------|-------------------|--------------------|
| Device listing/status | Device Management | - |
| Deployment monitoring | Deployment Management | - |
| Device inventory | Device Management | - |
| Deployment logs | Deployment Management | Device Logs |
| Release information | Deployment Management | Artifact Management |

## Troubleshooting

### Authentication Issues

**HTTP 401 - Unauthorized:**
- Verify your Personal Access Token is valid and not expired
- Check that the token has appropriate permissions (Device Management, Deployment Management)
- Ensure your Mender account has access to the devices/deployments
- Confirm token is properly formatted (no extra spaces or characters)

**HTTP 403 - Forbidden:**
- Token lacks required permissions for the requested operation
- Add Device Management permission for device operations
- Add Deployment Management permission for deployment operations
- Contact Mender admin to verify account permissions

### API Errors

**HTTP 404 - Not Found:**
- Confirm your Mender server URL is correct (https://hosted.mender.io)
- Verify specific device/deployment IDs exist in your Mender account
- Check if API endpoints are available in your Mender version
- For deployment logs: 404 is normal for successful deployments

**HTTP 429 - Rate Limited:**
- API rate limit exceeded - wait and retry
- Reduce frequency of API calls
- Implement exponential backoff in your usage patterns

**HTTP 500+ - Server Errors:**
- Temporary Mender server issues - retry after delay
- Check Mender status page for known issues
- Verify network connectivity to the Mender server

**Connection/Timeout Errors:**
- Check your network connectivity to the Mender server
- Verify firewall allows HTTPS connections to Mender
- Consider increasing timeout for large device fleets
- Verify DNS resolution for your Mender server URL

### Claude Code Integration

- Ensure the mcp-server-mender command is in your PATH
- Verify your MCP configuration file syntax is correct
- Check Claude Code logs for connection errors

### Deployment Logs Issues

- **"No deployment logs found"**: This is normal for successful deployments - logs are typically only retained for failed deployments
- **HTTP 404 errors**: Deployment logs API endpoints may not be available in your Mender configuration or API version  
- **Empty log responses**: Some Mender installations don't enable deployment logging by default
- **Successfully working**: ✅ Deployment logs now correctly parse both JSON and plain text responses from failed deployments

## Performance Considerations

### Large Device Fleet Management

**Device Count Guidelines:**
- **Small fleets** (1-50 devices): Default settings work well
- **Medium fleets** (50-200 devices): Consider increasing timeout values
- **Large fleets** (200+ devices): May need pagination and timeout adjustments
- **Enterprise fleets** (1000+ devices): Implement caching and batch operations

**Performance Optimization:**
- **API Limits**: Use appropriate limit values (devices: max 500, deployments: max 100)
- **Timeouts**: Default 30-second timeout may need adjustment for large operations
- **Memory Usage**: Resource endpoints load all data into memory - monitor usage
- **Rate Limiting**: Mender API has rate limits - implement backoff strategies

**Recommended Settings for Large Fleets:**
```json
{
  "mcpServers": {
    "mender": {
      "command": "mcp-server-mender",
      "args": [
        "--server-url", "https://hosted.mender.io",
        "--access-token", "YOUR_TOKEN"
      ],
      "env": {
        "MENDER_HTTP_TIMEOUT": "60",
        "MENDER_MAX_DEVICES": "100"
      }
    }
  }
}
```

## API Compatibility

### Mender Version Support

**Tested Versions:**
- **Mender 3.8.x**: Full compatibility with all features
- **Mender 3.7.x**: Compatible with automatic v2→v1 API fallback
- **Mender 3.6.x**: Limited compatibility (some features may be unavailable)

**API Version Strategy:**
- **Primary**: Uses Mender API v2 endpoints when available
- **Fallback**: Automatically falls back to v1 endpoints for compatibility
- **Feature Detection**: Gracefully handles missing endpoints or features

**Feature Compatibility Matrix:**

| Feature | Mender 3.8+ | Mender 3.7 | Mender 3.6 |
|---------|-------------|-------------|-------------|
| Device Management | ✅ Full | ✅ Full | ✅ Full |
| Deployment Tracking | ✅ Full | ✅ Full | ✅ Full |
| Release Management | ✅ Full | ✅ v1 API | ⚠️ Limited |
| Device Inventory | ✅ Full | ✅ Full | ⚠️ Limited |
| Deployment Logs | ✅ Full | ⚠️ Partial | ❌ None |

**Legend:** ✅ Full Support, ⚠️ Partial/Limited, ❌ Not Supported

## Production Deployment

### Environment Setup

**Production Configuration:**
```bash
# Environment variables for production
MENDER_ACCESS_TOKEN=your_production_token
MENDER_SERVER_URL=https://hosted.mender.io
MCP_LOG_LEVEL=INFO
MENDER_HTTP_TIMEOUT=60
```

**Security Hardening:**
- Use dedicated service account with minimal permissions
- Rotate access tokens regularly (quarterly recommended)
- Monitor token usage and API call patterns
- Implement network restrictions if possible

**Monitoring & Observability:**
- Monitor API response times and error rates
- Set up alerts for authentication failures
- Track device fleet growth and adjust limits accordingly
- Monitor memory usage for large resource operations

**Capacity Planning:**
- **Memory**: ~1MB per 100 devices in resource operations
- **Network**: ~10KB per device for typical API calls
- **API Calls**: ~2-5 calls per device listing operation
- **Response Time**: Target <2 seconds for most operations

## Limitations

- **Read-only**: No device control or deployment creation
- **Rate Limits**: Subject to Mender API rate limits (no built-in backoff)
- **No Caching**: Always fetches fresh data (planned for iteration 2)  
- **Single Tenant**: One Mender organization per server instance
- **Memory Usage**: Large device fleets (1000+) may cause memory pressure
- **Deployment Logs**: Available for failed deployments with smart parsing for multiple response formats (successful deployment logs typically not retained)
- **No Artifacts Filtering**: `get_artifacts()` method doesn't support filtering parameters
- **API Version Dependencies**: Some features require specific Mender API versions (automatic fallback v2→v1)

## License

MIT License - see LICENSE file for details.