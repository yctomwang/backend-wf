from celery import current_app as current_celery_app
import os

def make_celery(app):
    celery = current_celery_app
    celery.conf.update(
        broker_url=os.environ.get('CELERY_BROKER_URL', 'pyamqp://guest:guest@localhost//'),
        result_backend=os.environ.get('CELERY_RESULT_BACKEND',
                                      'db+postgresql://test_pam:test_pam@127.0.0.1:5432/test_pam')
    )
    return celery