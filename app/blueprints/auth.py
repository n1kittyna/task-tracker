from urllib.parse import urlsplit

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from ..extensions import db
from ..forms import LoginForm, RegisterForm
from ..models import Role, User
from ..services.users import create_user

bp = Blueprint("auth", __name__, url_prefix="/auth")


def _safe_next(target: str | None) -> str:
    """Защита от open redirect: принимаем только относительные пути."""
    if target:
        parts = urlsplit(target)
        if not parts.scheme and not parts.netloc and target.startswith("/"):
            return target
    return url_for("main.dashboard")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    form = RegisterForm()
    if form.validate_on_submit():
        # Роль ВСЕГДА employee: иначе любой сможет зарегистрироваться админом.
        create_user(form.username.data, form.email.data, form.password.data, Role.EMPLOYEE.value)
        db.session.commit()
        flash("Регистрация успешна. Войдите под своим логином.", "success")
        return redirect(url_for("auth.login"))
    return render_template("registration/register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            db.select(User).where(User.username == form.username.data.strip())
        )
        if user is None or not user.check_password(form.password.data):
            flash("Неверный логин или пароль.", "danger")  # не уточняем, что именно
        elif not user.is_active:
            flash("Учётная запись отключена. Обратитесь к администратору.", "danger")
        else:
            login_user(user, remember=form.remember.data)
            flash(f"Добро пожаловать, {user.username}!", "success")
            # next сохраняется в query-string: форма постит на тот же URL.
            return redirect(_safe_next(request.args.get("next")))
    return render_template("registration/login.html", form=form)


@bp.post("/logout")
def logout():
    # POST + CSRF: выход по GET-ссылке может сработать от чужой картинки на странице.
    logout_user()
    flash("Вы вышли из системы.", "info")
    return redirect(url_for("auth.login"))