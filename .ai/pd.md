> **Generated**: 2025-11-12
> **Analysis Depth**: Deep (All 8 source/test files analyzed)
---

## PROJECT_OVERVIEW

**Project Name**: mcp-server-mender
**Version**: 0.1.0
**Type**: CLI Tool + Python Library
**Domain**: IoT Device Management & Over-the-Air (OTA) Updates

**Purpose**: Bridge AI assistants (Claude Code, etc.) with Mender IoT platform via Model Context Protocol (MCP) for natural language device management, deployment monitoring, and audit logging.

**Critical Constraints**:
- Read-only operations (no device control)
- Zero credential leakage in logs/errors
- Comprehensive input validation on all inputs
- Stateless operation (no persistent storage)
- MCP protocol compatibility

---

## TECHNOLOGY_STACK

### Core Dependencies (from pyproject.toml & requirements.txt)

```toml
[project]
name = "mcp-server-mender"
version = "0.1.0"
requires-python = ">=3.8"

[project.dependencies]
click = ">=8.0.0"        # CLI framework
mcp = ">=1.0.0"          # Model Context Protocol
pydantic = ">=2.0.0"     # Data validation
httpx = ">=0.24.0"       # HTTP client
python-dateutil = ">=2.8.0"  # Date parsing

[development]
pytest = ">=7.0.0"       # Testing framework
black = ">=22.0.0"       # Code formatter
isort = ">=5.10.0"       # Import sorter
mypy = ">=1.0.0"         # Type checker
ruff = ">=0.1.0"         # Linter
```

---

## DIRECTORY_STRUCTURE

```
mender-mcp/
├── src/
│   └── mcp_server_mender/
│       ├── __init__.py          # Package entry, exports main()
│       ├── __main__.py           # Module execution entry point
│       ├── server.py             # MCP server (692 lines)
│       ├── mender_api.py         # API client (1102 lines)
│       └── security.py           # Security utils (300 lines)
├── tests/
│   ├── __init__.py
│   ├── test_security.py         # Security tests (279 lines)
│   └── test_server.py            # Server tests (1404 lines)
├── .ai/
│   └── pd.md                     # Project description
├── pyproject.toml                # Project config
├── requirements.txt              # Dev dependencies
└── README.md                     # User documentation
```

---

## CODE_STANDARDS_&_CONVENTIONS

### File Naming 
```python
# Module files
security.py              # ✓ snake_case
mender_api.py           # ✓ snake_case
server.py               # ✓ snake_case

# Test files
test_security.py        # ✓ test_*.py pattern
test_server.py          # ✓ test_*.py pattern
```

### Naming Conventions

```python
# Classes: PascalCase (mender_api.py:159, security.py:13, server.py:22)
class MenderAPIClient:
class SecurityLogger:
class MenderMCPServer:
class ErrorSanitizer:

# Functions/Methods: snake_case (mender_api.py:333, security.py:20)
def get_devices(self, status, device_type, limit):
def mask_token(token: str) -> str:
def validate_input(input_model, data):

# Constants: UPPER_SNAKE_CASE (security.py:86-98)
STATUS_CODE_MESSAGES = {
    400: "Invalid request parameters provided",
    401: "Authentication failed - please check your access token",
    # ...
}

# Private methods: _leading_underscore (mender_api.py:194, server.py:590)
def _make_request(self, method, endpoint, **kwargs):
def _format_device_output(self, device) -> str:

# Pydantic models: PascalCase (mender_api.py:15-67, security.py:190-277)
class MenderDevice(BaseModel):
class DeviceIdInput(BaseModel):
class LimitInput(BaseModel):
```

### Import Organization 

```python
"""Module docstring first."""

# Standard library imports
import asyncio
import os
import sys
from typing import Any, Dict, List, Optional

# Third-party imports (alphabetical)
import click
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, TextContent, Tool
from pydantic import AnyUrl

# Local imports (relative)
from .mender_api import MenderAPIClient, MenderAPIError
from .security import (
    SecurityLogger, ErrorSanitizer, validate_input,
    DeviceIdInput, DeploymentIdInput, ReleaseNameInput
)
```

