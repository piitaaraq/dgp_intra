# deduct_credits.py

from dgp_intra import create_app
from dgp_intra.extensions import db
from dgp_intra.models import User
from dotenv import load_dotenv
import os

# Load environment variables and app
load_dotenv()
app = create_app()

# File containing emails (one per line)
EMAIL_FILE = "deduct_list.txt"

with app.app_context():
    if not os.path.exists(EMAIL_FILE):
        print(f"Missing file: {EMAIL_FILE}")
        exit(1)

    with open(EMAIL_FILE, "r", encoding="utf-8") as f:
        emails = [line.strip() for line in f if line.strip()]

    for email in emails:
        user = User.query.filter_by(email=email).first()
        if user:
            if user.credit > 0:
                user.credit -= 1
                print(f"{user.name} ({email}) → New credit: {user.credit}")
            else:
                print(f"{user.name} ({email}) has no credits to deduct.")
        else:
            print(f"User not found: {email}")

    db.session.commit()
    print("\n✅ Done. Credits deducted.")
