# Mender MCP Server Development Plan

## Overview

This document outlines the development plan for a Model Context Protocol (MCP) server that integrates with Mender.io IoT platform. The server will enable AI assistants like Claude Code to interact with Mender services for device management, deployment tracking, and system monitoring.

## Project Goals

- **Primary**: Enable AI assistants to check device status and deployment information from Mender
- **Secondary**: Provide comprehensive IoT device management capabilities through natural language
- **Integration**: Seamless integration with Claude Code similar to existing Git and Jira MCP servers

## Research Insights

### MCP Server Patterns (from modelcontextprotocol/servers)
- **Modular Architecture**: Each server focuses on specific domain functionality
- **Standardized SDK Usage**: Python, TypeScript, and other language SDKs provide consistent implementation patterns
- **Authentication**: Secure, controlled access with configurable authentication mechanisms
- **Resource & Tool Separation**: Clear distinction between data resources and actionable tools

### Mender API Capabilities
- **Device Management**: Device inventory, status monitoring, configuration management
- **Deployment Operations**: Artifact management, deployment creation/tracking, rollback capabilities
- **Authentication**: JWT tokens, Personal Access Tokens, SSO/SAML support
- **Multi-API Structure**: Device APIs, Management APIs, Internal APIs

## Technical Architecture

### Technology Stack
- **Language**: Python (leveraging official MCP Python SDK)
- **Protocol**: Model Context Protocol (MCP) specification
- **Integration**: Mender Management APIs
- **Transport**: Standard I/O (stdio) for Claude Code integration

### Core Components

#### 1. Authentication Manager
- Support for Mender Personal Access Tokens (PAT)
- JWT token handling for session management
- Multi-tenant support for different Mender instances
- Secure credential storage and validation

#### 2. API Client Layer
```
MenderAPIClient
├── DeviceManager (Device inventory, status, groups)
├── DeploymentManager (Artifacts, deployments, rollbacks)
├── ConfigurationManager (Device configuration)
└── AuthenticationManager (Device auth, preauthorization)
```

#### 3. MCP Resources
```
Resources (read-only data)
├── /devices/{device_id} - Individual device information
├── /devices - Device inventory with filtering
├── /deployments/{deployment_id} - Deployment details
├── /deployments - Deployment history and status
├── /artifacts - Available artifacts
├── /releases/{release_name} - Individual release information
├── /releases - Release catalog with filtering
└── /device-groups - Device group information
```

#### 4. MCP Tools
```
Tools (actionable operations)
├── get_device_status - Get current status of specific device(s)
├── list_devices - List devices with filtering options
├── get_deployment_status - Check deployment progress
├── list_deployments - List deployments with filtering
├── get_release_status - Get details of specific release
├── list_releases - List releases with filtering options
├── create_deployment - Create new deployment
├── abort_deployment - Stop ongoing deployment
├── get_device_logs - Retrieve device logs (if available)
└── update_device_config - Modify device configuration
```

## Implementation Phases

### Phase 1: Foundation (Week 1-2) ✅ COMPLETED
**Deliverables:**
- [x] Project structure setup following MCP patterns
- [x] Mender API client implementation
- [x] Basic authentication (PAT support)
- [x] Core MCP server skeleton
- [x] Configuration management

**Key Features:**
- Basic device listing
- Simple deployment status checking
- Authentication with Personal Access Tokens

**Implementation Notes:**
- Used Hosted Mender (mender.io SaaS platform) as specified
- Implemented PAT-only authentication (no JWT session management)
- Read-only monitoring operations only (no device control)
- Fail fast error handling (iteration 2 will add graceful degradation)
- No caching (always fresh data as specified)
- Single organization per server instance

### Phase 2: Core Functionality (Week 3-4) ✅ COMPLETED
**Deliverables:**
- [x] Complete device management resources
- [x] Deployment tracking and management tools
- [x] Error handling and logging
- [x] Unit tests for core functionality

**Key Features:**
- Device status monitoring
- ~~Deployment creation and tracking~~ → Read-only deployment status checking only
- Device grouping and filtering
- ~~Comprehensive error handling~~ → Basic fail-fast error handling (comprehensive handling moved to iteration 2)

**Implementation Notes:**
- All device and deployment monitoring tools implemented
- Release management functionality added (list_releases, get_release_status)  
- Read-only approach maintained (no deployment creation)
- Basic unit tests created with pytest
- Status checking and monitoring workflows optimized
- CLI interface with flexible token configuration
- Display formatting with smart truncation (device types: 3, tags: 2)
- API pagination limits: devices (1-500, default 20), deployments (1-100, default 10), releases (1-100, default 20)

