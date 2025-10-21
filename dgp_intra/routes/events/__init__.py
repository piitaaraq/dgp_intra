# dgp_intra/routes/events/__init__.py
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import datetime, timedelta, date
from dgp_intra.extensions import db
from dgp_intra.models import Event, EventRegistration

bp = Blueprint("events", __name__, url_prefix="/events")

@bp.route("")
@login_required
def list():
    current_date = date.today()
    six_months_from_now = date.today() + timedelta(days=180)
    events = (Event.query
              .filter(Event.date >= date.today(), Event.date <= six_months_from_now)
              .order_by(Event.date, Event.time).all())
    user_registrations = {r.event_id for r in current_user.event_registrations}
    return render_template('events.html', events=events,
                           user_registrations=user_registrations, current_date=current_date)

@bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == 'POST':
        name = request.form.get('name')
        date_str = request.form.get('date')
        time_str = request.form.get('time')
        if not name or not date_str or not time_str:
            flash("Udfyld venligst alle felter.", "danger")
            return redirect(url_for('events.create'))
        try:
            event_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            event_time = datetime.strptime(time_str, '%H:%M').time()
        except ValueError:
            flash("Forkert dato eller tidspunkt.", "danger")
            return redirect(url_for('events.create'))

        deadline_str = request.form.get('deadline')
        deadline = None
        if deadline_str:
            try:
                deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
            except ValueError:
                flash("Ugyldig tilmeldingsfrist.", "danger")
                return redirect(url_for('events.create'))

        event = Event(name=name, date=event_date, time=event_time,
                      deadline=deadline, organizer_id=current_user.id)
        db.session.add(event)
        db.session.commit()
        flash("Arrangementet er oprettet!", "success")
        return redirect(url_for('events.list'))
    return render_template('create_event.html')

@bp.route("/register/<int:event_id>", methods=["POST"])
@login_required
def register(event_id):
    existing = EventRegistration.query.filter_by(user_id=current_user.id, event_id=event_id).first()
    if existing:
        flash("Du er allerede tilmeldt dette arrangement.")
    else:
        db.session.add(EventRegistration(user_id=current_user.id, event_id=event_id))
        db.session.commit()
        flash("Du er tilmeldt arrangementet.")
    return redirect(url_for('events.list'))

@bp.route("/unregister/<int:event_id>", methods=["POST"])
@login_required
def unregister(event_id):
    reg = EventRegistration.query.filter_by(user_id=current_user.id, event_id=event_id).first()
    if not reg:
        flash("Du er ikke tilmeldt dette arrangement.", "warning")
    else:
        db.session.delete(reg)
        db.session.commit()
        flash("Du er afmeldt arrangementet.", "success")
    return redirect(url_for('events.list'))

@bp.route("/delete/<int:event_id>", methods=["POST"])
@login_required
def delete(event_id):
    event = Event.query.get_or_404(event_id)
    if event.organizer_id != current_user.id:
        flash("Du har ikke tilladelse til at slette dette arrangement.", "danger")
        return redirect(url_for('events.list'))
    db.session.delete(event)
    db.session.commit()
    flash("Arrangementet er slettet.", "success")
    return redirect(url_for('events.list'))

@bp.route("/<int:event_id>")
@login_required
def detail(event_id):
    event = Event.query.get_or_404(event_id)
    registrations = EventRegistration.query.filter_by(event_id=event.id).all()
    registered_users = [r.user for r in registrations]
    is_registered = any(r.user_id == current_user.id for r in registrations)
    return render_template('event_detail.html', event=event,
                           registered_users=registered_users, is_registered=is_registered)
