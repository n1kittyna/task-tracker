from datetime import date, timedelta

from app.models import TaskStatus
from app.services.reports import assignee_report, report_totals, status_summary


def test_status_summary_counts(client, users, login, make_task):
    make_task(status=TaskStatus.TODO.value, assignee=users["employee"])
    make_task(status=TaskStatus.TODO.value, assignee=users["employee"])
    make_task(status=TaskStatus.DONE.value, assignee=users["employee"])
    login("admin")
    summary = {row["value"]: row["count"] for row in status_summary(users["admin"])}
    assert summary == {"todo": 2, "in_progress": 0, "done": 1}


def test_assignee_report_totals_done_overdue(client, users, login, make_task):
    past = date.today() - timedelta(days=2)
    make_task(assignee=users["employee"], status=TaskStatus.DONE.value, due_date=past)
    make_task(assignee=users["employee"], due_date=past)  # просрочена
    make_task(assignee=users["employee"])
    login("manager")
    rows = {r["username"]: r for r in assignee_report(users["manager"])}
    assert rows["employee"]["total"] == 3
    assert rows["employee"]["done"] == 1
    assert rows["employee"]["overdue"] == 1


def test_employee_report_is_personal(client, users, login, make_task):
    make_task(title="AAA-моя", assignee=users["employee"])
    make_task(title="BBB-чужая", assignee=users["stranger"])
    login("employee")
    resp = client.get("/reports/")
    assert resp.status_code == 200
    assert "личную статистику" in resp.get_data(as_text=True)
    assert report_totals(users["employee"])["total"] == 1


def test_manager_report_scoped_to_team(client, users, login, make_task):
    make_task(assignee=users["employee"])
    make_task(assignee=users["stranger"])
    login("manager")
    assert report_totals(users["manager"])["total"] == 1
    assert report_totals(users["admin"])["total"] == 2