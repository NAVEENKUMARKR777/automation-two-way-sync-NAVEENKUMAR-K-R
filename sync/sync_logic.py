import logging
from typing import Dict, List, Any

from .lead_client import LeadTrackerClient
from .task_client import TaskClient, TaskClientError
from .status_mapping import lead_to_task_status, task_to_lead_status, LeadStatus


logger = logging.getLogger(__name__)


class SyncService:
    """High-level orchestration for two-way sync between Lead Tracker and Work Tracker."""

    def __init__(self, lead_client: LeadTrackerClient, task_client: TaskClient) -> None:
        self.lead_client = lead_client
        self.task_client = task_client

    def _ensure_task_for_lead(self, lead: Dict[str, Any]) -> None:
        """Ensure a task exists for the given lead; create it if necessary."""
        lead_id = lead.get("id")
        if not lead_id:
            logger.warning("Lead at row %s is missing id; skipping", lead.get("_row"))
            return

        current_status = lead.get("status") or LeadStatus.NEW.value
        task_status = lead_to_task_status(current_status).value

        title = f"Follow up with {lead.get('name') or lead.get('email') or lead_id}"
        notes = f"Source: {lead.get('source')}" if lead.get("source") else None

        row = lead.get("_row")

        task_id = lead.get("task_id")
        if task_id:
            # Task already linked; keep it in sync with current lead status
            try:
                self.task_client.update_task(task_id=task_id, status=task_status)
                logger.info("Updated existing task %s for lead %s", task_id, lead_id)
            except TaskClientError:
                logger.exception("Failed to update task %s for lead %s", task_id, lead_id)
            return

        # No task yet; create one and write back the task_id
        try:
            task = self.task_client.create_task(
                title=title,
                status=task_status,
                lead_id=lead_id,
                notes=notes,
            )
            new_task_id = task["id"]
            self.lead_client.update_lead_fields(row=row, fields={"task_id": new_task_id})
            logger.info("Created task %s for lead %s", new_task_id, lead_id)
        except TaskClientError:
            logger.exception("Failed to create task for lead %s", lead_id)

    def initial_sync(self) -> None:
        """Perform initial idempotent sync from leads to tasks."""
        leads = self.lead_client.list_leads()
        for lead in leads:
            status = (lead.get("status") or "").upper()
            if status == LeadStatus.LOST.value:
                continue
            self._ensure_task_for_lead(lead)

    def sync_leads_to_tasks(self) -> None:
        """Propagate lead updates to their linked tasks."""
        leads = self.lead_client.list_leads()
        for lead in leads:
            status = (lead.get("status") or "").upper()
            if status == LeadStatus.LOST.value:
                continue
            self._ensure_task_for_lead(lead)

    def sync_tasks_to_leads(self) -> None:
        """Propagate task status updates back into leads."""
        leads_by_id: Dict[str, Dict[str, Any]] = {}
        for lead in self.lead_client.list_leads():
            lead_id = lead.get("id")
            if lead_id:
                leads_by_id[lead_id] = lead

        try:
            tasks: List[Dict[str, Any]] = self.task_client.list_tasks()
        except TaskClientError:
            logger.exception("Failed to list tasks from Work Tracker")
            return

        for task in tasks:
            lead_id = task.get("lead_id")
            if not lead_id:
                continue
            lead = leads_by_id.get(lead_id)
            if not lead:
                continue

            linked_task_id = lead.get("task_id")
            if linked_task_id and linked_task_id != task.get("id"):
                # Ignore unrelated tasks that happen to reference the same lead_id.
                continue
            if not linked_task_id:
                # If a lead somehow lacks a task_id, do not trust arbitrary tasks.
                continue

            desired_lead_status = task_to_lead_status(task.get("status"))
            current_status = (lead.get("status") or LeadStatus.NEW.value).upper()

            # Only let tasks "upgrade" leads; LOST remains final
            if current_status == LeadStatus.LOST.value:
                continue

            if current_status == desired_lead_status.value:
                continue

            row = lead.get("_row")
            logger.info(
                "Updating lead %s row=%s from status %s -> %s based on task %s",
                lead_id,
                row,
                current_status,
                desired_lead_status.value,
                task.get("id"),
            )
            try:
                self.lead_client.update_lead_fields(row=row, fields={"status": desired_lead_status.value})
            except Exception:  # noqa: BLE001
                logger.exception("Failed to update lead %s from task %s", lead_id, task.get("id"))

    def run_once(self, initial: bool = False) -> None:
        """Run a single sync iteration."""
        if initial:
            logger.info("Running initial sync (leads -> tasks)")
            self.initial_sync()
        else:
            logger.info("Running incremental sync (leads <-> tasks)")
            # Apply task-driven changes to leads first so we don't immediately
            # overwrite recent task updates with older lead state.
            self.sync_tasks_to_leads()
            self.sync_leads_to_tasks()


