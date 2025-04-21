gunicorn server_pay.asgi:application -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8888 --workers=$(python -c 'import multiprocessing; print(multiprocessing.cpu_count() * 2 + 1)')
