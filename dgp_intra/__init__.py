from flask import Flask
from dotenv import load_dotenv
import os
from config import Config
from .extensions import db, login_manager, mail, celery
from .routes import auth_bp, user_bp, admin_bp
from .models import User


def create_app():
    load_dotenv()

    app = Flask(__name__)
    app.config.from_object(Config)

    # Set Celery config keys
    app.config['broker_url'] = os.environ.get('CELERY_BROKER_URL')
    app.config['result_backend'] = os.environ.get('CELERY_RESULT_BACKEND')

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    mail.init_app(app)
    celery.conf.update(app.config)

    # Wrap Celery tasks with app context
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    celery.Task = ContextTask

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)

    # Error handler
    @app.errorhandler(403)
    def forbidden(e):
        return "<h1>403 Forbidden</h1><p>You do not have permission to access this resource.</p>", 403

    # User loader
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.query(User).get(user_id)

    return app

create_app = create_app

