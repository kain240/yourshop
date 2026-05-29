import os
import pymysql
pymysql.install_as_MySQLdb()
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'change-this-in-production-use-a-random-string'

    # Database — supports Railway/Render style DATABASE_URL or explicit MYSQL_ vars
    _db_url = os.environ.get('DATABASE_URL', '')

    # Railway gives MYSQL_URL; Render gives DATABASE_URL with postgres:// prefix
    # We normalise everything to mysql+pymysql://
    if _db_url.startswith('postgres://') or _db_url.startswith('postgresql://'):
        # Render free tier only gives Postgres — keep as-is (swap to pg driver if needed)
        SQLALCHEMY_DATABASE_URI = _db_url.replace('postgres://', 'postgresql://', 1)
    elif _db_url.startswith('mysql://'):
        SQLALCHEMY_DATABASE_URI = _db_url.replace('mysql://', 'mysql+pymysql://', 1)
    elif _db_url.startswith('mysql+pymysql://'):
        SQLALCHEMY_DATABASE_URI = _db_url
    else:
        # Build from individual env vars (local dev / Railway MySQL addon)
        SQLALCHEMY_DATABASE_URI = (
            'mysql+pymysql://{user}:{password}@{host}:{port}/{db}'.format(
                user=os.environ.get('MYSQL_USER', 'root'),
                password=os.environ.get('MYSQL_PASSWORD', 'password'),
                host=os.environ.get('MYSQL_HOST', 'localhost'),
                port=os.environ.get('MYSQL_PORT', '3306'),
                db=os.environ.get('MYSQL_DATABASE', 'yourshop'),
            )
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 280,   # < MySQL wait_timeout (300s)
        'pool_pre_ping': True,
        'pool_size': 5,
        'max_overflow': 2,
    }

    # Mail config
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@yourshop.com')

    # Upload folder — use /tmp on platforms with ephemeral filesystems
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
