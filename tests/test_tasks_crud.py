from datetime import date, timedelta

from app.extensions import db
from app.models import Task, TaskStatus


def test_manager_creates_task(client, users, login, tomorrow):
    login("manager")
    resp = client.post("/tasks/new", data={
        "title": "Подготовить отчёт", "description": "за квартал",
        "status": "todo", "priority": "high",
        "assignee_id": users["employee"].id,
        "due_date": tomorrow.isoformat(),
    }, follow_redirects=True)
    assert resp.status_code == 200
    task = db.session.scalar(db.select(Task).where(Task.title == "Подготовить отчёт"))
    assert task is not None
    assert task.assignee_id == users["employee"].id
    assert task.created_by_id == users["manager"].id


def test_title_is_required(client, users, login):
    login("manager")
    resp = client.post("/tasks/new", data={
        "title": "", "status": "todo", "priority": "low", "assignee_id": 0,
    })
    assert "Название обязательно" in resp.get_data(as_text=True)
    assert db.session.scalar(db.select(Task)) is None


def test_due_date_cannot_be_in_past(client, users, login):
    login("manager")
    past = (date.today() - timedelta(days=3)).isoformat()
    resp = client.post("/tasks/new", data={
        "title": "Просроченная", "status": "todo", "priority": "low",
        "assignee_id": 0, "due_date": past,
    })
    assert "Срок не может быть в прошлом" in resp.get_data(as_text=True)
    assert db.session.scalar(db.select(Task)) is None


def test_list_and_detail(client, users, login, make_task):
    task = make_task(title="Уникальная-задача-42", assignee=users["employee"])
    login("employee")
    assert "Уникальная-задача-42" in client.get("/tasks/").get_data(as_text=True)
    detail = client.get(f"/tasks/{task.id}")
    assert detail.status_code == 200
    assert "Уникальная-задача-42" in detail.get_data(as_text=True)


def test_manager_updates_task(client, users, login, make_task, tomorrow):
    task = make_task(title="Старое название", assignee=users["employee"])
    login("manager")
    resp = client.post(f"/tasks/{task.id}/edit", data={
        "title": "Новое название", "description": "",
        "status": "in_progress", "priority": "high",
        "assignee_id": users["employee"].id, "due_date": tomorrow.isoformat(),
    }, follow_redirects=True)
    assert resp.status_code == 200
    db.session.refresh(task)
    assert task.title == "Новое название"
    assert task.status == "in_progress"


def test_edit_keeps_old_overdue_date(client, users, login, make_task):
    """Просроченную задачу можно править, не меняя срок."""
    past = date.today() - timedelta(days=5)
    task = make_task(title="Долг", assignee=users["employee"], due_date=past)
    login("manager")
    client.post(f"/tasks/{task.id}/edit", data={
        "title": "Долг (правлен)", "description": "", "status": "todo",
        "priority": "low", "assignee_id": users["employee"].id,
        "due_date": past.isoformat(),
    }, follow_redirects=True)
    db.session.refresh(task)
    assert task.title == "Долг (правлен)"


def test_delete_requires_post_and_confirm_page(client, users, login, make_task):
    task = make_task(title="На удаление", assignee=users["employee"])
    login("manager")
    page = client.get(f"/tasks/{task.id}/delete")
    assert page.status_code == 200
    assert "Удалить задачу?" in page.get_data(as_text=True)
    assert db.session.get(Task, task.id) is not None   # GET ничего не удаляет

    resp = client.post(f"/tasks/{task.id}/delete", follow_redirects=True)
    assert resp.status_code == 200
    assert db.session.get(Task, task.id) is None