import pytest

from core.tickets.service import TicketService


@pytest.fixture(scope="module")
def ticket_service() -> TicketService:
    return TicketService()


def test_servicenow_defaults_priority_mapping(ticket_service: TicketService) -> None:
    job_dict = {
        "summary": "Database outage detected on primary cluster",
        "metrics": {"critical": 2, "errors": 10},
        "recommended_actions": ["Failover to replica", "Notify on-call DBA"],
        "categories": ["infrastructure", "database"],
    }

    defaults = ticket_service._servicenow_defaults(job_dict, "job-1234")

    assert defaults["short_description"].startswith("Database outage detected")
    # Critical severity should map to the highest ServiceNow priority
    assert defaults["priority"] == "1"
    assert "Recommended Actions" in defaults["description"]
    # Assignment defaults come from settings and may be None when not configured
    assert "assignment_group" in defaults


def test_jira_defaults_labels_and_priority(ticket_service: TicketService) -> None:
    job_dict = {
        "summary": "Memory leak identified in API service",
        "metrics": {"errors": 5, "warnings": 12},
        "recommended_actions": ["Redeploy patched build", "Increase monitoring thresholds"],
        "tags": ["api", "memory", "incident"],
    }

    defaults = ticket_service._jira_defaults(job_dict, "job-5678")

    assert defaults["summary"].startswith("Memory leak identified")
    # High severity (errors present) should map to "High"
    assert defaults["priority"] in {"High", "Highest"}
    assert "Redeploy patched build" in defaults["description"]
    assert set(defaults["labels"]) >= {"api", "memory", "incident"}
