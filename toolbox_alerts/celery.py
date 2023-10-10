from __future__ import absolute_import, unicode_literals

import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'toolbox_alerts.settings')

app = Celery('toolbox_alerts')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

# Specify RabbitMQ as the broker
# app.conf.broker_url = 'pyamqp://guest@localhost//'