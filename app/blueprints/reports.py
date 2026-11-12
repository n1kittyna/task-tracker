from flask import Blueprint, render_template
from flask_login import current_user, login_required

from ..services.reports import assignee_report, report_totals, status_summary

bp = Blueprint("reports", __name__, url_prefix="/reports")


@bp.get("/")
@login_required
def report_list():
    """Доступ всем авторизованным, но цифры — строго по области видимости.

    admin -> вся система, manager -> команда, employee -> только он.
    """
    summary = status_summary(current_user)
    return render_template(
        "reports/report_list.html",
        summary=summary,
        rows=assignee_report(current_user),
        totals=report_totals(current_user),
        chart_labels=[s["label"] for s in summary],
        chart_values=[s["count"] for s in summary],
    )