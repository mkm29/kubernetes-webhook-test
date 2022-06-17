# Generating TLS Certificate

## Get the IP address of the control plane

```shell
MASTER_IP=$(kubectl get node/kind-control-plane -o jsonpath="{.status.addresses[0].address}")
SERVICE_NAME="webhook"
NAMESPACE="webhook"
```

# Get CA from Cluster

First get the container ID for the Kind control plane (in my case it is `97e9064937ef`).

```shell
docker cp 97e9064937ef:/etc/kubernetes/pki/ca.key .
docker cp 97e9064937ef:/etc/kubernetes/pki/ca.crt .
```

## Generate Certificate

1. `openssl genrsa -out server.key 2048`
2. Create config file for generating the CSR

```shell
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
CN = kubernetes

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
```

5. `openssl req -new -key server.key -out server.csr -config csr.conf`
6.

```shell
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key \
  -CAcreateserial -out server.crt -days 10000 \
  -extensions v3_ext -extfile csr.conf
```

7. View CSR: `openssl req -noout -text -in ./server.csr`
8. View certificate: `openssl x509 -noout -text -in ./server.crt`
9. Generate CA Bundle: `ca_pem_b64="$(openssl base64 -A <"ca.crt")"`
10. Inject in manifests: `sed -i -e 's@${CA_BUNDLE}@'"$ca_pem_b64"'@g' ../config/mutate.yaml`
11. Create Kubernetes secret: `kubectl --namespace=webhook create secret tls webhook-certs --cert=server.crt --key=server.key`
