"""Security utilities for mender-mcp server.

This module provides security functions for token masking, error sanitization,
and input validation to prevent credential leakage and enhance security.
"""

import re
import logging
from typing import Dict, Any, Optional, Union
from pydantic import BaseModel, Field, field_validator


class SecurityLogger:
    """Security-aware logger that automatically masks sensitive information."""
    
    def __init__(self, logger_name: str = "mender_mcp_security"):
        self.logger = logging.getLogger(logger_name)
    
    @staticmethod
    def mask_token(token: str) -> str:
        """Mask authentication token for safe logging.
        
        Args:
            token: The authentication token to mask
            
        Returns:
            Masked token showing only first 8 and last 8 characters
            
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
    
    @staticmethod
    def sanitize_message(message: str) -> str:
        """Sanitize log message to remove potential sensitive information.
        
        Args:
            message: The message to sanitize
            
        Returns:
            Sanitized message with sensitive patterns masked
        """
        # Pattern to match potential tokens (JWT, API keys, UUIDs, etc.)
        patterns = [
            # JWT tokens (eyJ...)
            (r'\beyJ[a-zA-Z0-9._-]+', '[JWT_TOKEN]'),
            # API keys and tokens (long alphanumeric strings)
            (r'\b[a-zA-Z0-9]{32,}\b', '[API_KEY]'),
            # Generic key=value patterns
            (r'(?i)(key|api[-_]?key)\s*[:=]\s*[a-zA-Z0-9]{16,}', r'\1=[API_KEY]'),
            # Bearer tokens in Authorization headers
            (r'Bearer\s+[a-zA-Z0-9._-]+', 'Bearer [TOKEN]'),
            # Basic auth
            (r'Basic\s+[a-zA-Z0-9+/=]+', 'Basic [CREDENTIALS]'),
            # URLs with embedded credentials
            (r'://[^:]+:[^@]+@', '://[USER]:[PASS]@'),
            # Potential passwords or secrets
            (r'(?i)(password|secret|key|token)\s*[:=]\s*[^\s\'"]+', r'\1=[REDACTED]'),
        ]
        
        sanitized = message
        for pattern, replacement in patterns:
            sanitized = re.sub(pattern, replacement, sanitized)
        
        return sanitized
    
    def log_secure(self, level: int, message: str, *args, **kwargs):
        """Log message with automatic sanitization."""
        sanitized_message = self.sanitize_message(message)
        self.logger.log(level, sanitized_message, *args, **kwargs)


class ErrorSanitizer:
    """Sanitizes error responses to prevent information leakage."""
    
    # HTTP status code to user-friendly message mapping
    STATUS_CODE_MESSAGES = {
        400: "Invalid request parameters provided",
        401: "Authentication failed - please check your access token",
        403: "Access denied - insufficient permissions for this operation",
        404: "Requested resource not found",
        408: "Request timeout - the operation took too long",
        429: "Rate limit exceeded - please wait before making more requests",
        500: "Internal server error occurred",
        502: "Bad gateway - upstream service unavailable",
        503: "Service temporarily unavailable",
        504: "Gateway timeout - upstream service did not respond",
    }
    
    @staticmethod
    def sanitize_http_error(status_code: int, response_text: str, original_url: str = "") -> str:
        """Sanitize HTTP error response for safe display to users.
        
        Args:
            status_code: HTTP status code
            response_text: Raw response text that may contain sensitive data
            original_url: The URL that was requested (will be sanitized)
            
        Returns:
            Safe error message appropriate for user display
        """
        # Get base message for status code
        base_message = ErrorSanitizer.STATUS_CODE_MESSAGES.get(
            status_code, 
            f"HTTP error {status_code} occurred"
        )
        
        # For specific status codes, provide more context without exposing details
        if status_code == 401:
            return f"{base_message}. Verify your Personal Access Token is valid and has appropriate permissions."
        elif status_code == 403:
            return f"{base_message}. Your token may lack required permissions (Device Management, Deployment Management)."
        elif status_code == 404:
            # Don't expose the full URL, but give helpful context
            if "devices" in original_url.lower():
                return f"{base_message}. The device ID may not exist in your Mender account."
            elif "deployments" in original_url.lower():
                return f"{base_message}. The deployment ID may not exist or logs may not be available."
            else:
                return f"{base_message}. The requested endpoint may not be available in your Mender version."
        elif status_code == 429:
            return f"{base_message}. The Mender API rate limit has been exceeded."
        elif status_code >= 500:
            return f"{base_message}. This appears to be a temporary issue with the Mender service."
        
        return base_message
    
    @staticmethod
    def extract_safe_error_info(response_text: str) -> Optional[str]:
        """Extract safe error information from response text.
        
        Attempts to find structured error information that's safe to show
        while avoiding credential or sensitive data exposure.
        
        Args:
            response_text: Raw response text
            
        Returns:
            Safe error information if found, None otherwise
        """
        if not response_text:
            return None
        
        # Try to extract JSON error messages safely
        try:
            import json
            data = json.loads(response_text)
            
            # Look for common error message fields
            for field in ['message', 'error', 'detail', 'description']:
                if field in data and isinstance(data[field], str):
                    error_msg = data[field]
                    # Only return if it doesn't look like it contains sensitive data
                    if not ErrorSanitizer._contains_sensitive_data(error_msg):
                        return error_msg[:200]  # Limit length
        except:
            pass
        
        # For non-JSON responses, return None to use status code mapping
        return None
    
    @staticmethod
    def _contains_sensitive_data(text: str) -> bool:
        """Check if text potentially contains sensitive data."""
        sensitive_patterns = [
            r'\beyJ[a-zA-Z0-9._-]+',  # JWT tokens
            r'\b[a-zA-Z0-9]{32,}\b',  # Long API keys
            r'Bearer\s+[a-zA-Z0-9._-]+',  # Bearer tokens
            r'password|secret|key|token',  # Sensitive field names
            r'/[a-z0-9-]+/[a-z0-9-]+/',  # Internal paths
        ]
        
        for pattern in sensitive_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False


# Input validation models
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


class DeploymentIdInput(BaseModel):
    """Validation model for deployment ID parameters."""
    deployment_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        pattern=r'^[a-zA-Z0-9\-_\.]+$',
        description="Deployment ID must be alphanumeric with hyphens, underscores, or dots"
    )
    
    @field_validator('deployment_id')
    @classmethod
    def validate_deployment_id(cls, v):
        """Additional validation for deployment ID format."""
        # Prevent path traversal attempts
        if '..' in v or v.startswith('/') or v.endswith('/'):
            raise ValueError("Invalid deployment ID format")
        return v


class ReleaseNameInput(BaseModel):
    """Validation model for release name parameters."""
    release_name: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Release name"
    )
    
    @field_validator('release_name')
    @classmethod
    def validate_release_name(cls, v):
        """Validate release name format."""
        # Allow more flexible naming for releases but prevent obvious attacks
        if '..' in v or v.startswith('/'):
            raise ValueError("Invalid release name format")
        return v


class LimitInput(BaseModel):
    """Validation model for limit parameters."""
    limit: Optional[int] = Field(
        None,
        ge=1,
        le=500,
        description="Number of items to return (1-500)"
    )


class StatusInput(BaseModel):
    """Validation model for status filter parameters."""
    status: Optional[str] = Field(
        None,
        pattern=r'^(accepted|rejected|pending|noauth|inprogress|finished)$',
        description="Status filter value"
    )


class DeviceTypeInput(BaseModel):
    """Validation model for device type parameters."""
    device_type: Optional[str] = Field(
        None,
        min_length=1,
        max_length=128,
        pattern=r'^[a-zA-Z0-9\-_\.\s]+$',
        description="Device type filter"
    )


def validate_input(input_model: type, data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate input data using the specified Pydantic model.
    
    Args:
        input_model: Pydantic model class to use for validation
        data: Dictionary of data to validate
        
    Returns:
        Validated data dictionary
        
    Raises:
        ValueError: If validation fails
    """
    try:
        validated = input_model(**data)
        return validated.model_dump(exclude_none=True)
    except Exception as e:
        # Sanitize validation error messages
        error_msg = str(e)
        # Remove any potential sensitive information from validation errors
        sanitized_error = SecurityLogger.sanitize_message(error_msg)
        raise ValueError(f"Input validation failed: {sanitized_error}")