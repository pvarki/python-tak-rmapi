#!/bin/bash -l
# shellcheck disable=SC1091
. /container-init.sh

mkdir -p /ui_files/tak
if [ -d "/ui_build" ]; then
    echo "Copying UI files from /ui_build → /ui_files/tak ..."
    cp /ui_build/* /ui_files/tak/
else
    echo "No UI found at /ui_build, skipping copy."
fi

if [ "$#" -eq 0 ]; then
  exec gunicorn "takrmapi.app:get_app()" --bind 0.0.0.0:8003 --forwarded-allow-ips='*' -w 4 -k uvicorn.workers.UvicornWorker
else
  exec "$@"
fi
