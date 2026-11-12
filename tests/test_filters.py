from datetime import date, timedelta

from app.models import Priority, TaskStatus


def _html(client, query=""):
    return client.get("/tasks/" + query).get_data(as_text=True)


def test_filter_by_status(client, users, login, make_task):
    make_task(title="AAA-готово", status=TaskStatus.DONE.value, assignee=users["employee"])
    make_task(title="BBB-в-работе", status=TaskStatus.IN_PROGRESS.value, assignee=users["employee"])
    login("admin")
    html = _html(client, "?status=done")
    assert "AAA-готово" in html and "BBB-в-работе" not in html


def test_filter_by_priority(client, users, login, make_task):
    make_task(title="AAA-высокий", priority=Priority.HIGH.value)
    make_task(title="BBB-низкий", priority=Priority.LOW.value)
    login("admin")
    html = _html(client, "?priority=high")
    assert "AAA-высокий" in html and "BBB-низкий" not in html


def test_search_by_title_is_case_insensitive(client, users, login, make_task):
    make_task(title="Квартальный ОТЧЁТ")
    make_task(title="Прочее")
    login("admin")
    html = _html(client, "?q=отчёт")
    assert "Квартальный ОТЧЁТ" in html and "Прочее" not in html


def test_filter_overdue(client, users, login, make_task):
    yesterday = date.today() - timedelta(days=1)
    make_task(title="AAA-просрочена", due_date=yesterday)
    make_task(title="BBB-сделана-вовремя", due_date=yesterday, status=TaskStatus.DONE.value)
    make_task(title="CCC-будущее", due_date=date.today() + timedelta(days=2))
    login("admin")
    html = _html(client, "?due=overdue")
    assert "AAA-просрочена" in html
    assert "BBB-сделана-вовремя" not in html   # done не считается просрочкой
    assert "CCC-будущее" not in html


def test_filter_by_assignee_and_unassigned(client, users, login, make_task):
    make_task(title="AAA-у-сотрудника", assignee=users["employee"])
    make_task(title="BBB-без-исполнителя", assignee=None)
    login("admin")
    html = _html(client, f"?assignee={users['employee'].id}")
    assert "AAA-у-сотрудника" in html and "BBB-без-исполнителя" not in html
    html = _html(client, "?assignee=none")
    assert "BBB-без-исполнителя" in html and "AAA-у-сотрудника" not in html


def test_employee_assignee_filter_is_ignored(client, users, login, make_task):
    make_task(title="AAA-моя", assignee=users["employee"])
    make_task(title="BBB-чужая", assignee=users["stranger"])
    login("employee")
    html = _html(client, f"?assignee={users['stranger'].id}")
    assert "AAA-моя" in html and "BBB-чужая" not in html


def test_filters_survive_pagination(client, users, login, make_task):
    for i in range(12):
        make_task(title=f"ZZZ-{i:02d}", assignee=users["employee"])
    make_task(title="YYY-done", status="done", assignee=users["employee"])
    login("admin")
    html = _html(client, "?status=todo")
    assert "status=todo&amp;page=2" in html or "status=todo&page=2" in html
    assert "YYY-done" not in html