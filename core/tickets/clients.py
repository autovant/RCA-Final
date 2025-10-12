"""
HTTP client adapters for ServiceNow and Jira ITSM platforms.
"""

from __future__ import annotations

import asyncio
import base64
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from prometheus_client import Counter

from core.logging import get_logger

logger = get_logger(__name__)

# Prometheus metrics for retry attempts
itsm_ticket_retry_attempts_total = Counter(
    'itsm_ticket_retry_attempts_total',
    'Total number of ITSM ticket retry attempts',
    ['platform']
)


class TicketClientError(RuntimeError):
    """Raised when a remote ITSM integration fails."""


@dataclass
class RetryPolicy:
    """Configuration for retry behavior."""

    max_retries: int = 3
    retry_delay_seconds: float = 5.0
    exponential_backoff: bool = True
    backoff_multiplier: float = 2.0
    max_retry_delay_seconds: float = 60.0
    retryable_status_codes: List[int] = field(default_factory=lambda: [429, 500, 502, 503, 504])

    @classmethod
    def from_config(cls, config_path: Optional[str] = None) -> "RetryPolicy":
        """Load retry policy from itsm_config.json."""
        if config_path is None:
            config_path = str(Path(__file__).parent.parent.parent / "config" / "itsm_config.json")

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                retry_config = config.get("retry_policy", {})
                return cls(
                    max_retries=retry_config.get("max_retries", 3),
                    retry_delay_seconds=retry_config.get("retry_delay_seconds", 5.0),
                    exponential_backoff=retry_config.get("exponential_backoff", True),
                    backoff_multiplier=retry_config.get("backoff_multiplier", 2.0),
                    max_retry_delay_seconds=retry_config.get("max_retry_delay_seconds", 60.0),
                    retryable_status_codes=retry_config.get("retryable_status_codes", [429, 500, 502, 503, 504])
                )
        except Exception as e:
            logger.warning(f"Failed to load retry policy from config: {e}. Using defaults.")
            return cls()


@dataclass
class TimeoutConfig:
    """Configuration for request timeouts."""

    connection_timeout_seconds: float = 10.0
    read_timeout_seconds: float = 30.0
    total_timeout_seconds: float = 60.0

    @classmethod
    def from_config(cls, config_path: Optional[str] = None) -> "TimeoutConfig":
        """Load timeout config from itsm_config.json."""
        if config_path is None:
            config_path = str(Path(__file__).parent.parent.parent / "config" / "itsm_config.json")

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                timeout_config = config.get("timeout", {})
                return cls(
                    connection_timeout_seconds=timeout_config.get("connection_timeout_seconds", 10.0),
                    read_timeout_seconds=timeout_config.get("read_timeout_seconds", 30.0),
                    total_timeout_seconds=timeout_config.get("total_timeout_seconds", 60.0)
                )
        except Exception as e:
            logger.warning(f"Failed to load timeout config: {e}. Using defaults.")
            return cls()

    def to_httpx_timeout(self) -> httpx.Timeout:
        """Convert to httpx.Timeout object."""
        return httpx.Timeout(
            connect=self.connection_timeout_seconds,
            read=self.read_timeout_seconds,
            write=self.read_timeout_seconds,
            pool=self.total_timeout_seconds
        )


@dataclass(slots=True)
class ServiceNowClientConfig:
    """Configuration for the ServiceNow REST API adapter."""

    base_url: Optional[str] = None
    auth_type: str = "basic"  # "basic" | "oauth"
    username: Optional[str] = None
    password: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    token_url: Optional[str] = None
    default_assignment_group: Optional[str] = None
    default_configuration_item: Optional[str] = None
    default_category: Optional[str] = None
    default_subcategory: Optional[str] = None
    default_priority: Optional[str] = None
    default_state: Optional[str] = None
    assigned_to: Optional[str] = None
    verify_ssl: bool = True
    timeout: int = 30


@dataclass(slots=True)
class JiraClientConfig:
    """Configuration for the Jira REST API adapter."""

    base_url: Optional[str] = None
    auth_type: str = "basic"  # "basic" | "bearer"
    username: Optional[str] = None
    api_token: Optional[str] = None
    bearer_token: Optional[str] = None
    api_version: str = "3"
    default_project_key: Optional[str] = None
    default_issue_type: str = "Incident"
    default_priority: Optional[str] = None
    default_labels: Optional[list[str]] = None
    assignee: Optional[str] = None
    verify_ssl: bool = True
    timeout: int = 30


