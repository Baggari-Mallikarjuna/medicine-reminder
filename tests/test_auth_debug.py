import unittest

from app import create_app
from models import User, db


class AuthFlowDebugTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": True, "SECRET_KEY": "test-secret"})
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=True, SECRET_KEY="test-secret")
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.drop_all()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_register_and_login_work_without_csrf_token_in_debug_mode(self):
        register_response = self.client.post(
            "/register",
            data={
                "username": "debuguser",
                "email": "debug@example.com",
                "password": "Password123",
                "confirm_password": "Password123",
            },
            follow_redirects=False,
        )
        self.assertEqual(register_response.status_code, 302)
        self.assertEqual(register_response.headers.get("Location"), "/dashboard")

        user = User.query.filter_by(email="debug@example.com").first()
        self.assertIsNotNone(user)

        login_response = self.client.post(
            "/login",
            data={"email": "debug@example.com", "password": "Password123"},
            follow_redirects=False,
        )
        self.assertEqual(login_response.status_code, 302)
        self.assertEqual(login_response.headers.get("Location"), "/dashboard")


if __name__ == "__main__":
    unittest.main()