### Type Annotations

```python
# All function signatures are fully typed (mender_api.py:333-366)
def get_devices(self,
               status: Optional[str] = None,
               device_type: Optional[str] = None,
               limit: Optional[int] = None,
               skip: Optional[int] = None) -> List[MenderDevice]:

# Return types always specified (security.py:20-41)
@staticmethod
def mask_token(token: str) -> str:

# Complex types with proper imports (security.py:279-300)
def validate_input(input_model: type, data: Dict[str, Any]) -> Dict[str, Any]:
```

### Docstring Style

```python
def __init__(self, server_url: str, access_token: str, timeout: int = 30):
    """Initialize the Mender API client.

    Args:
        server_url: Base URL of the Mender server (e.g., https://hosted.mender.io)
        access_token: Personal Access Token for authentication
        timeout: Request timeout in seconds
    """
```

### Code Formatting

- **Line Length**: 88 characters (Black standard)
- **Indentation**: 4 spaces
- **Quotes**: Double quotes for strings
- **Trailing Commas**: Always in multi-line structures

---

## DESIGN_PATTERNS

### 1. Layered Architecture 

```
MCP Protocol Layer (server.py)
    ↓
Handler Layer (server.py:_setup_handlers)
    ↓
Security Layer (security.py:validate_input, ErrorSanitizer)
    ↓
API Client Layer (mender_api.py:MenderAPIClient)
    ↓
External API (Mender REST API)
```

### 2. Dependency Injection (server.py:25-27)

```python
def __init__(self, server_url: str, access_token: str):
    """Initialize the server with Mender API client."""
    self.mender_client = MenderAPIClient(server_url, access_token)  # ← Injected
    self.server = Server("mender")
    self.security_logger = SecurityLogger("mender_mcp_server")  # ← Injected
```

### 3. Factory Pattern (mender_api.py:70-92)

```python
class MenderRelease(BaseModel):
    """Mender release model."""

    # Factory methods to handle API version differences
    @classmethod
    def from_v1_data(cls, data: Dict[str, Any]) -> 'MenderRelease':
        """Create MenderRelease from v1 API response data."""
        return cls(name=data.get('name', ''), ...)

    @classmethod
    def from_v2_data(cls, data: Dict[str, Any]) -> 'MenderRelease':
        """Create MenderRelease from v2 API response data."""
        return cls(name=data.get('name', ''), ...)
```

### 4. Strategy Pattern - API Version Fallback (mender_api.py:481-498)

```python
# Try v2 endpoint first, fallback to v1 if not available
try:
    data = self._make_request("GET", "/api/management/v2/deployments/...")
    releases = [MenderRelease.from_v2_data(release) for release in data]
except MenderAPIError as e:
    if e.status_code == 404:
        # Try v1 endpoint as fallback
        data = self._make_request("GET", "/api/management/v1/deployments/...")
        releases = [MenderRelease.from_v1_data(release) for release in data]
    else:
        raise
```

### 5. Template Method Pattern - Error Handling (mender_api.py:194-254)

```python
def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
    """Template method for all API requests."""
    url = urljoin(self.server_url, endpoint)

    try:
        response = self.client.request(method, url, **kwargs)
        response.raise_for_status()

        if not response.content:
            return {}

        return response.json()

    except httpx.HTTPStatusError as e:
        # Sanitize error
        safe_error_msg = ErrorSanitizer.sanitize_http_error(...)
        self.security_logger.log_secure(logging.ERROR, ...)
        raise MenderAPIError(safe_error_msg, e.response.status_code)

    except httpx.RequestError as e:
        error_msg = f"Request failed: Network error occurred..."
        self.security_logger.log_secure(logging.ERROR, ...)
        raise MenderAPIError(error_msg)
```

---

## ERROR_HANDLING

### Exception Hierarchy (mender_api.py:150-157)

```python
class MenderAPIError(Exception):
    """Exception raised for Mender API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)
```

### Error Handling Pattern (server.py:563-588)

