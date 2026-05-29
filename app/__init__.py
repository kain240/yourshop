from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
import os

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()


def create_app():
    app = Flask(__name__)
    app.config.from_object('app.config.Config')

    # Ensure upload folder exists (uses /tmp on ephemeral platforms)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.inventory import inventory_bp
    from app.routes.billing import billing_bp
    from app.routes.customers import customers_bp
    from app.routes.suppliers import suppliers_bp
    from app.routes.reports import reports_bp
    from app.routes.settings import settings_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(inventory_bp, url_prefix='/inventory')
    app.register_blueprint(billing_bp, url_prefix='/billing')
    app.register_blueprint(customers_bp, url_prefix='/customers')
    app.register_blueprint(suppliers_bp, url_prefix='/suppliers')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(settings_bp, url_prefix='/settings')

    # Import models so Flask-Migrate can detect them
    from app.models import user, inventory, billing, supplier, payment, report  # noqa

    # Create tables (safe on first deploy; migrations handle subsequent changes)
    with app.app_context():
        db.create_all()

    return app
