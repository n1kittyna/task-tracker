from flask import Blueprint, render_template
from flask_login import current_user, login_required

from ..extensions import db
from ..models import Task
from ..services.reports import dashboard_stats
from ..services.tasks import visible_tasks_stmt

bp = Blueprint("main", __name__)


@bp.get("/")
@login_required
def dashboard():
    stats = dashboard_stats(current_user)
    recent = list(db.session.scalars(
        visible_tasks_stmt(current_user).order_by(Task.created_at.desc()).limit(5)
    ))
    return render_template("dashboard.html", stats=stats, recent=recent)