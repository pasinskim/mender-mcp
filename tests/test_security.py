"""Tests for security utilities and features."""

import json
import logging
import pytest
from unittest.mock import patch, MagicMock

from mcp_server_mender.security import (
    SecurityLogger, ErrorSanitizer, validate_input,
    DeviceIdInput, DeploymentIdInput, ReleaseNameInput,
    LimitInput, StatusInput, DeviceTypeInput
)


class TestSecurityLogger:
    """Test SecurityLogger functionality."""
    
    def test_mask_token_short(self):
        """Test token masking for short tokens."""
        token = "short"
        masked = SecurityLogger.mask_token(token)
        assert masked == "*****"
        
    def test_mask_token_medium(self):
        """Test token masking for medium tokens."""
        token = "medium_length_token"  # 19 chars - should be masked with first 8 + * + last 8
        masked = SecurityLogger.mask_token(token)
        expected = f"{token[:8]}{'*' * (len(token) - 16)}{token[-8:]}"
        assert masked == expected
        
    def test_mask_token_long(self):
        """Test token masking for long tokens."""
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        masked = SecurityLogger.mask_token(token)
        expected = f"{token[:8]}{'*' * (len(token) - 16)}{token[-8:]}"
        assert masked == expected
        assert token[:8] in masked
        assert token[-8:] in masked
        assert len(masked) == len(token)
        
    def test_mask_token_empty(self):
        """Test token masking for empty token."""
        masked = SecurityLogger.mask_token("")
        assert masked == "*[EMPTY]*"
        
    def test_sanitize_message_jwt_token(self):
        """Test message sanitization for JWT tokens."""
        message = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3"
        sanitized = SecurityLogger.sanitize_message(message)
        assert "eyJ" not in sanitized
        assert "[JWT_TOKEN]" in sanitized
        
    def test_sanitize_message_api_key(self):
        """Test message sanitization for API keys."""
        message = "API-Key: abcd1234567890abcd1234567890abcd1234567890"
        sanitized = SecurityLogger.sanitize_message(message)
        assert "abcd1234567890abcd1234567890abcd1234567890" not in sanitized
        # Should match the key=value pattern and be redacted
        assert "[API_KEY]" in sanitized or "[REDACTED]" in sanitized
        
    def test_sanitize_message_bearer_token(self):
        """Test message sanitization for Bearer tokens."""
        message = "Authorization: Bearer abc123def456ghi789"
        sanitized = SecurityLogger.sanitize_message(message)
        assert "abc123def456ghi789" not in sanitized
        assert "Bearer [TOKEN]" in sanitized
        
    def test_sanitize_message_password(self):
        """Test message sanitization for passwords."""
        message = "password=secretpassword123"
        sanitized = SecurityLogger.sanitize_message(message)
        assert "secretpassword123" not in sanitized
        assert "password=[REDACTED]" in sanitized
        
    def test_log_secure(self):
        """Test secure logging functionality."""
        logger = SecurityLogger("test_logger")
        with patch.object(logger.logger, 'log') as mock_log:
            logger.log_secure(logging.INFO, "Test message with token=abc123")
            mock_log.assert_called_once()
            # Verify message was sanitized
            logged_message = mock_log.call_args[0][1]
            assert "token=[REDACTED]" in logged_message


class TestErrorSanitizer:
    """Test ErrorSanitizer functionality."""
    
    def test_sanitize_http_error_401(self):
        """Test HTTP 401 error sanitization."""
        sanitized = ErrorSanitizer.sanitize_http_error(401, "Unauthorized", "")
        assert "Authentication failed" in sanitized
        assert "Personal Access Token" in sanitized
        
    def test_sanitize_http_error_403(self):
        """Test HTTP 403 error sanitization."""
        sanitized = ErrorSanitizer.sanitize_http_error(403, "Forbidden", "")
        assert "Access denied" in sanitized
        assert "permissions" in sanitized
        
    def test_sanitize_http_error_404_devices(self):
        """Test HTTP 404 error sanitization for device endpoints."""
        sanitized = ErrorSanitizer.sanitize_http_error(404, "Not found", "/api/devices/123")
        assert "device ID may not exist" in sanitized
        
    def test_sanitize_http_error_404_deployments(self):
        """Test HTTP 404 error sanitization for deployment endpoints."""
        sanitized = ErrorSanitizer.sanitize_http_error(404, "Not found", "/api/deployments/456")
        assert "deployment ID may not exist" in sanitized
        
    def test_sanitize_http_error_429(self):
        """Test HTTP 429 error sanitization."""
        sanitized = ErrorSanitizer.sanitize_http_error(429, "Rate limited", "")
        assert "rate limit exceeded" in sanitized.lower()
        
    def test_sanitize_http_error_500(self):
        """Test HTTP 500 error sanitization."""
        sanitized = ErrorSanitizer.sanitize_http_error(500, "Internal error", "")
        assert "Internal server error" in sanitized
        assert "temporary issue" in sanitized
        
    def test_extract_safe_error_info_json(self):
        """Test safe error info extraction from JSON."""
        response_text = '{"message": "Invalid request", "code": 400}'
        safe_info = ErrorSanitizer.extract_safe_error_info(response_text)
        assert safe_info == "Invalid request"
        
    def test_extract_safe_error_info_sensitive(self):
        """Test safe error info extraction filters sensitive data."""
        response_text = '{"message": "Token eyJhbGci invalid", "code": 401}'
        safe_info = ErrorSanitizer.extract_safe_error_info(response_text)
        assert safe_info is None  # Should be filtered out due to token
        
    def test_extract_safe_error_info_invalid_json(self):
        """Test safe error info extraction with invalid JSON."""
        response_text = "Not JSON content"
        safe_info = ErrorSanitizer.extract_safe_error_info(response_text)
        assert safe_info is None
        
    def test_contains_sensitive_data(self):
        """Test sensitive data detection."""
        assert ErrorSanitizer._contains_sensitive_data("eyJhbGciOiJIUzI1NiI") == True  # JWT
        assert ErrorSanitizer._contains_sensitive_data("Bearer abc123def456") == True  # Bearer token
        assert ErrorSanitizer._contains_sensitive_data("password=secret") == True  # Password
        assert ErrorSanitizer._contains_sensitive_data("Normal message") == False  # Clean message


