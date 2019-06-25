# Webcam

Hack Shack challenge created for HPE Discover 2019 at Las Vegas.

## Setup
We have 3 EdgeLine servers (GL20, EL300 and EL1000) running Kubernetes and Istio.

| Node    | Hostname     | Public IP   | Private IP  | K8s    |
| :-----: |:------------:| :----------:|:-----------:| :-----:|
| GL20    | discover-1   | 10.111.0.96 | 192.168.1.1 | Master |
| EL300   | discover-2   | 10.111.0.97 | 192.168.1.2 | Worker |
| EL1000  | discover-3   | 10.111.0.98 | 192.168.1.3 | Worker |

## Launch webcam deployment with one pod
1. Log in discover-1 with username (nsg) and password (nsg-discover).
2. Navigate to /home/nsg/webcam
3. Start one pod deployment with ```kubectl apply -f webcam-single-pod.yaml```.
4. Run ```kubectl get pods -o wide ``` to find which worker node you pod is running on.
5. Run ```kubectl get svc``` to find the PORT of webcam service.
6. On you laptop, use your browser to open takeSelfi.html. 
7. Now you can see you picture and detection results of your face.

## Problem statement
In the section above, you have created a K8s deployment with one pod running on node discover-3. However, if failure happens (e.g., server failure and network failure), you may lose service of the webcam application. We want you to come up with a solution to improve the high availibility of the webcam deployment so that you webcam deployment still functions when part of the server or network fails.

## Hint
1. Try to add redundancy to your deployment. For instance, you can create multiple pods in you deployment and assign them to different worker nodes.
2. Try to control the ingress workload traffic using Istio (already installed) and redirect it properly when failure happens.

## Solution
- ```kubectl apply -f webcam-single-pod.yaml``` - Deploy one pod of ```webcam``` app.
- ```kubectl apply -f webcam-dual-pod.yaml``` - Deploy two replicas of ```webcam``` app and assign them on two different nodes.
- ```kubectl apply -f webcam-istio-pod.yaml``` - Deploy two pods of ```webcam``` app and specify two different worker nodes for each pod.
- ```kubectl apply -f webcam-istio-net.yaml``` - Create Istio services (gateway, destination rules and virtual services) to control the ingress traffic.

## Reading
* What is Kubernetes? https://kubernetes.io/docs/concepts/overview/what-is-kubernetes/
* Understanding Kubernetes Objects, https://kubernetes.io/docs/concepts/overview/working-with-objects/kubernetes-objects/
* Introduction to YAML: Creating a Kubernetes deployment, https://www.mirantis.com/blog/introduction-to-yaml-creating-a-kubernetes-deployment/
* A Crash Course For Running Istio, https://medium.com/namely-labs/a-crash-course-for-running-istio-1c6125930715
* Tutorial: Blue/Green Deployments with Kubernetes and Istio, https://thenewstack.io/tutorial-blue-green-deployments-with-kubernetes-and-istio/
