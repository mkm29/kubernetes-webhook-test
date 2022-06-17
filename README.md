# Kubernetes Admission Controller Demo in Python

1. Create Kind cluster: `kind create cluster --image kindest/node:v1.21.0`
2. Create a Kubernetes namespace: `kubectl create namespace webhook`
3. Generate TLS certificate: [guide](tls/create_certs.md)
4. Create a Kubernetes secret: `kubectl create secret tls webhook-tls --cert=tls/server.crt --key=tls/server.key --namespace=webhook` _Note_: this step is detailed in above guide.
5. Create Kubernetes resources: `kubectl apply -f config/deployment.yaml`
6. Create the ValidatingWebhookConfiguration: `kubectl apply -f config/validate.yaml`
7. Create the MutatingWebhookConfiguration: `kubectl apply -f config/mutate.yaml`
8. Test the webhook: `kubectl apply -f config/pod.yaml`
