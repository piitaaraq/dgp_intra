from flask_mail import Message
import datetime
from dgp_intra.extensions import db, mail
from dgp_intra.models import User


def send_weekly_payment_reminders():
    """
    Send payment reminder emails to users who owe more than DKK 0.
    Intended to run every Monday at 8am.
    """
    print("[Payment Reminder] Running at:", datetime.datetime.now().isoformat())
    
    # Query users who owe money
    users_with_debt = User.query.filter(User.owes > 0).order_by(User.owes.desc()).all()
    
    if not users_with_debt:
        print("[Payment Reminder] No users with outstanding debt.")
        return
    
    print(f"[Payment Reminder] Found {len(users_with_debt)} users with debt")
    
    # Send individual emails to each user
    for user in users_with_debt:
        if not user.email:
            print(f"[Payment Reminder] Skipping {user.name} - no email address")
            continue
        
        subject = "Påmindelse: Betaling af madkonto"
        
        body = f"""Hej {user.name},

Dette er en venlig påmindelse om, at du skylder DKK {user.owes} på din madkonto hos Det Grønlandske Patienthjem.

Venligst afregn dit tilgodehavende ved lejlighed.

Med venlig hilsen,
DgP Intra
"""
        
        try:
            msg = Message(
                subject=subject,
                recipients=[user.email],
                body=body
            )
            mail.send(msg)
            print(f"[Payment Reminder] Sent to {user.name} ({user.email}) - owes DKK {user.owes}")
        except Exception as e:
            print(f"[Payment Reminder] Failed to send to {user.name}: {str(e)}")
    
    print(f"[Payment Reminder] Completed sending {len(users_with_debt)} reminder emails")