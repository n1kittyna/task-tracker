from flask import Flask, render_template, request, url_for

from config import get_config

from .extensions import csrf, db, login_manager, migrate


def create_app(config_class=None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class or get_config())

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Импорт внутри функции — чтобы модели увидели уже настроенный db.
    from . import models  # noqa: F401  (регистрация таблиц + user_loader)
    from .blueprints import auth, main, reports, tasks, users
    for module in (main, auth, tasks, reports, users):
        app.register_blueprint(module.bp)

    register_jinja_globals(app)
    register_errors(app)

    from .cli import register_cli
    register_cli(app)
    return app


def register_jinja_globals(app: Flask) -> None:
    """Подписи, роли и хелперы — как ГЛОБАЛЫ Jinja, а не context_processor.

    Почему: макросы, подключённые через {% import %} без "with context",
    не видят контекст конкретного render_template, но видят глобалы
    окружения (именно так там работает url_for). Иначе STATUS_LABELS
    внутри status_badge был бы undefined.
    """
    from .models import (PRIORITY_LABELS, ROLE_LABELS, STATUS_LABELS, Priority,
                         Role, TaskStatus)
    from .security import can_change_status, can_manage_task

    def url_with(**overrides) -> str:
        """Текущий URL с изменёнными GET-параметрами (фильтры живут в ссылке)."""
        args = request.args.to_dict(flat=True)
        args.update(overrides)
        args = {k: v for k, v in args.items() if v not in (None, "")}
        return url_for(request.endpoint, **(request.view_args or {}), **args)

    app.jinja_env.globals.update(
        url_with=url_with,
        Role=Role,
        TaskStatus=TaskStatus,
        Priority=Priority,
        ROLE_LABELS=ROLE_LABELS,
        STATUS_LABELS=STATUS_LABELS,
        PRIORITY_LABELS=PRIORITY_LABELS,
        can_manage_task=can_manage_task,
        can_change_status=can_change_status,
    )


def register_errors(app: Flask) -> None:
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404