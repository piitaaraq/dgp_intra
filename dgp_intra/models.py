# models.py
from .extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(200))
    is_admin = db.Column(db.Boolean, default=False)
    credit = db.Column(db.Integer, default=0)
    owes = db.Column(db.Integer, default=0)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return str(self.id)
    
    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False


class LunchRegistration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class WeeklyMenu(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    week = db.Column(db.String(10))  # e.g. "2025-W14"
    monday = db.Column(db.String(200))
    tuesday = db.Column(db.String(200))
    wednesday = db.Column(db.String(200))
    thursday = db.Column(db.String(200))
    friday = db.Column(db.String(200))


class Vacation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

    user = db.relationship("User", backref="vacations")

    def __repr__(self):
        return f"<Vacation {self.user.name}: {self.start_date} to {self.end_date}>"