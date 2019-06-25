# Useful Commands
This documents talks useful commands to create docker image, K8s deployments, etc.

## Docker Image
Create the [Dockerfile]() to make Docker image and push it to [Docker Hub](https://cloud.docker.com/repository/docker/gongbaifei/webcam).
```bash
docker build -t gongbaifei/webcam:v1 .
docker push gongbaifei/webcam:v1
```
Test the image by creating a container:
```bash
docker run -d --name webcam-test -p 0.0.0.0:10001:8888 gongbaifei/webcam:v1
docker exec -it webcam-test /bin/bash
```
Other commands:
```bash
# List all docker containers
docker ps -a
# Stop Docker container
docker stop webcam-test
# Remove Docker container
docker rm webcam-test
# List docker images
docker image ls
# Remove docker
docker image rm gongbaifei/webcam:v1
```

## Kubernetes
```bash
# Get cluster info
kubectl cluster-info
# Get node info
kubectl get nodes -o wide
# Create namespace with labels
kubectl create namespace webcam
kubectl label namespace webcam istio-injection=enabled
kubectl label namespace webcam istio-injection-
kubectl get namespace --show-labels
# Create K8s objects, services, etc
kubectl apply -f webcam-single-pod.yaml
# Delete K8s objects, services, etc
kubectl delete -f webcam-single-pod.yaml
kubectl delete pods webcam -n webcam
# Get pod info
kubectl get pods -o wide --all-namespaces
# Get pod details/log
kubectl describe pod webcam -n webcam
kubectl log -f webcam -n webcam
```

## Istio
```bash
# Create yaml with sidecar manually, if auto label injection not enabled
istioctl kube-inject -f webcam-single-pod.yaml | kubectl apply -f -
# Get external IP
kubectl get pod -l istio=ingressgateway -n istio-system -o jsonpath='{.items[0].status.hostIP}'
# Get port number
kubectl -n istio-system get svc istio-ingressgateway -o jsonpath='{.spec.ports[?(@.name=="http2")].nodePort}'
# Create port forwarding for Prometheus/Kiali
kubectl -n istio-system port-forward $(kubectl -n istio-system get pod -l app=kiali -o jsonpath='{.items[0].metadata.name}') 20001:20001 --address 0.0.0.0
kubectl -n istio-system port-forward $(kubectl -n istio-system get pod -l app=prometheus -o jsonpath='{.items[0].metadata.name}') 9090:9090 --address 0.0.0.0
# Get gateway/destination rules/virtual services
kubectl get gateway -o yaml
kubectl get destinationrules -o yaml
kubectl get virtualservices -o yaml
```

## Reading
- Master-Node communication, https://kubernetes.io/docs/concepts/architecture/master-node-communication/
- Under the Hood: An Introduction to Kubernetes Architecture, https://kublr.com/blog/under-the-hood-an-introduction-to-kubernetes-architecture/
- Custom Resources, https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/
- This is how easy it is to create a REST API, https://codeburst.io/this-is-how-easy-it-is-to-create-a-rest-api-8a25122ab1f3
- What's the difference between ClusterIP, NodePort and LoadBalancer service types in Kubernetes? https://stackoverflow.com/questions/41509439/whats-the-difference-between-clusterip-nodeport-and-loadbalancer-service-types
