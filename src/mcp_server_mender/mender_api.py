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
    artifact_provides: Optional[Dict[str, Any]] = None
    artifact_depends: Optional[Dict[str, Any]] = None


class MenderRelease(BaseModel):
    """Mender release model."""

    name: str
    modified: Optional[datetime] = None
    artifacts: List[Dict[str, Any]] = []
    artifacts_count: Optional[int] = None
    tags: List[Dict[str, str]] = []
    notes: Optional[str] = None

    @classmethod
    def from_v1_data(cls, data: Dict[str, Any]) -> "MenderRelease":
        """Create a MenderRelease from v1 API response data."""
        return cls(
            name=data.get("Name", ""),
            modified=data.get("Modified"),
            artifacts=data.get("Artifacts", []),
            artifacts_count=data.get("ArtifactsCount"),
            tags=data.get("tags", []),
            notes=data.get("notes", "")
        )
    
    @classmethod
    def from_v2_data(cls, data: Dict[str, Any]) -> "MenderRelease":
        """Create a MenderRelease from v2 API response data."""
        return cls(
            name=data.get("name", ""),
            modified=data.get("modified"),
            artifacts=data.get("artifacts", []),
            artifacts_count=data.get("artifacts_count"),
            tags=data.get("tags", []),
            notes=data.get("notes", "")
        )


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

    def get_releases(self,
                    name: Optional[str] = None,
                    tag: Optional[str] = None,
                    limit: Optional[int] = None,
                    skip: Optional[int] = None) -> List[MenderRelease]:
        """Get list of releases.
        
        Args:
            name: Filter by release name
            tag: Filter by release tag
            limit: Maximum number of releases to return
            skip: Number of releases to skip (for pagination)
            
        Returns:
            List of MenderRelease objects
        """
        params = {}
        if limit:
            params["per_page"] = limit
        if skip:
            params["page"] = (skip // (limit or 20)) + 1

        # Try v2 endpoint first, fallback to v1 if not available
        try:
            data = self._make_request(
                "GET",
                "/api/management/v2/deployments/deployments/releases",
                params=params
            )
            releases = [MenderRelease.from_v2_data(release) for release in data]
        except MenderAPIError as e:
            if e.status_code == 404:
                # Try v1 endpoint as fallback
                data = self._make_request(
                    "GET",
                    "/api/management/v1/deployments/deployments/releases",
                    params=params
                )
                releases = [MenderRelease.from_v1_data(release) for release in data]
            else:
                raise

        # Apply client-side filtering
        filtered_releases = releases
        
        if name:
            filtered_releases = [r for r in filtered_releases if name.lower() in r.name.lower()]
        
        if tag:
            # Filter by tag (search in tags)
            tag_filtered = []
            for release in filtered_releases:
                for tag_obj in release.tags:
                    if (tag.lower() in tag_obj.get("key", "").lower() or 
                        tag.lower() in str(tag_obj.get("value", "")).lower()):
                        tag_filtered.append(release)
                        break
            filtered_releases = tag_filtered
        
        return filtered_releases

    def get_release(self, release_name: str) -> MenderRelease:
        """Get details for a specific release.
        
        Args:
            release_name: Release name
            
        Returns:
            MenderRelease object
        """
        # Try v2 endpoint first, fallback to v1 if not available
        try:
            data = self._make_request(
                "GET",
                f"/api/management/v2/deployments/deployments/releases/{release_name}"
            )
            return MenderRelease.from_v2_data(data)
        except MenderAPIError as e:
            if e.status_code == 404:
                # Try v1 endpoint as fallback
                try:
                    data = self._make_request(
                        "GET",
                        f"/api/management/v1/deployments/deployments/releases/{release_name}"
                    )
                    return MenderRelease.from_v1_data(data)
                except MenderAPIError as v1_error:
                    # If both fail, try getting all releases and search
                    releases = self.get_releases()
                    for release in releases:
                        if release.name == release_name:
                            return release
                    
                    available_names = [r.name for r in releases]
                    raise MenderAPIError(
                        f"Release '{release_name}' not found. Available releases: {available_names}",
                        404
                    )
            else:
                raise

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()
