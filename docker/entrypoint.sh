#!/bin/bash -l
set -e
if [ "$#" -eq 0 ]; then
  # TODO: Put your actual program start here
  uvicorn takrmapi.web.application:get_app
  exec true
else
  exec "$@"
fi