```python
try:
    # Validate input
    validated = validate_input(DeviceIdInput, arguments)
    device_id = validated["device_id"]

    # Perform operation
    device = self.mender_client.get_device(device_id)
    result = self._format_device_output(device)

    return [TextContent(type="text", text=result)]

except ValueError as e:
    # Input validation errors
    error_msg = f"Input validation error: {str(e)}"
    self.security_logger.log_secure(40, f"Input validation failed: {str(e)}")
    return [TextContent(type="text", text=error_msg)]

except MenderAPIError as e:
    # Mender API errors (already sanitized)
    error_msg = f"Mender API Error: {e.message}"
    if e.status_code:
        error_msg += f" (HTTP {e.status_code})"
    return [TextContent(type="text", text=error_msg)]

except Exception as e:
    # Unexpected errors - sanitize before exposing
    sanitized_error = SecurityLogger.sanitize_message(str(e))
    error_msg = f"Unexpected error: {sanitized_error}"
    self.security_logger.log_secure(50, f"Unexpected error: {str(e)}")
    return [TextContent(type="text", text=error_msg)]
```

### HTTP Error Sanitization (security.py:86-136)

```python
# Mapping for user-friendly messages
STATUS_CODE_MESSAGES = {
    400: "Invalid request parameters provided",
    401: "Authentication failed - please check your access token",
    403: "Access denied - insufficient permissions for this operation",
    404: "Requested resource not found",
    429: "Rate limit exceeded - please wait before making more requests",
    500: "Internal server error occurred",
    503: "Service temporarily unavailable",
}

@staticmethod
def sanitize_http_error(status_code: int, response_text: str, original_url: str = "") -> str:
    """Sanitize HTTP error for safe display to users."""
    base_message = ErrorSanitizer.STATUS_CODE_MESSAGES.get(
        status_code,
        f"HTTP error {status_code} occurred"
    )

    # Context-aware messaging
    if status_code == 404:
        if "devices" in original_url.lower():
            return f"{base_message}. The device ID may not exist..."
        elif "deployments" in original_url.lower():
            return f"{base_message}. The deployment ID may not exist..."

    return base_message
```

---

## SECURITY_ARCHITECTURE

### 1. Token Masking (security.py:20-41)

```python
@staticmethod
def mask_token(token: str) -> str:
    """Mask authentication token for safe logging.

    Examples:
        >>> SecurityLogger.mask_token("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")
        'eyJhbGci*************************VCJ9'
        >>> SecurityLogger.mask_token("short")
        '*****'
    """
    if not token:
        return "*[EMPTY]*"

    if len(token) < 16:
        return "*" * len(token)

    return f"{token[:8]}{'*' * (len(token) - 16)}{token[-8:]}"
```

**Usage in codebase** (mender_api.py:178-182):
```python
masked_token = SecurityLogger.mask_token(access_token)
self.security_logger.log_secure(
    logging.INFO,
    f"Initializing Mender API client for {server_url} with token {masked_token}"
)
```

### 2. Message Sanitization (security.py:44-75)

```python
@staticmethod
def sanitize_message(message: str) -> str:
    """Sanitize log message to remove potential sensitive information."""
    patterns = [
        (r'\beyJ[a-zA-Z0-9._-]+', '[JWT_TOKEN]'),                   # JWT tokens
        (r'\b[a-zA-Z0-9]{32,}\b', '[API_KEY]'),                     # API keys
        (r'Bearer\s+[a-zA-Z0-9._-]+', 'Bearer [TOKEN]'),            # Bearer tokens
        (r'Basic\s+[a-zA-Z0-9+/=]+', 'Basic [CREDENTIALS]'),        # Basic auth
        (r'://[^:]+:[^@]+@', '://[USER]:[PASS]@'),                  # URL credentials
        (r'(?i)(password|secret|key|token)\s*[:=]\s*[^\s\'"]+', r'\1=[REDACTED]'),
    ]

    sanitized = message
    for pattern, replacement in patterns:
        sanitized = re.sub(pattern, replacement, sanitized)

    return sanitized
```

### 3. Input Validation (security.py:190-277)

