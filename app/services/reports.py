"""Агрегации, совместимые с SQLite и PostgreSQL."""
from sqlalchemy import and_, case, func

from ..extensions import db
from ..models import STATUS_LABELS, Task, TaskStatus, User
from .tasks import overdue_conditions, scope_conditions


def _count(user: User, *extra) -> int:
    stmt = db.select(func.count(Task.id)).where(*scope_conditions(user), *extra)
    return db.session.scalar(stmt) or 0


def _percent(done: int, total: int) -> int:
    return round(done * 100 / total) if total else 0


def status_summary(user: User) -> list[dict]:
    stmt = (
        db.select(Task.status, func.count(Task.id))
        .where(*scope_conditions(user))
        .group_by(Task.status)
    )
    raw = dict(db.session.execute(stmt).all())
    return [
        {"value": s.value, "label": STATUS_LABELS[s.value], "count": raw.get(s.value, 0)}
        for s in TaskStatus
    ]


def assignee_report(user: User) -> list[dict]:
    """Задачи без исполнителя учитываются в общей сводке, но не в этой таблице."""
    stmt = (
        db.select(
            User.id, User.username,
            func.count(Task.id).label("total"),
            func.sum(case((Task.status == TaskStatus.DONE.value, 1), else_=0)).label("done"),
            func.sum(case((and_(*overdue_conditions()), 1), else_=0)).label("overdue"),
        )
        .join(Task, Task.assignee_id == User.id)
        .where(*scope_conditions(user))
        .group_by(User.id, User.username)
        .order_by(User.username)
    )
    return [
        {"id": r.id, "username": r.username, "total": r.total,
         "done": int(r.done or 0), "overdue": int(r.overdue or 0)}
        for r in db.session.execute(stmt).all()
    ]


def report_totals(user: User) -> dict:
    total = _count(user)
    done = _count(user, Task.status == TaskStatus.DONE.value)
    return {
        "total": total,
        "done": done,
        "overdue": _count(user, *overdue_conditions()),
        "completion_percent": _percent(done, total),
    }


def dashboard_stats(user: User) -> dict:
    mine = (Task.assignee_id == user.id,)
    total = _count(user)
    done = _count(user, Task.status == TaskStatus.DONE.value)
    return {
        "my_total": _count(user, *mine),
        "my_overdue": _count(user, *mine, *overdue_conditions()),
        "visible_total": total,
        "done": done,
        "overdue": _count(user, *overdue_conditions()),
        "completion_percent": _percent(done, total),
    }
