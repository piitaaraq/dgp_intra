# dgp_intra/tasks/email_tasks.py
from flask_mail import Message
import datetime
from datetime import date
import os
from dgp_intra.extensions import db, mail
from dgp_intra.models import LunchRegistration, User, WeeklyMenu, BreakfastRegistration


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

    danish_weekdays = [
        "mandag",
        "tirsdag",
        "onsdag",
        "torsdag",
        "fredag",
        "lørdag",
        "søndag",
    ]
    weekday_str = danish_weekdays[weekday]

    regs = (
        db.session.query(LunchRegistration, User)
        .join(User, LunchRegistration.user_id == User.id)
        .filter(LunchRegistration.date == today)
        .all()
    )

    br_regs = []
    if weekday == 4:  # Friday
        br_regs = (
            db.session.query(BreakfastRegistration, User)
            .join(User, BreakfastRegistration.user_id == User.id)
            .filter(BreakfastRegistration.date == today)
            .order_by(User.name)
            .all()
        )

    recipients = load_recipients()
    subject = f"[DGP] Frokostregistreringer for {weekday_str} {today.strftime('%d/%m')}"

    print("Recipients loaded:", recipients)
    if not recipients:
        print("[Warning] No recipients found — email will not be sent.")
        return

    names_lunch = [user.name for reg, user in regs]
    names_breakfast = [user.name for _br, user in br_regs] if br_regs else []

    menu = WeeklyMenu.query.filter_by(week=iso_week).first()
    menu_text = (
        [menu.monday, menu.tuesday, menu.wednesday, menu.thursday, menu.friday][weekday]
        if menu
        else None
    )

    lines = []

    # Friday breakfast section (free, no menu)
    if weekday == 4:
        if names_breakfast:
            lines.append(f"Morgenmad (fredag {today.strftime('%d/%m')} kl. 10:00):")
            lines.extend(f"- {n}" for n in names_breakfast)
            lines.append("")  # spacer
        else:
            lines.append("Morgenmad: ingen tilmeldinger.")
            lines.append("")

    # Lunch section (existing behavior)
    if names_lunch:
        lines.append(
            f"Dagens registreringer til frokost ({weekday_str} {today.strftime('%d/%m')}):"
        )
        lines.extend(f"- {n}" for n in names_lunch)
        if menu_text:
            lines.append("")
            lines.append("Menu:")
            lines.append(menu_text)
    else:
        # If there were breakfast regs, we still want to say lunch has none
        if weekday == 4 and names_breakfast:
            lines.append("Frokost: ingen tilmeldinger.")
        else:
            lines.append("Ingen registreringer for i dag.")

    body = "\n".join(lines)

    msg = Message(subject=subject, recipients=recipients, body=body)
    mail.send(msg)
    print("Email sent to:", recipients)
