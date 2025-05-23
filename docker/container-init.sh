#!/bin/bash -l
set -e
# Resolve our magic names to docker internal ip
sed 's/.*localmaeher.*//g' /etc/hosts >/etc/hosts.new && cat /etc/hosts.new >/etc/hosts
echo "$(getent ahostsv4 host.docker.internal | awk '{ print $1 }') localmaeher.dev.pvarki.fi mtls.localmaeher.dev.pvarki.fi" >>/etc/hosts
cat /etc/hosts

# Make sure /opt/tak and the symlinks to /opt/tak/data exist just in case something still
# uses the old wrong paths
TR=/opt/tak
mkdir -p ${TR}
if [[ ! -L "${TR}/certs"  ]];then
  ln -f -s "${TR}/data/certs/" "${TR}/certs"
fi
# Make sure takinit and coreconfig XMLs exist in the default path
if [[ ! -L "${TR}/TAKIgniteConfig.xml"  ]];then
  ln -f -s "${TR}/data/TAKIgniteConfig.xml" "${TR}/TAKIgniteConfig.xml"
fi
if [[ ! -L "${TR}/CoreConfig.xml"  ]];then
  ln -f -s "${TR}/data/CoreConfig.xml" "${TR}/CoreConfig.xml"
fi

if [ -f /data/persistent/firstrun.done ]
then
  echo "First run already done"
else
  # Do the normal init
  if [ -f /pvarki/kraftwerk-init.json ]
  then
    /kw_product_init init /pvarki/kraftwerk-init.json
    date -u +"%Y%m%dT%H%M" >/data/persistent/firstrun.done
  fi
fi
