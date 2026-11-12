from flask import (Blueprint, abort, flash, redirect, render_template, request,
                   url_for)
from flask_login import current_user

from ..extensions import db
from ..forms import UserForm
from ..models import ROLE_VALUES, Role, User
from ..security import roles_required
from ..services.users import create_user

bp = Blueprint("users", __name__, url_prefix="/users")


def _fill_managers(form: UserForm) -> None:
    managers = db.session.scalars(
        db.select(User).where(User.role == Role.MANAGER.value).order_by(User.username)
    )
    form.manager_id.choices = [(0, "— нет —")] + [(m.id, m.username) for m in managers]


@bp.get("/")
@roles_required(Role.ADMIN.value)
def user_list():
    stmt = db.select(User).order_by(User.username)
    role = request.args.get("role", "")
    if role in ROLE_VALUES:
        stmt = stmt.where(User.role == role)
    return render_template("users/user_list.html", users=list(db.session.scalars(stmt)))


@bp.route("/new", methods=["GET", "POST"])
@roles_required(Role.ADMIN.value)
def user_create():
    form = UserForm()
    _fill_managers(form)
    if form.validate_on_submit():
        if not form.password.data:
            form.password.errors.append("Для нового пользователя пароль обязателен.")
        else:
            user = create_user(
                form.username.data, form.email.data, form.password.data,
                role=form.role.data,
                manager=db.session.get(User, form.manager_id.data) if form.manager_id.data else None,
            )
            user.is_active = bool(form.is_active.data)
            db.session.commit()
            flash("Пользователь создан.", "success")
            return redirect(url_for("users.user_list"))
    return render_template("users/user_form.html", form=form, user=None)


@bp.route("/<int:user_id>/edit", methods=["GET", "POST"])
@roles_required(Role.ADMIN.value)
def user_edit(user_id: int):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    form = UserForm(obj=user, original_user=user)
    _fill_managers(form)
    if request.method == "GET":
        form.manager_id.data = user.manager_id or 0
    if form.validate_on_submit():
        if user.id == current_user.id and (
            form.role.data != Role.ADMIN.value or not form.is_active.data
        ):
            flash("Нельзя менять свою роль или отключать себя.", "danger")
            return redirect(url_for("users.user_edit", user_id=user.id))
        if form.manager_id.data == user.id:
            form.manager_id.errors.append("Пользователь не может быть руководителем сам себе.")
        else:
            user.username = form.username.data
            user.email = form.email.data
            user.role = form.role.data
            user.is_active = form.is_active.data
            user.manager_id = form.manager_id.data or None
            if form.password.data:
                user.set_password(form.password.data)
            db.session.commit()
            flash("Пользователь обновлён.", "success")
            return redirect(url_for("users.user_list"))
    return render_template("users/user_form.html", form=form, user=user)
