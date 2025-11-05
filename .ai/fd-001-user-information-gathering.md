# Feature Description: User Information Gathering for Mender MCP

## 🎯 Business Context & Purpose

The Mender MCP integration tool currently lacks visibility into tenant user management and RBAC (Role-Based Access Control) configurations. This creates a critical gap for organizations needing to:

- **Audit Access Control**: Security teams cannot programmatically audit who has access to their IoT fleet management system
- **Compliance Reporting**: Unable to generate automated compliance reports for SOC2, ISO 27001, or other regulatory requirements
- **Incident Investigation**: During security incidents, teams lack quick access to understand user permissions and recent access patterns
- **Permission Troubleshooting**: Support teams cannot efficiently diagnose permission-related issues without manual console access

**Expected Business Impact:**
- 40% reduction in security incident investigation time
- Enable automated compliance reporting for enterprise customers
- Improve support response time by 30% for permission-related issues
- Support enterprise adoption by meeting security audit requirements

## 📋 Expected Behavior/Outcome

The enhanced mender-mcp tool will provide read-only access to:

1. **User Listing**: Retrieve all users in a Mender tenant with their basic information and role assignments
2. **User Details**: Get comprehensive information about specific users including permissions and access history
3. **RBAC Roles**: List all available roles (built-in and custom) with their permission sets
4. **Permission Mapping**: Understand what actions each role can perform across the platform
5. **Tenant Information**: Access organization-level settings and configurations

### Key User Interactions:
- AI assistants can query "Who has admin access to our Mender instance?"
- Automated compliance scripts can generate user access reports
- Security teams can correlate deployment actions with user permissions
- Support engineers can quickly verify user permissions during troubleshooting

## 🔬 Research Summary

**Investigation Depth**: STANDARD
**Confidence Level**: High

## 🔬 Research Summary

**Product & User Story**:
- Primary personas: Security Engineers, Compliance Officers, DevOps Admins, Support Engineers
- Critical for meeting enterprise security requirements
- Enables self-service permission troubleshooting
- Foundation for future user management automation

**Design & UX Approach**:
- Follows existing mender-mcp tool patterns for consistency
- Provides AI-optimized output format with clear hierarchy
- Implements progressive data masking for privacy protection
- Includes comprehensive error states for permission scenarios

**Technical Plan & Risks**:
- Leverages existing Mender REST API endpoints (useradm, tenantadm services)
- Read-only implementation minimizes security risks
- Requires Mender 3.0+ for RBAC support
- Graceful degradation for older Mender versions

**Pragmatic Effort Estimate**: 16-22 hours (2-3 days)

## ✅ Acceptance Criteria

### Functional Requirements
- [ ] List all tenant users with basic information (email, roles, status)
- [ ] Retrieve detailed user information including complete permission sets
- [ ] List all RBAC roles with their permission structures
- [ ] Query specific user permissions by email or ID
- [ ] Display tenant/organization configuration details
- [ ] Support pagination for large user lists (>100 users)
- [ ] Implement 5-minute caching for performance optimization

### UX Requirements
- [ ] Email addresses are partially masked for privacy (j***@example.com)
- [ ] Output format is consistent with existing mender-mcp tools
- [ ] Clear error messages for permission denied scenarios
- [ ] Support filtering users by role or email search
- [ ] Response time under 2 seconds for user lists

### Technical Requirements
- [ ] Integrate with Mender useradm API endpoints
- [ ] Implement comprehensive input validation
- [ ] Add unit tests with >90% coverage
- [ ] Ensure backward compatibility with existing mender-mcp functionality
- [ ] Support both single-tenant and multi-tenant deployments
- [ ] No storage of sensitive user data locally

### Security Requirements
- [ ] All user queries are audit logged
- [ ] Personal access tokens never exposed in outputs
- [ ] Rate limiting implemented to prevent abuse
- [ ] Graceful handling of insufficient permissions
- [ ] Email addresses and sensitive data masked in all logs

## 🔗 Dependencies & Constraints

### Dependencies
- **Mender API Version**: Requires Mender 3.0+ for RBAC support (optimal: 3.7+)
- **API Endpoints**: useradm and tenantadm services must be accessible
- **Authentication**: Personal Access Token must have user management read permissions
- **Python Libraries**: Existing Pydantic, httpx dependencies

### Technical Constraints
- **Read-only Access**: No user creation, modification, or deletion capabilities
- **Data Privacy**: Must comply with GDPR/privacy regulations for user data handling
- **Performance**: Must handle tenants with up to 10,000 users efficiently
- **Caching**: 5-minute TTL to balance freshness with API load

## 💡 Implementation Notes

### Recommended Technical Approach

1. **Extend Existing MCP Server** (`src/mender_mcp/server.py`):
   ```python
   # Add new MCP tools
   - list_users: Paginated user listing with role filtering
   - get_user_details: Complete user information retrieval
   - list_roles: RBAC role enumeration
   - get_rbac_permissions: Permission matrix display
   ```

2. **Enhance API Client** (`src/mender_mcp/mender_api.py`):
   ```python
   # New API methods
   - get_users(limit, role_filter, email_search)
   - get_user_by_id(user_id)
   - get_rbac_roles()
   - get_tenant_info()
   ```

3. **Add Data Models**:
   ```python
   class MenderUser(BaseModel)
   class MenderRole(BaseModel)
   class MenderPermission(BaseModel)
   class MenderTenant(BaseModel)
   ```

### Security Implementation
- Implement `UserDataSanitizer` class for email masking
- Add permission check decorator for user management operations
- Integrate with existing `SecurityLogger` for audit trails

### Error Handling Strategy
- Map HTTP 403 → "Insufficient permissions for user management"
- Map HTTP 404 → "User/Role not found in tenant"
- Map HTTP 429 → "Rate limit exceeded, retry with backoff"
- Map connection timeout → "Mender API temporarily unavailable"

### Testing Strategy
- Unit tests: Data model validation, email masking, permission mapping
- Integration tests: API endpoint availability, error scenarios
- Security tests: No sensitive data leakage, injection prevention

### Potential Gotchas
- **API Versioning**: Older Mender versions may have different endpoint structures
- **Multi-tenancy**: Child tenant access requires additional permission checks
- **Large User Lists**: Implement proper pagination to avoid memory issues
- **Role Inheritance**: Complex permission hierarchies need careful mapping
- **Email Uniqueness**: Handle cases where users share email across tenants

