from flask import (Blueprint, abort, current_app, flash, jsonify, redirect,
                   render_template, request, url_for)
from flask_login import current_user, login_required

from ..extensions import db
from ..forms import StatusForm, TaskForm
from ..models import STATUS_LABELS, STATUS_VALUES, Role, Task
from ..security import can_change_status, can_manage_task, roles_required
from ..services.tasks import (apply_filters, assignable_users,
                              get_visible_task_or_404, visible_tasks_stmt)

bp = Blueprint("tasks", __name__, url_prefix="/tasks")

MANAGERS = (Role.ADMIN.value, Role.MANAGER.value)


def _fill_assignees(form: TaskForm) -> None:
    """Список исполнителей зависит от роли. Заполняем ДО валидации."""
    form.assignee_id.choices = [(0, "— не назначен —")] + [
        (u.id, f"{u.username} ({u.role_label})") for u in assignable_users(current_user)
    ]


# ---------- READ: список + фильтры ----------
@bp.get("/")
@login_required
def task_list():
    stmt = apply_filters(visible_tasks_stmt(current_user), request.args, current_user)
    page = request.args.get("page", 1, type=int)
    pagination = db.paginate(stmt, page=page,
                             per_page=current_app.config["TASKS_PER_PAGE"],
                             error_out=False)
    return render_template("tasks/task_list.html", pagination=pagination,
                           tasks=pagination.items,
                           assignees=assignable_users(current_user))


# ---------- READ: детальная ----------
@bp.get("/<int:task_id>")
@login_required
def task_detail(task_id: int):
    task = get_visible_task_or_404(task_id, current_user)
    form = StatusForm(status=task.status)
    return render_template("tasks/task_detail.html", task=task, status_form=form)


# ---------- CREATE ----------
@bp.route("/new", methods=["GET", "POST"])
@roles_required(*MANAGERS)
def task_create():
    form = TaskForm()
    _fill_assignees(form)
    if form.validate_on_submit():
        task = Task(
            title=form.title.data.strip(),
            description=form.description.data or "",
            status=form.status.data,
            priority=form.priority.data,
            assignee_id=form.assignee_id.data or None,   # 0 -> «не назначен»
            created_by_id=current_user.id,
            due_date=form.due_date.data,
        )
        db.session.add(task)
        db.session.commit()
        flash("Задача создана.", "success")
        return redirect(url_for("tasks.task_detail", task_id=task.id))
    return render_template("tasks/task_form.html", form=form, task=None)


# ---------- UPDATE ----------
@bp.route("/<int:task_id>/edit", methods=["GET", "POST"])
@roles_required(*MANAGERS)
def task_edit(task_id: int):
    task = get_visible_task_or_404(task_id, current_user)
    if not can_manage_task(current_user, task):
        abort(403)
    form = TaskForm(obj=task, original_due_date=task.due_date)
    _fill_assignees(form)
    if request.method == "GET":
        form.assignee_id.data = task.assignee_id or 0
    if form.validate_on_submit():
        task.title = form.title.data.strip()
        task.description = form.description.data or ""
        task.status = form.status.data
        task.priority = form.priority.data
        task.assignee_id = form.assignee_id.data or None
        task.due_date = form.due_date.data
        db.session.commit()   # updated_at проставится сам (onupdate)
        flash("Задача обновлена.", "success")
        return redirect(url_for("tasks.task_detail", task_id=task.id))
    return render_template("tasks/task_form.html", form=form, task=task)


# ---------- DELETE: GET = подтверждение, POST = удаление ----------
@bp.route("/<int:task_id>/delete", methods=["GET", "POST"])
@roles_required(*MANAGERS)
def task_delete(task_id: int):
    task = get_visible_task_or_404(task_id, current_user)
    if not can_manage_task(current_user, task):
        abort(403)
    if request.method == "POST":
        db.session.delete(task)
        db.session.commit()
        flash("Задача удалена.", "info")
        return redirect(url_for("tasks.task_list"))
    return render_template("tasks/task_confirm_delete.html", task=task)


# ---------- Смена статуса (доступна и employee) ----------
@bp.post("/<int:task_id>/status")
@login_required
def change_status(task_id: int):
    task = get_visible_task_or_404(task_id, current_user)
    if not can_change_status(current_user, task):
        abort(403)
    payload = request.get_json(silent=True) or {}
    new_status = request.form.get("status") or payload.get("status")
    if new_status not in STATUS_VALUES:
        abort(400)
    task.status = new_status
    db.session.commit()
    if request.is_json:   # для опционального fetch из app.js
        return jsonify(ok=True, status=task.status, status_label=STATUS_LABELS[task.status])
    flash("Статус обновлён.", "success")
    return redirect(url_for("tasks.task_detail", task_id=task.id))