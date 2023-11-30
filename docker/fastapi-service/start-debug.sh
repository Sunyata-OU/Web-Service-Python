#!/bin/sh

pip install debugpy
python -m debugpy --wait-for-client --listen 0.0.0.0:5678  /usr/local/bin/gunicorn -b 0.0.0.0:${SERVICE_PORT} src.main:app -w ${WORKERS_COUNT} -k uvicorn.workers.UvicornWorker --preload --reload
