#!/bin/bash -l
TR=/opt/tak
CR=${TR}/certs

set -e
# Resolve our magic names to docker internal ip
sed 's/.*localmaeher.*//g' /etc/hosts >/etc/hosts.new && cat /etc/hosts.new >/etc/hosts
echo "$(getent hosts host.docker.internal | awk '{ print $1 }') localmaeher.pvarki.fi mtls.localmaeher.pvarki.fi" >>/etc/hosts
cat /etc/hosts

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

if [ -f /data/persistent/firstrun.done ]
then
  echo "First run already cone"
else
  # Do the normal init
  if [ -f /pvarki/kraftwerk-init.json ]
  then
    /kw_product_init init /pvarki/kraftwerk-init.json
    date -u +"%Y%m%dT%H%M" >/data/persistent/firstrun.done
  fi
fi
