#!/bin/bash -l
set -e
# Resolve our magic names to docker internal ip
GW_IP=$(getent ahostsv4 host.docker.internal | grep RAW | awk '{ print $1 }')
echo "GW_IP=$GW_IP"
grep -v -F -e "localmaeher"  -- /etc/hosts >/etc/hosts.new && cat /etc/hosts.new >/etc/hosts
echo "$GW_IP localmaeher.dev.pvarki.fi mtls.localmaeher.dev.pvarki.fi" >>/etc/hosts
echo "*** BEGIN /etc/hosts ***"
cat /etc/hosts
echo "*** END /etc/hosts ***"

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

# takinit obtains the product identity once; its CSR token is single-use.
# Both containers mount the same persistent credentials volume.
if [ -f /pvarki/kraftwerk-init.json ]; then
  if [ ! -s /data/persistent/public/mtlsclient.pem ] || [ ! -s /data/persistent/private/mtlsclient.key ]; then
    echo "TAK product credentials are missing. Run takinit with the shared /data/persistent volume first." >&2
    exit 1
  fi
  echo "Using product credentials provisioned by takinit"
fi
