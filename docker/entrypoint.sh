#!/bin/bash -l
set -e
SET_TEST_CERTIFICATES="${SET_TEST_CERTIFICATES:-no}"

if [[ "${SET_TEST_CERTIFICATES}" == "yes" ]];then
  cp /app/devel_certs/cfssl/* /opt/tak/data/certs/
fi

if [ "$#" -eq 0 ]; then
  # TODO: Put your actual program start here
  exec gunicorn "takrmapi.app:get_app()" --bind 0.0.0.0:8000 --forwarded-allow-ips='*' -w 4 -k uvicorn.workers.UvicornWorker
else
  exec "$@"
fi
