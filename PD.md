# Project Architecture Documentation - Mender MCP Server

## Executive Summary

The Mender MCP Server is a Model Context Protocol (MCP) implementation that bridges AI assistants with the Mender IoT platform, enabling natural language interactions for device management, deployment monitoring, and system auditing. This Python-based server provides a secure, read-only interface to Mender's REST APIs, allowing AI agents like Claude Code to query and monitor IoT device fleets through conversational commands. The architecture prioritizes security, input validation, and user-friendly error handling while maintaining stateless operation and comprehensive logging capabilities.

The system serves as a critical integration layer for DevOps teams, security engineers, and support personnel who need quick access to IoT device status, deployment progress, and system audit information without directly interacting with the Mender web interface or APIs.

## System Overview

### Purpose & Domain

The Mender MCP Server operates in the IoT device management domain, specifically targeting over-the-air (OTA) update management and fleet monitoring use cases. It addresses the gap between conversational AI interfaces and specialized IoT management platforms, enabling:

- Natural language queries for device status and inventory
- Automated deployment monitoring and troubleshooting
- Security audit and compliance reporting
- Real-time fleet health assessment
- Historical deployment analysis

### Technology Stack

**Core Technologies:**
- **Language**: Python 3.8+ (chosen for rapid development, extensive library ecosystem)
- **MCP Framework**: mcp>=1.0.0 (Model Context Protocol standard implementation)
- **HTTP Client**: httpx>=0.24.0 (modern async-capable HTTP client with connection pooling)
- **Data Validation**: Pydantic>=2.0.0 (type-safe data validation and serialization)
- **CLI Framework**: Click>=8.0.0 (user-friendly command-line interface)
- **Date Handling**: python-dateutil>=2.8.0 (robust datetime parsing)

**Development Tools:**
- **Testing**: pytest>=7.0.0 (comprehensive test framework)
- **Code Quality**: black, isort, mypy, ruff (formatting, import sorting, type checking, linting)
- **Build System**: Hatchling (PEP 517 compliant build backend)

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        AI Assistant                             │
│                    (Claude Code, etc.)                          │
└────────────────────────┬────────────────────────────────────────┘
                         │ MCP Protocol (stdio)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   MenderMCPServer                               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                 MCP Request Handlers                      │  │
│  │  • list_resources() • read_resource() • list_tools()    │  │
│  │  • call_tool()                                          │  │
│  └──────────────────────┬───────────────────────────────────┘  │
│                         │                                       │
│  ┌──────────────────────▼───────────────────────────────────┐  │
│  │              Security & Validation Layer                 │  │
│  │  • Input validation (Pydantic models)                   │  │
│  │  • Token masking & sanitization                        │  │
│  │  • Error sanitization                                  │  │
│  └──────────────────────┬───────────────────────────────────┘  │
│                         │                                       │
│  ┌──────────────────────▼───────────────────────────────────┐  │
│  │                MenderAPIClient                           │  │
│  │  • HTTP request handling                                │  │
│  │  • Authentication management                            │  │
│  │  • Response parsing & model conversion                  │  │
│  └──────────────────────┬───────────────────────────────────┘  │
└─────────────────────────┼───────────────────────────────────────┘
                         │ HTTPS (Bearer Token Auth)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Mender Platform                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐              │
│  │  Device    │  │ Deployment │  │  Inventory │              │
│  │ Management │  │ Management │  │ Management │              │
│  └────────────┘  └────────────┘  └────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

## Architectural Patterns & Design Decisions

### Primary Pattern

The system follows a **Layered Architecture** pattern with clear separation of concerns:

1. **Protocol Layer**: MCP server implementation handling stdio communication
2. **Handler Layer**: Request routing and response formatting
3. **Security Layer**: Input validation and data sanitization
4. **API Client Layer**: HTTP communication and data transformation
5. **External Integration Layer**: Mender platform APIs

### Design Principles

- **Security-First Design**: All inputs validated, outputs sanitized, tokens masked
- **Fail-Safe Defaults**: Read-only operations, conservative error handling
- **Stateless Operation**: No persistent state between requests
- **Progressive Enhancement**: Graceful degradation for older Mender versions
- **Defensive Programming**: Comprehensive error handling at every layer
- **Privacy by Design**: Automatic masking of sensitive information

### Key Architectural Decisions