@dataclass(slots=True)
class TicketCreationResult:
    """Unified response for ticket creation in any ITSM platform."""

    ticket_id: str
    status: Optional[str]
    url: Optional[str]
    payload: Dict[str, Any]
    metadata: Dict[str, Any]


class ServiceNowClient:
    """Thin wrapper around the ServiceNow incident REST API."""

    _STATE_MAP = {
        "1": "New",
        "2": "In Progress",
        "3": "On Hold",
        "4": "Resolved",
        "5": "Closed",
        "6": "Cancelled",
        "7": "Closed",
    }

    def __init__(self, config: ServiceNowClientConfig, retry_policy: Optional[RetryPolicy] = None, timeout_config: Optional[TimeoutConfig] = None) -> None:
        self._config = config
        self._token: Optional[str] = None
        self._token_expiry: Optional[float] = None
        self._retry_policy = retry_policy or RetryPolicy.from_config()
        self._timeout_config = timeout_config or TimeoutConfig.from_config()

    @property
    def enabled(self) -> bool:
        return bool(self._config.base_url)

    async def _get_oauth_token(self) -> str:
        if (
            self._token
            and self._token_expiry is not None
            and self._token_expiry - time.monotonic() > 30
        ):
            return self._token

        if not all(
            [self._config.token_url, self._config.client_id, self._config.client_secret]
        ):
            raise TicketClientError(
                "ServiceNow OAuth configuration is incomplete (token_url/client credentials required)"
            )

        async with httpx.AsyncClient(timeout=self._config.timeout) as client:
            response = await client.post(
                self._config.token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._config.client_id,
                    "client_secret": self._config.client_secret,
                },
            )
            if response.status_code >= 400:
                raise TicketClientError(
                    f"ServiceNow OAuth token request failed with status {response.status_code}: {response.text}"
                )
            payload = response.json()
            token = payload.get("access_token")
            expires_in = payload.get("expires_in", 1800)
            if not token:
                raise TicketClientError("ServiceNow OAuth token response missing access_token")
            self._token = token
            self._token_expiry = time.monotonic() + int(expires_in)
            return token

    def _build_headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}

        if self._config.auth_type.lower() == "basic":
            if not (self._config.username and self._config.password):
                raise TicketClientError(
                    "ServiceNow basic authentication requires username and password"
                )
            credentials = f"{self._config.username}:{self._config.password}".encode()
            headers["Authorization"] = f"Basic {base64.b64encode(credentials).decode()}"
        elif self._config.auth_type.lower() == "oauth":
            # Token retrieval is async; this header is added later per request
            pass
        else:
            raise TicketClientError(
                f"Unsupported ServiceNow auth type: {self._config.auth_type}"
            )
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_payload: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> tuple[httpx.Response, Dict[str, Any]]:
        """
        Execute HTTP request with retry logic and exponential backoff.

        Returns:
            Tuple of (response, retry_metadata)
        """
        if not self.enabled:
            raise TicketClientError("ServiceNow client is not configured with a base URL")

        url = f"{self._config.base_url.rstrip('/')}/{path.lstrip('/')}"
        retry_metadata: Dict[str, Any] = {
            "retry_attempts": 0,
            "retry_delays": [],
            "retryable_errors": [],
            "final_error": None
        }

        for attempt in range(self._retry_policy.max_retries + 1):
            try:
                headers = self._build_headers()
                auth = None
                if self._config.auth_type.lower() == "oauth":
                    token = await self._get_oauth_token()
                    headers["Authorization"] = f"Bearer {token}"

                timeout = self._timeout_config.to_httpx_timeout()
                async with httpx.AsyncClient(
                    timeout=timeout, verify=self._config.verify_ssl
                ) as client:
                    response = await client.request(
                        method,
                        url,
                        headers=headers,
                        json=json_payload,
                        params=params,
                        auth=auth,
                    )

                # Check if response is retryable
                if response.status_code in self._retry_policy.retryable_status_codes:
                    error_msg = f"ServiceNow API responded with retryable status {response.status_code}"
                    retry_metadata["retryable_errors"].append({
                        "attempt": attempt + 1,
                        "status_code": response.status_code,
                        "message": error_msg
                    })

                    if attempt < self._retry_policy.max_retries:
                        # Calculate delay with exponential backoff
                        if self._retry_policy.exponential_backoff:
                            delay = min(
                                self._retry_policy.retry_delay_seconds * (self._retry_policy.backoff_multiplier ** attempt),
                                self._retry_policy.max_retry_delay_seconds
                            )
                        else:
                            delay = self._retry_policy.retry_delay_seconds

                        retry_metadata["retry_delays"].append(delay)
                        retry_metadata["retry_attempts"] = attempt + 1
                        
                        # Increment retry metric
                        itsm_ticket_retry_attempts_total.labels(platform="servicenow").inc()

                        logger.warning(f"ServiceNow request failed (attempt {attempt + 1}/{self._retry_policy.max_retries + 1}), retrying in {delay}s: {error_msg}")
                        await asyncio.sleep(delay)
                        continue

                # Non-retryable error
                if response.status_code >= 400:
                    error_msg = f"ServiceNow API responded with {response.status_code}: {response.text}"
                    retry_metadata["final_error"] = error_msg
                    raise TicketClientError(error_msg)

                # Success
                return response, retry_metadata

            except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError) as e:
                error_msg = f"ServiceNow request failed with network error: {type(e).__name__}: {str(e)}"
                retry_metadata["retryable_errors"].append({
                    "attempt": attempt + 1,
                    "error_type": type(e).__name__,
                    "message": str(e)
                })

                if attempt < self._retry_policy.max_retries:
                    if self._retry_policy.exponential_backoff:
                        delay = min(
                            self._retry_policy.retry_delay_seconds * (self._retry_policy.backoff_multiplier ** attempt),
                            self._retry_policy.max_retry_delay_seconds
                        )
                    else:
                        delay = self._retry_policy.retry_delay_seconds

                    retry_metadata["retry_delays"].append(delay)
                    retry_metadata["retry_attempts"] = attempt + 1

                    logger.warning(f"ServiceNow request failed (attempt {attempt + 1}/{self._retry_policy.max_retries + 1}), retrying in {delay}s: {error_msg}")
                    await asyncio.sleep(delay)
                    continue
                else:
                    retry_metadata["final_error"] = error_msg
                    raise TicketClientError(error_msg) from e

        # Should not reach here, but handle gracefully
        final_error = f"ServiceNow request exhausted all {self._retry_policy.max_retries + 1} attempts"
        retry_metadata["final_error"] = final_error
        raise TicketClientError(final_error)

    def _default_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(payload)
        data.setdefault("assignment_group", self._config.default_assignment_group)
        data.setdefault("configuration_item", self._config.default_configuration_item)
        data.setdefault("category", self._config.default_category)
        data.setdefault("subcategory", self._config.default_subcategory)
        data.setdefault("priority", self._config.default_priority or "3")
        data.setdefault("state", self._config.default_state or "1")
        data.setdefault("assigned_to", self._config.assigned_to)
        return data

    async def create_incident(self, payload: Dict[str, Any]) -> TicketCreationResult:
        """Create an incident and return the assigned identifiers."""
        request_payload = self._default_payload(payload)
        response, retry_metadata = await self._request(
            "POST",
            "/api/now/table/incident",
            json_payload=request_payload,
        )
        result = response.json().get("result") or {}
        sys_id = result.get("sys_id")
        number = result.get("number") or sys_id
        state = result.get("state")
        state_label = self._STATE_MAP.get(str(state), state)
        url = None
        if sys_id:
            url = f"{self._config.base_url.rstrip('/')}/nav_to.do?uri=incident.do?sys_id={sys_id}"
        metadata = {
            "sys_id": sys_id,
            "number": number,
            "state": state,
            "state_label": state_label,
            "retry_metadata": retry_metadata,
        }
        return TicketCreationResult(
            ticket_id=str(number),
            status=state_label,
            url=url,
            payload=request_payload,
            metadata=metadata,
        )

    async def fetch_incident(self, ticket_number: str) -> Optional[Dict[str, Any]]:
        """Retrieve a ServiceNow incident by ticket number."""
        try:
            response, retry_metadata = await self._request(
                "GET",
                "/api/now/table/incident",
                params={"sysparm_query": f"number={ticket_number}", "sysparm_limit": 1},
            )
        except TicketClientError:
            return None
        data = response.json()
        result = data.get("result")
        if isinstance(result, list):
            for entry in result:
                if str(entry.get("number")) == str(ticket_number):
                    entry["_retry_metadata"] = retry_metadata
                    return entry
        return None


