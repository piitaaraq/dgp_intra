# dgp_intra/routes/vacations/__init__.py
from flask import Blueprint, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from dgp_intra.extensions import db
from dgp_intra.models import Vacation
from datetime import datetime

bp = Blueprint("vacations", __name__, url_prefix="/vacations")

@bp.route("", methods=["POST"])
@login_required
def add():
    try:
        start_str = request.form.get('start_date')
        end_str = request.form.get('end_date')
        start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_str, '%Y-%m-%d').date()

        if end_date < start_date:
            flash("Slutdato kan ikke være før startdato.", "danger")
            return redirect(url_for('dashboard.view'))

        vacation = Vacation(user_id=current_user.id, start_date=start_date, end_date=end_date)
        db.session.add(vacation)
        db.session.commit()
        flash("Din ferie/fravær er registreret.", "success")
    except Exception as e:
        print(f"[Vacation Error] {e}")
        flash("Noget gik galt. Prøv igen.", "danger")
    return redirect(url_for('dashboard.view'))

@bp.route("/delete/<int:vacation_id>", methods=["POST"])
@login_required
def delete(vacation_id):
    vacation = Vacation.query.get_or_404(vacation_id)
    if vacation.user_id != current_user.id:
        abort(403)
    db.session.delete(vacation)
    db.session.commit()
    flash("Fraværet er slettet.", "success")
    return redirect(url_for('dashboard.view'))
