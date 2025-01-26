#!/bin/bash -l
# shellcheck disable=SC1091
. /container-init.sh

if [ "$#" -eq 0 ]; then
  exec gunicorn "takrmapi.app:get_app()" --bind 0.0.0.0:8003 --forwarded-allow-ips='*' -w 4 -k uvicorn.workers.UvicornWorker
else
  exec "$@"
fi
