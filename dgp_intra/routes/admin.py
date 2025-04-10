# routes/admin.py
from flask import Blueprint, request, render_template, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from ..extensions import db
from ..models import User, LunchRegistration, WeeklyMenu
from datetime import datetime, timedelta
from collections import defaultdict
from datetime import date

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

from datetime import date, timedelta
from collections import defaultdict

@admin_bp.route('/')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        abort(403)

    users_who_owe = User.query.filter(User.owes > 0).all()

    today = date.today()  # Use pure date, not datetime
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=4)

    raw_regs = (
        db.session.query(LunchRegistration, User)
        .join(User, LunchRegistration.user_id == User.id)
        .filter(LunchRegistration.date.between(start_of_week, end_of_week))
        .order_by(LunchRegistration.date)
        .all()
    )

    grouped = defaultdict(list)
    for reg, user in raw_regs:
        grouped[reg.date].append(user)

    return render_template(
        'admin_dashboard.html',
        users_who_owe=users_who_owe,
        registrations=raw_regs,
        grouped_registrations=grouped
    )

@admin_bp.route('/mark_paid/<int:user_id>', methods=['POST'])
@login_required
def mark_paid(user_id):
    if not current_user.is_admin:
        abort(403)

    user = User.query.get(user_id)
    if not user:
        flash("User not found.")
        return redirect(url_for('admin.admin_dashboard'))

    user.owes = 0
    db.session.commit()
    flash(f"{user.name}'s balance has been cleared.")
    return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/menu', methods=['GET', 'POST'])
@login_required
def menu_input():
    if not current_user.is_admin:
        abort(403)

    # Get ISO week string for today
    current_week = date.today().strftime("%Y-W%V")

    menu = WeeklyMenu.query.filter_by(week=current_week).first()

    if request.method == 'POST':
        if not menu:
            menu = WeeklyMenu(week=current_week)

        menu.monday = request.form.get('monday')
        menu.tuesday = request.form.get('tuesday')
        menu.wednesday = request.form.get('wednesday')
        menu.thursday = request.form.get('thursday')
        menu.friday = request.form.get('friday')

        db.session.add(menu)
        db.session.commit()
        flash("Menu gemt for denne uge.")
        return redirect(url_for('admin.menu_input'))

    return render_template("admin_menu.html", menu=menu, current_week=current_week)

