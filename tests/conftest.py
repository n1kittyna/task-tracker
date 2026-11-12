from datetime import date, timedelta

import pytest

from app import create_app
from app.extensions import db
from app.models import Priority, Role, Task, TaskStatus
from app.services.users import create_user
from config import TestConfig

PASSWORD = "password123"


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def users(app):
    admin = create_user("admin", "admin@example.com", PASSWORD, Role.ADMIN.value)
    manager = create_user("manager", "manager@example.com", PASSWORD, Role.MANAGER.value)
    manager2 = create_user("manager2", "manager2@example.com", PASSWORD, Role.MANAGER.value)
    employee = create_user("employee", "employee@example.com", PASSWORD, Role.EMPLOYEE.value, manager)
    stranger = create_user("stranger", "stranger@example.com", PASSWORD, Role.EMPLOYEE.value, manager2)
    db.session.commit()
    return {"admin": admin, "manager": manager, "manager2": manager2,
            "employee": employee, "stranger": stranger}


@pytest.fixture
def login(client):
    def _login(username, password=PASSWORD):
        return client.post("/auth/login",
                           data={"username": username, "password": password},
                           follow_redirects=True)
    return _login


@pytest.fixture
def make_task(app, users):
    def _make(title="Задача", assignee=None, author=None,
              status=TaskStatus.TODO.value, priority=Priority.MEDIUM.value,
              due_date=None, description=""):
        task = Task(title=title, description=description, status=status, priority=priority,
                    assignee=assignee, created_by_id=(author or users["manager"]).id,
                    due_date=due_date)
        db.session.add(task)
        db.session.commit()
        return task
    return _make


@pytest.fixture
def tomorrow():
    return date.today() + timedelta(days=1)