class TestInputValidation:
    """Test input validation models."""
    
    def test_device_id_input_valid(self):
        """Test valid device ID input."""
        data = {"device_id": "valid-device-123"}
        validated = validate_input(DeviceIdInput, data)
        assert validated["device_id"] == "valid-device-123"
        
    def test_device_id_input_invalid_chars(self):
        """Test invalid characters in device ID."""
        data = {"device_id": "invalid/device/id"}
        with pytest.raises(ValueError, match="Input validation failed"):
            validate_input(DeviceIdInput, data)
            
    def test_device_id_input_path_traversal(self):
        """Test path traversal prevention in device ID."""
        data = {"device_id": "../../../etc/passwd"}
        with pytest.raises(ValueError, match="Input validation failed"):
            # This should fail at the regex pattern level first
            validate_input(DeviceIdInput, data)
            
    def test_device_id_input_too_long(self):
        """Test device ID length validation."""
        data = {"device_id": "a" * 200}  # Too long
        with pytest.raises(ValueError, match="Input validation failed"):
            validate_input(DeviceIdInput, data)
            
    def test_deployment_id_input_valid(self):
        """Test valid deployment ID input."""
        data = {"deployment_id": "valid-deployment-456"}
        validated = validate_input(DeploymentIdInput, data)
        assert validated["deployment_id"] == "valid-deployment-456"
        
    def test_deployment_id_input_invalid(self):
        """Test invalid deployment ID input."""
        data = {"deployment_id": "invalid<script>alert(1)</script>"}
        with pytest.raises(ValueError, match="Input validation failed"):
            validate_input(DeploymentIdInput, data)
            
    def test_release_name_input_valid(self):
        """Test valid release name input."""
        data = {"release_name": "my-release-v1.2.3"}
        validated = validate_input(ReleaseNameInput, data)
        assert validated["release_name"] == "my-release-v1.2.3"
        
    def test_release_name_input_path_traversal(self):
        """Test path traversal prevention in release name."""
        data = {"release_name": "../admin/secrets"}
        with pytest.raises(ValueError, match="Invalid release name format"):
            validate_input(ReleaseNameInput, data)
            
    def test_limit_input_valid(self):
        """Test valid limit input."""
        data = {"limit": 50}
        validated = validate_input(LimitInput, data)
        assert validated["limit"] == 50
        
    def test_limit_input_too_large(self):
        """Test limit input validation for maximum value."""
        data = {"limit": 1000}  # Too large
        with pytest.raises(ValueError, match="Input validation failed"):
            validate_input(LimitInput, data)
            
    def test_limit_input_zero(self):
        """Test limit input validation for minimum value."""
        data = {"limit": 0}  # Too small
        with pytest.raises(ValueError, match="Input validation failed"):
            validate_input(LimitInput, data)
            
    def test_status_input_valid(self):
        """Test valid status input."""
        data = {"status": "accepted"}
        validated = validate_input(StatusInput, data)
        assert validated["status"] == "accepted"
        
    def test_status_input_invalid(self):
        """Test invalid status input."""
        data = {"status": "invalid_status"}
        with pytest.raises(ValueError, match="Input validation failed"):
            validate_input(StatusInput, data)
            
    def test_device_type_input_valid(self):
        """Test valid device type input."""
        data = {"device_type": "raspberry-pi-4"}
        validated = validate_input(DeviceTypeInput, data)
        assert validated["device_type"] == "raspberry-pi-4"
        
    def test_device_type_input_with_spaces(self):
        """Test device type input with spaces."""
        data = {"device_type": "Raspberry Pi 4"}
        validated = validate_input(DeviceTypeInput, data)
        assert validated["device_type"] == "Raspberry Pi 4"
        
    def test_device_type_input_invalid_chars(self):
        """Test invalid characters in device type."""
        data = {"device_type": "device<script>alert(1)</script>"}
        with pytest.raises(ValueError, match="Input validation failed"):
            validate_input(DeviceTypeInput, data)


class TestValidateInputFunction:
    """Test the validate_input helper function."""
    
    def test_validate_input_success(self):
        """Test successful input validation."""
        data = {"device_id": "valid-device"}
        result = validate_input(DeviceIdInput, data)
        assert result["device_id"] == "valid-device"
        
    def test_validate_input_error_sanitization(self):
        """Test that validation errors are sanitized."""
        data = {"device_id": "invalid token=secret123 device"}
        with pytest.raises(ValueError) as exc_info:
            validate_input(DeviceIdInput, data)
        
        # Error message should be sanitized
        error_msg = str(exc_info.value)
        assert "token=secret123" not in error_msg
        assert "token=[REDACTED]" in error_msg
        
    def test_validate_input_exclude_none(self):
        """Test that None values are excluded from validation result."""
        from typing import Optional
        
        class TestInput(DeviceIdInput):
            optional_field: Optional[str] = None
            
        data = {"device_id": "valid-device"}  # Don't include None field
        result = validate_input(TestInput, data)
        assert "optional_field" not in result
        assert result["device_id"] == "valid-device"