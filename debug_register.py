from app import create_app
from forms import RegisterForm

app = create_app()
app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

with app.test_request_context('/register', method='POST', data={'username':'debuguser777','email':'debuguser777@example.com','password':'Password123','confirm_password':'Password123'}):
    form = RegisterForm()
    print('validate', form.validate())
    print('errors', form.errors)
    print('data', form.data)
