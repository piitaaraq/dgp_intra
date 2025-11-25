# dgp_intra/routes/public/__init__.py
from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user
from dgp_intra.models import PatientsMenu
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

@bp.route("/patients-menu")
def patients_menu():
    today = date.today()
    weekday = today.strftime("%A").lower()  # monday, tuesday, etc.
    current_week = today.strftime("%Y-W%V")
    
    menu = PatientsMenu.query.filter_by(week=current_week).first()
    
    lunch = getattr(menu, weekday, None) if menu else None
    dinner = getattr(menu, f"{weekday}_dinner", None) if menu else None
    
    return render_template("daily_menu.html", lunch=lunch, dinner=dinner)
