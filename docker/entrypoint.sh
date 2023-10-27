#!/bin/bash -l
. /container-init.sh
TR=/opt/tak
CR=${TR}/certs

if [ "$#" -eq 0 ]; then

  # Symlink the log directory under data dir
  if [[ ! -d "${TR}/data/logs" ]];then
    mkdir -p "${TR}/data/logs"
  fi
  if [[ ! -L "${TR}/logs"  ]];then
    ln -f -s "${TR}/data/logs/" "${TR}/logs"
  fi

  # Seed initial certificate data if necessary
  if [[ ! -d "${TR}/data/certs" ]];then
    mkdir -p "${TR}/data/certs"
  fi
  # Move original certificate data and symlink to certificate data in data dir
  if [[ ! -L "${TR}/certs"  ]];then
    mv ${TR}/certs ${TR}/certs.orig
    ln -f -s "${TR}/data/certs/" "${TR}/certs"
  fi
  exec gunicorn "takrmapi.app:get_app()" --bind 0.0.0.0:8003 --forwarded-allow-ips='*' -w 4 -k uvicorn.workers.UvicornWorker
else
  exec "$@"
fi
