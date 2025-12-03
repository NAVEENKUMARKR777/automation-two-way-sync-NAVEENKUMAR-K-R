import logging
from typing import Any, Dict, List, Optional

import requests

from .config import WORK_TRACKER_BASE_URL


logger = logging.getLogger(__name__)


class TaskClientError(Exception):
    pass


class TaskClient:
    """HTTP client for the Work Tracker FastAPI service."""

    def __init__(self, base_url: str = WORK_TRACKER_BASE_URL) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def _request(self, method: str, path: str, **kwargs) -> Any:
        url = f"{self.base_url}{path}"
        try:
            resp = self.session.request(method, url, timeout=10, **kwargs)
        except requests.RequestException as exc:
            logger.error("HTTP request failed: %s %s error=%s", method, url, exc)
            raise TaskClientError(str(exc)) from exc

        if not resp.ok:
            logger.error(
                "Work Tracker API error: %s %s status=%s body=%s",
                method,
                url,
                resp.status_code,
                resp.text,
            )
            raise TaskClientError(f"Status {resp.status_code}: {resp.text}")

        if resp.status_code == 204:
            return None
        return resp.json()

    def list_tasks(self) -> List[Dict[str, Any]]:
        return self._request("GET", "/tasks")

    def create_task(self, title: str, status: str, lead_id: str, notes: Optional[str] = None) -> Dict[str, Any]:
        payload = {"title": title, "status": status, "lead_id": lead_id, "notes": notes}
        return self._request("POST", "/tasks", json=payload)

    def get_task(self, task_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/tasks/{task_id}")

    def update_task(
        self,
        task_id: str,
        title: Optional[str] = None,
        status: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        if title is not None:
            payload["title"] = title
        if status is not None:
            payload["status"] = status
        if notes is not None:
            payload["notes"] = notes
        return self._request("PUT", f"/tasks/{task_id}", json=payload)

    def get_tasks_by_lead(self, lead_id: str) -> List[Dict[str, Any]]:
        return self._request("GET", f"/tasks/by-lead/{lead_id}")


