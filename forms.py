from flask_wtf import FlaskForm
from wtforms import BooleanField, DateField, FileField, IntegerField, PasswordField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, NumberRange
from flask_wtf.file import FileAllowed


class RegisterForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match")],
    )
    submit = SubmitField("Create account")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Remember me")
    submit = SubmitField("Sign in")


class ForgotPasswordForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    submit = SubmitField("Send reset link")


class ResetPasswordForm(FlaskForm):
    password = PasswordField("New Password", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(
        "Confirm New Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match")],
    )
    submit = SubmitField("Reset password")


class MedicineForm(FlaskForm):
    name = StringField("Medicine Name", validators=[DataRequired(), Length(max=120)])
    dosage = StringField("Dosage", validators=[DataRequired(), Length(max=50)])
    medicine_type = SelectField(
        "Medicine Type",
        choices=[
            ("Tablet", "Tablet"),
            ("Capsule", "Capsule"),
            ("Syrup", "Syrup"),
            ("Injection", "Injection"),
            ("Drops", "Drops"),
        ],
        validators=[DataRequired()],
    )
    intake_instruction = SelectField(
        "Before/After Food",
        choices=[("Before Food", "Before Food"), ("After Food", "After Food")],
        validators=[DataRequired()],
    )
    start_date = DateField("Start Date", validators=[DataRequired()])
    end_date = DateField("End Date", validators=[Optional()])
    reminder_time = StringField("Reminder Time", validators=[DataRequired(), Length(max=20)])
    frequency = SelectField(
        "Frequency",
        choices=[("Daily", "Daily"), ("Alternate Days", "Alternate Days"), ("Weekly", "Weekly"), ("Monthly", "Monthly"), ("Custom", "Custom")],
        validators=[DataRequired()],
    )
    notes = TextAreaField("Notes", validators=[Optional()])
    color_label = StringField("Color Label", validators=[Optional(), Length(max=20)])
    submit = SubmitField("Save medicine")


class ProfileForm(FlaskForm):
    full_name = StringField("Full name", validators=[Optional(), Length(max=120)])
    phone = StringField("Phone number", validators=[Optional(), Length(max=20)])
    age = IntegerField("Age", validators=[Optional(), NumberRange(min=0, max=150)])
    gender = SelectField("Gender", choices=[("", "Prefer not to say"), ("Male", "Male"), ("Female", "Female"), ("Other", "Other")])
    emergency_contact = StringField("Emergency contact", validators=[Optional(), Length(max=100)])
    profile_picture = FileField("Profile picture", validators=[FileAllowed(["jpg", "jpeg", "png", "webp"], "Images only")])
    submit = SubmitField("Save profile")


class SettingsForm(FlaskForm):
    email_reminders = BooleanField("Email reminders")
    browser_notifications = BooleanField("Browser notifications")
    notification_sound = BooleanField("Notification sound")
    timezone = StringField("Timezone", validators=[Optional(), Length(max=80)])
    language = StringField("Language", validators=[Optional(), Length(max=20)])
    theme = SelectField("Theme", choices=[("light", "Light"), ("dark", "Dark")])
    submit = SubmitField("Save settings")
