# dgp_intra/routes/profile/__init__.py
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from datetime import datetime
from flask_mail import Message
from dgp_intra.extensions import db, mail

bp = Blueprint("profile", __name__, url_prefix="/me")

@bp.route("/change-password", methods=["GET", "POST"])
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
            return redirect(url_for('dashboard.view'))
    return render_template('change_password.html')

@bp.route("/dob-consent", methods=["POST"])
@login_required
def dob_consent():
    wants_public = request.form.get('pub_dob') == '1'
    current_user.pub_dob = wants_public

    dob_str = request.form.get('dob')
    if dob_str:
        try:
            current_user.dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
        except ValueError:
            flash("Ugyldig fødselsdato.", "danger")
            return redirect(url_for('dashboard.view'))
    db.session.commit()
    flash("Dine indstillinger er opdateret.", "success")
    return redirect(url_for('dashboard.view'))

@bp.route("/send-test-email")
@login_required
def send_test_email():
    msg = Message(
        "Lunch App Test Email",
        recipients=[current_user.email],
        body=f"Hi {current_user.name},\n\nThis is a test email from your lunch registration app."
    )
    mail.send(msg)
    flash("Test email sent to your address!")
    return redirect(url_for('dashboard.view'))
