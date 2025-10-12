"""
HTTP client adapters for ServiceNow and Jira ITSM platforms.
"""

from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx


class TicketClientError(RuntimeError):
    """Raised when a remote ITSM integration fails."""


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

    def __init__(self, config: ServiceNowClientConfig) -> None:
        self._config = config
        self._token: Optional[str] = None
        self._token_expiry: Optional[float] = None

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
    ) -> httpx.Response:
        if not self.enabled:
            raise TicketClientError("ServiceNow client is not configured with a base URL")

        url = f"{self._config.base_url.rstrip('/')}/{path.lstrip('/')}"
        headers = self._build_headers()
        auth = None
        if self._config.auth_type.lower() == "oauth":
            token = await self._get_oauth_token()
            headers["Authorization"] = f"Bearer {token}"
        else:
            # Basic auth already encoded in header
            pass

        async with httpx.AsyncClient(
            timeout=self._config.timeout, verify=self._config.verify_ssl
        ) as client:
            response = await client.request(
                method,
                url,
                headers=headers,
                json=json_payload,
                params=params,
                auth=auth,
            )
        if response.status_code >= 400:
            raise TicketClientError(
                f"ServiceNow API responded with {response.status_code}: {response.text}"
            )
        return response

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
        response = await self._request(
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
            response = await self._request(
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
                    return entry
        return None


class JiraClient:
    """Thin wrapper around the Jira issue REST API."""

    def __init__(self, config: JiraClientConfig) -> None:
        self._config = config

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
    ) -> httpx.Response:
        if not self.enabled:
            raise TicketClientError("Jira client is not configured with a base URL")
        url = f"{self._config.base_url.rstrip('/')}/{path.lstrip('/')}"
        headers = self._build_headers()
        async with httpx.AsyncClient(
            timeout=self._config.timeout, verify=self._config.verify_ssl
        ) as client:
            response = await client.request(
                method, url, headers=headers, json=json_payload, params=params
            )
        if response.status_code >= 400:
            raise TicketClientError(
                f"Jira API responded with {response.status_code}: {response.text}"
            )
        return response

    async def create_issue(self, payload: Dict[str, Any]) -> TicketCreationResult:
        body = self._default_payload(payload)
        body = self._augment_with_links(body, payload)
        response = await self._request("POST", self._issue_endpoint(), json_payload=body)
        data = response.json()
        key = data.get("key")
        url = f"{self._config.base_url.rstrip('/')}/browse/{key}" if key else None
        metadata = {
            "id": data.get("id"),
            "key": key,
            "self": data.get("self"),
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
            response = await self._request("GET", f"{self._issue_endpoint()}/{ticket_key}")
        except TicketClientError:
            return None
        return response.json()


__all__ = [
    "ServiceNowClient",
    "JiraClient",
    "TicketClientError",
    "ServiceNowClientConfig",
    "JiraClientConfig",
    "TicketCreationResult",
]
