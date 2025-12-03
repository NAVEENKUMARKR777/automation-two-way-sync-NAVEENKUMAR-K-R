from enum import Enum


class LeadStatus(str, Enum):
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    QUALIFIED = "QUALIFIED"
    LOST = "LOST"


class TaskStatus(str, Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"


def lead_to_task_status(lead_status: str) -> TaskStatus:
    """Map Lead Tracker status to Work Tracker task status."""
    try:
        status = LeadStatus(lead_status)
    except ValueError:
        # Default to TODO for unknown statuses
        return TaskStatus.TODO

    if status in (LeadStatus.NEW, LeadStatus.CONTACTED):
        return TaskStatus.IN_PROGRESS if status == LeadStatus.CONTACTED else TaskStatus.TODO
    if status == LeadStatus.QUALIFIED:
        return TaskStatus.DONE
    if status == LeadStatus.LOST:
        return TaskStatus.DONE
    return TaskStatus.TODO


def task_to_lead_status(task_status: str) -> LeadStatus:
    """Map Work Tracker task status to Lead Tracker status.

    We treat DONE as "terminal" and upgrade the lead to QUALIFIED
    if it is not already QUALIFIED or LOST.
    """
    try:
        status = TaskStatus(task_status)
    except ValueError:
        return LeadStatus.NEW

    if status == TaskStatus.TODO:
        return LeadStatus.NEW
    if status == TaskStatus.IN_PROGRESS:
        return LeadStatus.CONTACTED
    if status == TaskStatus.DONE:
        return LeadStatus.QUALIFIED
    return LeadStatus.NEW


