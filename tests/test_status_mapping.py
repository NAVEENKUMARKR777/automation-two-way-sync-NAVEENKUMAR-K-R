from sync.status_mapping import lead_to_task_status, task_to_lead_status, LeadStatus, TaskStatus


def test_lead_to_task_status_mapping():
    assert lead_to_task_status("NEW") == TaskStatus.TODO
    assert lead_to_task_status("CONTACTED") == TaskStatus.IN_PROGRESS
    assert lead_to_task_status("QUALIFIED") == TaskStatus.DONE
    assert lead_to_task_status("LOST") == TaskStatus.DONE


def test_task_to_lead_status_mapping():
    assert task_to_lead_status("TODO") == LeadStatus.NEW
    assert task_to_lead_status("IN_PROGRESS") == LeadStatus.CONTACTED
    assert task_to_lead_status("DONE") == LeadStatus.QUALIFIED


