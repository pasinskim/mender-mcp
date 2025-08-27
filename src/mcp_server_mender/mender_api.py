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
    # Device statistics, e.g., {"inprogress": 5, "finished": 10, ...}
    statistics: Optional[Dict[str, Any]] = None


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

    # Factory methods to handle differences between v1 and v2 API responses
    @classmethod
    def from_v1_data(cls, data: Dict[str, Any]) -> 'MenderRelease':
        """Create MenderRelease from v1 API response data."""
        return cls(
            name=data.get('name', ''),
            modified=data.get('modified'),
            artifacts=data.get('artifacts', []),
            artifacts_count=len(data.get('artifacts', [])),
            tags=data.get('tags', []),
            notes=data.get('notes')
        )
    
    @classmethod
    def from_v2_data(cls, data: Dict[str, Any]) -> 'MenderRelease':
        """Create MenderRelease from v2 API response data."""
        return cls(
            name=data.get('name', ''),
            modified=data.get('modified'),
            artifacts=data.get('artifacts', []),
            artifacts_count=data.get('artifacts_count', len(data.get('artifacts', []))),
            tags=data.get('tags', []),
            notes=data.get('notes')
        )


class MenderInventoryItem(BaseModel):
    """Individual inventory attribute item."""
    
    name: str
    value: Any
    description: Optional[str] = None


class MenderDeviceInventory(BaseModel):
    """Complete device inventory including attributes."""
    
    device_id: str
    attributes: List[MenderInventoryItem] = []
    updated_ts: Optional[datetime] = None


class MenderDeploymentLogEntry(BaseModel):
    """Individual deployment log entry."""
    
    timestamp: Optional[datetime] = None
    level: Optional[str] = None  # INFO, ERROR, DEBUG, etc.
    message: str


