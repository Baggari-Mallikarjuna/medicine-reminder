from datetime import UTC, datetime, timedelta
import io
import csv
import os

from werkzeug.utils import secure_filename
from flask import send_file, Response

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from itsdangerous import URLSafeTimedSerializer

from email_service import send_password_reset_email, send_test_email
from forms import ForgotPasswordForm, LoginForm, MedicineForm, RegisterForm, ResetPasswordForm
from forms import ProfileForm, SettingsForm
from models import Medicine, ReminderLog, User, UserSettings, db
from scheduler import process_due_reminders
import uuid

main_bp = Blueprint("main", __name__)


def _get_serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


@main_bp.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("main.login"))


@main_bp.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter((User.username == form.username.data) | (User.email == form.email.data)).first():
            flash("A user with that username or email already exists.", "danger")
            return redirect(url_for("main.register"))

        username = form.username.data.strip()
        email = form.email.data.strip().lower()
        user = User(username=username, email=email, full_name=username)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()

        settings = UserSettings(user_id=user.id)
        db.session.add(settings)
        db.session.commit()

        login_user(user)
        flash("Welcome! Your account has been created.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("register.html", form=form)


@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            flash("You are now logged in.", "success")
            return redirect(url_for("main.dashboard"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html", form=form)


@main_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.login"))


@main_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = _get_serializer().dumps(user.email, salt="password-reset")
            send_password_reset_email(user, token)
        flash("If an account exists for that email, a reset link has been sent.", "info")
        return redirect(url_for("main.login"))
    return render_template("forgot_password.html", form=form)


@main_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    form = ResetPasswordForm()
    try:
        email = _get_serializer().loads(token, salt="password-reset", max_age=3600)
    except Exception:
        flash("The password reset link is invalid or has expired.", "danger")
        return redirect(url_for("main.forgot_password"))

    user = User.query.filter_by(email=email).first_or_404()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash("Your password has been updated.", "success")
        return redirect(url_for("main.login"))

    return render_template("reset_password.html", form=form)




@main_bp.route("/debug/send-test-email")
def debug_send_test_email():
    if not (current_app.debug or current_app.testing):
        return redirect(url_for("main.login"))

    recipient = request.args.get("to") or current_app.config.get("MAIL_USERNAME") or current_app.config.get("MAIL_DEFAULT_SENDER")
    if send_test_email(recipient):
        flash("Test email sent successfully.", "success")
    else:
        flash("Test email could not be sent. Check the SMTP settings in the environment.", "warning")
    return redirect(url_for("main.settings"))


@main_bp.route("/dashboard")
@login_required
def dashboard():
    medicines = Medicine.query.filter_by(user_id=current_user.id, is_active=True).all()
    today = datetime.now(UTC).date()
    upcoming = []
    for medicine in medicines:
        if medicine.start_date <= today and (medicine.end_date is None or medicine.end_date >= today):
            upcoming.append(medicine)

    reminder_logs = ReminderLog.query.filter_by(user_id=current_user.id).order_by(ReminderLog.id.desc()).limit(5).all()
    taken_count = ReminderLog.query.filter_by(user_id=current_user.id, status="taken").count()
    missed_count = ReminderLog.query.filter_by(user_id=current_user.id, status="skipped").count()
    today_pending = ReminderLog.query.filter(ReminderLog.user_id == current_user.id, ReminderLog.reminder_time >= datetime.combine(today, datetime.min.time(), tzinfo=UTC), ReminderLog.reminder_time <= datetime.combine(today, datetime.max.time(), tzinfo=UTC), ReminderLog.status == "pending").count()

    return render_template(
        "dashboard.html",
        medicines=medicines,
        upcoming=upcoming[:5],
        total_medicines=len(medicines),
        reminder_logs=reminder_logs,
        taken_count=taken_count,
        missed_count=missed_count,
        today_pending=today_pending,
        today=today,
    )


@main_bp.route("/medicines")
@login_required
def medicines():
    search = request.args.get("search", "", type=str)
    filter_type = request.args.get("filter_type", "", type=str)
    query = Medicine.query.filter_by(user_id=current_user.id, is_active=True)

    if search:
        query = query.filter(Medicine.name.ilike(f"%{search}%"))
    if filter_type:
        query = query.filter(Medicine.medicine_type == filter_type)

    medicines_list = query.order_by(Medicine.created_at.desc()).all()
    return render_template("medicines.html", medicines=medicines_list, search=search, filter_type=filter_type)


@main_bp.route("/medicines/add", methods=["GET", "POST"])
@login_required
def add_medicine():
    form = MedicineForm()
    if form.validate_on_submit():
        medicine = Medicine(
            name=form.name.data,
            dosage=form.dosage.data,
            medicine_type=form.medicine_type.data,
            intake_instruction=form.intake_instruction.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            reminder_time=form.reminder_time.data,
            frequency=form.frequency.data,
            notes=form.notes.data,
            color_label=form.color_label.data,
            user_id=current_user.id,
        )
        db.session.add(medicine)
        db.session.commit()
        flash("Medicine added successfully.", "success")
        return redirect(url_for("main.medicines"))
    return render_template("add_medicine.html", form=form)


@main_bp.route("/medicines/edit/<int:medicine_id>", methods=["GET", "POST"])
@login_required
def edit_medicine(medicine_id):
    medicine = Medicine.query.filter_by(id=medicine_id, user_id=current_user.id).first_or_404()
    form = MedicineForm(obj=medicine)
    if form.validate_on_submit():
        medicine.name = form.name.data
        medicine.dosage = form.dosage.data
        medicine.medicine_type = form.medicine_type.data
        medicine.intake_instruction = form.intake_instruction.data
        medicine.start_date = form.start_date.data
        medicine.end_date = form.end_date.data
        medicine.reminder_time = form.reminder_time.data
        medicine.frequency = form.frequency.data
        medicine.notes = form.notes.data
        medicine.color_label = form.color_label.data
        db.session.commit()
        flash("Medicine updated successfully.", "success")
        return redirect(url_for("main.medicines"))
    return render_template("edit_medicine.html", form=form, medicine=medicine)


@main_bp.route("/medicines/delete/<int:medicine_id>", methods=["POST"])
@login_required
def delete_medicine(medicine_id):
    medicine = Medicine.query.filter_by(id=medicine_id, user_id=current_user.id).first_or_404()
    medicine.is_active = False
    db.session.commit()
    flash("Medicine deleted successfully.", "info")
    return redirect(url_for("main.medicines"))


@main_bp.route("/reminders")
@login_required
def reminders():
    process_due_reminders(current_app)
    reminder_logs = ReminderLog.query.filter_by(user_id=current_user.id).order_by(ReminderLog.reminder_time.desc()).all()
    return render_template("reminders.html", reminders=reminder_logs)


@main_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.full_name = form.full_name.data
        current_user.phone = form.phone.data
        current_user.age = form.age.data
        current_user.gender = form.gender.data
        current_user.emergency_contact = form.emergency_contact.data

        file = form.profile_picture.data
        if file:
            filename = file.filename or ''
            ext = os.path.splitext(filename)[1].lower()
            allowed_ext = {'.jpg', '.jpeg', '.png', '.webp'}

            # check extension
            if ext not in allowed_ext:
                flash('Invalid image type. Allowed: JPG, JPEG, PNG, WebP.', 'danger')
                return redirect(url_for('main.profile'))

            # check size (file may be a FileStorage with stream)
            file.stream.seek(0, os.SEEK_END)
            size = file.stream.tell()
            file.stream.seek(0)
            max_size = current_app.config.get('MAX_CONTENT_LENGTH', 2 * 1024 * 1024)
            if size > max_size:
                flash('Image too large. Max size is 2 MB.', 'danger')
                return redirect(url_for('main.profile'))

            upload_folder = current_app.config.get('UPLOAD_FOLDER')
            os.makedirs(upload_folder, exist_ok=True)

            # remove previous image
            if current_user.profile_image:
                try:
                    prev = os.path.join(upload_folder, current_user.profile_image)
                    if os.path.exists(prev):
                        os.remove(prev)
                except Exception:
                    pass

            # create secure unique filename
            unique_name = f"{uuid.uuid4().hex}{ext}"
            secure_name = secure_filename(unique_name)
            save_path = os.path.join(upload_folder, secure_name)
            file.save(save_path)
            current_user.profile_image = secure_name

        db.session.commit()
        flash('Profile updated.', 'success')
        return redirect(url_for('main.profile'))

    return render_template('profile.html', form=form, user=current_user)


@main_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    settings = UserSettings.query.filter_by(user_id=current_user.id).first()
    form = SettingsForm(obj=settings)
    if form.validate_on_submit():
        settings.email_reminders = form.email_reminders.data
        settings.browser_notifications = form.browser_notifications.data
        settings.notification_sound = form.notification_sound.data
        settings.timezone = form.timezone.data or settings.timezone
        settings.language = form.language.data or settings.language
        settings.theme = form.theme.data
        db.session.commit()
        flash('Settings updated.', 'success')
        return redirect(url_for('main.settings'))

    return render_template('settings.html', form=form)


@main_bp.route('/settings/export_csv')
@login_required
def export_csv():
    medicines = Medicine.query.filter_by(user_id=current_user.id).all()
    si = io.StringIO()
    writer = csv.writer(si)
    writer.writerow(['name', 'dosage', 'type', 'start_date', 'end_date', 'reminder_time', 'frequency', 'notes'])
    for m in medicines:
        writer.writerow([m.name, m.dosage, m.medicine_type, m.start_date, m.end_date, m.reminder_time, m.frequency, m.notes])
    output = si.getvalue().encode('utf-8')
    return Response(output, mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=medicines.csv"})


@main_bp.route('/settings/backup_db')
@login_required
def backup_db():
    uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if uri.startswith('sqlite:///'):
        path = uri.replace('sqlite:///', '')
        if os.path.exists(path):
            return send_file(path, as_attachment=True)
    flash('Backup not available.', 'warning')
    return redirect(url_for('main.settings'))


@main_bp.route('/settings/toggle_theme', methods=['POST'])
@login_required
def toggle_theme():
    settings = UserSettings.query.filter_by(user_id=current_user.id).first()
    if not settings:
        settings = UserSettings(user_id=current_user.id)
        db.session.add(settings)
    settings.theme = 'dark' if (settings.theme or 'light') == 'light' else 'light'
    db.session.commit()
    return redirect(request.referrer or url_for('main.dashboard'))


@main_bp.route('/profile/delete_image', methods=['POST'])
@login_required
def delete_profile_image():
    if not current_user.profile_image:
        flash('No profile image to delete.', 'info')
        return redirect(url_for('main.profile'))

    upload_folder = current_app.config.get('UPLOAD_FOLDER')
    try:
        path = os.path.join(upload_folder, current_user.profile_image)
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        flash('Unable to delete image on server.', 'warning')
        return redirect(url_for('main.profile'))

    current_user.profile_image = None
    db.session.commit()
    flash('Profile image deleted.', 'success')
    return redirect(url_for('main.profile'))


@main_bp.route("/reminders/<int:reminder_id>/taken", methods=["POST"])
@login_required
def mark_taken(reminder_id):
    reminder = ReminderLog.query.filter_by(id=reminder_id, user_id=current_user.id).first_or_404()
    reminder.status = "taken"
    db.session.commit()
    flash("Reminder marked as taken.", "success")
    return redirect(url_for("main.reminders"))


@main_bp.route("/reminders/<int:reminder_id>/skip", methods=["POST"])
@login_required
def skip_reminder(reminder_id):
    reminder = ReminderLog.query.filter_by(id=reminder_id, user_id=current_user.id).first_or_404()
    reminder.status = "skipped"
    db.session.commit()
    flash("Reminder skipped.", "info")
    return redirect(url_for("main.reminders"))


@main_bp.route("/calendar")
@login_required
def calendar():
    # prepare events for the month (reminder logs and medicines)
    from calendar import monthrange

    today = datetime.now(UTC).date()
    first_day = today.replace(day=1)
    last_day = today.replace(day=monthrange(today.year, today.month)[1])

    events = []
    # include medicines as daily events
    medicines = Medicine.query.filter_by(user_id=current_user.id, is_active=True).all()
    for m in medicines:
        # if within range
        if m.start_date <= last_day and (m.end_date is None or m.end_date >= first_day):
            # create an event for display (FullCalendar expects ISO datetime)
            events.append({
                "title": f"{m.name} ({m.dosage})",
                "start": m.start_date.isoformat(),
                "allDay": True,
            })

    # include reminder logs as timed events
    logs = ReminderLog.query.filter_by(user_id=current_user.id).all()
    for log in logs:
        try:
            start_iso = log.reminder_time.isoformat()
        except Exception:
            start_iso = None
        events.append({
            "title": f"Reminder: {log.medicine_name}",
            "start": start_iso,
            "status": log.status,
        })

    return render_template("calendar.html", events=events)


@main_bp.route("/reports")
@login_required
def reports():
    # aggregate reminder logs for charts
    from collections import defaultdict

    now = datetime.now(UTC)
    # last 7 days
    days = 7
    day_counts = defaultdict(lambda: {"taken": 0, "skipped": 0, "pending": 0})
    start_date = (now.date() - timedelta(days=days - 1))
    logs = (
        ReminderLog.query.filter(
            ReminderLog.user_id == current_user.id,
            ReminderLog.reminder_time >= datetime(start_date.year, start_date.month, start_date.day, tzinfo=UTC),
        )
        .all()
    )

    for log in logs:
        d = log.reminder_time.date().isoformat()
        if log.status == "taken":
            day_counts[d]["taken"] += 1
        elif log.status == "skipped":
            day_counts[d]["skipped"] += 1
        else:
            day_counts[d]["pending"] += 1

    labels = []
    taken_data = []
    skipped_data = []
    pending_data = []
    for i in range(days):
        day = (start_date + timedelta(days=i)).isoformat()
        labels.append(day)
        taken_data.append(day_counts[day]["taken"])
        skipped_data.append(day_counts[day]["skipped"])
        pending_data.append(day_counts[day]["pending"])

    # pie summary
    total_taken = sum(taken_data)
    total_skipped = sum(skipped_data)
    total_pending = sum(pending_data)

    return render_template(
        "reports.html",
        labels=labels,
        taken_data=taken_data,
        skipped_data=skipped_data,
        pending_data=pending_data,
        total_taken=total_taken,
        total_skipped=total_skipped,
        total_pending=total_pending,
    )
