import os
import tempfile
import unittest

from app import create_app
from models import db


class MedicineFlowTests(unittest.TestCase):
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
        import gc
        gc.collect()
        self.tmp_dir.cleanup()

    def test_register_and_create_medicine(self):
        response = self.client.post(
            "/register",
            data={
                "username": "tester",
                "email": "tester@example.com",
                "password": "secret123",
                "confirm_password": "secret123",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            "/medicines/add",
            data={
                "name": "Paracetamol",
                "dosage": "500mg",
                "medicine_type": "Tablet",
                "intake_instruction": "After Food",
                "start_date": "2026-07-17",
                "end_date": "2026-07-30",
                "reminder_time": "08:00",
                "frequency": "Daily",
                "notes": "Take with water",
                "color_label": "Blue",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Paracetamol", response.data)


if __name__ == "__main__":
    unittest.main()
