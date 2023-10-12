#!/bin/bash -l
set -e
set -x
SET_TEST_CERTIFICATES="${SET_TEST_CERTIFICATES:-no}"
SETUP_CERTS_USING_MANIFEST="${SETUP_CERTS_USING_MANIFEST:-no}"
RM_API_MANIFEST_FILE="${RM_API_MANIFEST_FILE:=/pvarkishares/tak/kraftwerk-init.json}"


if [[ "${SET_TEST_CERTIFICATES}" == "yes" ]];then
  cp /app/devel_certs/cfssl/* /opt/tak/data/certs/
fi

if [[ "${SETUP_CERTS_USING_MANIFEST}" == "yes" ]];then
  # Get the endpoint from manifest, wait until the manifest is manifested
  set +e
  MAX_ATTEMPTS=240
  for i in $(seq 1 $MAX_ATTEMPTS);
  do
    echo "Waiting for manifest file ${RM_API_MANIFEST_FILE}  ${i}/${MAX_ATTEMPTS}"
    if [[ -f "${RM_API_MANIFEST_FILE}" ]]; then
      echo "Manifest file found ${RM_API_MANIFEST_FILE}"
      break
    fi
    sleep 10
  done
  set -e

  # Get the needed variables from manfiest
  RM_API_HOST=$(cat "${RM_API_MANIFEST_FILE}" | jq -r .rasenmaeher.init.base_uri)
  RM_MTLS_API_HOST=$(cat "${RM_API_MANIFEST_FILE}" | jq -r .rasenmaeher.mtls.base_uri)
  RM_PRODUCT_DNS=$(cat "${RM_API_MANIFEST_FILE}" | jq -r .product.dns)
  # Poll the endpoint until healthcheck starts to give 200
  set +e
  MAX_ATTEMPTS=240
  HEALTHCHECK_OK="no"
  for i in $(seq 1 $MAX_ATTEMPTS);
  do
    # curl -k https://localmaeher.pvarki.fi:4439/api/v1/healthcheck
    RESPONSE_CODE=$(curl -k -XGET -s -o /dev/null -I -w "%{http_code}" "http://rmapi:8000/api/v1/healthcheck")
    if [[ "$RESPONSE_CODE" == "200" ]]; then
      echo "http://rmapi:8000/ healthcheck success. Moving on..."
      HEALTHCHECK_OK="ok"
      break
    fi
    echo "Waiting http://rmapi:8000/api/v1/healthcheck to respond with 200 ... ${i}/${MAX_ATTEMPTS}"
    sleep 10
  done


  # Get the initial certificates
  /kw_product_init init "${RM_API_MANIFEST_FILE}"

  # Test that the certficates work
  #RESPONSE_CODE=$(curl -k --cert /data/persistent/public/mtlsclient.pem --key /data/persistent/private/mtlsclient.key -XGET -s -o /dev/null -I -w "%{http_code}" "${RM_MTLS_API_HOST}api/v1/healthcheck")
  #if [[ "$RESPONSE_CODE" != "200" ]]; then
  #  echo "ERROR! Non 200 response code from mtls healhcheck endpoint!!! '${RM_MTLS_API_HOST}api/v1/healthcheck'"
  #fi



  # PURKKA, REMOVE WHEN mtlsclient.pem has admin permissions
  if [[ ! -f "/data/persistent/public/tak-server.pem" ]]; then
    TMP_JWT_EXCHANGE_CODE="$(cat /pvarkishares/tak/tmp_jwt_exchange_code.code)"
    JWT_TOKEN=$(curl -s -k -XPOST -H 'Content-Type: application/json' "${RM_API_HOST}api/v1/token/code/exchange" -d "{\"code\":\"${TMP_JWT_EXCHANGE_CODE}\"}" | jq -r .jwt)
    TMP_ADMIN_CODE=$(curl -s -k -H 'Content-Type: application/json' -H "Authorization: Bearer ${JWT_TOKEN}" -XPOST "${RM_API_HOST}api/v1/firstuser/add-admin" -d '{"callsign": "tak-superjyra666"}' | jq -r .jwt_exchange_code )
    ADMIN_JWT_TOKEN=$(curl -s -k -XPOST -H 'Content-Type: application/json' "${RM_API_HOST}api/v1/token/code/exchange" -d "{\"code\":\"${TMP_ADMIN_CODE}\"}" | jq -r .jwt)
    curl -k -XGET -H "Authorization: Bearer ${ADMIN_JWT_TOKEN}" "${RM_API_HOST}api/v1/enduserpfx/tak-superjyra666.pfx"  -o /data/persistent/private/tak-superjyra666.pfx
    sleep 1
    openssl pkcs12 -in /data/persistent/private/tak-superjyra666.pfx -nocerts -out /data/persistent/private/tak-superjyra666-key.pem -passin pass:tak-superjyra666 -passout pass:tak-superjyra666
    openssl pkcs12 -in /data/persistent/private/tak-superjyra666.pfx -clcerts -nokeys -out /data/persistent/public/tak-superjyra666.pem -passin pass:tak-superjyra666
    openssl rsa -passin pass:tak-superjyra666 -in /data/persistent/private/tak-superjyra666-key.pem -out /data/persistent/private/tak-superjyra666-openkey.pem


    CERT_RESP=$(curl -d "{\"bundle\":true, \"profile\":\"server\", \"request\": { \"key\": {\"algo\":\"rsa\",\"size\":4096}, \"hosts\":[\"${RM_PRODUCT_DNS}\"], \"names\":[{\"C\":\"FI\", \"ST\":\"Joku\", \"L\":\"Kaupunki\", \"O\":\"${RM_PRODUCT_DNS}\"}], \"CN\": \"${RM_PRODUCT_DNS}\"} }" \
    http://cfssl:8888/api/v1/cfssl/newcert )

    echo $CERT_RESP | jq -r .result.certificate >> /data/persistent/public/tak-server.pem
    echo $CERT_RESP | jq -r .result.bundle.bundle >> /data/persistent/public/tak-server-bundle.pem
    echo $CERT_RESP | jq -r .result.private_key >> /data/persistent/private/tak-server-key.pem
    echo $CERT_RESP | jq -r .result.bundle.root >> /data/persistent/public/tak-server-root.pem

  fi

  # Copy certificates and keys to TAK destination
  if [[ ! -f "/opt/tak/data/certs/files/tak-server.pem" ]]; then
    mkdir -p /opt/tak/data/certs/files
    cp /data/persistent/public/* /opt/tak/data/certs/files/
    cp /data/persistent/private/* /opt/tak/data/certs/files/
    cp /ca_public/* /opt/tak/data/certs/files/
  fi

fi



if [ "$#" -eq 0 ]; then
  # TODO: Put your actual program start here
  exec gunicorn "takrmapi.app:get_app()" --bind 0.0.0.0:8000 --forwarded-allow-ips='*' -w 4 -k uvicorn.workers.UvicornWorker
else
  exec "$@"
fi