1. **Synchronous over Asynchronous**: Despite httpx supporting async, the implementation uses synchronous calls for simplicity and MCP compatibility
2. **Pydantic for Validation**: Chosen for its robust validation, automatic documentation, and type safety
3. **Multi-Endpoint Fallback**: Automatically tries v2 then v1 API endpoints for compatibility
4. **Structured Logging**: Custom SecurityLogger ensures no credential leakage
5. **Token Management Flexibility**: Supports environment variables, files, and direct input
6. **Caching Omission**: No caching implemented to ensure real-time data accuracy

## Component Architecture

### Component Inventory

1. **MenderMCPServer** - Main server orchestrator
2. **MenderAPIClient** - Mender API communication handler
3. **SecurityLogger** - Secure logging utility
4. **ErrorSanitizer** - Error message sanitization
5. **Input Validators** - Pydantic models for input validation
6. **Data Models** - Pydantic models for API responses
7. **CLI Interface** - Command-line entry point

### Component Details

#### MenderMCPServer

- **Purpose**: Core MCP server implementation managing protocol communication
- **Technology**: Python, MCP library
- **Key Responsibilities**:
  - Register and handle MCP resources and tools
  - Route requests to appropriate handlers
  - Format responses for AI consumption
  - Manage server lifecycle
- **Interfaces**:
  - Input: MCP protocol messages via stdio
  - Output: Formatted text responses
- **Dependencies**:
  - MenderAPIClient for API operations
  - Security modules for validation
- **Data Models**:
  - Uses MCP protocol types (Resource, Tool, TextContent)

#### MenderAPIClient

- **Purpose**: Encapsulates all Mender API interactions
- **Technology**: httpx for HTTP, Pydantic for data modeling
- **Key Responsibilities**:
  - Manage authentication headers
  - Execute HTTP requests with error handling
  - Parse and validate API responses
  - Handle API version compatibility
- **Interfaces**:
  - Input: Method calls with parameters
  - Output: Pydantic model instances
- **Dependencies**:
  - httpx client for HTTP communication
  - Security modules for error sanitization
- **Data Models**:
  - MenderDevice, MenderDeployment, MenderRelease, etc.

#### Security Components

- **Purpose**: Ensure security throughout the system
- **Technology**: Python regex, Pydantic validation
- **Key Responsibilities**:
  - Mask tokens and credentials in logs
  - Sanitize error messages
  - Validate all user inputs
  - Prevent injection attacks
- **Interfaces**:
  - Input: Raw strings and dictionaries
  - Output: Sanitized/validated data
- **Dependencies**:
  - Python standard library
  - Pydantic for validation models
- **Data Models**:
  - DeviceIdInput, DeploymentIdInput, LimitInput, etc.

## Communication Architecture

### Message Flow Patterns

1. **Request Flow**:
   ```
   AI → MCP Request → Server Handler → Validation → API Client → Mender
   ```

2. **Response Flow**:
   ```
   Mender → API Client → Data Model → Formatter → MCP Response → AI
   ```

### API Specifications

**MCP Resources** (Data endpoints):
- `mender://devices` - Device listing
- `mender://deployments` - Deployment listing
- `mender://releases` - Release catalog
- `mender://inventory` - Device inventory
- `mender://audit-logs` - Audit trail

**MCP Tools** (Actions):
- `get_device_status` - Query specific device
- `list_devices` - List devices with filtering
- `get_deployment_status` - Check deployment
- `list_deployments` - List deployments
- `get_release_status` - Release details
- `list_releases` - Release listing
- `get_device_inventory` - Device attributes
- `get_deployment_logs` - Deployment logs
- `get_audit_logs` - System audit logs

### Event/Message Schemas

All tools use JSON schemas for input validation:
```json
{
  "type": "object",
  "properties": {
    "device_id": {
      "type": "string",
      "description": "Device identifier"
    }
  },
  "required": ["device_id"]
}
```

### Integration Points

- **Mender REST API v1/v2**: Primary integration via HTTPS
- **stdio Interface**: MCP protocol communication
- **File System**: Token file reading
- **Environment Variables**: Configuration input

## Data Architecture

### Storage Systems

The system is **stateless** and maintains no persistent storage. All data is:
- Fetched on-demand from Mender APIs
- Transformed in-memory
- Returned immediately to the client

### Data Flow

1. **Input Processing**:
   - Raw JSON from MCP protocol
   - Validation through Pydantic models
   - Sanitization of sensitive data