### Phase 3: Documentation & Integration (Week 3-4) ✅ COMPLETED
**Original Advanced Features moved to Iteration 2 due to read-only scope**

**Deliverables:**
- [x] Complete documentation with README.md
- [x] Claude Code integration guide
- [x] Example configurations
- [x] Installation and setup instructions
- [x] CLI usage documentation

**Key Features:**
- Production-ready basic deployment
- Comprehensive setup documentation
- Claude Code MCP configuration examples
- Security best practices (read-only, token handling)
- Troubleshooting guide

**Implementation Notes:**
- Focused on documentation and usability instead of advanced features
- Created comprehensive README with all configuration options
- Verified Claude Code integration works properly
- Added security considerations for read-only deployment

## API Integration Details

### Authentication Flow
1. **Personal Access Token (PAT)**: Primary authentication method
2. **JWT Session Management**: For extended operations
3. **Multi-instance Support**: Handle multiple Mender deployments

### Key Endpoints to Integrate
```
Device Management:
- GET /api/management/v2/devauth/devices
- GET /api/management/v2/devauth/devices/{id}
- PUT /api/management/v2/devauth/devices/{id}/status

Deployment Management:
- GET /api/management/v1/deployments/deployments
- POST /api/management/v1/deployments/deployments
- GET /api/management/v1/deployments/deployments/{id}
- PUT /api/management/v1/deployments/deployments/{id}/status

Artifact Management:
- GET /api/management/v1/deployments/artifacts
- POST /api/management/v1/deployments/artifacts

Release Management:
- GET /api/management/v2/deployments/deployments/releases
- GET /api/management/v1/deployments/deployments/releases
- GET /api/management/v1/deployments/deployments/releases/list
- GET /api/management/v2/deployments/deployments/releases/{name}
- GET /api/management/v1/deployments/deployments/releases/{name}
```

### Data Models
```python
Device:
- id, name, status, last_checkin
- device_type, artifacts_installed
- authentication_status, group_membership

Deployment:
- id, name, artifact_name, status
- created, finished, device_count
- statistics (success, failure, pending)
- target_devices, device_groups

Artifact:
- id, name, description, size
- device_types_compatible, created
- download_url, checksum

Release:
- name, artifacts, modified, tags, notes
- artifacts_count, supports v1/v2 API formats
- client-side filtering by name and tag
- display truncation for readability (tags: first 2)
```

## Configuration

### MCP Server Configuration
```json
{
  "mcpServers": {
    "mender": {
      "command": "mender-mcp-server",
      "args": [
        "--server-url", "https://hosted.mender.io",
        "--token-file", "~/.mender/token"
      ]
    }
  }
}
```

### Environment Variables
```bash
MENDER_SERVER_URL=https://hosted.mender.io
MENDER_ACCESS_TOKEN=<personal_access_token>
MENDER_TOKEN_FILE=~/.mender/token
MCP_LOG_LEVEL=INFO
```

## Testing Strategy

### Unit Tests
- API client functionality
- Authentication mechanisms
- Data model validation
- Error handling scenarios

### Integration Tests
- End-to-end MCP protocol communication
- Real Mender API interactions
- Claude Code integration scenarios

### Manual Testing
- Claude Code conversation flows
- Device management workflows
- Deployment monitoring scenarios

## Security Considerations

- **Token Security**: Secure handling of Personal Access Tokens
- **API Rate Limiting**: Respect Mender API limits
- **Input Validation**: Sanitize all user inputs
- **Error Information**: Avoid exposing sensitive data in errors
- **Network Security**: HTTPS-only communication

## Success Metrics

1. **Functional**: All core device and deployment operations working
2. **Integration**: Seamless Claude Code integration
3. **Performance**: Sub-2-second response times for common operations
4. **Reliability**: 99%+ uptime with proper error handling
5. **Documentation**: Complete setup and usage documentation

## Risk Analysis & Mitigation

### Technical Risks
- **API Changes**: Mender API evolution → Version pinning and monitoring
- **Rate Limits**: API throttling → Implement caching and request batching
- **Authentication**: Token expiry → Implement refresh mechanisms