class MenderDeploymentLog(BaseModel):
    """Complete deployment log for a device."""
    
    deployment_id: str
    device_id: str
    entries: List[MenderDeploymentLogEntry] = []
    retrieved_at: Optional[datetime] = None


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

    def _make_logs_request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make HTTP request for deployment logs that can handle various response formats.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments for httpx request
            
        Returns:
            Response data in original format (JSON dict, string, or raw content)
            
        Raises:
            MenderAPIError: If request fails or returns error status
        """
        url = urljoin(self.server_url, endpoint)

        try:
            response = self.client.request(method, url, **kwargs)
            response.raise_for_status()

            # Handle empty responses
            if not response.content:
                return ""

            # Try to determine response format based on content type
            content_type = response.headers.get("content-type", "").lower()
            
            # Try JSON first for structured log responses
            if "application/json" in content_type:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    # Fallback to text if JSON parsing fails
                    pass
            
            # Handle text-based responses (logs are often plain text)
            if any(text_type in content_type for text_type in ["text/", "application/text"]):
                return response.text
            
            # Try JSON parsing even without explicit content-type
            try:
                return response.json()
            except json.JSONDecodeError:
                pass
            
            # Try text decoding for any other content
            try:
                return response.text
            except UnicodeDecodeError:
                # If text decoding fails, return raw bytes as string representation
                return f"Binary content ({len(response.content)} bytes): {response.content[:100]!r}..."

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            raise MenderAPIError(error_msg, e.response.status_code)
        except httpx.RequestError as e:
            raise MenderAPIError(f"Request failed: {str(e)}")

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

    def get_device_inventory(self, device_id: str) -> MenderDeviceInventory:
        """Get complete inventory for a specific device.
        
        Args:
            device_id: Device ID
            
        Returns:
            MenderDeviceInventory object
        """
        data = self._make_request(
            "GET",
            f"/api/management/v1/inventory/devices/{device_id}"
        )
        
        # Convert API response to inventory items
        attributes = []
        if isinstance(data, dict):
            # v1 API returns attributes as a nested list
            if "attributes" in data and isinstance(data["attributes"], list):
                for attr in data["attributes"]:
                    if isinstance(attr, dict) and "name" in attr and "value" in attr:
                        attributes.append(MenderInventoryItem(
                            name=attr["name"], 
                            value=attr["value"],
                            description=attr.get("scope")  # Use scope as description
                        ))
            else:
                # Fallback: treat all keys as attributes
                for key, value in data.items():
                    if key not in ["id", "updated_ts"]:
                        attributes.append(MenderInventoryItem(name=key, value=value))
        
        return MenderDeviceInventory(
            device_id=device_id,
            attributes=attributes,
            updated_ts=data.get("updated_ts")
        )

    def get_devices_inventory(self,
                             limit: Optional[int] = None,
                             has_attribute: Optional[str] = None) -> List[MenderDeviceInventory]:
        """Get inventory for multiple devices.
        
        Args:
            limit: Maximum number of device inventories to return
            has_attribute: Filter devices that have a specific attribute name
            
        Returns:
            List of MenderDeviceInventory objects
        """
        params = {}
        if limit:
            params["per_page"] = limit
        if has_attribute:
            params["has_attribute"] = has_attribute
            
        data = self._make_request(
            "GET",
            "/api/management/v1/inventory/devices",
            params=params
        )
        
        inventories = []
        if isinstance(data, list):
            for device_data in data:
                device_id = device_data.get("id", "unknown")
                attributes = []
                
                # v1 API returns attributes as a nested list
                if "attributes" in device_data and isinstance(device_data["attributes"], list):
                    for attr in device_data["attributes"]:
                        if isinstance(attr, dict) and "name" in attr and "value" in attr:
                            attributes.append(MenderInventoryItem(
                                name=attr["name"], 
                                value=attr["value"],
                                description=attr.get("scope")  # Use scope as description
                            ))
                else:
                    # Fallback: treat all keys as attributes
                    for key, value in device_data.items():
                        if key not in ["id", "updated_ts"]:
                            attributes.append(MenderInventoryItem(name=key, value=value))
                
                inventories.append(MenderDeviceInventory(
                    device_id=device_id,
                    attributes=attributes,
                    updated_ts=device_data.get("updated_ts")
                ))
        
        return inventories

    def get_inventory_groups(self) -> List[Dict[str, Any]]:
        """Get all inventory groups.
        
        Returns:
            List of inventory group objects
        """
        data = self._make_request(
            "GET",
            "/api/management/v1/inventory/groups"
        )
        
        return data if isinstance(data, list) else []

    def get_device_group(self, device_id: str) -> Optional[str]:
        """Get group membership for a specific device.
        
        Args:
            device_id: Device ID
            
        Returns:
            Group name if device is in a group, None otherwise
        """
        try:
            data = self._make_request(
                "GET", 
                f"/api/management/v1/inventory/devices/{device_id}/group"
            )
            return data.get("group") if isinstance(data, dict) else None
        except MenderAPIError:
            # Device may not be in any group
            return None

    def get_deployment_device_log(self, deployment_id: str, device_id: str) -> MenderDeploymentLog:
        """Get deployment logs for specific device in deployment.
        
        Args:
            deployment_id: Deployment ID
            device_id: Device ID
            
        Returns:
            MenderDeploymentLog object
        """
        # Try v2 endpoint first, fallback to v1 if not available
        try:
            data = self._make_logs_request(
                "GET",
                f"/api/management/v2/deployments/deployments/{deployment_id}/devices/{device_id}/log"
            )
        except MenderAPIError as e:
            if e.status_code == 404:
                # Try v1 endpoint as fallback
                data = self._make_logs_request(
                    "GET", 
                    f"/api/management/v1/deployments/deployments/{deployment_id}/devices/{device_id}/log"
                )
            else:
                raise
        
        return self._parse_deployment_log_response(data, deployment_id, device_id)

    def get_deployment_logs(self, deployment_id: str) -> List[MenderDeploymentLog]:
        """Get deployment logs for all devices in deployment.
        
        Args:
            deployment_id: Deployment ID
            
        Returns:
            List of MenderDeploymentLog objects
        """
        # First get deployment details to find devices
        deployment = self.get_deployment(deployment_id)
        
        # Get devices that were part of this deployment
        # Try to get deployment devices endpoint, fallback to general approach
        try:
            # Try v2 endpoint first
            devices_data = self._make_request(
                "GET",
                f"/api/management/v2/deployments/deployments/{deployment_id}/devices"
            )
        except MenderAPIError as e:
            if e.status_code == 404:
                # Try v1 endpoint as fallback
                try:
                    devices_data = self._make_request(
                        "GET",
                        f"/api/management/v1/deployments/deployments/{deployment_id}/devices"
                    )
                except MenderAPIError:
                    # If we can't get deployment devices, return empty list
                    return []
            else:
                raise
        
        logs = []
        
        # Extract device IDs from deployment devices response
        device_ids = []
        if isinstance(devices_data, list):
            device_ids = [device.get("id") for device in devices_data if device.get("id")]
        elif isinstance(devices_data, dict) and "devices" in devices_data:
            device_ids = [device.get("id") for device in devices_data["devices"] if device.get("id")]
        
        # Get logs for each device
        for device_id in device_ids:
            try:
                log = self.get_deployment_device_log(deployment_id, device_id)
                logs.append(log)
            except MenderAPIError:
                # Continue if we can't get logs for one device
                continue
                
        return logs

    def _parse_deployment_log_response(self, data: Any, deployment_id: str, device_id: str) -> MenderDeploymentLog:
        """Parse deployment log response into MenderDeploymentLog object.
        
        Args:
            data: Raw response data from API
            deployment_id: Deployment ID
            device_id: Device ID
            
        Returns:
            MenderDeploymentLog object
        """
        entries = []
        
        if isinstance(data, str):
            # Plain text response - split into lines and create entries
            lines = data.strip().split('\n')
            for line in lines:
                if line.strip():
                    # Try to parse common log formats
                    entry = self._parse_log_line(line)
                    entries.append(entry)
        
        elif isinstance(data, list):
            # JSON array of log entries
            for entry_data in data:
                if isinstance(entry_data, dict):
                    entries.append(MenderDeploymentLogEntry(
                        timestamp=entry_data.get("timestamp"),
                        level=entry_data.get("level"),
                        message=entry_data.get("message", str(entry_data))
                    ))
                else:
                    entries.append(MenderDeploymentLogEntry(
                        message=str(entry_data)
                    ))
        
        elif isinstance(data, dict):
            # JSON object response
            if "entries" in data:
                # Structured log with entries
                for entry_data in data["entries"]:
                    entries.append(MenderDeploymentLogEntry(
                        timestamp=entry_data.get("timestamp"),
                        level=entry_data.get("level"),
                        message=entry_data.get("message", str(entry_data))
                    ))
            elif "messages" in data:
                # Alternative structure
                for message in data["messages"]:
                    entries.append(MenderDeploymentLogEntry(
                        message=str(message)
                    ))
            else:
                # Treat entire response as single log entry
                entries.append(MenderDeploymentLogEntry(
                    message=str(data)
                ))
        
        else:
            # Unknown format, treat as string
            entries.append(MenderDeploymentLogEntry(
                message=str(data)
            ))
        
        return MenderDeploymentLog(
            deployment_id=deployment_id,
            device_id=device_id,
            entries=entries,
            retrieved_at=datetime.now()
        )

    def _parse_log_line(self, line: str) -> MenderDeploymentLogEntry:
        """Parse individual log line into MenderDeploymentLogEntry.
        
        Args:
            line: Raw log line
            
        Returns:
            MenderDeploymentLogEntry object
        """
        # Try to extract timestamp and level from common log formats
        # Format 1: "2023-08-27T12:30:45Z INFO: message"
        # Format 2: "INFO: message"
        # Format 3: "message"
        
        import re
        
        # Try to match timestamp and level pattern
        timestamp_pattern = r'(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)'
        level_pattern = r'\b(DEBUG|INFO|WARN|WARNING|ERROR|FATAL|TRACE)\b'
        
        timestamp = None
        level = None
        message = line.strip()
        
        # Extract timestamp
        timestamp_match = re.search(timestamp_pattern, line)
        if timestamp_match:
            try:
                from dateutil.parser import parse
                timestamp = parse(timestamp_match.group(1))
                # Remove timestamp from message
                message = line.replace(timestamp_match.group(1), '').strip()
            except:
                pass
        
        # Extract level
        level_match = re.search(level_pattern, line, re.IGNORECASE)
        if level_match:
            level = level_match.group(1).upper()
            # Remove level indicator from message
            message = re.sub(rf'\b{re.escape(level_match.group(1))}\b\s*:?\s*', '', message, flags=re.IGNORECASE).strip()
        
        return MenderDeploymentLogEntry(
            timestamp=timestamp,
            level=level,
            message=message or line.strip()
        )

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()
