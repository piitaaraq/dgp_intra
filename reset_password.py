# reset_password.py
from werkzeug.security import generate_password_hash
from dgp_intra import create_app
from dgp_intra.extensions import db
from dgp_intra.models import User

app = create_app()

def reset_password(email, new_password):
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if not user:
            print(f"❌ No user found with email: {email}")
            return

        user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        print(f"✅ Password reset for user: {email}")

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3:
        print("Usage: python reset_password.py <email> <new_password>")
    else:
        _, email, new_password = sys.argv
        reset_password(email, new_password)