**DeviceIdInput** (security.py:190-207):
```python
class DeviceIdInput(BaseModel):
    """Validation model for device ID parameters."""
    device_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        pattern=r'^[a-zA-Z0-9\-_\.]+$',
        description="Device ID must be alphanumeric with hyphens, underscores, or dots"
    )

    @field_validator('device_id')
    @classmethod
    def validate_device_id(cls, v):
        """Additional validation for device ID format."""
        # Prevent path traversal attempts
        if '..' in v or v.startswith('/') or v.endswith('/'):
            raise ValueError("Invalid device ID format")
        return v
```

**LimitInput** (security.py:249-256):
```python
class LimitInput(BaseModel):
    """Validation model for limit parameters."""
    limit: Optional[int] = Field(
        None,
        ge=1,
        le=500,
        description="Number of items to return (1-500)"
    )
```

**StatusInput** (security.py:259-265):
```python
class StatusInput(BaseModel):
    """Validation model for status filter parameters."""
    status: Optional[str] = Field(
        None,
        pattern=r'^(accepted|rejected|pending|noauth|inprogress|finished)$',
        description="Status filter value"
    )
```

### 4. Validation Usage Pattern (server.py:393-398)

```python
if name == "get_device_status":
    # Validate input parameters
    validated = validate_input(DeviceIdInput, arguments)
    device_id = validated["device_id"]
    device = self.mender_client.get_device(device_id)
    result = self._format_device_output(device)
```

---

## TESTING_STRATEGY

### Test Organization

```python
# Class-based test organization (test_security.py:15-84)
class TestSecurityLogger:
    """Test SecurityLogger functionality."""

    def test_mask_token_short(self):
        """Test token masking for short tokens."""
        token = "short"
        masked = SecurityLogger.mask_token(token)
        assert masked == "*****"

    def test_mask_token_long(self):
        """Test token masking for long tokens."""
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ..."
        masked = SecurityLogger.mask_token(token)
        assert token[:8] in masked
        assert token[-8:] in masked
        assert len(masked) == len(token)
```

### Test Naming Convention

```python
# Test files: test_*.py
test_security.py
test_server.py

# Test classes: Test<ComponentName>
TestSecurityLogger
TestErrorSanitizer
TestInputValidation

# Test methods: test_<what>_<condition>
def test_mask_token_short(self):
def test_sanitize_http_error_401(self):
def test_device_id_input_path_traversal(self):
```

### Fixtures (test_server.py:54-60, 351-386)

```python
@pytest.fixture
def mock_devices():
    """Mock devices for testing."""
    return [
        MenderDevice(id="device1", status="accepted"),
        MenderDevice(id="device2", status="pending")
    ]

@pytest.fixture
def mock_inventory():
    """Mock device inventory for testing."""
    return MenderDeviceInventory(
        device_id="test-device-123",
        attributes=[
            MenderInventoryItem(name="device_type", value="beaglebone"),
            MenderInventoryItem(name="kernel", value="Linux 5.4.0"),
        ]
    )
```

### Mocking Strategy (test_server.py:21-27, 45-51)

```python
def test_mender_api_client_init():
    """Test MenderAPIClient initialization."""
    client = MenderAPIClient("https://hosted.mender.io", "test_token")

    assert client.server_url == "https://hosted.mender.io"
    assert client.access_token == "test_token"
    assert "Bearer test_token" in client.client.headers["Authorization"]

def test_mender_mcp_server_init():
    """Test MenderMCPServer initialization."""
    with patch('mcp_server_mender.server.MenderAPIClient') as mock_client:
        server = MenderMCPServer("https://hosted.mender.io", "test_token")

        assert server.server.name == "mender"
        mock_client.assert_called_once_with("https://hosted.mender.io", "test_token")
```

### Test Structure Pattern (test_security.py:151-155)

```python
def test_device_id_input_valid(self):
    """Test valid device ID input."""
    # Arrange
    data = {"device_id": "valid-device-123"}

    # Act
    validated = validate_input(DeviceIdInput, data)

    # Assert
    assert validated["device_id"] == "valid-device-123"
```

---

## API_ARCHITECTURE

