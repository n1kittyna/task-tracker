"""Выборки задач: сначала «что мне вообще видно», потом фильтры из URL."""
from datetime import date

from flask import abort

from ..extensions import db
from ..models import PRIORITY_VALUES, STATUS_VALUES, Role, Task, TaskStatus, User
from ..security import can_view_task, team_member_ids


def scope_conditions(user: User) -> list:
    """Список SQL-условий видимости. Переиспользуется в списках и отчётах."""
    if user.role == Role.ADMIN.value:
        return []
    if user.role == Role.MANAGER.value:
        ids = team_member_ids(user)
        return [db.or_(Task.assignee_id.in_(ids), Task.created_by_id == user.id)]
    return [Task.assignee_id == user.id]


def overdue_conditions() -> tuple:
    """Условия «просрочено» — один раз для фильтров, отчётов и дашборда."""
    return (
        Task.due_date.is_not(None),
        Task.due_date < date.today(),
        Task.status != TaskStatus.DONE.value,
    )


def visible_tasks_stmt(user: User):
    return db.select(Task).where(*scope_conditions(user))


def apply_filters(stmt, args, user: User):
    """Фильтры из GET-параметров. Невалидные значения молча игнорируем."""
    status = (args.get("status") or "").strip()
    if status in STATUS_VALUES:
        stmt = stmt.where(Task.status == status)

    priority = (args.get("priority") or "").strip()
    if priority in PRIORITY_VALUES:
        stmt = stmt.where(Task.priority == priority)

    q = (args.get("q") or "").strip()
    if q:
        # ilike: LIKE в SQLite (регистронезависим) и ILIKE в PostgreSQL.
        stmt = stmt.where(Task.title.ilike(f"%{q}%"))

    due = (args.get("due") or "").strip()
    if due == "overdue":
        stmt = stmt.where(*overdue_conditions())
    elif due == "today":
        stmt = stmt.where(Task.due_date == date.today())

    # Сотруднику фильтр по исполнителю не нужен: область уже сужена до него.
    if user.role != Role.EMPLOYEE.value:
        assignee = (args.get("assignee") or "").strip()
        if assignee == "none":
            stmt = stmt.where(Task.assignee_id.is_(None))
        elif assignee.isdigit():
            stmt = stmt.where(Task.assignee_id == int(assignee))

    return stmt.order_by(Task.created_at.desc(), Task.id.desc())


def assignable_users(user: User) -> list[User]:
    """Кого можно назначить исполнителем (ограничение на уровне формы)."""
    stmt = db.select(User).where(User.is_active.is_(True)).order_by(User.username)
    if user.role == Role.ADMIN.value:
        return list(db.session.scalars(stmt))
    if user.role == Role.MANAGER.value:
        return list(db.session.scalars(stmt.where(User.id.in_(team_member_ids(user)))))
    return []


def get_visible_task_or_404(task_id: int, user: User) -> Task:
    task = db.session.get(Task, task_id)
    # 404, а не 403: не подтверждаем существование чужой задачи.
    if task is None or not can_view_task(user, task):
        abort(404)
    return task