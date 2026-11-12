from functools import wraps

from flask import abort, current_app
from flask_login import current_user

from .extensions import db
from .models import Role, User


def roles_required(*roles: str):
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return current_app.login_manager.unauthorized()
            if current_user.role not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapper
    return decorator


def team_member_ids(user: User) -> list[int]:
    ids = list(db.session.scalars(db.select(User.id).where(User.manager_id == user.id)))
    return ids + [user.id]


def can_view_task(user: User, task) -> bool:
    if user.role == Role.ADMIN.value:
        return True
    if user.role == Role.MANAGER.value:
        return task.created_by_id == user.id or task.assignee_id in team_member_ids(user)
    return task.assignee_id == user.id  # employee


def can_manage_task(user: User, task) -> bool:
    if user.role == Role.ADMIN.value:
        return True
    if user.role == Role.MANAGER.value:
        return can_view_task(user, task)
    return False


def can_change_status(user: User, task) -> bool:
    if can_manage_task(user, task):
        return True
    return task.assignee_id == user.id