### Development Risks
- **Complexity**: Over-engineering → Start simple, iterate based on feedback
- **Testing**: Limited test environment → Use Mender demo/trial accounts
- **Integration**: Claude Code compatibility → Follow established MCP patterns

## Future Enhancements

### Phase 5+: Advanced Features
- **Real-time Notifications**: WebSocket support for live updates
- **Multi-tenant Management**: Support multiple organizations
- **Advanced Analytics**: Device health trends and deployment insights
- **Custom Integrations**: Plugin system for custom Mender workflows

### Potential Extensions
- **Alerting**: Integration with monitoring systems
- **Automation**: Smart deployment recommendations
- **Reporting**: Custom dashboard generation
- **Mobile Support**: Device management from mobile interfaces

## Getting Started

1. **Prerequisites**: Python 3.8+, Mender account with API access
2. **Setup**: Clone repository, install dependencies
3. **Configuration**: Set up Mender credentials
4. **Testing**: Run basic device listing test
5. **Integration**: Add to Claude Code MCP configuration

---

## Iteration 2: Enhanced Error Handling & Caching

Based on user feedback and the completed iteration 1, the following improvements are planned for iteration 2:

### Scope & Approach
- **Target**: Maintain read-only, hosted Mender focus
- **Error Handling**: Upgrade from fail-fast to graceful degradation with retries
- **Caching**: Add intelligent caching to improve performance and reduce API calls
- **Compatibility**: Maintain backward compatibility with iteration 1

### Phase 1: Enhanced Error Handling (Week 1)
**Deliverables:**
- [ ] Error categorization system (authentication, network, API, validation)
- [ ] Retry logic with exponential backoff for transient failures
- [ ] User-friendly error messages with actionable guidance
- [ ] Structured logging framework for debugging
- [ ] Partial success handling (continue processing when some operations fail)

**Key Features:**
- Resilient API communication with automatic retries
- Clear error messages for common issues
- Graceful degradation when some services are unavailable
- Comprehensive logging for troubleshooting

### Phase 2: Smart Caching System (Week 2)
**Deliverables:**
- [ ] TTL-based caching with configurable durations
- [ ] Cache invalidation based on data relationships
- [ ] LRU eviction policy for memory management
- [ ] Cache bypass options for fresh data when needed
- [ ] Cache warmup for commonly requested data

**Key Features:**
- Device cache: 5 minute TTL
- Deployment cache: 1 minute TTL  
- Artifact cache: 1 hour TTL
- Smart invalidation when related data changes
- 50% reduction in API calls through intelligent caching

### Phase 3: Performance & UX Improvements (Week 3)
**Deliverables:**
- [ ] Batch API operations where possible
- [ ] Async/await for concurrent request handling
- [ ] Enhanced output formatting with tables and summaries
- [ ] Progress indicators for long-running operations
- [ ] Improved pagination handling for large datasets

**Key Features:**
- Faster response times through batching and async operations
- Better user experience with formatted output
- Efficient handling of large device fleets
- Progress feedback for long operations

### Phase 4: Monitoring & Production Readiness (Week 4)
**Deliverables:**
- [ ] Health check endpoints for server monitoring
- [ ] Performance and usage metrics collection
- [ ] Rate limit monitoring and alerting
- [ ] Connection status monitoring
- [ ] End-to-end testing with error scenarios

**Key Features:**
- Production-ready monitoring and observability
- Proactive rate limit management
- Comprehensive error scenario testing
- Performance benchmarking and optimization

### Configuration Changes

#### New CLI Options:
```bash
mcp-server-mender \
  --access-token YOUR_TOKEN \
  --cache-enabled true \
  --cache-ttl-devices 300 \
  --cache-ttl-deployments 60 \
  --max-retries 3 \
  --log-level INFO
```

#### Updated MCP Configuration:
```json
{
  "mcpServers": {
    "mender": {
      "command": "mcp-server-mender",
      "args": [
        "--server-url", "https://hosted.mender.io",
        "--access-token", "YOUR_TOKEN",
        "--cache-enabled", "true",
        "--max-retries", "3",
        "--log-level", "INFO"
      ]
    }
  }
}
```

### Success Metrics
1. **Reliability**: 99.9% uptime with graceful error handling
2. **Performance**: 50% reduction in API calls through intelligent caching
3. **User Experience**: Improved error messages and faster response times
4. **Observability**: Comprehensive logging and monitoring
5. **Compatibility**: Zero breaking changes for existing users

