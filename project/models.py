from . import db
from sqlalchemy.dialects.postgresql import JSONB
from flask_login import UserMixin
from bcrypt import checkpw, gensalt, hashpw
from datetime import datetime

class User(UserMixin,db.Model):
    __tablename__ = "users"

    user_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable = False)
    email = db.Column(db.String(255), unique=True, nullable = False)
    password = db.Column(db.String, nullable = False)
    user_type = db.Column(db.String(255), nullable = False)
    company = db.Column(db.String(255))

    e_scans = db.relationship('ExhibitorScan', back_populates = 'user', cascade = 'all, delete-orphan')

    def get_id(self):
        return str(self.user_id)

    def set_password(self, raw_password):
        if isinstance(raw_password, str):
            raw_password = raw_password.encode("utf-8")
        salt = gensalt()
        self.password = hashpw(raw_password, salt).decode("utf-8")

    def check_password(self, raw_password):
        if not self.password:
            return False
        if isinstance(raw_password, str):
            raw_password = raw_password.encode("utf-8")
        return checkpw(raw_password, self.password.encode("utf-8"))

class Event(db.Model):
    __tablename__ = "events"

    event_id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(50), nullable=False)
    year = db.Column(db.SmallInteger, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

    e_scans_ev = db.relationship('ExhibitorScan', back_populates = 'event', cascade = 'all, delete-orphan')
    stats_ev = db.relationship('Stats', back_populates = 'event', uselist=False, cascade = 'all, delete-orphan')

class Stats(db.Model):
    __tablename__ = "statistics"
    
    stats_id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.event_id'), unique=True, nullable=False)
    stats = db.Column(JSONB)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    event = db.relationship('Event', back_populates = 'stats_ev')
    
class ExhibitorScan(db.Model):
    __tablename__ = "exhibitors_scans"

    e_scan_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('events.event_id'), nullable=False)
    scanned_a_last_name = db.Column(db.String(255), nullable=False)
    scanned_a_name = db.Column(db.String(255), nullable=False)
    scanned_a_phone = db.Column(db.String(20))
    scanned_a_email = db.Column(db.String(255))
    scanned_a_company = db.Column(db.String(255))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now(), nullable=False, index = True)
    updated_at = db.Column(db.DateTime, default=datetime.now(), nullable=False)
    
    user = db.relationship('User', back_populates = 'e_scans')
    event = db.relationship('Event', back_populates = 'e_scans_ev')

    appointment = db.relationship('Appointment', back_populates = 'exhibitor_scan', uselist=False, cascade = 'all, delete-orphan')

    def to_dict(self):
        return {
            'e_scan_id': self.e_scan_id,
            'scanned_a_last_name': self.scanned_a_last_name,
            'scanned_a_name': self.scanned_a_name,
            'scanned_a_phone': self.scanned_a_phone,
            'scanned_a_email': self.scanned_a_email,
            'scanned_a_company': self.scanned_a_company,
            'notes': self.notes,
            'appointment': self.appointment.to_dict() if self.appointment else None
        }

class Appointment(db.Model):
    __tablename__ = "appointments"

    appointment_id = db.Column(db.Integer, primary_key=True)
    e_scan_id = db.Column(db.Integer, db.ForeignKey('exhibitors_scans.e_scan_id'), unique=True, nullable=False)
    date = db.Column(db.String(20), nullable=False)
    hour = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(255))
    status = db.Column(db.Boolean)
    created_at = db.Column(db.DateTime, default=datetime.now(), nullable=False, index = True)
    updated_at = db.Column(db.DateTime, default=datetime.now(), nullable=False)

    exhibitor_scan = db.relationship('ExhibitorScan', back_populates = 'appointment')

    def to_dict(self):
        return {
            'appointment_id': self.appointment_id,
            'e_scan_id': self.e_scan_id,
            'date': self.date,
            'hour': self.hour,
            'description': self.description,
            'location': self.location,
            'status': self.status
        }