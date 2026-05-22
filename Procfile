web: gunicorn check_in_backend.wsgi --workers 3 --bind 0.0.0.0:$PORT
worker: celery -A check_in_backend worker -l INFO
beat: celery -A check_in_backend beat -l INFO
