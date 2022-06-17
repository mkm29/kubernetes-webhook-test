#!/bin/bash

MASTER_IP=$(kubectl get node/kind-control-plane -o jsonpath="{.status.addresses[0].address}")
SERVICE_NAME="webhook"
NAMESPACE="webhook"

openssl genrsa -out ca.key 2048
openssl req -x509 -new -nodes -key ca.key -subj "/CN=${MASTER_IP}" -days 10000 -out ca.crt
openssl genrsa -out server.key 2048

cat <<EOF > csr.conf
[ req ]
default_bits = 2048
prompt = no
default_md = sha256
req_extensions = req_ext
distinguished_name = dn

[ dn ]
C = US
ST = FL
L = Tampa
O = RTX
OU = DX
CN = $MASTER_IP

[ req_ext ]
subjectAltName = @alt_names

[ alt_names ]
DNS.1 = $SERVICE_NAME
DNS.2 = $SERVICE_NAME.$NAMESPACE
DNS.3 = $SERVICE_NAME.$NAMESPACE.svc
DNS.4 = $SERVICE_NAME.$NAMESPACE.svc.cluster
DNS.5 = $SERVICE_NAME.$NAMESPACE.svc.cluster.local
IP.1 = $MASTER_IP
IP.2 = 127.0.0.1

[ v3_ext ]
authorityKeyIdentifier=keyid,issuer:always
basicConstraints=CA:FALSE
keyUsage=keyEncipherment,dataEncipherment
extendedKeyUsage=serverAuth,clientAuth
subjectAltName=@alt_names
EOF

openssl req -new -key server.key -out server.csr -config csr.conf

openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key \
  -CAcreateserial -out server.crt -days 10000 \
  -extensions v3_ext -extfile csr.conf
export ca_pem_b64="$(openssl base64 -A <"ca.crt")"
