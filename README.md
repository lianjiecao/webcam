# Webcam

Webcam application created for HPE Discover 2019 Las Vegas

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
