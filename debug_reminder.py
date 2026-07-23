import os
import tempfile
from datetime import datetime, timedelta

from app import create_app
from models import Medicine, ReminderLog, User, UserSettings, db
from routes import process_due_reminders


def main():
    tmp_dir = tempfile.mkdtemp()
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{os.path.join(tmp_dir, 'test.db')}",
        "SECRET_KEY": "x",
        "WTF_CSRF_ENABLED": False,
    })
    with app.app_context():
        db.create_all()
        user = User(username="x", email="x@example.com", full_name="x")
        user.set_password("123")
        db.session.add(user)
        db.session.flush()
        db.session.add(UserSettings(user_id=user.id))
        medicine = Medicine(
            name="Insulin",
            dosage="10mg",
            medicine_type="Injection",
            intake_instruction="Before Food",
            start_date=datetime.now().date(),
            end_date=datetime.now().date() + timedelta(days=7),
            reminder_time=datetime.now().strftime("%H:%M"),
            frequency="Daily",
            notes="",
            user_id=user.id,
        )
        db.session.add(medicine)
        db.session.commit()
        print("before", ReminderLog.query.count())
        process_due_reminders(app)
        print("after", ReminderLog.query.count())
        print(ReminderLog.query.all())


if __name__ == "__main__":
    main()
