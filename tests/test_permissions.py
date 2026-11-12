from app.extensions import db
from app.models import Task, TaskStatus


def test_employee_cannot_create_task(client, users, login):
    login("employee")
    assert client.get("/tasks/new").status_code == 403
    assert client.post("/tasks/new", data={"title": "Хак"}).status_code == 403


def test_employee_cannot_delete_own_task(client, users, login, make_task):
    """Видит, но удалять не вправе -> 403."""
    task = make_task(assignee=users["employee"])
    login("employee")
    assert client.post(f"/tasks/{task.id}/delete").status_code == 403
    assert db.session.get(Task, task.id) is not None


def test_employee_cannot_delete_foreign_task(client, users, login, make_task):
    """Чужая задача даже не видна -> 404 (не раскрываем существование)."""
    task = make_task(assignee=users["stranger"])
    login("employee")
    resp = client.post(f"/tasks/{task.id}/delete")
    assert resp.status_code == 404
    assert db.session.get(Task, task.id) is not None


def test_employee_cannot_open_foreign_task(client, users, login, make_task):
    task = make_task(title="Секрет", assignee=users["stranger"])
    login("employee")
    assert client.get(f"/tasks/{task.id}").status_code == 404
    assert "Секрет" not in client.get("/tasks/").get_data(as_text=True)


def test_employee_can_change_status_of_own_task(client, users, login, make_task):
    task = make_task(assignee=users["employee"])
    login("employee")
    resp = client.post(f"/tasks/{task.id}/status", data={"status": "done"}, follow_redirects=True)
    assert resp.status_code == 200
    db.session.refresh(task)
    assert task.status == TaskStatus.DONE.value


def test_employee_cannot_change_foreign_status(client, users, login, make_task):
    task = make_task(assignee=users["stranger"])
    login("employee")
    assert client.post(f"/tasks/{task.id}/status", data={"status": "done"}).status_code == 404
    db.session.refresh(task)
    assert task.status == TaskStatus.TODO.value


def test_employee_cannot_edit_task_fields(client, users, login, make_task):
    task = make_task(assignee=users["employee"])
    login("employee")
    assert client.post(f"/tasks/{task.id}/edit", data={"title": "Взлом"}).status_code == 403


def test_users_page_admin_only(client, users, login):
    login("employee")
    assert client.get("/users/").status_code == 403
    client.post("/auth/logout")
    login("manager")
    assert client.get("/users/").status_code == 403
    client.post("/auth/logout")
    login("admin")
    assert client.get("/users/").status_code == 200


def test_manager_sees_only_own_team(client, users, login, make_task):
    make_task(title="Задача-своей-команды", assignee=users["employee"])
    make_task(title="Задача-чужой-команды", assignee=users["stranger"])
    login("manager")
    html = client.get("/tasks/").get_data(as_text=True)
    assert "Задача-своей-команды" in html
    assert "Задача-чужой-команды" not in html


def test_manager_cannot_assign_outside_team(client, users, login, tomorrow):
    login("manager")
    resp = client.post("/tasks/new", data={
        "title": "Не свою", "status": "todo", "priority": "low",
        "assignee_id": users["stranger"].id, "due_date": tomorrow.isoformat(),
    })
    assert resp.status_code == 200
    assert db.session.scalar(db.select(Task).where(Task.title == "Не свою")) is None