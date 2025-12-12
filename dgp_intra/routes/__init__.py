# dgp_intra/routes/__init__.py

def register_blueprints(app):
    from .public import bp as public_bp
    from .auth import bp as auth_bp
    from .dashboard import bp as dashboard_bp
    from .lunch import bp as lunch_bp
    from .breakfast import bp as breakfast_bp
    from .credit import bp as credit_bp
    from .profile import bp as profile_bp
    from .vacations import bp as vacations_bp
    from .events import bp as events_bp
    from .admin import bp as admin_bp
    from .rooms import bp as rooms_bp
    from dgp_intra.routes import klippekort

    app.register_blueprint(public_bp)     # no prefix -> keeps "/"
    app.register_blueprint(auth_bp)       # no prefix -> keeps "/login"
    app.register_blueprint(dashboard_bp)  # no prefix (route is "/dashboard")
    app.register_blueprint(lunch_bp)
    app.register_blueprint(breakfast_bp)
    app.register_blueprint(credit_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(vacations_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(klippekort.bp)
    app.register_blueprint(rooms_bp)
