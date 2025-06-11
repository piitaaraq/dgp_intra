# routes/user.py
from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user
from ..models import LunchRegistration, WeeklyMenu, Vacation, User, Event, EventRegistration
from datetime import datetime, timedelta, time, date 

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
    now = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    dates = [(start_of_week + timedelta(days=i)).date() for i in range(5)]

    registered_dates = {
        r.date for r in LunchRegistration.query.filter_by(user_id=current_user.id).all()
    }

    next_event = (
    Event.query
    .filter(Event.date >= today.date())
    .order_by(Event.date.asc(), Event.time.asc())
    .first()
    )

    user_registrations = {r.event_id for r in current_user.event_registrations}

    if next_event:
        days_left = (next_event.date - today.date()).days
    else:
        days_left = None

    iso_week = today.strftime("%Y-W%V")
    weekly_menu = WeeklyMenu.query.filter_by(week=iso_week).first()
    user_vacations = Vacation.query.filter_by(user_id=current_user.id).order_by(Vacation.start_date).all()

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
        today_vacations=today_vacations,
        current_date=today.date(),
        current_time=now.time(),
        time = time,
        next_event=next_event,
        user_registrations=user_registrations,
        days_left=days_left,

    )


@user_bp.route('/register/<date>', methods=['POST'])
@login_required
def register_lunch(date):
    try:
        reg_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        abort(400)

    today = datetime.today().date()
    now = datetime.now().time()

    if reg_date == today and now >= time(9, 0):
        flash("Registrering er lukket for i dag (efter kl. 9).")
        return redirect(url_for('user.dashboard'))

    existing = LunchRegistration.query.filter_by(user_id=current_user.id, date=reg_date).first()
    if existing:
        flash("Already registered for that day.")
        return redirect(url_for('user.dashboard'))

    if reg_date.weekday() != 2 and current_user.credit < 1:  # Wednesday check
        flash("Not enough credit to register.")
        return redirect(url_for('user.dashboard'))

    reg = LunchRegistration(date=reg_date, user_id=current_user.id)
    db.session.add(reg)

    if reg_date.weekday() != 2:
        current_user.credit -= 1

    db.session.commit()

    flash(f"Registered for lunch on {reg_date.strftime('%A %d/%m')}")
    return redirect(url_for('user.dashboard'))


@user_bp.route('/plus_one/<date>', methods=['POST'])
@login_required
def add_plus_one(date):
    try:
        reg_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        abort(400)

    today = datetime.today().date()
    now = datetime.now().time()

    if reg_date == today and now >= time(9, 0):
        flash("Du kan ikke tilføje ekstra frokost efter kl. 9.")
        return redirect(url_for('user.dashboard'))

    if reg_date.weekday() != 2 and current_user.credit < 1:  # Wednesday check
        flash("Not enough credit to add an extra registration.")
        return redirect(url_for('user.dashboard'))

    plus_one = LunchRegistration(date=reg_date, user_id=current_user.id)
    db.session.add(plus_one)

    if reg_date.weekday() != 2:
        current_user.credit -= 1

    db.session.commit()

    flash(f"Added an extra meal for {reg_date.strftime('%A %d/%m')}")
    return redirect(url_for('user.dashboard'))


@user_bp.route('/cancel/<date>', methods=['POST'])
@login_required
def cancel_registration(date):
    try:
        reg_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        abort(400)

    today = datetime.today().date()
    now = datetime.now().time()

    if reg_date == today and now >= time(9, 0):
        flash("Du kan ikke afmelde efter kl. 9.")
        return redirect(url_for('user.dashboard'))

    if reg_date < today:
        flash("Du kan ikke afmelde tidligere dage.")
        return redirect(url_for('user.dashboard'))

    registration = LunchRegistration.query.filter_by(user_id=current_user.id, date=reg_date).first()

    if not registration:
        flash("Du er ikke tilmeldt den dag.")
        return redirect(url_for('user.dashboard'))

    db.session.delete(registration)

    if reg_date.weekday() != 2:  # Don't refund credit for Wednesdays
        current_user.credit += 1

    db.session.commit()

    flash(f"Din tilmelding til {reg_date.strftime('%A %d/%m')} er annulleret.")
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
    msg = Message(
        "Lunch App Test Email",
        recipients=[current_user.email],
        body=f"Hi {current_user.name},\n\nThis is a test email from your lunch registration app."
    )
    mail.send(msg)
    flash("Test email sent to your address!")
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

