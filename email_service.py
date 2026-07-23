from flask_mail import Mail, Message

mail = Mail()


def _get_mail_sender():
    from flask import current_app

    return current_app.config.get("MAIL_DEFAULT_SENDER") or current_app.config.get("MAIL_USERNAME") or "noreply@medicinereminder.local"


def send_password_reset_email(user, token):
    from flask import current_app, url_for

    reset_url = url_for("main.reset_password", token=token, _external=True)
    subject = "Medicine Reminder Password Reset"
    body = (
        f"Hello {user.full_name or user.username},\n\n"
        f"You can reset your password by visiting: {reset_url}\n\n"
        "If you did not request this, you can safely ignore this email."
    )

    msg = Message(subject=subject, recipients=[user.email], body=body)
    try:
        mail.send(msg)
        return True
    except Exception:
        current_app.logger.exception("Failed to send password reset email")
        return False


def send_reminder_email(user, medicine, reminder_dt):
    from flask import current_app

    subject = f"Medicine reminder: {medicine.name}"
    body = (
        f"Hello {user.full_name or user.username},\n\n"
        f"This is a reminder to take your medicine '{medicine.name}' ({medicine.dosage}) at {reminder_dt.strftime('%Y-%m-%d %H:%M %Z')}.\n\n"
        f"Instructions: {medicine.intake_instruction}.\n"
        "If you have already taken it, please update your reminder status in the app."
    )

    msg = Message(subject=subject, recipients=[user.email], body=body, sender=_get_mail_sender())
    try:
        mail.send(msg)
        current_app.logger.info("Sent medicine reminder email to %s for medicine %s", user.email, medicine.name)
        return True
    except Exception:
        current_app.logger.exception("Failed to send medicine reminder email to %s", user.email)
        return False


def send_test_email(recipient=None):
    from flask import current_app

    recipient = recipient or current_app.config.get("MAIL_USERNAME") or current_app.config.get("MAIL_DEFAULT_SENDER")
    if not recipient:
        current_app.logger.warning("Skipping test email because no recipient is configured")
        return False

    if not current_app.config.get("MAIL_USERNAME") or not current_app.config.get("MAIL_PASSWORD"):
        current_app.logger.warning("Skipping test email because SMTP credentials are not configured")
        return False

    subject = "Medicine Reminder SMTP test"
    body = "This is a test email from the Medicine Reminder app."
    msg = Message(subject=subject, recipients=[recipient], body=body, sender=_get_mail_sender())
    try:
        mail.send(msg)
        current_app.logger.info("Sent test email to %s", recipient)
        return True
    except Exception:
        current_app.logger.exception("Failed to send test email to %s", recipient)
        return False