2. **API Communication**:
   - JSON requests to Mender
   - JSON responses parsed to Pydantic models
   - Error responses sanitized

3. **Output Generation**:
   - Pydantic models formatted to readable text
   - Structured data for AI comprehension
   - Consistent formatting patterns

### Schema Design

**Core Data Models**:
- `MenderDevice`: Device state and attributes
- `MenderDeployment`: Deployment status and statistics
- `MenderRelease`: Release metadata and artifacts
- `MenderInventoryItem`: Device attributes
- `MenderDeploymentLog`: Deployment execution logs
- `MenderAuditLog`: System audit entries

## Testing Architecture

### Testing Strategy

- **Unit Testing**: Component isolation with mocks
- **Integration Testing**: API client validation
- **Security Testing**: Input validation and sanitization
- **Format Testing**: Output formatting verification

### Test Organization

```
tests/
├── test_server.py       # Server component tests
├── test_security.py     # Security validation tests
└── __init__.py
```

### Coverage Approach

- Minimum 90% code coverage target
- Focus on security-critical paths
- Comprehensive input validation testing
- Error handling verification

## Build & Deployment Architecture

### Build Process

1. **Package Building**:
   ```bash
   pip install -e .  # Development installation
   pip install .     # Production installation
   ```

2. **Dependency Resolution**:
   - Requirements specified in pyproject.toml
   - Development dependencies in requirements.txt

### Deployment Strategy

- **Standalone Execution**: Direct CLI invocation
- **MCP Integration**: Configuration in AI assistant settings
- **Container Support**: Can be containerized with Python base image

### Environment Configuration

**Required Configuration**:
- `MENDER_ACCESS_TOKEN`: Authentication token
- `--server-url`: Mender server endpoint

**Optional Configuration**:
- `--token-file`: Alternative token source
- `MCP_LOG_LEVEL`: Debug logging control

## Operational Considerations

### Monitoring & Observability

- **Logging Levels**: INFO, DEBUG, ERROR, CRITICAL
- **Security Logging**: Automatic credential masking
- **Error Tracking**: Sanitized error reporting
- **Performance Metrics**: Response time tracking

### Performance Characteristics

- **Request Timeout**: 30 seconds default
- **No Caching**: Real-time data accuracy prioritized
- **Connection Pooling**: httpx client connection reuse
- **Rate Limiting**: Respects Mender API limits

### Scaling Strategy

- **Horizontal Scaling**: Multiple instances supported
- **Stateless Design**: No coordination required
- **API Rate Limits**: Primary scaling constraint

### Security Measures

- **Authentication**: Bearer token authentication
- **Input Validation**: Comprehensive Pydantic validation
- **Output Sanitization**: Automatic credential masking
- **Error Sanitization**: No information leakage
- **Path Traversal Prevention**: Input pattern validation
- **Injection Prevention**: Parameterized API calls

## Technical Debt & Improvement Opportunities

### Identified Enhancements

1. **Caching Layer**: Optional Redis cache for frequently accessed data
2. **Async Support**: Full async implementation for better concurrency
3. **Batch Operations**: Support for bulk device queries
4. **Webhook Integration**: Real-time deployment status updates
5. **User Management**: RBAC and user information queries (planned)
6. **Multi-Tenant Support**: Enhanced organization-level operations
7. **Metrics Collection**: Prometheus metrics for monitoring
8. **Response Streaming**: Streaming for large result sets
9. **Offline Mode**: Local data caching for disconnected operation
10. **Plugin Architecture**: Extensible tool registration system

### Migration Paths

- **Python 3.12+**: Leverage newer language features
- **MCP v2**: Prepare for protocol evolution
- **Mender v4**: Support upcoming API changes
- **GraphQL Support**: Alternative query interface

### Code Quality Improvements

- **Type Coverage**: Increase mypy strict checking
- **Documentation**: Expand inline documentation
- **Test Coverage**: Achieve 95%+ coverage
- **Performance Tests**: Add load testing suite
- **Security Scanning**: Integrate SAST/DAST tools

## Conclusion

The Mender MCP Server successfully bridges the gap between conversational AI and IoT device management, providing a secure, extensible, and user-friendly interface to the Mender platform. Its layered architecture, comprehensive security measures, and focus on operational safety make it suitable for production enterprise environments while maintaining the flexibility needed for rapid feature development and AI integration evolution.