@user_bp.route('/events/create', methods=['GET', 'POST'])
@login_required
def create_event():
    if request.method == 'POST':
        name = request.form.get('name')
        date_str = request.form.get('date')
        time_str = request.form.get('time')

        if not name or not date_str or not time_str:
            flash("Udfyld venligst alle felter.", "danger")
            return redirect(url_for('user.create_event'))

        try:
            event_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            event_time = datetime.strptime(time_str, '%H:%M').time()
        except ValueError:
            flash("Forkert dato eller tidspunkt.", "danger")
            return redirect(url_for('user.create_event'))
        
        deadline_str = request.form.get('deadline')
        deadline = None
        if deadline_str:
            try:
                deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
            except ValueError:
                flash("Ugyldig tilmeldingsfrist.", "danger")
                return redirect(url_for('user.create_event'))


        event = Event(
            name=name,
            date=event_date,
            time=event_time,
            deadline=deadline,
            organizer_id=current_user.id
        )
        db.session.add(event)
        db.session.commit()

        flash("Arrangementet er oprettet!", "success")
        return redirect(url_for('user.events'))

    return render_template('create_event.html')


@user_bp.route('/events')
@login_required
def events():
    current_date = date.today()

    six_months_from_now = date.today() + timedelta(days=180)
    events = Event.query.filter(
        Event.date >= date.today(),
        Event.date <= six_months_from_now
    ).order_by(Event.date, Event.time).all()

    user_registrations = {r.event_id for r in current_user.event_registrations}

    return render_template(
        'events.html',
        events=events,
        user_registrations=user_registrations,
        current_date=current_date
    )

@user_bp.route('/events/register/<int:event_id>', methods=['POST'])
@login_required
def register_for_event(event_id):
    existing = EventRegistration.query.filter_by(user_id=current_user.id, event_id=event_id).first()
    if existing:
        flash("Du er allerede tilmeldt dette arrangement.")
    else:
        registration = EventRegistration(user_id=current_user.id, event_id=event_id)
        db.session.add(registration)
        db.session.commit()
        flash("Du er tilmeldt arrangementet.")

    return redirect(url_for('user.events'))

@user_bp.route('/events/unregister/<int:event_id>', methods=['POST'])
@login_required
def unregister_for_event(event_id):
    registration = EventRegistration.query.filter_by(
        user_id=current_user.id,
        event_id=event_id
    ).first()

    if not registration:
        flash("Du er ikke tilmeldt dette arrangement.", "warning")
    else:
        db.session.delete(registration)
        db.session.commit()
        flash("Du er afmeldt arrangementet.", "success")

    return redirect(url_for('user.events'))

@user_bp.route('/events/delete/<int:event_id>', methods=['POST'])
@login_required
def delete_event(event_id):
    event = Event.query.get_or_404(event_id)

    # Only the organizer can delete
    if event.organizer_id != current_user.id:
        flash("Du har ikke tilladelse til at slette dette arrangement.", "danger")
        return redirect(url_for('user.events'))

    db.session.delete(event)
    db.session.commit()
    flash("Arrangementet er slettet.", "success")

    return redirect(url_for('user.events'))

@user_bp.route('/events/<int:event_id>')
@login_required
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    registrations = EventRegistration.query.filter_by(event_id=event.id).all()
    registered_users = [r.user for r in registrations]

    is_registered = any(r.user_id == current_user.id for r in registrations)

    return render_template(
        'event_detail.html',
        event=event,
        registered_users=registered_users,
        is_registered=is_registered
    )

