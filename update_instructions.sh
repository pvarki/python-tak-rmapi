#!/bin/bash

# Dockerfile takes the generated tak.json and stores it under /opt/templates/tak.json where the
# api serves it.

# https://github.com/hyperifyio/rune

pushd instructions > /dev/null
make build
