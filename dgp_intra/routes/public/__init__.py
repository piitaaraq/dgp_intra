# dgp_intra/routes/public/__init__.py
from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user
from datetime import date

bp = Blueprint("public", __name__)

@bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.view"))
    return redirect(url_for("auth.login"))

@bp.route("/terms")
def terms():
    return render_template("terms.html", last_updated=date.today().strftime("%d.%m.%Y"))
