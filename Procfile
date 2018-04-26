release: python manage.py migrate
web: waitress-serve --port=$PORT settings.wsgi:application
worker: REMAP_SIGTERM=SIGQUIT celery --app=taskapp worker --concurrency=7 --hostname=$DYNO@%h -Ofair --purge --without-heartbeat --without-gossip --loglevel=debug
scheduler: celery --app=taskapp beat --max-interval=10
pollqueue: python manage.py poll_queue
infobot: python manage.py run_info_bot
