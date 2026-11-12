"""Общая логика создания пользователя: регистрация, админка, сид."""
from ..extensions import db
from ..models import Role, User


def create_user(username: str, email: str, password: str,
                role: str = Role.EMPLOYEE.value, manager: User | None = None) -> User:
    user = User(username=username.strip(), email=email.strip().lower(),
                role=role, manager=manager)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()  # чтобы у объекта появился id до commit
    return user