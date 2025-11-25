# models.py
from .extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from enum import Enum



class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(200))
    is_admin = db.Column(db.Boolean, default=False)
    credit = db.Column(db.Integer, default=0)
    owes = db.Column(db.Integer, default=0)
    dob = db.Column(db.Date, nullable=True, index=True)
    pub_dob = db.Column(db.Boolean, nullable=False, default=False) 

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

class BreakfastRegistration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class WeeklyMenu(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    week = db.Column(db.String(10))  # e.g. "2025-W14"
    monday = db.Column(db.String(200))
    tuesday = db.Column(db.String(200))
    wednesday = db.Column(db.String(200))
    thursday = db.Column(db.String(200))
    friday = db.Column(db.String(200))

class PatientsMenu(db.Model):
    #lunch menu for patients
    id = db.Column(db.Integer, primary_key=True)
    week = db.Column(db.String(10))  # e.g. "2025-W14"
    monday = db.Column(db.String(200))
    tuesday = db.Column(db.String(200))
    wednesday = db.Column(db.String(200))
    thursday = db.Column(db.String(200))
    friday = db.Column(db.String(200))
    #dinner menu for patients
    monday_dinner = db.Column(db.String(200))
    tuesday_dinner = db.Column(db.String(200))
    wednesday_dinner = db.Column(db.String(200))
    thursday_dinner = db.Column(db.String(200))
    friday_dinner = db.Column(db.String(200))

class Vacation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

    user = db.relationship("User", backref="vacations")

    def __repr__(self):
        return f"<Vacation {self.user.name}: {self.start_date} to {self.end_date}>"
    
class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    deadline = db.Column(db.Date, nullable=True)
    
    organizer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    organizer = db.relationship('User', backref='organized_events')

    registrations = db.relationship('EventRegistration', back_populates='event', cascade="all, delete-orphan")


class EventRegistration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)

    user = db.relationship('User', backref='event_registrations')
    event = db.relationship('Event', back_populates='registrations')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'event_id', name='unique_event_registration'),
    )

# Implementatin of a ledger system for tracking credits and debts
class TxType(Enum):
    PURCHASE   = "purchase"    # top-up (+)
    SPEND      = "spend"       # charge for meal/event (-)
    ADJUSTMENT = "adjustment"  # manual +/- correction
    REFUND     = "refund"      # money back (+), usually the inverse of a spend

class TxStatus(Enum):
    PENDING = "pending"  # not yet applied to balance
    POSTED  = "posted"   # applied to balance
    CANCELED= "canceled" # voided, never applied

class CreditTransaction(db.Model):
    __tablename__ = "credit_transaction"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer,
                        db.ForeignKey('user.id', ondelete="CASCADE"),
                        index=True, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True, nullable=False)
    posted_at  = db.Column(db.DateTime, nullable=True)

    # Positive adds credits, negative removes
    delta_credits = db.Column(db.Integer, nullable=False)

    tx_type  = db.Column(db.Enum(TxType), nullable=False, index=True)
    status   = db.Column(db.Enum(TxStatus), default=TxStatus.PENDING, nullable=False, index=True)

    # Optional bookkeeping if you *do* want to show kr owed/paid one day
    amount_dkk_ore = db.Column(db.Integer, nullable=True)

    # Optional linkage to “what caused it”
    # e.g. a meal registration id, event registration id, or admin user
    source = db.Column(db.String(64), nullable=True)      # "lunch:2025-10-20"
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    note = db.Column(db.String(280), nullable=True)

    user = db.relationship("User", foreign_keys=[user_id],
                           backref=db.backref("credit_transactions", lazy="dynamic"))

    __table_args__ = (
        db.CheckConstraint('delta_credits <> 0', name='ck_tx_nonzero_delta'),
    )
