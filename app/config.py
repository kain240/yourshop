import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'change-this-in-production-use-a-random-string'

    # Database — defaults to SQLite (works on PythonAnywhere free tier, no setup needed)
    # For production on PythonAnywhere, DATABASE_URL stays as sqlite:///...
    # If you ever upgrade to MySQL: mysql+pymysql://user:pass@host/db
    _db_url = os.environ.get('DATABASE_URL', '')

    if _db_url.startswith('sqlite'):
        SQLALCHEMY_DATABASE_URI = _db_url
        SQLALCHEMY_ENGINE_OPTIONS = {}  # SQLite doesn't need pool settings
    elif _db_url.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = _db_url.replace('postgres://', 'postgresql://', 1)
        SQLALCHEMY_ENGINE_OPTIONS = {'pool_recycle': 280, 'pool_pre_ping': True}
    elif _db_url.startswith('postgresql://'):
        SQLALCHEMY_DATABASE_URI = _db_url
        SQLALCHEMY_ENGINE_OPTIONS = {'pool_recycle': 280, 'pool_pre_ping': True}
    elif _db_url.startswith('mysql://'):
        import pymysql
        pymysql.install_as_MySQLdb()
        SQLALCHEMY_DATABASE_URI = _db_url.replace('mysql://', 'mysql+pymysql://', 1)
        SQLALCHEMY_ENGINE_OPTIONS = {'pool_recycle': 280, 'pool_pre_ping': True, 'pool_size': 5, 'max_overflow': 2}
    elif _db_url.startswith('mysql+pymysql://'):
        import pymysql
        pymysql.install_as_MySQLdb()
        SQLALCHEMY_DATABASE_URI = _db_url
        SQLALCHEMY_ENGINE_OPTIONS = {'pool_recycle': 280, 'pool_pre_ping': True, 'pool_size': 5, 'max_overflow': 2}
    else:
        # Default: SQLite in project root — works on PythonAnywhere free tier (persistent storage)
        _base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(_base_dir, 'yourshop.db')
        SQLALCHEMY_ENGINE_OPTIONS = {}

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Mail config
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@yourshop.com')

    # Razorpay
    RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', 'rzp_test_placeholder')
    RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', 'placeholder_secret')

    # Twilio WhatsApp
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
    TWILIO_WHATSAPP_FROM = os.environ.get('TWILIO_WHATSAPP_FROM', 'whatsapp:+14155238886')

    # Upload folder
    UPLOAD_FOLDER = os.environ.get(
        'UPLOAD_FOLDER',
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    )

    # Pagination
    ITEMS_PER_PAGE = 25

    # Production hardening
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


def get_config():
    return Config
