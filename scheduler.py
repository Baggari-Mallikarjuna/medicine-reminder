from datetime import UTC, datetime

from apscheduler.schedulers.background import BackgroundScheduler
from flask import current_app

from email_service import send_reminder_email
from models import Medicine, ReminderLog, User, db

scheduler = BackgroundScheduler()


def process_due_reminders(app=None):
    if app is not None:
        with app.app_context():
            return _process_due_reminders_internal()

    return _process_due_reminders_internal()


def _process_due_reminders_internal():
    now = datetime.now(UTC)
    medicines = Medicine.query.filter_by(is_active=True).all()

    for medicine in medicines:
        if medicine.start_date > now.date() or (medicine.end_date and medicine.end_date < now.date()):
            continue

        reminder_dt = now
        if medicine.reminder_time:
            try:
                reminder_hour, reminder_minute = map(int, medicine.reminder_time.split(":"))
                reminder_dt = datetime(now.year, now.month, now.day, reminder_hour, reminder_minute, tzinfo=UTC)
            except ValueError:
                reminder_dt = now

        if reminder_dt > now:
            continue

        existing = ReminderLog.query.filter_by(
            user_id=medicine.user_id,
            medicine_id=medicine.id,
            status="pending",
            reminder_time=reminder_dt,
        ).first()

        if not existing:
            log = ReminderLog(
                medicine_name=medicine.name,
                status="pending",
                reminder_time=reminder_dt,
                user_id=medicine.user_id,
                medicine_id=medicine.id,
            )
            db.session.add(log)
            db.session.commit()

            user = User.query.get(medicine.user_id)
            if not user:
                current_app.logger.warning("No user found for reminder user_id=%s", medicine.user_id)
                continue

            if getattr(user, "settings", None) and user.settings.email_reminders:
                send_reminder_email(user, medicine, reminder_dt)

    return True


def init_scheduler(app):
    if scheduler.running:
        return

    scheduler.start()

    @scheduler.scheduled_job("interval", minutes=1, id="reminder_job")
    def reminder_job():
        with app.app_context():
            current_app.logger.info("Reminder scheduler running")
            process_due_reminders()
