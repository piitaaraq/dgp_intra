import os
import time
from celery import Celery
from dgp_intra import create_app
from celery.schedules import crontab

os.environ['TZ'] = 'Europe/Copenhagen'
time.tzset()

flask_app = create_app()

def make_celery(app):
    celery = Celery(
        app.import_name,
        broker=app.config['broker_url'],
        backend=app.config['result_backend'],
    )
    celery.conf.update(app.config)
    celery.conf.task_default_queue = 'dgp_intra'

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery

print("BROKER:", flask_app.config.get("broker_url"))

celery = make_celery(flask_app)

# Import the function *after* celery is defined to avoid circular imports
from dgp_intra.tasks.email_tasks import send_daily_kitchen_email as send_email_logic

@celery.task(name='dgp_intra.tasks.email_tasks.send_daily_kitchen_email')
def send_daily_kitchen_email():
    return send_email_logic()

celery.conf.timezone = "Europe/Copenhagen"
celery.conf.enable_utc = False

celery.conf.beat_schedule = {
    'send-kitchen-email-9am': {
        'task': 'dgp_intra.tasks.email_tasks.send_daily_kitchen_email',
        'schedule': crontab(hour=9, minute=0, day_of_week='mon-fri'),
    },
}
