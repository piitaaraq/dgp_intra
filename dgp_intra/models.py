# models.py
from .extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from enum import Enum
import enum




class UserRole(enum.Enum):
    STAFF = "staff"                 # Regular staff (default)
    KITCHEN = "kitchen"             # Kitchen staff
    PATIENT_ADMIN = "patient_admin" # Patient management
    CLEANING = "cleaning"           # Cleaning personnel
    ADMIN = "admin"                 # Full system access


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(200))
    is_admin = db.Column(db.Boolean, default=False)  # Keep for backward compatibility
    role = db.Column(db.Enum(UserRole), default=UserRole.STAFF, nullable=False)
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
    
    # Role-based helper properties
    @property
    def is_kitchen_staff(self):
        """Check if user has kitchen access"""
        return self.role == UserRole.KITCHEN or self.role == UserRole.ADMIN
    
    @property
    def is_patient_admin(self):
        """Check if user can manage patient check-ins/outs"""
        return self.role == UserRole.PATIENT_ADMIN or self.role == UserRole.ADMIN
    
    @property
    def is_cleaning_staff(self):
        """Check if user can mark rooms as cleaned"""
        return self.role == UserRole.CLEANING or self.role == UserRole.ADMIN
    
    @property
    def is_admin_role(self):
        """Check if user has admin role (new role system)"""
        return self.role == UserRole.ADMIN
    
    @property
    def role_display(self):
        """Get user-friendly role name for display"""
        role_names = {
            UserRole.STAFF: "Personale",
            UserRole.KITCHEN: "Køkken",
            UserRole.PATIENT_ADMIN: "Patient Administrator",
            UserRole.CLEANING: "Rengøring",
            UserRole.ADMIN: "Administrator"
        }
        return role_names.get(self.role, "Personale")
    

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
    saturday = db.Column(db.String(200))
    sunday = db.Column(db.String(200))
    #dinner menu for patients
    monday_dinner = db.Column(db.String(200))
    tuesday_dinner = db.Column(db.String(200))
    wednesday_dinner = db.Column(db.String(200))
    thursday_dinner = db.Column(db.String(200))
    friday_dinner = db.Column(db.String(200))
    saturday_dinner = db.Column(db.String(200))
    sunday_dinner = db.Column(db.String(200))

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


class CleaningStatus(enum.Enum):
    CLEAN = "clean"
    NEEDS_CLEANING = "needs_cleaning"



class DailyArrivalForecast(db.Model):
    __tablename__ = 'daily_arrival_forecasts'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, nullable=False, index=True)
    expected_arrivals = db.Column(db.Integer, default=0, nullable=False)
    
    # Tracking
    updated_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    updated_by = db.relationship('User', backref='forecast_updates')
    
    def __repr__(self):
        return f'<DailyArrivalForecast {self.date}: {self.expected_arrivals} arrivals>'
    


class Room(db.Model):
    __tablename__ = 'rooms'
    
    id = db.Column(db.Integer, primary_key=True)
    room_number = db.Column(db.String(10), unique=True, nullable=False, index=True)
    floor = db.Column(db.Integer, nullable=False)  # 1, 2, 3, or 4
    
    # Occupancy tracking
    patient_count = db.Column(db.Integer, default=0)  # 0, 1, or 2
    relative_count = db.Column(db.Integer, default=0)  # 0 or 1
    
    # Cleaning tracking
    cleaning_status = db.Column(db.Enum(CleaningStatus), default=CleaningStatus.CLEAN)
    last_cleaned_at = db.Column(db.DateTime, nullable=True)
    last_cleaned_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Timestamps
    last_occupancy_change = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Optional notes
    notes = db.Column(db.Text, nullable=True)
    
    # Relationships
    last_cleaned_by = db.relationship('User', foreign_keys=[last_cleaned_by_id], backref='rooms_cleaned')
    cleaning_logs = db.relationship('CleaningLog', back_populates='room', cascade='all, delete-orphan')

    # Checking out
    checking_out_tomorrow = db.Column(db.Boolean, default=False, nullable=False)
    
    @property
    def is_occupied(self):
        """Check if room has any occupants"""
        return self.patient_count > 0 or self.relative_count > 0
    
    @property
    def total_occupants(self):
        """Total number of people in the room"""
        return self.patient_count + self.relative_count
    
    @property
    def needs_cleaning(self):
        """Check if room needs cleaning"""
        return self.cleaning_status == CleaningStatus.NEEDS_CLEANING
    
    def __repr__(self):
        return f'<Room {self.room_number}>'


class CleaningLog(db.Model):
    __tablename__ = 'cleaning_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    
    # Who cleaned it
    cleaned_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    cleaned_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Status changes
    status_before = db.Column(db.Enum(CleaningStatus), nullable=False)
    status_after = db.Column(db.Enum(CleaningStatus), nullable=False)
    
    # Optional notes
    notes = db.Column(db.Text, nullable=True)
    
    # Relationships
    room = db.relationship('Room', back_populates='cleaning_logs')
    cleaned_by = db.relationship('User', backref='cleaning_history')
    
    def __repr__(self):
        return f'<CleaningLog room={self.room.room_number} by={self.cleaned_by.name} at={self.cleaned_at}>'


class MealType(enum.Enum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"


class MealRegistration(db.Model):
    __tablename__ = 'meal_registrations'
    
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    meal_type = db.Column(db.Enum(MealType), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    
    # How many people ate
    people_count = db.Column(db.Integer, nullable=False)
    
    # Breakdown for billing (optional, can be calculated from room data)
    patients_count = db.Column(db.Integer, nullable=False)
    relatives_count = db.Column(db.Integer, nullable=False)
    
    # Who registered it
    registered_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    registered_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    room = db.relationship('Room', backref='meal_registrations')
    registered_by = db.relationship('User', backref='meal_registrations_created')
    
    # Ensure one registration per room per meal per day
    __table_args__ = (
        db.UniqueConstraint('room_id', 'meal_type', 'date', name='unique_meal_registration'),
    )
    
    def __repr__(self):
        return f'<MealRegistration {self.room.room_number} {self.meal_type.value} {self.date}>'
    
    @property
    def is_breakfast(self):
        return self.meal_type == MealType.BREAKFAST
    
    @property
    def is_paid_meal(self):
        """Check if this meal requires payment for relatives"""
        return self.meal_type in [MealType.LUNCH, MealType.DINNER]
    
    @property
    def billable_count(self):
        """Number of people who should be charged (relatives for lunch/dinner)"""
        if self.is_paid_meal:
            return self.relatives_count
        return 0