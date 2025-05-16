# dgp_intra/tasks/email_tasks.py
from flask_mail import Message
import datetime
from datetime import date
import os
from dgp_intra.extensions import db, mail
from dgp_intra.models import LunchRegistration, User, WeeklyMenu


def load_recipients(filename="email_recipients.txt"):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(base_dir, "..", "..", filename)

    try:
        with open(full_path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"[Warning] Could not find {full_path}. No email will be sent.")
        return []

def send_daily_kitchen_email():
    print("[Kitchen Email] Running at:", datetime.datetime.now().isoformat())
    today = date.today()
    iso_week = today.strftime("%Y-W%V")
    weekday = today.weekday()

    danish_weekdays = ["mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag", "søndag"]
    weekday_str = danish_weekdays[weekday]

    regs = (
        db.session.query(LunchRegistration, User)
        .join(User, LunchRegistration.user_id == User.id)
        .filter(LunchRegistration.date == today)
        .all()
    )

    recipients = load_recipients()
    subject = f"[DGP] Frokostregistreringer for {weekday_str} {today.strftime('%d/%m')}"

    print("Recipients loaded:", recipients)
    if not recipients:
        print("[Warning] No recipients found — email will not be sent.")
        return

    if not regs:
        print("Ingen registreringer for i dag.")
        body = "Ingen registreringer for i dag."
    else:
        names = [user.name for reg, user in regs]
        menu = WeeklyMenu.query.filter_by(week=iso_week).first()
        menu_text = [
            menu.monday, menu.tuesday, menu.wednesday,
            menu.thursday, menu.friday
        ][weekday] if menu else None

        body = f"Dagens registreringer ({weekday_str} {today.strftime('%d/%m')}):\n\n"
        body += "\n".join(f"- {name}" for name in names)

        if menu_text:
            body += f"\n\nMenu:\n{menu_text}"

    msg = Message(
        subject=subject,
        recipients=recipients,
        body=body
    )
    mail.send(msg)
    print("Email sent to:", recipients)