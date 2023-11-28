#!/bin/sh
gunicorn -b 0.0.0.0:${SERVICE_PORT} src.main:app -w ${WORKERS_COUNT} -k uvicorn.workers.UvicornWorker --preload
