from dgp_intra import create_app
from flask_mail import Message
from dgp_intra.extensions import db, mail
from dgp_intra.models import User

def send_email_to_all_users():
    """
    Send an email to all users in the database who have an email address.
    """
    # Get all users with email addresses
    users = User.query.filter(User.email.isnot(None), User.email != '').all()
    
    print(f"Found {len(users)} users with email addresses")
    
    # Customize your message here
    subject = "Frokosten i dag"
    
    body = """Hej,

Kl. 12 frokosten i dag udgår, da vi afholder vores Julehygge kl. 13 i spisesalen. Vel mødt!

Med venlig hilsen,
DgP Intra
"""
    
    sent_count = 0
    failed_count = 0
    
    for user in users:
        try:
            msg = Message(
                subject=subject,
                recipients=[user.email],
                body=body
            )
            mail.send(msg)
            print(f"✓ Sent to {user.name} ({user.email})")
            sent_count += 1
        except Exception as e:
            print(f"✗ Failed to send to {user.name}: {str(e)}")
            failed_count += 1
    
    print(f"\nCompleted: {sent_count} sent, {failed_count} failed")

if __name__ == '__main__':
    app = create_app()
    
    with app.app_context():
        # Show preview first
        user_count = User.query.filter(User.email.isnot(None), User.email != '').count()
        print(f"About to send email to {user_count} users")
        confirm = input("Continue? (yes/no): ")
        
        if confirm.lower() == 'yes':
            send_email_to_all_users()
        else:
            print("Cancelled")