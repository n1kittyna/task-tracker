from datetime import date, datetime, timezone
from enum import Enum

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Role(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    EMPLOYEE = "employee"


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


ROLE_LABELS = {"admin": "Администратор", "manager": "Менеджер", "employee": "Сотрудник"}
STATUS_LABELS = {"todo": "К выполнению", "in_progress": "В работе", "done": "Завершена"}
PRIORITY_LABELS = {"low": "Низкий", "medium": "Средний", "high": "Высокий"}

ROLE_VALUES = tuple(r.value for r in Role)
STATUS_VALUES = tuple(s.value for s in TaskStatus)
PRIORITY_VALUES = tuple(p.value for p in Priority)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=Role.EMPLOYEE.value)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    manager_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=now_utc)
    manager = db.relationship("User", remote_side=[id], back_populates="team_members")
    team_members = db.relationship("User", back_populates="manager")

    assigned_tasks = db.relationship(
        "Task", foreign_keys="Task.assignee_id", back_populates="assignee"
    )
    created_tasks = db.relationship(
        "Task", foreign_keys="Task.created_by_id", back_populates="author"
    )

    def set_password(self, raw: str) -> None:
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw: str) -> bool:
        return check_password_hash(self.password_hash, raw)

    @property
    def role_label(self) -> str:
        return ROLE_LABELS.get(self.role, self.role)

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.role})>"


class Task(db.Model):
    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    status = db.Column(db.String(20), nullable=False, default=TaskStatus.TODO.value, index=True)
    priority = db.Column(db.String(10), nullable=False, default=Priority.MEDIUM.value, index=True)
    assignee_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=now_utc)
    updated_at = db.Column(db.DateTime, nullable=False, default=now_utc, onupdate=now_utc)
    due_date = db.Column(db.Date, nullable=True)
    assignee = db.relationship("User", foreign_keys=[assignee_id], back_populates="assigned_tasks")
    author = db.relationship("User", foreign_keys=[created_by_id], back_populates="created_tasks")

    @property
    def is_overdue(self) -> bool:
        return (
            self.due_date is not None
            and self.due_date < date.today()
            and self.status != TaskStatus.DONE.value
        )

    @property
    def status_label(self) -> str:
        return STATUS_LABELS.get(self.status, self.status)

    @property
    def priority_label(self) -> str:
        return PRIORITY_LABELS.get(self.priority, self.priority)

    def __repr__(self) -> str:
        return f"<Task #{self.id} {self.title!r} {self.status}>"


@login_manager.user_loader
def load_user(user_id: str):
    try:
        user = db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None
    # Отключение администратором действует сразу, даже в уже открытой сессии.
    return user if user is not None and user.is_active else None
