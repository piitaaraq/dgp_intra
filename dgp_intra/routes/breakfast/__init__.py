# dgp_intra/routes/breakfast/__init__.py
from flask import Blueprint, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from datetime import datetime
from dgp_intra.extensions import db
from dgp_intra.models import BreakfastRegistration
from dgp_intra.routes.shared import BREAKFAST_LOCK

bp = Blueprint("breakfast", __name__, url_prefix="/breakfast")

@bp.route("/register/<date>", methods=["POST"])
@login_required
def register(date):
    try:
        reg_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        abort(400)
    today = datetime.today().date()
    now = datetime.now().time()

    if reg_date.weekday() != 4:
        flash("Morgenmad er kun om fredagen.")
        return redirect(url_for('dashboard.view'))
    if reg_date == today and now >= BREAKFAST_LOCK:
        flash("Morgenmadstilmelding er lukket i dag (efter kl. 9).")
        return redirect(url_for('dashboard.view'))

    existing = BreakfastRegistration.query.filter_by(user_id=current_user.id, date=reg_date).first()
    if existing:
        flash("Allerede tilmeldt morgenmad den dag.")
        return redirect(url_for('dashboard.view'))

    db.session.add(BreakfastRegistration(date=reg_date, user_id=current_user.id))
    db.session.commit()
    flash(f"Tilmeldt morgenmad {reg_date.strftime('%A %d/%m')} kl. 10:00")
    return redirect(url_for('dashboard.view'))

@bp.route("/cancel/<date>", methods=["POST"])
@login_required
def cancel(date):
    try:
        reg_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        abort(400)
    today = datetime.today().date()
    now = datetime.now().time()

    if reg_date == today and now >= BREAKFAST_LOCK:
        flash("Du kan ikke afmelde morgenmad efter kl. 9.")
        return redirect(url_for('dashboard.view'))
    if reg_date < today:
        flash("Du kan ikke afmelde tidligere dage.")
        return redirect(url_for('dashboard.view'))

    registration = BreakfastRegistration.query.filter_by(user_id=current_user.id, date=reg_date).first()
    if not registration:
        flash("Du er ikke tilmeldt morgenmad den dag.")
        return redirect(url_for('dashboard.view'))

    db.session.delete(registration)
    db.session.commit()
    flash(f"Din morgenmadstilmelding {reg_date.strftime('%A %d/%m')} er annulleret.")
    return redirect(url_for('dashboard.view'))
