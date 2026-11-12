"""Дополнительные тесты: личные CRUD-задачи, фильтры, сортировка и валидация."""
from datetime import date, timedelta

from app.extensions import db
from app.models import Priority, Role, Task, TaskStatus, User


def task_form_data(**overrides):
    data = {
        "title": "Личная задача", "description": "Написать конспект",
        "status": "todo", "priority": "medium", "due_date": "",
    }
    data.update(overrides)
    return data


def user_form_data(**overrides):
    data = {
        "username": "created", "email": "created@example.com",
        "role": Role.EMPLOYEE.value, "manager_id": "0",
        "is_active": "y", "password": "password123",
    }
    data.update(overrides)
    return data


def test_employee_personal_crud(client, users, login):
    login("employee")
    create = client.post("/tasks/new", data=task_form_data())
    assert create.status_code == 302
    task = db.session.scalar(db.select(Task).where(Task.title == "Личная задача"))
    assert task is not None
    assert task.created_by_id == users["employee"].id
    assert task.assignee_id == users["employee"].id

    assert client.get(f"/tasks/{task.id}/edit").status_code == 200
    edit = client.post(f"/tasks/{task.id}/edit", data=task_form_data(
        title="Моя отредактированная задача", description="Обновлённое описание",
        status="in_progress", priority="high",
        assignee_id=users["stranger"].id,
    ))
    assert edit.status_code == 302
    db.session.refresh(task)
    assert task.title == "Моя отредактированная задача"
    assert task.description == "Обновлённое описание"
    assert task.priority == "high"
    assert task.status == "in_progress"
    assert task.assignee_id == users["employee"].id  # подмена не сработала

    assert client.get(f"/tasks/{task.id}/delete").status_code == 200
    assert client.post(f"/tasks/{task.id}/delete").status_code == 302
    assert db.session.get(Task, task.id) is None
    assert client.get(f"/tasks/{task.id}").status_code == 404


def test_task_form_rejects_invalid_input(client, users, login):
    login("employee")
    for title in ("", "a" * 201):
        resp = client.post("/tasks/new", data=task_form_data(title=title))
        assert resp.status_code == 200
    assert db.session.scalar(db.select(db.func.count(Task.id))) == 0


def test_manager_task_not_editable_by_employee(client, users, login, make_task):
    task = make_task(assignee=users["employee"], author=users["manager"])
    login("employee")
    assert client.get(f"/tasks/{task.id}").status_code == 200
    assert client.get(f"/tasks/{task.id}/edit").status_code == 403
    assert client.get(f"/tasks/{task.id}/delete").status_code == 403
    assert client.post(f"/tasks/{task.id}/status", data={"status": "done"}).status_code == 302


def test_search_in_description_and_cyrillic_case(client, users, login, make_task):
    make_task(title="Семинар", description="ПОДГОТОВИТЬ ИССЛЕДОВАНИЕ", assignee=users["employee"])
    make_task(title="Другой текст", description="Ничего похожего", assignee=users["employee"])
    login("employee")
    html = client.get("/tasks/?q=исследование").get_data(as_text=True)
    assert "Семинар" in html
    assert "Другой текст" not in html


def test_combined_status_priority_filter(client, users, login, make_task):
    make_task(title="Нужная задача", status="todo", priority="high")
    make_task(title="Не тот статус", status="done", priority="high")
    make_task(title="Не тот приоритет", status="todo", priority="low")
    login("admin")
    html = client.get("/tasks/?status=todo&priority=high").get_data(as_text=True)
    assert "Нужная задача" in html
    assert "Не тот статус" not in html
    assert "Не тот приоритет" not in html


def test_sort_by_priority_and_due_date(client, users, login, make_task):
    today = date.today()
    low = make_task(title="Низкий порядок", priority=Priority.LOW.value,
                    due_date=today + timedelta(days=3))
    high = make_task(title="Высокий порядок", priority=Priority.HIGH.value,
                     due_date=today + timedelta(days=8))
    medium = make_task(title="Средний порядок", priority=Priority.MEDIUM.value,
                       due_date=today + timedelta(days=1))
    login("admin")
    html = client.get("/tasks/?sort=priority_desc").get_data(as_text=True)
    assert html.index("Высокий порядок") < html.index("Средний порядок") < html.index("Низкий порядок")
    html = client.get("/tasks/?sort=due_asc").get_data(as_text=True)
    assert html.index("Средний порядок") < html.index("Низкий порядок") < html.index("Высокий порядок")


def test_oldest_and_newest_sort(client, users, login, make_task):
    make_task(title="Первая задача")
    make_task(title="Вторая задача")
    login("admin")
    oldest = client.get("/tasks/?sort=oldest").get_data(as_text=True)
    newest = client.get("/tasks/?sort=newest").get_data(as_text=True)
    assert oldest.index("Первая задача") < oldest.index("Вторая задача")
    assert newest.index("Вторая задача") < newest.index("Первая задача")


def test_sort_filter_url_survives_pagination(client, users, login, make_task):
    for i in range(13):
        make_task(title=f"TEST-{i:02d}", priority="high")
    login("admin")
    html = client.get("/tasks/?sort=priority_desc&priority=high").get_data(as_text=True)
    assert "page=2" in html
    assert "sort=priority_desc" in html
    assert "priority=high" in html
    assert client.get("/tasks/?sort=priority_desc&priority=high&page=2").status_code == 200


def test_user_create_duplicate_username_or_email(client, users, login):
    login("admin")
    duplicate_name = client.post("/users/new", data=user_form_data(username="employee"))
    assert duplicate_name.status_code == 200
    assert "Такой логин уже занят" in duplicate_name.get_data(as_text=True)
    duplicate_email = client.post("/users/new", data=user_form_data(
        username="unused_name", email=" EMPLOYEE@example.com "
    ))
    assert duplicate_email.status_code == 200
    assert "Такой e-mail уже зарегистрирован" in duplicate_email.get_data(as_text=True)
    assert db.session.scalar(db.select(User).where(User.username == "unused_name")) is None


def test_user_edit_duplicate_username_or_email(client, users, login):
    login("admin")
    target = users["employee"]
    path = f"/users/{target.id}/edit"
    base = user_form_data(username="employee", email="employee@example.com", password="")
    name = client.post(path, data={**base, "username": "stranger"})
    assert name.status_code == 200
    assert "Такой логин уже занят" in name.get_data(as_text=True)
    mail = client.post(path, data={**base, "email": "stranger@example.com"})
    assert mail.status_code == 200
    assert "Такой e-mail уже зарегистрирован" in mail.get_data(as_text=True)
    db.session.refresh(target)
    assert target.username == "employee"
    assert target.email == "employee@example.com"


def test_admin_can_edit_user_without_changing_own_unique_values(client, users, login):
    login("admin")
    target = users["employee"]
    resp = client.post(f"/users/{target.id}/edit", data=user_form_data(
        username="employee", email="employee@example.com", password=""
    ))
    assert resp.status_code == 302


def test_user_deactivation_invalidates_existing_session(client, users, login):
    login("employee")
    assert client.get("/tasks/").status_code == 200
    users["employee"].is_active = False
    db.session.commit()
    response = client.get("/tasks/")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_report_progress_empty_and_completed(client, users, login, make_task):
    login("admin")
    empty = client.get("/reports/").get_data(as_text=True)
    assert "0%" in empty
    make_task(status=TaskStatus.DONE.value)
    make_task(status=TaskStatus.TODO.value)
    html = client.get("/reports/").get_data(as_text=True)
    assert "50%" in html
