#!/bin/sh

# Start Celery
celery -A toolbox-alerts worker --loglevel=info &

# Start Flower
flower -A toolbox-alerts --port=5555 &

# Start the Django server
exec python manage.py runserver 0.0.0.0:8009


