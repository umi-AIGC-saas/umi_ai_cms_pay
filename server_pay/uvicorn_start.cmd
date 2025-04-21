uvicorn server_pay.asgi:application --workers=$(python -c 'import multiprocessing; print(multiprocessing.cpu_count() * 2 + 1)')
--host=0.0.0.0 --port=8888
