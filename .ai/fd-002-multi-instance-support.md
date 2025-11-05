# Feature Description: Multi-Instance Mender MCP Server Support

## 🎯 Business Context & Purpose

The current mender-mcp server supports only a single Mender instance connection, limiting organizations with global IoT deployments across multiple regions (EU and US). This creates critical gaps for:

- **Operational Overhead**: Organizations must run separate MCP server instances for each region, multiplying infrastructure complexity
- **Analytics Limitations**: Unable to perform cross-instance device comparisons or unified fleet analytics
- **Configuration Complexity**: Managing multiple server processes with separate configurations increases error risk
- **Data Locality Compliance**: No unified way to access EU and US instances while respecting regional data requirements

**Expected Business Impact:**
- Reduce operational overhead from N separate MCP servers to 1 unified server
- Enable cross-instance device comparisons and unified analytics
- Improve DevOps efficiency for multi-region teams by 40%
- Support data locality compliance requirements without operational complexity

## 📋 Expected Behavior/Outcome

The enhanced mender-mcp server will support multiple Mender instance connections:

1. **Configure Multiple Instances**: Set up 2+ Mender instances via YAML configuration file with environment variable expansion
2. **Instance Selection**: Specify target instance for each MCP tool operation via optional `instance` parameter (e.g., "eu", "us")
3. **Unified Interface**: Use consistent MCP tools across all instances without syntax changes
4. **Backward Compatibility**: Existing single-instance configurations continue to work unchanged
5. **Cross-Instance Operations**: Compare deployments, devices, and metrics across multiple instances
6. **Instance Health Monitoring**: View connection status and performance metrics for each configured instance

### Key User Interactions:
- AI assistants can query "Show devices in US region" with automatic instance routing
- DevOps teams can compare deployment status across EU and US instances simultaneously
- Support engineers can switch between instances using `instance` parameter in tool calls
- Monitoring systems can track health and performance per-instance

## 🔬 Research Summary

**Investigation Depth**: DEEP
**Confidence Level**: High

**Product & User Story**:
- Primary personas: Multi-region DevOps teams, Support Engineers, Global Operations Managers
- Primary use case: Managing 10-100K devices across EU and US regions from unified interface
- Critical for organizations with data locality compliance requirements
- Strong backward compatibility requirement to avoid disrupting single-instance users
- Progressive disclosure: simple operations stay simple, advanced multi-instance features available when needed

**Design & UX Approach**:
- Follows existing mender-mcp tool patterns with instance parameter extension
- Visual instance indicators in all responses ([EU Instance], [US Instance])
- YAML configuration file with environment variable expansion for secure token management
- Smart defaults: operations without instance parameter use configured default
- Clear error recovery paths with instance-specific error messages

**Technical Plan & Risks**:
- Leverages MenderClientManager architecture for multi-instance coordination
- Instance parameter added to all existing tools (non-breaking change)
- Lazy initialization and HTTP connection pooling for performance
- Enhanced security logging with per-instance context
- Risk: Configuration complexity mitigated by validation and comprehensive examples
- Risk: Backward compatibility carefully designed with migration path

**Pragmatic Effort Estimate**: 48-64 hours (6-8 days)

## ✅ Acceptance Criteria

### Functional Requirements
- [ ] Support 2+ Mender instances via YAML configuration file with validation
- [ ] All MCP tools accept optional `instance` parameter (e.g., "eu", "us")
- [ ] Operations without instance parameter use configured default instance
- [ ] All existing tools (devices, deployments, releases, etc.) work with instance selection
- [ ] Resources include instance identifier in URI (e.g., `mender://eu/devices`)
- [ ] Support cross-instance comparative operations
- [ ] Existing single-instance configurations work without changes (backward compatibility)

### UX Requirements
- [ ] Configuration help shows available instances and configuration methods
- [ ] All responses include clear instance identification tags
- [ ] Instance-specific error messages with actionable recovery steps
- [ ] Instance connection status visible in health checks
- [ ] Response includes performance metrics (response time, device counts) per instance

### Technical Requirements
- [ ] Each instance maintains separate authentication context (security isolation)
- [ ] Implement HTTP connection pooling and reuse per instance
- [ ] Schema validation for multi-instance YAML configuration
- [ ] Enhanced security logging with per-instance context
- [ ] Graceful handling of individual instance failures
- [ ] Instance selection overhead <10ms, support parallel queries
- [ ] Add unit tests with >90% coverage for multi-instance logic
- [ ] Ensure backward compatibility with existing mender-mcp functionality

