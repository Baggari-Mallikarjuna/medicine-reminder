from flask import Flask
from flask_login import LoginManager
from sqlalchemy import inspect, text

from config import Config
from email_service import mail
from models import NotificationHistory, ReminderLog, User, UserSettings, db
from routes import main_bp
from scheduler import init_scheduler

login_manager = LoginManager()


def _ensure_schema(app):
    with app.app_context():
        inspector = inspect(db.engine)
        for model in (User, ReminderLog, NotificationHistory, UserSettings):
            table_name = model.__tablename__
            if table_name not in inspector.get_table_names():
                continue

            existing_columns = {column['name'] for column in inspector.get_columns(table_name)}
            for column in model.__table__.columns:
                if column.name in existing_columns or column.name == "id":
                    continue

                column_type = column.type.compile(dialect=db.engine.dialect)
                statement = f"ALTER TABLE {table_name} ADD COLUMN {column.name} {column_type}"
                with db.engine.begin() as connection:
                    connection.execute(text(statement))
                app.logger.info("Migrated %s table: added %s column", table_name, column.name)


def create_app(config_class=Config):
    app = Flask(__name__)
    if isinstance(config_class, dict):
        app.config.update(config_class)
    else:
        app.config.from_object(config_class)

    if "WTF_CSRF_ENABLED" not in app.config:
        app.config["WTF_CSRF_ENABLED"] = not app.debug

    db.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "main.login"
    login_manager.login_message_category = "info"

    app.register_blueprint(main_bp)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    with app.app_context():
        db.create_all()
        _ensure_schema(app)

    if not app.testing:
        init_scheduler(app)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
