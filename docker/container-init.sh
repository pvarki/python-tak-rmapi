#!/bin/bash -l
set -e
# Resolve our magic names to docker internal ip
sed 's/.*localmaeher.*//g' /etc/hosts >/etc/hosts.new && cat /etc/hosts.new >/etc/hosts
echo "$(getent hosts rmnginx | awk '{ print $1 }') localmaeher.pvarki.fi mtls.localmaeher.pvarki.fi" >>/etc/hosts
cat /etc/hosts
if [ -f /data/persistent/firstrun.done ]
then
  echo "First run already cone"
else
  # Do the normal init
  /kw_product_init init /pvarki/kraftwerk-init.json
  date -u +"%Y%m%dT%H%M" >/data/persistent/firstrun.done
fi
