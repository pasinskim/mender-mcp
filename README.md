# Mender MCP Server

Model Context Protocol (MCP) server for seamless Mender IoT platform integration with AI assistants.

## Overview

The **Mender MCP Server** enables AI assistants like Claude Code to interact directly with your Mender IoT platform for device management, deployment tracking, and system monitoring. Through natural language commands, you can manage your IoT devices, monitor deployments, and troubleshoot issues without leaving your development environment.

## ✨ Key Features

- 🔍 **Device Management**: List, filter, and monitor IoT device status across your fleet
- 🚀 **Deployment Tracking**: Monitor deployment progress, success rates, and failure analysis
- 📊 **Real-time Monitoring**: Check device inventory, hardware specs, and system attributes
- 📝 **Deployment Logs**: Access detailed logs for failed deployments and troubleshooting
- 🏷️ **Release Management**: Browse releases, artifacts, and compatibility information
- 🔒 **Enterprise Security**: Token-based authentication with comprehensive input validation
- 📋 **Read-only Operations**: Safe monitoring without risk of accidental device control
- 🌐 **Multi-platform Support**: Works with hosted Mender and on-premise installations

## 🚀 Quick Start

### 1. Installation

#### Prerequisites
- **Python 3.8+** installed on your system
- **Active hosted Mender account**
- **Claude Code** or other AI agent capable of using MCP 

#### Install from Source
```bash
# Clone the repository
git clone https://github.com/pasinskim/mender-mcp.git
cd mender-mcp

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# Install the package
pip install -e .
```

#### Verify Installation
```bash
# Test the server installation
mcp-server-mender --help
```

### 2. Mender Authentication Setup

#### Get Your Personal Access Token

