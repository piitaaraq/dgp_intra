# config.py
import os
from celery.schedules import crontab

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "mysql+pymysql://peter:peter@localhost/lunch_db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Mail configuration
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "True") == "True"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER")
    
    # Celery configuration
    broker_url = 'redis://localhost:6379/0'
    result_backend = 'redis://localhost:6379/0'
    CELERY_BEAT_SCHEDULE = {
        'send-kitchen-email-9am': {
            'task': 'tasks.email_tasks.send_daily_kitchen_email',
            'schedule': crontab(hour=9, minute=0, day_of_week='mon-fri'),
        }
    }
    
    # Vipps MobilePay configuration
    VIPPS_API_BASE_URL = os.environ.get('VIPPS_API_BASE_URL', 'http://localhost:8000')
    VIPPS_CLIENT_ID = os.environ.get('VIPPS_CLIENT_ID', 'mock')
    VIPPS_CLIENT_SECRET = os.environ.get('VIPPS_CLIENT_SECRET', 'mock')
    VIPPS_SUBSCRIPTION_KEY = os.environ.get('VIPPS_SUBSCRIPTION_KEY', 'mock')
    VIPPS_MSN = os.environ.get('VIPPS_MSN', 'mock')
    
    # Klippekort pricing
    KLIPPEKORT_PRICE_PER_CLIP = int(os.environ.get('KLIPPEKORT_PRICE_PER_CLIP', '22'))