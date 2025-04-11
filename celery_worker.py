from celery import Celery
from dgp_intra import create_app
from dgp_intra.tasks.email_tasks import send_daily_kitchen_email  # This ensures the task is registered
from celery.schedules import crontab

flask_app = create_app()

def make_celery(app):
    celery = Celery(
        app.import_name,
        broker=app.config['CELERY_BROKER_URL'],
        backend=app.config['CELERY_RESULT_BACKEND'],
    )
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery

celery = make_celery(flask_app)

celery.conf.beat_schedule = {
    'send-kitchen-email-9am': {
        'task': 'dgp_intra.tasks.email_tasks.send_daily_kitchen_email',
        'schedule': crontab(hour=9, minute=0, day_of_week='mon-fri'),
    },
}
