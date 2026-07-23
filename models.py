from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash


db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(20), nullable=True)
    profile_image = db.Column(db.String(200), nullable=True)
    emergency_contact = db.Column(db.String(100), nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    medicines = db.relationship("Medicine", backref="owner", cascade="all, delete-orphan", lazy=True)
    reminder_logs = db.relationship("ReminderLog", backref="user", cascade="all, delete-orphan", lazy=True)
    notification_history = db.relationship("NotificationHistory", backref="user", cascade="all, delete-orphan", lazy=True)
    settings = db.relationship("UserSettings", backref="user", uselist=False, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"


class Medicine(db.Model):
    __tablename__ = "medicines"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    dosage = db.Column(db.String(50), nullable=False)
    medicine_type = db.Column(db.String(50), nullable=False)
    intake_instruction = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    reminder_time = db.Column(db.String(20), nullable=False)
    frequency = db.Column(db.String(50), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    color_label = db.Column(db.String(20), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)


class ReminderLog(db.Model):
    __tablename__ = "reminder_logs"

    id = db.Column(db.Integer, primary_key=True)
    medicine_name = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    reminder_time = db.Column(db.DateTime, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    medicine_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class NotificationHistory(db.Model):
    __tablename__ = "notification_history"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)


class UserSettings(db.Model):
    __tablename__ = "user_settings"

    id = db.Column(db.Integer, primary_key=True)
    email_reminders = db.Column(db.Boolean, default=True)
    browser_notifications = db.Column(db.Boolean, default=True)
    notification_sound = db.Column(db.Boolean, default=True)
    timezone = db.Column(db.String(80), default="UTC")
    language = db.Column(db.String(20), default="en")
    theme = db.Column(db.String(20), default="light")
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)

    def __repr__(self):
        return f"<UserSettings {self.user_id} theme={self.theme}>"