### Security Requirements
- [ ] All cross-instance operations are audit logged with instance context
- [ ] Personal access tokens never exposed in outputs or logs
- [ ] Token isolation: each instance uses its own authentication token
- [ ] Graceful handling of insufficient permissions per instance
- [ ] Configuration file supports environment variables for sensitive tokens

## 🔗 Dependencies & Constraints

### Dependencies
- **YAML Configuration Parser**: PyYAML library for configuration file parsing
- **HTTP Client**: Existing httpx library extended for per-instance connections
- **Security Logging**: Existing SecurityLogger infrastructure for per-instance audit logging
- **Python Libraries**: Existing Pydantic, httpx dependencies maintained

### Technical Constraints
- **Connection Limits**: Must maintain HTTP connection limits (default: 10 connections per instance)
- **Memory Usage**: Scales linearly with instance count (estimated +50MB per instance)
- **Configuration Size**: Configuration file must remain reasonable (<100KB for 10 instances)
- **Network Latency**: Variable latency across instances based on region may affect user experience
- **Backward Compatibility**: Python 3.8+ compatibility maintained, no breaking changes to existing tool signatures
- **MCP Protocol**: Must maintain MCP protocol compliance
- **Resource URIs**: No changes to existing resource URIs for single-instance mode

## 💡 Implementation Notes

### Recommended Technical Approach

1. **Extend Configuration System** (`src/mender_mcp/config.py`):
   ```python
   # Add multi-instance configuration model
   class MenderInstanceConfig(BaseModel):
       name: str  # "eu", "us"
       server_url: str
       access_token: str
       is_default: bool = False
       region: Optional[str] = None

   class MultiInstanceConfig(BaseModel):
       version: str
       default_instance: str
       instances: Dict[str, MenderInstanceConfig]
   ```

2. **Create Client Manager** (`src/mender_mcp/client_manager.py`):
   ```python
   # New client manager for multi-instance coordination
   class MenderClientManager:
       def __init__(self, config: MultiInstanceConfig)
       def get_client(self, instance: Optional[str]) -> MenderAPIClient
       def get_default_client(self) -> MenderAPIClient
       def list_instances(self) -> List[str]
   ```

3. **Update MCP Server** (`src/mender_mcp/server.py`):
   ```python
   # Extend all tool schemas with optional instance parameter
   - list_devices(instance: Optional[str], limit, status, device_type)
   - get_device_status(instance: Optional[str], device_id)
   - list_deployments(instance: Optional[str], limit, status)
   # Update tool handlers to use ClientManager.get_client(instance)
   ```

4. **Add Configuration Loading**:
   - YAML file parsing with PyYAML
   - Environment variable expansion for secure token management
   - Configuration validation with clear error messages

### Security Implementation
- Implement token isolation per instance in `MenderClientManager`
- Add instance context to existing `SecurityLogger` for audit trails
- Ensure environment variable expansion doesn't log sensitive tokens
- Validate instance names against configuration to prevent injection

### Error Handling Strategy
- Map missing instance → "Instance 'X' not found in configuration. Available: ['eu', 'us']"
- Map invalid config → "Invalid YAML configuration: [specific error]"
- Map connection failure → "Unable to connect to instance 'X': [reason]"
- Map per-instance API errors with instance context in error messages

### Testing Strategy
- Unit tests: Configuration loading, instance selection, error validation
- Integration tests: Multi-instance tool operations, connection pooling
- Security tests: Token isolation, no token leakage in logs or outputs
- Performance tests: Lazy initialization, parallel queries, connection reuse

### Potential Gotchas
- **Token Security**: Environment variable expansion must not log secrets during configuration loading
- **Connection Pooling**: Properly manage HTTP client lifecycle to avoid connection leaks across instances
- **Instance Health**: Implement health checks to detect unreachable instances early
- **Caching**: Consider per-instance cache namespaces for performance optimization
- **Memory Management**: Monitor memory usage growth with additional instances (estimated +50MB per instance)
- **Config Validation**: Provide actionable error messages for malformed YAML configurations