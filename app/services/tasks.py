"""Область видимости, фильтрация, поиск и сортировка задач.

Для небольших команд поиск использует Unicode casefold без добавления отдельного
индекса или колонки в БД. Это обеспечивает одинаковое поведение для русского
текста в SQLite и PostgreSQL. При росте базы можно заменить его полнотекстовым
поиском соответствующей СУБД.
"""
from datetime import date

from flask import abort
from sqlalchemy import case

from ..extensions import db
from ..models import PRIORITY_VALUES, STATUS_VALUES, Priority, Role, Task, TaskStatus, User
from ..security import can_view_task, team_member_ids

SORT_OPTIONS = (
    ("newest", "Сначала новые"),
    ("oldest", "Сначала старые"),
    ("due_asc", "По ближайшему сроку"),
    ("priority_desc", "По приоритету"),
)


def scope_conditions(user: User) -> list:
    """Единая область данных для списка, сводок и отчётов."""
    if user.role == Role.ADMIN.value:
        return []
    if user.role == Role.MANAGER.value:
        ids = team_member_ids(user)
        return [db.or_(Task.assignee_id.in_(ids), Task.created_by_id == user.id)]
    return [Task.assignee_id == user.id]


def overdue_conditions() -> tuple:
    return (
        Task.due_date.is_not(None),
        Task.due_date < date.today(),
        Task.status != TaskStatus.DONE.value,
    )


def visible_tasks_stmt(user: User):
    return db.select(Task).where(*scope_conditions(user))


def apply_filters(stmt, args, user: User):
    """Фильтры и сортировка из GET-параметров; неподдерживаемые игнорируются."""
    status = (args.get("status") or "").strip()
    if status in STATUS_VALUES:
        stmt = stmt.where(Task.status == status)

    priority = (args.get("priority") or "").strip()
    if priority in PRIORITY_VALUES:
        stmt = stmt.where(Task.priority == priority)

    due = (args.get("due") or "").strip()
    if due == "overdue":
        stmt = stmt.where(*overdue_conditions())
    elif due == "today":
        stmt = stmt.where(Task.due_date == date.today())

    # Сотрудник не может расширить свою область доступа через query string.
    if user.role != Role.EMPLOYEE.value:
        assignee = (args.get("assignee") or "").strip()
        if assignee == "none":
            stmt = stmt.where(Task.assignee_id.is_(None))
        elif assignee.isdigit():
            stmt = stmt.where(Task.assignee_id == int(assignee))

    q = (args.get("q") or "").strip()[:200]
    if q:
        needle = q.casefold()
        # Сначала применены SQL-условия области доступа и другие фильтры,
        # только затем загружаются нужные для Unicode-поиска поля.
        candidates = db.session.execute(
            stmt.with_only_columns(Task.id, Task.title, Task.description).order_by(None)
        )
        matched_ids = [
            row.id for row in candidates
            if needle in row.title.casefold()
            or needle in (row.description or "").casefold()
        ]
        stmt = stmt.where(Task.id.in_(matched_ids))

    sort = (args.get("sort") or "newest").strip()
    if sort == "oldest":
        return stmt.order_by(Task.created_at.asc(), Task.id.asc())
    if sort == "due_asc":
        # NULL в конце, независимо от особенностей SQLite / PostgreSQL.
        return stmt.order_by(Task.due_date.is_(None), Task.due_date.asc(), Task.id.desc())
    if sort == "priority_desc":
        priority_rank = case(
            (Task.priority == Priority.HIGH.value, 0),
            (Task.priority == Priority.MEDIUM.value, 1),
            else_=2,
        )
        return stmt.order_by(priority_rank.asc(), Task.created_at.desc(), Task.id.desc())
    return stmt.order_by(Task.created_at.desc(), Task.id.desc())


def assignable_users(user: User) -> list[User]:
    stmt = db.select(User).where(User.is_active.is_(True)).order_by(User.username)
    if user.role == Role.ADMIN.value:
        return list(db.session.scalars(stmt))
    if user.role == Role.MANAGER.value:
        return list(db.session.scalars(stmt.where(User.id.in_(team_member_ids(user)))))
    return [user]  # сотруднику доступно назначение только самому себе


def get_visible_task_or_404(task_id: int, user: User) -> Task:
    task = db.session.get(Task, task_id)
    if task is None or not can_view_task(user, task):
        abort(404)
    return task
