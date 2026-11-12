from app.extensions import db
from app.models import Role, User


def test_register_creates_employee(client, users):
    resp = client.post("/auth/register", data={
        "username": "newbie", "email": "newbie@example.com",
        "password": "secret123", "confirm": "secret123",
    }, follow_redirects=True)
    assert resp.status_code == 200
    user = db.session.scalar(db.select(User).where(User.username == "newbie"))
    assert user is not None and user.role == Role.EMPLOYEE.value
    assert user.check_password("secret123")


def test_login_and_logout(client, users, login):
    resp = login("employee")
    assert "Добро пожаловать" in resp.get_data(as_text=True)
    resp = client.post("/auth/logout", follow_redirects=True)
    assert "Вы вышли" in resp.get_data(as_text=True)
    assert client.get("/tasks/").status_code == 302


def test_wrong_password_rejected(client, users, login):
    resp = login("employee", "wrong-password")
    assert "Неверный логин или пароль" in resp.get_data(as_text=True)
    assert client.get("/tasks/").status_code == 302


def test_anonymous_redirected_to_login(client, users):
    resp = client.get("/tasks/")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_inactive_user_cannot_login(client, users, login):
    users["employee"].is_active = False
    db.session.commit()
    resp = login("employee")
    assert "отключена" in resp.get_data(as_text=True)