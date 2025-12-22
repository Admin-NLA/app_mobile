from . import db
from sqlalchemy.dialects.postgresql import JSONB
from flask_login import UserMixin

class User(UserMixin,db.Model):
    __tablename__ = "users"

    user_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable = False)
    email = db.Column(db.String(255), unique=True, nullable = False)
    password = db.Column(db.String, nullable = False)

    def get_id(self):
        return (self.user_id)

class Stats(db.Model):
    __tablename__ = "statistics"
    
    stats_id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(50), nullable = False)
    year = db.Column(db.Integer, nullable = False)
    stats = db.Column(JSONB)
    created_at = db.Column(db.DateTime, nullable = False)
    updated_at = db.Column(db.DateTime, nullable = False)

class Event(db.Model):
    __tablename__ = "events"

    event_id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(50), nullable = False)
    year = db.Column(db.Integer, nullable = False)
    start_date = db.Column(db.Date, nullable = False)
    end_date = db.Column(db.Date, nullable = False)

class Scans(db.Model):
    __tablename__ = "scans"

    scan_id = db.Column(db.String(255), primary_key=True)
    attendee_id = db.Column(db.String(10), nullable = False)
    entries = db.Column(JSONB)
    sessions = db.Column(JSONB)
    location = db.Column(db.String(50), nullable = False)
    year = db.Column(db.Integer, nullable = False)