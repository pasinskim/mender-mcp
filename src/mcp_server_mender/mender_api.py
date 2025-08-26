"""Mender API client with Personal Access Token authentication."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx
from pydantic import BaseModel


class MenderDevice(BaseModel):
    """Mender device model."""

    id: str
    status: str
    created_ts: Optional[datetime] = None
    updated_ts: Optional[datetime] = None
    auth_sets: List[Dict[str, Any]] = []
    decommissioning: bool = False
    device_type: Optional[str] = None
    attributes: List[Dict[str, Any]] = []


class MenderDeployment(BaseModel):
    """Mender deployment model."""

    id: str
    name: str
    artifact_name: str
    status: str
    created: Optional[datetime] = None
    finished: Optional[datetime] = None
    device_count: Optional[int] = None
    max_devices: Optional[int] = None
    statistics: Optional[Dict[str, int]] = None


class MenderArtifact(BaseModel):
    """Mender artifact model."""

    id: str
    name: str
    description: Optional[str] = None
    device_types_compatible: List[str] = []
    info: Optional[Dict[str, Any]] = None
    signed: bool = False
    updates: List[Dict[str, Any]] = []
    size: Optional[int] = None
    modified: Optional[datetime] = None


class MenderAPIError(Exception):
    """Exception raised for Mender API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class MenderAPIClient:
    """Mender API client with Personal Access Token authentication."""

    def __init__(self, server_url: str, access_token: str, timeout: int = 30):
        """Initialize the Mender API client.
        
        Args:
            server_url: Base URL of the Mender server (e.g., https://hosted.mender.io)
            access_token: Personal Access Token for authentication
            timeout: Request timeout in seconds
        """
        self.server_url = server_url.rstrip("/")
        self.access_token = access_token
        self.timeout = timeout

        # Initialize HTTP client with authentication headers
        self.client = httpx.Client(
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=timeout,
        )

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to Mender API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments for httpx request
            
        Returns:
            JSON response data
            
        Raises:
            MenderAPIError: If request fails or returns error status
        """
        url = urljoin(self.server_url, endpoint)

        try:
            response = self.client.request(method, url, **kwargs)
            response.raise_for_status()

            # Handle empty responses
            if not response.content:
                return {}

            return response.json()

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            raise MenderAPIError(error_msg, e.response.status_code)
        except httpx.RequestError as e:
            raise MenderAPIError(f"Request failed: {str(e)}")
        except json.JSONDecodeError as e:
            raise MenderAPIError(f"Invalid JSON response: {str(e)}")

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
        if device_type:
            params["device_type"] = device_type
        if limit:
            params["per_page"] = limit
        if skip:
            params["page"] = (skip // (limit or 20)) + 1

        data = self._make_request(
            "GET",
            "/api/management/v2/devauth/devices",
            params=params
        )

        return [MenderDevice(**device) for device in data]

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

    def get_deployments(self,
                       status: Optional[str] = None,
                       limit: Optional[int] = None,
                       skip: Optional[int] = None) -> List[MenderDeployment]:
        """Get list of deployments.
        
        Args:
            status: Filter by deployment status (inprogress, finished, etc.)
            limit: Maximum number of deployments to return
            skip: Number of deployments to skip (for pagination)
            
        Returns:
            List of MenderDeployment objects
        """
        params = {}
        if status:
            params["status"] = status
        if limit:
            params["per_page"] = limit
        if skip:
            params["page"] = (skip // (limit or 20)) + 1

        data = self._make_request(
            "GET",
            "/api/management/v1/deployments/deployments",
            params=params
        )

        return [MenderDeployment(**deployment) for deployment in data]

    def get_deployment(self, deployment_id: str) -> MenderDeployment:
        """Get details for a specific deployment.
        
        Args:
            deployment_id: Deployment ID
            
        Returns:
            MenderDeployment object
        """
        data = self._make_request(
            "GET",
            f"/api/management/v1/deployments/deployments/{deployment_id}"
        )

        return MenderDeployment(**data)

    def get_artifacts(self) -> List[MenderArtifact]:
        """Get list of artifacts.
        
        Returns:
            List of MenderArtifact objects
        """
        data = self._make_request(
            "GET",
            "/api/management/v1/deployments/artifacts"
        )

        return [MenderArtifact(**artifact) for artifact in data]

    def get_artifact(self, artifact_id: str) -> MenderArtifact:
        """Get details for a specific artifact.
        
        Args:
            artifact_id: Artifact ID
            
        Returns:
            MenderArtifact object
        """
        data = self._make_request(
            "GET",
            f"/api/management/v1/deployments/artifacts/{artifact_id}"
        )

        return MenderArtifact(**data)

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()
