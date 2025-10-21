# dgp_intra/routes/dashboard.py
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from datetime import datetime, timedelta, time
from sqlalchemy import and_
from dgp_intra.extensions import db
from dgp_intra.models import (
    LunchRegistration, WeeklyMenu, Vacation, User, Event, EventRegistration, BreakfastRegistration
)
from dgp_intra.routes.shared import next_birthday

bp = Blueprint("dashboard", __name__)

@bp.route("/dashboard")
@login_required
def view():
    today = datetime.today()
    now = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    dates = [(start_of_week + timedelta(days=i)).date() for i in range(5)]

    registered_dates = {
        r.date for r in LunchRegistration.query.filter_by(user_id=current_user.id).all()
    }
    registered_breakfast_dates = {
        r.date for r in BreakfastRegistration.query.filter_by(user_id=current_user.id).all()
    }

    next_events = (
        Event.query
        .filter(Event.date >= today.date())
        .order_by(Event.date.asc(), Event.time.asc())
        .limit(2)
        .all()
    )
    user_registrations = {r.event_id for r in current_user.event_registrations}
    days_left = (next_events[0].date - today.date()).days if next_events else None

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

    all_with_dob = User.query.filter(and_(User.pub_dob == True, User.dob.isnot(None))).all()
    today_d = today.date()
    upcoming_birthdays = []
    for u in all_with_dob:
        nb = next_birthday(u.dob, today_d)
        delta = (nb - today_d).days
        if 0 <= delta <= 30:
            upcoming_birthdays.append({
                "user": u,
                "date": nb,
                "in_days": delta,
                "age": nb.year - u.dob.year
            })
    upcoming_birthdays.sort(key=lambda x: (x["date"].month, x["date"].day))

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
        time=time,
        next_events=next_events,
        user_registrations=user_registrations,
        days_left=days_left,
        registered_breakfast_dates=registered_breakfast_dates,
        upcoming_birthdays=upcoming_birthdays,
    )
