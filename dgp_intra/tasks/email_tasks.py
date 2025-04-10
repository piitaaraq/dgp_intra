from celery_worker import celery
from flask_mail import Message
from extensions import db, mail
from models import LunchRegistration, User, WeeklyMenu
from datetime import date

def load_recipients(filename="email_recipients.txt"):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"[Warning] Could not find {filename}. No email will be sent.")
        return []


@celery.task
def send_daily_kitchen_email():
    today = date.today()
    iso_week = today.strftime("%Y-W%V")
    weekday = today.weekday()

    regs = (
        db.session.query(LunchRegistration, User)
        .join(User, LunchRegistration.user_id == User.id)
        .filter(LunchRegistration.date == today)
        .all()
    )

    if not regs:
        print("No registrations today.")
        return

    names = [user.name for reg, user in regs]
    menu = WeeklyMenu.query.filter_by(week=iso_week).first()
    menu_text = [
        menu.monday, menu.tuesday, menu.wednesday,
        menu.thursday, menu.friday
    ][weekday] if menu else None

    body = f"Dagens registreringer ({today.strftime('%A %d/%m')}):\n\n"
    body += "\n".join(f"- {name}" for name in names)

    if menu_text:
        body += f"\n\nMenu:\n{menu_text}"

    msg = Message(
        subject=f"Frokostregistreringer for {today.strftime('%A %d/%m')}",
        recipients=load_recipients(),
        body=body
    )
    mail.send(msg)
    print("Email sent to kitchen.")