class JiraClient:
    """Thin wrapper around the Jira issue REST API."""

    def __init__(self, config: JiraClientConfig, retry_policy: Optional[RetryPolicy] = None, timeout_config: Optional[TimeoutConfig] = None) -> None:
        self._config = config
        self._retry_policy = retry_policy or RetryPolicy.from_config()
        self._timeout_config = timeout_config or TimeoutConfig.from_config()

    @property
    def enabled(self) -> bool:
        return bool(self._config.base_url)

    def _build_headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        auth_type = self._config.auth_type.lower()
        if auth_type == "basic":
            if not (self._config.username and self._config.api_token):
                raise TicketClientError(
                    "Jira basic authentication requires username and api_token"
                )
            credentials = f"{self._config.username}:{self._config.api_token}".encode()
            headers["Authorization"] = f"Basic {base64.b64encode(credentials).decode()}"
        elif auth_type == "bearer":
            if not self._config.bearer_token:
                raise TicketClientError("Jira bearer authentication requires bearer_token")
            headers["Authorization"] = f"Bearer {self._config.bearer_token}"
        else:
            raise TicketClientError(f"Unsupported Jira auth type: {self._config.auth_type}")
        return headers

    def _issue_endpoint(self) -> str:
        version = self._config.api_version or "3"
        return f"/rest/api/{version}/issue"

    def _default_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        project_key = payload.get("project_key") or self._config.default_project_key
        if not project_key:
            raise TicketClientError("Jira project key is required to create an issue")

        issue_type = payload.get("issue_type") or self._config.default_issue_type
        description = payload.get("description")
        if isinstance(description, dict):
            # Already formatted in Atlassian doc format
            description_field = description
        else:
            description_field = description

        fields: Dict[str, Any] = {
            "project": {"key": project_key},
            "issuetype": {"name": issue_type},
            "summary": payload.get("summary") or "RCA Ticket",
        }
        if description_field:
            fields["description"] = description_field
        assignee = payload.get("assignee")
        if assignee:
            if isinstance(assignee, dict):
                fields["assignee"] = assignee
            else:
                fields["assignee"] = {"name": assignee}
        elif self._config.assignee:
            fields["assignee"] = {"name": self._config.assignee}
        labels = payload.get("labels") or self._config.default_labels or []
        if labels:
            fields["labels"] = labels
        priority = payload.get("priority") or self._config.default_priority
        if priority:
            if isinstance(priority, dict):
                fields["priority"] = priority
            else:
                fields["priority"] = {"name": priority}
        if payload.get("custom_fields"):
            fields.update(payload["custom_fields"])
        if payload.get("components"):
            fields["components"] = payload["components"]
        return {"fields": fields}

    def _augment_with_links(
        self, body: Dict[str, Any], payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        links = payload.get("issue_links")
        if links:
            body.setdefault("update", {})
            body["update"]["issuelinks"] = [
                {"add": link} for link in links if isinstance(link, dict)
            ]
        return body

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_payload: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> tuple[httpx.Response, Dict[str, Any]]:
        """
        Execute HTTP request with retry logic and exponential backoff.

        Returns:
            Tuple of (response, retry_metadata)
        """
        if not self.enabled:
            raise TicketClientError("Jira client is not configured with a base URL")

        url = f"{self._config.base_url.rstrip('/')}/{path.lstrip('/')}"
        retry_metadata: Dict[str, Any] = {
            "retry_attempts": 0,
            "retry_delays": [],
            "retryable_errors": [],
            "final_error": None
        }

        for attempt in range(self._retry_policy.max_retries + 1):
            try:
                headers = self._build_headers()
                timeout = self._timeout_config.to_httpx_timeout()

                async with httpx.AsyncClient(
                    timeout=timeout, verify=self._config.verify_ssl
                ) as client:
                    response = await client.request(
                        method, url, headers=headers, json=json_payload, params=params
                    )

                # Check if response is retryable
                if response.status_code in self._retry_policy.retryable_status_codes:
                    error_msg = f"Jira API responded with retryable status {response.status_code}"
                    retry_metadata["retryable_errors"].append({
                        "attempt": attempt + 1,
                        "status_code": response.status_code,
                        "message": error_msg
                    })

                    if attempt < self._retry_policy.max_retries:
                        # Calculate delay with exponential backoff
                        if self._retry_policy.exponential_backoff:
                            delay = min(
                                self._retry_policy.retry_delay_seconds * (self._retry_policy.backoff_multiplier ** attempt),
                                self._retry_policy.max_retry_delay_seconds
                            )
                        else:
                            delay = self._retry_policy.retry_delay_seconds

                        retry_metadata["retry_delays"].append(delay)
                        retry_metadata["retry_attempts"] = attempt + 1
                        
                        # Increment retry metric
                        itsm_ticket_retry_attempts_total.labels(platform="jira").inc()

                        logger.warning(f"Jira request failed (attempt {attempt + 1}/{self._retry_policy.max_retries + 1}), retrying in {delay}s: {error_msg}")
                        await asyncio.sleep(delay)
                        continue

                # Non-retryable error
                if response.status_code >= 400:
                    error_msg = f"Jira API responded with {response.status_code}: {response.text}"
                    retry_metadata["final_error"] = error_msg
                    raise TicketClientError(error_msg)

                # Success
                return response, retry_metadata

            except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError) as e:
                error_msg = f"Jira request failed with network error: {type(e).__name__}: {str(e)}"
                retry_metadata["retryable_errors"].append({
                    "attempt": attempt + 1,
                    "error_type": type(e).__name__,
                    "message": str(e)
                })

                if attempt < self._retry_policy.max_retries:
                    if self._retry_policy.exponential_backoff:
                        delay = min(
                            self._retry_policy.retry_delay_seconds * (self._retry_policy.backoff_multiplier ** attempt),
                            self._retry_policy.max_retry_delay_seconds
                        )
                    else:
                        delay = self._retry_policy.retry_delay_seconds

                    retry_metadata["retry_delays"].append(delay)
                    retry_metadata["retry_attempts"] = attempt + 1

                    logger.warning(f"Jira request failed (attempt {attempt + 1}/{self._retry_policy.max_retries + 1}), retrying in {delay}s: {error_msg}")
                    await asyncio.sleep(delay)
                    continue
                else:
                    retry_metadata["final_error"] = error_msg
                    raise TicketClientError(error_msg) from e

        # Should not reach here, but handle gracefully
        final_error = f"Jira request exhausted all {self._retry_policy.max_retries + 1} attempts"
        retry_metadata["final_error"] = final_error
        raise TicketClientError(final_error)

    async def create_issue(self, payload: Dict[str, Any]) -> TicketCreationResult:
        body = self._default_payload(payload)
        body = self._augment_with_links(body, payload)
        response, retry_metadata = await self._request("POST", self._issue_endpoint(), json_payload=body)
        data = response.json()
        key = data.get("key")
        url = f"{self._config.base_url.rstrip('/')}/browse/{key}" if key else None
        metadata = {
            "id": data.get("id"),
            "key": key,
            "self": data.get("self"),
            "retry_metadata": retry_metadata,
        }
        # Retrieve current status if requested
        fields = payload.get("fields") or {}
        status_name = fields.get("status", {}).get("name") if isinstance(fields, dict) else None
        return TicketCreationResult(
            ticket_id=key or str(data.get("id")),
            status=status_name,
            url=url,
            payload=body,
            metadata=metadata,
        )

    async def fetch_issue(self, ticket_key: str) -> Optional[Dict[str, Any]]:
        try:
            response, retry_metadata = await self._request("GET", f"{self._issue_endpoint()}/{ticket_key}")
        except TicketClientError:
            return None
        issue_data = response.json()
        issue_data["_retry_metadata"] = retry_metadata
        return issue_data


__all__ = [
    "ServiceNowClient",
    "JiraClient",
    "TicketClientError",
    "ServiceNowClientConfig",
    "JiraClientConfig",
    "TicketCreationResult",
    "RetryPolicy",
    "TimeoutConfig",
]