### MCP Resources (server.py:44-90)

```python
@self.server.list_resources()
async def list_resources() -> List[Resource]:
    """List available resources."""
    return [
        Resource(
            uri=AnyUrl("mender://devices"),
            name="Devices",
            description="List of all Mender devices",
            mimeType="text/plain",
        ),
        Resource(
            uri=AnyUrl("mender://deployments"),
            name="Deployments",
            description="List of all Mender deployments",
            mimeType="text/plain",
        ),
        Resource(
            uri=AnyUrl("mender://audit-logs"),
            name="Audit Logs",
            description="System audit logs for user actions",
            mimeType="text/plain",
        ),
    ]
```

### MCP Tools (server.py:154-380)

```python
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
                        "enum": ["accepted", "rejected", "pending", "noauth"]
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 500,
                        "default": 20
                    }
                }
            }
        ),
    ]
```

### API Client Methods (mender_api.py:333-427)

```python
def get_devices(self,
               status: Optional[str] = None,
               device_type: Optional[str] = None,
               limit: Optional[int] = None,
               skip: Optional[int] = None) -> List[MenderDevice]:
    """Get list of devices.

    Args:
        status: Filter by device status (accepted, rejected, pending, etc.)
        device_type: Filter by device type
        limit: Maximum number of devices to return
        skip: Number of devices to skip (for pagination)

    Returns:
        List of MenderDevice objects
    """
    params = {}
    if status:
        params["status"] = status
    if limit:
        params["per_page"] = limit

    data = self._make_request(
        "GET",
        "/api/management/v2/devauth/devices",
        params=params
    )

    return [MenderDevice(**device) for device in data]
```

---

## REAL_CODE_SNIPPETS

### 1: Complete API Method with Error Handling

**File**: mender_api.py:367-381

```python
def get_device(self, device_id: str) -> MenderDevice:
    """Get details for a specific device.

    Args:
        device_id: Device ID

    Returns:
        MenderDevice object
    """
    data = self._make_request(
        "GET",
        f"/api/management/v2/devauth/devices/{device_id}"
    )

    return MenderDevice(**data)
```

### 2: MCP Tool Handler with Validation

**File**: server.py:393-398

```python
if name == "get_device_status":
    # Validate input parameters
    validated = validate_input(DeviceIdInput, arguments)
    device_id = validated["device_id"]
    device = self.mender_client.get_device(device_id)
    result = self._format_device_output(device)
```

### 3: Security Logger Usage

**File**: mender_api.py:175-182

```python
# Initialize security logger
self.security_logger = SecurityLogger("mender_api_client")

# Log initialization with masked token
masked_token = SecurityLogger.mask_token(access_token)
self.security_logger.log_secure(
    logging.INFO,
    f"Initializing Mender API client for {server_url} with token {masked_token}"
)
```

### 4: Pydantic Model with Validators

**File**: security.py:190-207

```python
class DeviceIdInput(BaseModel):
    """Validation model for device ID parameters."""
    device_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        pattern=r'^[a-zA-Z0-9\-_\.]+$',
        description="Device ID must be alphanumeric with hyphens, underscores, or dots"
    )

    @field_validator('device_id')
    @classmethod
    def validate_device_id(cls, v):
        """Additional validation for device ID format."""
        if '..' in v or v.startswith('/') or v.endswith('/'):
            raise ValueError("Invalid device ID format")
        return v
```

### 5: Test with Fixtures and Mocking

**File**: test_server.py:54-74

```python
@pytest.fixture
def mock_devices():
    """Mock devices for testing."""
    return [
        MenderDevice(id="device1", status="accepted"),
        MenderDevice(id="device2", status="pending")
    ]

def test_format_devices_output(mock_devices):
    """Test device output formatting."""
    with patch('mcp_server_mender.server.MenderAPIClient') as mock_client:
        server = MenderMCPServer("https://hosted.mender.io", "test_token")

        output = server._format_devices_output(mock_devices)

        assert "Found 2 device(s)" in output
        assert "device1" in output
        assert "device2" in output
```

### 6: API Version Fallback Pattern

**File**: mender_api.py:528-557

