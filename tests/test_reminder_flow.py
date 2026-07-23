import os
import tempfile
import unittest
from datetime import datetime, timedelta

from app import create_app
from models import Medicine, ReminderLog, db


class ReminderFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp_dir.name, "test.db")
        self.app = create_app({
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{self.db_path}",
            "SECRET_KEY": "test-secret",
            "WTF_CSRF_ENABLED": False,
        })
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        self.tmp_dir.cleanup()

    def test_reminder_processing_creates_pending_log(self):
        with self.app.app_context():
            from models import User, UserSettings
            user = User(username="reminder", email="reminder@example.com", full_name="Reminder")
            user.set_password("secret123")
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

        self.client.post("/register", data={
            "username": "tester",
            "email": "tester@example.com",
            "password": "secret123",
            "confirm_password": "secret123",
        }, follow_redirects=True)

        response = self.client.get("/reminders", follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        with self.app.app_context():
            self.assertTrue(ReminderLog.query.filter_by(medicine_name="Insulin").first())


if __name__ == "__main__":
    unittest.main()
