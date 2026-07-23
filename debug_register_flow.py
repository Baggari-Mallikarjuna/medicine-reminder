from app import create_app
from models import User, UserSettings

app = create_app()
app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

client = app.test_client()
resp = client.post('/register', data={'username':'debuguser888','email':'debuguser888@example.com','password':'Password123','confirm_password':'Password123'}, follow_redirects=False)
print('status', resp.status_code)
print('location', resp.headers.get('Location'))
print('user_exists', User.query.filter_by(email='debuguser888@example.com').first() is not None)
print('settings_count', UserSettings.query.count())