```python
def get_release(self, release_name: str) -> MenderRelease:
    """Get details for a specific release."""
    # Try v2 endpoint first
    try:
        data = self._make_request(
            "GET",
            f"/api/management/v2/deployments/deployments/releases/{release_name}"
        )
        return MenderRelease.from_v2_data(data)
    except MenderAPIError as e:
        if e.status_code == 404:
            # Fallback to v1 endpoint
            try:
                data = self._make_request(
                    "GET",
                    f"/api/management/v1/deployments/deployments/releases/{release_name}"
                )
                return MenderRelease.from_v1_data(data)
            except MenderAPIError:
                # Search through all releases
                releases = self.get_releases()
                for release in releases:
                    if release.name == release_name:
                        return release
                raise MenderAPIError(f"Release '{release_name}' not found", 404)
        else:
            raise
```

---

## AI_CODING_GUIDELINES

### ALWAYS Do

1. **Use Type Hints**:
```python
def get_devices(self, limit: Optional[int] = None) -> List[MenderDevice]:
```

2. **Validate All User Inputs**:
```python
validated = validate_input(DeviceIdInput, arguments)
device_id = validated["device_id"]
```

3. **Mask Tokens in Logs**:
```python
masked_token = SecurityLogger.mask_token(access_token)
self.security_logger.log_secure(logging.INFO, f"Using token {masked_token}")
```

4. **Use Pydantic for Data Models**:
```python
class MenderDevice(BaseModel):
    id: str
    status: str
    device_type: Optional[str] = None
```

5. **Include Docstrings**:
```python
def get_device(self, device_id: str) -> MenderDevice:
    """Get details for a specific device.

    Args:
        device_id: Device ID

    Returns:
        MenderDevice object
    """
```

6. **Sanitize Error Messages**:
```python
safe_error = ErrorSanitizer.sanitize_http_error(status_code, response_text, url)
raise MenderAPIError(safe_error, status_code)
```

7. **Use Try-Catch Comprehensively**:
```python
try:
    result = operation()
except ValueError as e:
    # Handle validation errors
except MenderAPIError as e:
    # Handle API errors
except Exception as e:
    # Handle unexpected errors
```

8. **Write Tests with Arrange-Act-Assert**:
```python
def test_mask_token_short(self):
    # Arrange
    token = "short"
    # Act
    masked = SecurityLogger.mask_token(token)
    # Assert
    assert masked == "*****"
```

### NEVER Do

1. **Never log unmasked tokens**:
```python
# ✗ WRONG
logging.info(f"Token: {access_token}")

# ✓ CORRECT
logging.info(f"Token: {SecurityLogger.mask_token(access_token)}")
```

2. **Never skip input validation**:
```python
# ✗ WRONG
device_id = arguments["device_id"]
device = self.mender_client.get_device(device_id)

# ✓ CORRECT
validated = validate_input(DeviceIdInput, arguments)
device_id = validated["device_id"]
device = self.mender_client.get_device(device_id)
```

3. **Never use 'any' type without justification**:
```python
# ✗ WRONG
def process(data: any):

# ✓ CORRECT
def process(data: Dict[str, Any]):
```

4. **Never expose raw error messages**:
```python
# ✗ WRONG
except httpx.HTTPStatusError as e:
    raise Exception(str(e))

# ✓ CORRECT
except httpx.HTTPStatusError as e:
    safe_msg = ErrorSanitizer.sanitize_http_error(e.response.status_code, ...)
    raise MenderAPIError(safe_msg, e.response.status_code)
```

5. **Never hardcode URLs or configuration**:
```python
# ✗ WRONG
url = "https://hosted.mender.io/api/devices"

# ✓ CORRECT
url = urljoin(self.server_url, "/api/management/v2/devauth/devices")
```

6. **Never mix concerns in functions**:
```python
# ✗ WRONG - validation, API call, formatting in one function

# ✓ CORRECT - separate validation, API call, formatting
validated = validate_input(DeviceIdInput, arguments)
device = self.mender_client.get_device(validated["device_id"])
result = self._format_device_output(device)
```