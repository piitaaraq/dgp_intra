# routes/auth/auth.py
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user
from werkzeug.security import generate_password_hash

from dgp_intra.extensions import db, mail
from dgp_intra.models import User
from dgp_intra.utils.tokens import generate_reset_token, verify_reset_token
from dgp_intra.utils.emails import send_email

bp = Blueprint("auth", __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        pw = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(pw):
            login_user(user)
            return redirect(url_for('dashboard.view'))  # was user.dashboard
        flash("Invalid login")
    return render_template('login.html')

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            token = generate_reset_token(email)
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            send_email(email, 'Password Reset', f'Klik her: {reset_url}')
        flash('Der kommer et link til dig, hvis din emailadresse er registreret i systemet.')
        return redirect(url_for('auth.login'))
    return render_template('forgot_password.html')

@bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    email = verify_reset_token(token)
    if not email:
        flash('Invalid or expired token.')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        new_password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user:
            user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            flash('Password opdateret. Venligst log in.')
            return redirect(url_for('auth.login'))

    return render_template('reset_password.html')
