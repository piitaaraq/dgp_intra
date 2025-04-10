# routes/user.py
from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user
from ..models import LunchRegistration, WeeklyMenu, Vacation, User
from datetime import datetime, timedelta
from flask_mail import Message
from ..extensions import mail, db
from werkzeug.security import check_password_hash, generate_password_hash

user_bp = Blueprint('user', __name__)

@user_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('user.dashboard'))
    return redirect(url_for('auth.login'))


@user_bp.route('/dashboard')
@login_required
def dashboard():
    today = datetime.today()
    start_of_week = today - timedelta(days=today.weekday())  # Monday
    dates = [(start_of_week + timedelta(days=i)).date() for i in range(5)]

    # Lunch registrations
    registered_dates = {
        r.date for r in LunchRegistration.query.filter_by(user_id=current_user.id).all()
    }

    # Weekly menu
    iso_week = today.strftime("%Y-W%V")
    weekly_menu = WeeklyMenu.query.filter_by(week=iso_week).first()

    # User vacations
    user_vacations = Vacation.query.filter_by(user_id=current_user.id).order_by(Vacation.start_date).all()

    # All vacations happening today (org-wide)
    today_vacations = (
        db.session.query(Vacation, User)
        .join(User, Vacation.user_id == User.id)
        .filter(Vacation.start_date <= today.date(), Vacation.end_date >= today.date())
        .order_by(User.name)
        .all()
    )

    return render_template(
        "dashboard.html",
        user=current_user,
        dates=dates,
        registered_dates=registered_dates,
        weekly_menu=weekly_menu,
        user_vacations=user_vacations,
        today_vacations=today_vacations  
    )


@user_bp.route('/register/<date>', methods=['POST'])
@login_required
def register_lunch(date):
    try:
        reg_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        abort(400)

    existing = LunchRegistration.query.filter_by(user_id=current_user.id, date=reg_date).first()
    if existing:
        flash("Already registered for that day.")
        return redirect(url_for('user.dashboard'))

    if current_user.credit < 1:
        flash("Not enough credit to register.")
        return redirect(url_for('user.dashboard'))

    reg = LunchRegistration(date=reg_date, user_id=current_user.id)
    db.session.add(reg)
    current_user.credit -= 1
    db.session.commit()

    flash(f"Registered for lunch on {reg_date.strftime('%A %d/%m')}")
    return redirect(url_for('user.dashboard'))

@user_bp.route('/cancel/<date>', methods=['POST'])
@login_required
def cancel_registration(date):
    try:
        reg_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        abort(400)

    registration = LunchRegistration.query.filter_by(user_id=current_user.id, date=reg_date).first()

    if not registration:
        flash("You have no registration for that date.")
        return redirect(url_for('user.dashboard'))

    db.session.delete(registration)
    current_user.credit += 1
    db.session.commit()

    flash(f"Your registration for {reg_date.strftime('%A %d/%m')} has been cancelled.")
    return redirect(url_for('user.dashboard'))

@user_bp.route('/buy', methods=['GET', 'POST'])
@login_required
def buy_credits():
    if request.method == 'POST':
        amount = int(request.form.get('amount'))
        if amount not in [1, 5]:
            flash("Ugyldigt antal klip valgt.")
            return redirect(url_for('user.buy_credits'))

        cost = amount * 22
        user = db.session.merge(current_user)

        if user.owes >= 110:
            flash("Du skylder allerede 110 kr. Du kan ikke købe flere klip før du har betalt.")
            return redirect(url_for('user.dashboard'))

        # Optional: also prevent buying if this purchase would push them over the cap
        if user.owes + cost > 110:
            flash("Denne transaktion vil få din gæld til at overstige 110 kr. Køb færre klip eller betal først.")
            return redirect(url_for('user.dashboard'))

        user.credit += amount
        user.owes += cost
        db.session.commit()

        flash(f"Du har købt {amount} klip. Du skylder nu {user.owes} DKK.")
        return redirect(url_for('user.dashboard'))

    return render_template('buy_credits.html')


@user_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current = request.form.get('current_password')
        new = request.form.get('new_password')
        confirm = request.form.get('confirm_password')

        if not current_user.check_password(current):
            flash("Nuværende adgangskode er forkert.")
        elif new != confirm:
            flash("De nye adgangskoder matcher ikke.")
        else:
            current_user.password_hash = generate_password_hash(new)
            db.session.commit()
            flash("Adgangskoden er blevet opdateret.")
            return redirect(url_for('user.dashboard'))

    return render_template('change_password.html')


@user_bp.route('/send_test_email')
@login_required
def send_test_email():
    msg = Message("Lunch App Test Email",
                  recipients=[current_user.email])
    msg.body = f"Hi {current_user.name},\n\nThis is a test email from your lunch registration app."
    mail.send(msg)

    flash("Test email sent to {{ current_user.email }}!")
    return redirect(url_for('user.dashboard'))

@user_bp.route('/vacation', methods=['POST'])
@login_required
def add_vacation():
    try:
        start_str = request.form.get('start_date')
        end_str = request.form.get('end_date')

        start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_str, '%Y-%m-%d').date()

        if end_date < start_date:
            flash("Slutdato kan ikke være før startdato.", "danger")
            return redirect(url_for('user.dashboard'))

        vacation = Vacation(user_id=current_user.id, start_date=start_date, end_date=end_date)
        db.session.add(vacation)
        db.session.commit()

        flash("Din ferie/fravær er registreret.", "success")
    except Exception as e:
        print(f"[Vacation Error] {e}")
        flash("Noget gik galt. Prøv igen.", "danger")

    return redirect(url_for('user.dashboard'))

@user_bp.route('/vacation/delete/<int:vacation_id>', methods=['POST'])
@login_required
def delete_vacation(vacation_id):
    vacation = Vacation.query.get_or_404(vacation_id)

    if vacation.user_id != current_user.id:
        abort(403)

    db.session.delete(vacation)
    db.session.commit()
    flash("Fraværet er slettet.", "success")
    return redirect(url_for('user.dashboard'))

