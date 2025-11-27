from flask import Flask
from config import Config
from .extensions import db, login_manager, mail, migrate, init_celery
from .models import User
from dotenv import load_dotenv

def create_app():
    load_dotenv()
    app = Flask(__name__)
    app.config.from_object(Config)

    app.config['broker_url'] = 'redis://localhost:6379/0'
    app.config['result_backend'] = 'redis://localhost:6379/0'
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    mail.init_app(app)
    
    # Always initialize Celery - it's safe to call
    init_celery(app)
    
    # Register blueprints
    from dgp_intra.routes import register_blueprints
    register_blueprints(app)
    
    # Error handler
    @app.errorhandler(403)
    def forbidden(e):
        return "<h1>403 Forbidden</h1><p>You do not have permission to access this resource.</p>", 403
    
    # User loader
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.query(User).get(user_id)
    
    return app