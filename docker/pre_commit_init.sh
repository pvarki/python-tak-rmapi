#!/bin/bash -l
if [ ! -d .git ]
then
  git init
  git checkout -b precommit_init
  git add .
fi
set -e
uv run pre-commit install --install-hooks
uv run pre-commit run --all-files