1. **Log into hosted Mender**:
   - Go to [hosted.mender.io](https://hosted.mender.io) (or your on-premise URL)
   - Sign in with your Mender account credentials

2. **Navigate to Settings**:
   - Click your profile/avatar in the top right
   - Select **"Settings"** from the dropdown menu

3. **Create Personal Access Token**:
   - Go to **"Personal Access Tokens"** tab
   - Click **"Generate new token"**
   - **Token Name**: `mender-mcp-integration` (or descriptive name)
   - **Permissions Required**:
     - ✅ **Device Management** - Read device status, inventory, and attributes
     - ✅ **Deployment Management** - Read deployment status and history  
     - ✅ **Artifact Management** - View artifacts and releases (optional)
     - ✅ **Device Logs** - Access deployment logs (optional, if available)

4. **Save Your Token**:
   - Copy the generated token immediately (it won't be shown again)
   - Store it securely using one of the methods below

#### Token Storage Options

**Option 1: Environment Variable (Recommended)**
```bash
# Add to your ~/.bashrc, ~/.zshrc, or shell profile
export MENDER_ACCESS_TOKEN="your_personal_access_token_here"

# Reload your shell or run:
source ~/.bashrc  # or ~/.zshrc
```

**Option 2: Secure Token File**
```bash
# Create secure token directory
mkdir -p ~/.mender
chmod 700 ~/.mender

# Save token to file (replace with your actual token)
echo "your_personal_access_token_here" > ~/.mender/token
chmod 600 ~/.mender/token
```

### 3. Claude Code Integration

#### Add to Claude Code Configuration

1. **Open Claude Code Settings**:
   - In Claude Code, go to Settings → MCP Servers
   - Or edit your MCP configuration file directly

2. **Add Mender MCP Server**:

**Using Environment Variable (Recommended):**
```json
{
  "mcpServers": {
    "mender": {
      "command": "mcp-server-mender",
      "args": [
        "--server-url", "https://hosted.mender.io"
      ],
      "env": {
        "MENDER_ACCESS_TOKEN": "your_token_here"
      }
    }
  }
}
```

**Using Token File:**
```json
{
  "mcpServers": {
    "mender": {
      "command": "mcp-server-mender", 
      "args": [
        "--server-url", "https://hosted.mender.io",
        "--token-file", "~/.mender/token"
      ]
    }
  }
}
```

**For On-Premise Mender:**
```json
{
  "mcpServers": {
    "mender": {
      "command": "mcp-server-mender",
      "args": [
        "--server-url", "https://your-mender-server.company.com",
        "--token-file", "~/.mender/token"
      ]
    }
  }
}
```

3. **Restart Claude Code** to load the new MCP server configuration.

## 💬 Usage Examples

Once configured, you can interact with your Mender devices using natural language in Claude Code:

### Device Management
```
"List all my Mender devices"
"Show me devices with status 'accepted'"
"Check the status of device abc123"
"What devices are offline?"
"Show me Raspberry Pi devices"
```

### Deployment Monitoring
```
"What deployments are currently running?"
"Show me the latest deployments"
"Check deployment status for ID def456"
"List failed deployments"
"What deployments finished today?"
```

### Device Inventory & Hardware
```
"What inventory information do you have for device abc123?"
"Show me hardware specs for all devices"
"List devices by device type"
"What Mender client versions are running?"
```

### Release & Artifact Management
```
"What releases are available?"
"Show me details for release mender-demo-artifact-3.8.2"
"List releases with 'demo' in the name"
"What artifacts are compatible with Raspberry Pi?"
```

### Troubleshooting & Logs
```
"Get deployment logs for the latest failed deployment"
"Show me deployment logs for device abc123 in deployment def456"
"Why did my last deployment fail?"
"Show me error logs for failed deployments"
```

### Fleet Analysis & Monitoring
```
"How many devices do I have in total?"
"What's the distribution of device types in my fleet?"
"Show me devices that haven't connected recently"
"Which devices are running outdated software versions?"
"What's the success rate of my recent deployments?"
"Show me devices grouped by their hardware platform"
```

### Security & Compliance Monitoring
```
"List devices with pending authorization"
"Show me devices that failed authentication"
"What devices have been rejected and why?"
"Check which devices need attention or manual intervention"
"Show me the security status of my device fleet"
```

### Operational Intelligence
```
"Compare deployment performance across different device types"
"What's the average deployment time for Raspberry Pi devices?"
"Show me deployment trends over the past week"
"Which releases have the highest failure rates?"
"Find devices with unusual inventory attributes"
"What's the geographic distribution of my devices?" (if location data available)
```

### Audit Logs
```
"Show me the audit logs for the last 24 hours"
"Get audit logs for user admin@company.com"
"Show me all device_accept actions in the logs"
"What deployment actions were performed yesterday?"
"Show me audit logs filtered by deployment object type"
"Get recent login attempts from the audit logs"
```

### Automated Workflows
```
"Create a report of all failed deployments this month"
"Monitor deployment def456 and alert me if any devices fail"
"Check if all critical devices received the security update"
"Generate a fleet health summary for management review"
"Track the rollout progress of release v2.1.0"
```

### Custom Logging & Debugging

**Enable debug logging:**
```json
{
  "mcpServers": {
    "mender": {
      "command": "mcp-server-mender",
      "args": [
        "--server-url", "https://hosted.mender.io",
        "--token-file", "~/.mender/token"
      ],
      "env": {
        "MCP_LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

## 🔧 Command Line Interface

You can also run the server directly for testing:

```bash
# Using environment variable
export MENDER_ACCESS_TOKEN="your_token"
mcp-server-mender --server-url https://hosted.mender.io

# Using token file
mcp-server-mender --server-url https://hosted.mender.io --token-file ~/.mender/token

# Using direct token (not recommended)
mcp-server-mender --server-url https://hosted.mender.io --access-token your_token

# On-premise installation
mcp-server-mender --server-url https://mender.company.com --token-file ~/.mender/token
```

## 📋 Available Tools & Resources

### MCP Tools (Actions)
- **get_device_status**: Get current status of a specific device
- **list_devices**: List devices with filtering (status, device type, limit)
- **get_deployment_status**: Check deployment progress and details  
- **list_deployments**: List deployments with status filtering
- **get_deployment_device_log**: Get deployment logs for a specific device
- **get_deployment_logs**: Get deployment logs for all devices in a deployment
- **get_release_status**: Get detailed information about a specific release
- **list_releases**: List releases with filtering (name, tag, limit)
- **get_device_inventory**: Get complete inventory attributes for a device
- **list_device_inventory**: List device inventories with filtering
- **get_inventory_groups**: Get all device inventory groups
- **get_audit_logs**: Get Mender audit logs with comprehensive filtering (user, action, date range, object type)

### MCP Resources (Data Access)
- **mender://devices**: Complete device inventory
- **mender://deployments**: All deployments 
- **mender://artifacts**: Available artifacts
- **mender://releases**: Complete release catalog
- **mender://inventory**: Device inventory with hardware specs and custom attributes
- **mender://inventory-groups**: Device grouping information
- **mender://audit-logs**: System audit logs for user actions and system changes
- **mender://devices/{device_id}**: Specific device details
- **mender://deployments/{deployment_id}**: Specific deployment details
- **mender://releases/{release_name}**: Specific release details

## 🔒 Security & Best Practices

### Token Security
- ✅ **Use environment variables** or secure token files (not direct configuration)
- ✅ **Set appropriate permissions** on token files (`chmod 600 ~/.mender/token`)
- ✅ **Rotate tokens regularly** (quarterly recommended for production)
- ✅ **Use minimal required permissions** (Device Management, Deployment Management)
- ❌ **Never commit tokens** to version control or share in plain text

### Performance Considerations
- **API rate limits**: Respect Mender's API limits with reasonable request frequencies
- **Fleet size scaling**: Use appropriate limit values for large device fleets
- **Timeout settings**: Adjust timeouts for large deployments and slow networks
- **Memory usage**: Monitor memory consumption with 1000+ device fleets

## 🐛 Troubleshooting

### Common Issues

**Authentication Errors:**
```
Error: HTTP 401 - Authentication failed
```
- Verify your Personal Access Token is valid and not expired
- Check token has Device Management and Deployment Management permissions
- Ensure token is properly formatted (no extra spaces or newlines)

**Permission Errors:**
```
Error: HTTP 403 - Access denied
```
- Add required permissions: Device Management, Deployment Management
- Contact your Mender admin to verify account access levels
- Check if organization access is properly configured

**Connection Issues:**
```
Error: Request failed - Network error occurred
```
- Verify Mender server URL is correct (https://hosted.mender.io)
- Check network connectivity and firewall settings
- Confirm DNS resolution works for your Mender server
- Test with browser access to the same URL

**Configuration Problems:**
```
Error: Command 'mcp-server-mender' not found
```
- Ensure virtual environment is activated: `source venv/bin/activate`
- Verify installation completed successfully: `pip install -e .`
- Check PATH includes the virtual environment's bin directory

### Deployment Logs Issues

**"No deployment logs found":**
- This is normal for successful deployments (logs typically only retained for failures)
- Failed deployments should have detailed logs available
- Some Mender configurations don't enable deployment logging by default

**Empty or truncated logs:**
- Large deployments may have truncated logs due to size limits
- Check device-side logs for more detailed information
- Consider deployment size and timeout settings

### Getting Help

1. **Check server connectivity**: Test with `mcp-server-mender --help`
2. **Verify Mender access**: Log into Mender web interface with same credentials
3. **Test token manually**: Use Mender API documentation to test token directly
4. **Enable debug logging**: Set `MCP_LOG_LEVEL=DEBUG` for detailed output
5. **Review Claude Code logs**: Check Claude Code's MCP connection status

## 🧪 Development & Testing

### Running Tests
```bash
# Activate virtual environment
source venv/bin/activate

# Install test dependencies
pip install pytest

# Run all tests
pytest tests/

# Run security tests only
pytest tests/test_security.py -v

# Run with coverage
pip install pytest-cov
pytest tests/ --cov=src/mcp_server_mender
```
## 📝 License

MIT License - see LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests for any improvements.

## 📞 Support

- **Documentation**: This README and inline help (`--help`)
- **Issues**: GitHub Issues for bug reports and feature requests
- **Community**: Mender Community Hub for general IoT device management discussions