### Backward Compatibility
- All existing configuration options remain supported
- Default behavior matches iteration 1 (no caching, fail fast)
- New features are opt-in through configuration flags
- Existing Claude Code integrations continue working unchanged

---

**Current Status**: ✅ Iteration 1 Complete - Ready for Iteration 2 planning and implementation

---

## Bug Fix: Device Types Display Truncation (TASK-20250826-1350-001)

### Issue
The `_format_release_output()` method artificially truncates device types compatible list to show only first 3 items with "+X more" indicator, preventing users from seeing complete device compatibility information.

### Technical Details
- **Location**: `/src/mcp_server_mender/server.py:417-421`
- **Root Cause**: Intentional truncation with `device_types_compatible[:]3]` for "readability"
- **Impact**: Users cannot make informed deployment decisions without full compatibility info

### Fix Implementation
- **Approach**: Multi-line bullet point format for all device types
- **Line Length**: 64 characters max with smart wrapping
- **Scope**: Device types only (tags truncation addressed separately)

### Acceptance Criteria
- [ ] Display all device types without truncation
- [ ] Use bullet point format for readability with many types
- [ ] Maintain 64 character line length limit
- [ ] Preserve existing functionality for other fields
- [ ] Update tests to validate complete device type display
- [ ] Update documentation if needed

### Status: ✅ Complete - Ready for Tags Fix (MEN-8721)

---

## Bug Fix: Tags Display Truncation (TASK-20250826-1720-002 - MEN-8721)

### Issue
The `_format_releases_output()` method artificially truncates release tags list to show only first 2 tags with "+X more" indicator, preventing users from seeing complete tag information for release identification and management.

### Technical Details
- **Location**: `/src/mcp_server_mender/server.py:464-469`
- **Root Cause**: Intentional truncation with `release.tags[:2]` for "readability"
- **Current Code**: 
  ```python
  tags = [f"{t.get('key', 'N/A')}:{t.get('value', 'N/A')}" for t in release.tags[:2]]
  output += f"  Tags: {', '.join(tags)}"
  if len(release.tags) > 2:
      output += f" (+{len(release.tags) - 2} more)"
  ```
- **Impact**: Users cannot see complete tag information for release identification

### Fix Implementation Strategy
- **Approach**: Reuse the `_format_device_types()` pattern for tags display
- **Method**: Create new `_format_tags()` method following established pattern
- **Line Length**: 64 characters max with smart wrapping
- **Formatting**: 
  - ≤3 tags: inline format `Tags: key1:value1, key2:value2, key3:value3`
  - >3 tags: bullet point format with count `Tags (5): • key1:value1 • key2:value2 ...`

### Implementation Steps
1. **Create `_format_tags()` method** - Mirror `_format_device_types()` pattern
2. **Update `_format_releases_output()`** - Replace truncated tags logic
3. **Handle edge cases** - Empty tags, malformed tags, very long key:value pairs
4. **Add comprehensive tests** - Cover all formatting scenarios
5. **Validate consistency** - Ensure consistent behavior with device types formatting

### Acceptance Criteria
- [x] Display all tags without truncation in release output
- [x] Use bullet point format for readability with 3+ tags
- [x] Maintain 64 character line length limit with smart wrapping
- [x] Handle edge cases (empty, malformed, very long tags)
- [x] Preserve existing functionality for other fields
- [x] Add comprehensive test coverage for all tag formatting scenarios
- [x] Maintain consistency with device types formatting patterns
- [x] Update documentation if needed

### Code Changes Implemented
1. **New Method**: `_format_tags(tags)` in server.py - ✅ Added
2. **Modified Method**: `_format_releases_output()` line 464-469 - ✅ Updated
3. **New Tests**: Tag formatting test cases in test_server.py - ✅ 6 comprehensive tests added
4. **Updated Documentation**: PLAN.md with implementation details - ✅ Completed

### Implementation Summary
- **Created `_format_tags()` method** following the same pattern as `_format_device_types()`
- **Inline format for ≤3 tags**: `Tags: key1:value1, key2:value2, key3:value3`
- **Bullet format for >3 tags**: `Tags (5): • key1:value1 • key2:value2 ...`
- **64-character line length enforced** with smart truncation (key:value...)" 
- **Comprehensive error handling** for missing keys/values (defaults to "N/A")
- **6 test cases added** covering all scenarios: empty, few, many, malformed, long names, line length
- **All tests passing** - 16/16 tests pass including existing functionality

### Status: ✅ Complete - MEN-8721 Resolved