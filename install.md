# Create Demo Setup
This document talks about how to create the demo setup including network, docker, Kubernetes and Istio.

## Network
There three different types of EdgeLine servers in this demo as shown below.

| Node    | Hostname     | Public IP   | Private IP  | K8s    |
| :-----: |:------------:| :----------:|:-----------:| :-----:|
| GL20    | discover-1   | 10.111.0.96 | 192.168.1.1 | Master |
| EL300   | discover-2   | 10.111.0.97 | 192.168.1.2 | Worker |
| EL1000  | discover-3   | 10.111.0.98 | 192.168.1.3 | Worker |

To connect the three servers and web cameras, we create a VLAN on an [ARUBA 2930F 48G POE+ 4SFP SWITCH (JL262A)](https://www.arubanetworks.com/products/networking/switches/2930f-series/).
Connect the micro USB console port on the switch to a laptop and log in the switch using ```Putty``` as a "Serial" port (find the COMX port using Device Manager -> Ports) to configure VLAN on switch:
```bash
> configure
> vlan 100
> untagged 25-48
```
* Note that you may need to press enter a few times in putty to connect to the switch.

#### Reference
- ArubaOS Switches Let's Build a Network Management VLAN and Cabling - 2, https://youtu.be/czqljzdFukw
- Configuring VLANs, https://www.arubanetworks.com/techdocs/ArubaOS_62_Web_Help/Content/ArubaFrameStyles/Network_Parameters/Configuring_VLANs.htm#network_parameters_2319977163_1016949
- Aruba Basic Operation Guide for ArubaOS-Switch 16.07, http://h22208.www2.hpe.com/eginfolib/Aruba/16.07/5200-5371/index.html#book.html

## Server
We configure the GL20 as K8s master node and EL300 and EL1000 as K8s worker nodes and install different components of K8s on them.
### System
First, we configure the hostnames of the three servers which are used as K8s node name.
Modify ```/etc/hostname``` as:
```bash
127.0.0.1       localhost
192.168.1.1     discover-1
192.168.1.2     discover-2
192.168.1.3     discover-3
```
And run ```sudo hostnamectl set-hostname discover-X``` on each machine.

### Proxy (optional)
If the machines are running inside HPE network, we need to configure proxy.
Add the following to ```/etc/environment```:
```bash
http_proxy=http://web-proxy-pa.labs.hpecorp.net:8088
HTTP_PROXY=http://web-proxy-pa.labs.hpecorp.net:8088
https_proxy=http://web-proxy-pa.labs.hpecorp.net:8088
HTTPS_PROXY=http://web-proxy-pa.labs.hpecorp.net:8088
no_proxy=localhost,127.0.0.1,192.168.0.0/16,10.96.0.0/16,10.244.0.0/16,svc,.cluster.local
NO_PROXY=localhost,127.0.0.1,192.168.0.0/16,10.96.0.0/16,10.244.0.0/16,svc,.cluster.local
```
In case different tools may pickup proxy information from different configuration files, we also need to add the following to ```~/.bashrc``` and ```/root/.bashrc/```:
```
export http_proxy=http://web-proxy-pa.labs.hpecorp.net:8088
export HTTP_PROXY=http://web-proxy-pa.labs.hpecorp.net:8088
export https_proxy=http://web-proxy-pa.labs.hpecorp.net:8088
export HTTPS_PROXY=http://web-proxy-pa.labs.hpecorp.net:8088
export no_proxy=localhost,127.0.0.1,192.168.0.0/16,10.96.0.0/16,10.244.0.0/16,svc,.cluster.local
export NO_PROXY=localhost,127.0.0.1,192.168.0.0/16,10.96.0.0/16,10.244.0.0/16,svc,.cluster.local
```
* Note that ```no_proxy``` has to be set properly and exclude K8s related networks from proxy. Otherwise, you may experience various network problem for K8s and Istio. ```10.96.0.0/16``` is the default service network of K8s and ```10.244.0.0/16``` is the pod network for ```Flannel``` container network interface (CNI).

### Docker
We use Docker as the container runtime for K8s.
By default Docker uses ```cgroupfs``` as the cgroup driver. [However, this may cause problems for K8s](https://kubernetes.io/docs/setup/production-environment/container-runtimes/). Run the following commands to install Docker and configure cgroup driver as ```systemd```.
```bash
sudo apt install -y apt-transport-https ca-certificates curl gnupg-agent software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository \
  "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) \
  stable"
sudo apt update
sudo apt install -y docker-ce=18.06.2~ce~3-0~ubuntu
echo -e '{
  "exec-opts": ["native.cgroupdriver=systemd"],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m"
  },
  "storage-driver": "overlay2"
}' | sudo tee /etc/docker/daemon.json
mkdir -p /etc/systemd/system/docker.service.d
sudo usermod -aG docker ${USER} # add current user to docker user group
sudo systemctl enable docker
sudo systemctl daemon-reload
sudo systemctl restart docker.service
```
To verify, run the following:
```bash
$ docker info | grep Driver
Storage Driver: overlay2
Logging Driver: json-file
Cgroup Driver: systemd
WARNING: No swap limit support
$ docker run hello-world
```

You may also need to setup proxy if running inside HPE network. Add the following to ```/etc/systemd/system/docker.service.d/http-proxy.conf``` and restart docker ```sudo systemctl daemon-reload && sudo systemctl restart docker```:
```bash
[Service]
Environment="HTTP_PROXY=http://web-proxy-pa.labs.hpecorp.net:8088/" "HTTPS_PROXY=http://web-proxy-pa.labs.hpecorp.net:8088/"  "NO_PROXY=localhost,127.0.0.1,192.168.1.0/24,10.96.0.0/16,10.240.0.0/16"
```

### Kubernetes
[Since K8s doesn't work well with swap, we need to turn off swap.](https://github.com/kubernetes/kubernetes/issues/53533) Run ```sudo swapoff -a``` and add it to ```/etc/rc.local``` to disable swap after reboot. To verify swap is disabled:
```bash
$ free -h
              total        used        free      shared  buff/cache   available
Mem:            15G        161M         14G        9.1M        535M         15G
Swap:            0B          0B          0B
```

Then run the following commands to install ```kubeadm```, ```kubectl``` and ```kubelet```.
```bash
curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
echo -e 'deb http://apt.kubernetes.io/ kubernetes-xenial main' | sudo tee --append /etc/apt/sources.list.d/kubernetes.list
sudo apt update
sudo apt install -y kubeadm kubelet kubectl
```
Then we need to configure K8s master node and worker node separately.
#### Master node
Run the following command to initialize the master node and install ```Flannel``` CNI:
```bash
sudo kubeadm init --pod-network-cidr=10.244.0.0/16 --service-cidr=10.96.0.0/16 --apiserver-advertise-address=192.168.1.1 | tee kubeadm_init.log
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
kubectl apply -f https://raw.githubusercontent.com/coreos/flannel/master/Documentation/kube-flannel.yml
```
The output of ```kubeadm init``` is stored in ```kubeadm_init.log``` and make sure there is no error or warning in the output. We will need to use the token and certificate in the output to add K8s worker nodes to this cluster. Here is an example of the output:
```bash
[init] Using Kubernetes version: v1.14.3
[preflight] Running pre-flight checks
[preflight] Pulling images required for setting up a Kubernetes cluster
[preflight] This might take a minute or two, depending on the speed of your internet connection
[preflight] You can also perform this action in beforehand using 'kubeadm config images pull'
[kubelet-start] Writing kubelet environment file with flags to file "/var/lib/kubelet/kubeadm-flags.env"
[kubelet-start] Writing kubelet configuration to file "/var/lib/kubelet/config.yaml"
[kubelet-start] Activating the kubelet service
[certs] Using certificateDir folder "/etc/kubernetes/pki"
[certs] Generating "ca" certificate and key
[certs] Generating "apiserver" certificate and key
[certs] apiserver serving cert is signed for DNS names [k8s-master kubernetes kubernetes.default kubernetes.default.svc kubernetes.default.svc.cluster.local] and IPs [10.96.0.1 192.168.1.1]
[certs] Generating "apiserver-kubelet-client" certificate and key
[certs] Generating "front-proxy-ca" certificate and key
[certs] Generating "front-proxy-client" certificate and key
[certs] Generating "etcd/ca" certificate and key
[certs] Generating "etcd/peer" certificate and key
[certs] etcd/peer serving cert is signed for DNS names [k8s-master localhost] and IPs [192.168.1.1 127.0.0.1 ::1]
[certs] Generating "etcd/healthcheck-client" certificate and key
[certs] Generating "etcd/server" certificate and key
[certs] etcd/server serving cert is signed for DNS names [k8s-master localhost] and IPs [192.168.1.1 127.0.0.1 ::1]
[certs] Generating "apiserver-etcd-client" certificate and key
[certs] Generating "sa" key and public key
[kubeconfig] Using kubeconfig folder "/etc/kubernetes"
[kubeconfig] Writing "admin.conf" kubeconfig file
[kubeconfig] Writing "kubelet.conf" kubeconfig file
[kubeconfig] Writing "controller-manager.conf" kubeconfig file
[kubeconfig] Writing "scheduler.conf" kubeconfig file
[control-plane] Using manifest folder "/etc/kubernetes/manifests"
[control-plane] Creating static Pod manifest for "kube-apiserver"
[control-plane] Creating static Pod manifest for "kube-controller-manager"
[control-plane] Creating static Pod manifest for "kube-scheduler"
[etcd] Creating static Pod manifest for local etcd in "/etc/kubernetes/manifests"
[wait-control-plane] Waiting for the kubelet to boot up the control plane as static Pods from directory "/etc/kubernetes/manifests". This can take up to 4m0s
[apiclient] All control plane components are healthy after 20.007953 seconds
[upload-config] storing the configuration used in ConfigMap "kubeadm-config" in the "kube-system" Namespace
[kubelet] Creating a ConfigMap "kubelet-config-1.14" in namespace kube-system with the configuration for the kubelets in the cluster
[upload-certs] Skipping phase. Please see --experimental-upload-certs
[mark-control-plane] Marking the node k8s-master as control-plane by adding the label "node-role.kubernetes.io/master=''"
[mark-control-plane] Marking the node k8s-master as control-plane by adding the taints [node-role.kubernetes.io/master:NoSchedule]
[bootstrap-token] Using token: y8ksjd.f8jjid8djl6p2upn
[bootstrap-token] Configuring bootstrap tokens, cluster-info ConfigMap, RBAC Roles
[bootstrap-token] configured RBAC rules to allow Node Bootstrap tokens to post CSRs in order for nodes to get long term certificate credentials
[bootstrap-token] configured RBAC rules to allow the csrapprover controller automatically approve CSRs from a Node Bootstrap Token
[bootstrap-token] configured RBAC rules to allow certificate rotation for all node client certificates in the cluster
[bootstrap-token] creating the "cluster-info" ConfigMap in the "kube-public" namespace
[addons] Applied essential addon: CoreDNS
[addons] Applied essential addon: kube-proxy

Your Kubernetes control-plane has initialized successfully!

To start using your cluster, you need to run the following as a regular user:

  mkdir -p $HOME/.kube
  sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
  sudo chown $(id -u):$(id -g) $HOME/.kube/config

You should now deploy a pod network to the cluster.
Run "kubectl apply -f [podnetwork].yaml" with one of the options listed at:
  https://kubernetes.io/docs/concepts/cluster-administration/addons/

Then you can join any number of worker nodes by running the following on each as root:

kubeadm join 192.168.1.1:6443 --token y8ksjd.f8jjid8djl6p2upn \
    --discovery-token-ca-cert-hash sha256:bd85912f36830a77c78cf264c8c858332210645c3929fb029c3c68ac3f1f5ed6
```
* Note that here we use Flannel, but there are (others available)[https://kubernetes.io/docs/concepts/cluster-administration/networking/]. For ```Flannel``` to work correctly, you must pass ```--pod-network-cidr=10.244.0.0/16``` to ```kubeadm init```.
* By default, ```kubeadm init``` use ```10.96.0.0/12``` for ```--service-cidr```. It is better to set this in accordance with ```noproxy``` setting. Otherwise you may running into networking problems between services and pods.

* In case you lost the token for joining a worker, run this ```sudo kubeadm token create --print-join-command``` to retrieve the join command.

Run the following command to make sure all pods are started successfully.
```bash
$ kubectl get pods --all-namespaces
kube-system    coredns-fb8b8dccf-56v59                   1/1     Running     1          13d     10.244.0.4    k8s-master     <none>           <none>
kube-system    coredns-fb8b8dccf-d6s7s                   1/1     Running     1          13d     10.244.0.5    k8s-master     <none>           <none>
kube-system    etcd-k8s-master                           1/1     Running     1          13d     192.168.1.2   k8s-master     <none>           <none>
kube-system    kube-apiserver-k8s-master                 1/1     Running     1          13d     192.168.1.2   k8s-master     <none>           <none>
kube-system    kube-controller-manager-k8s-master        1/1     Running     1          13d     192.168.1.2   k8s-master     <none>           <none>
kube-system    kube-flannel-ds-amd64-79jxz               1/1     Running     1          13d     192.168.1.2   k8s-master     <none>           <none>
kube-system    kube-flannel-ds-amd64-zk2tr               1/1     Running     1          13d     192.168.1.3   k8s-worker-1   <none>           <none>
kube-system    kube-proxy-m62zg                          1/1     Running     1          13d     192.168.1.3   k8s-worker-1   <none>           <none>
kube-system    kube-proxy-xm82r                          1/1     Running     1          13d     192.168.1.2   k8s-master     <none>           <none>
kube-system    kube-scheduler-k8s-master                 1/1     Running     1          13d     192.168.1.2   k8s-master     <none>           <none>

```

### Worker node
Switch worker nodes and run the following to join the cluster:
```bash
sudo kubeadm join 192.168.2.17:6443 --token y8ksjd.f8jjid8djl6p2upn \
    --discovery-token-ca-cert-hash sha256:bd85912f36830a77c78cf264c8c858332210645c3929fb029c3c68ac3f1f5ed6
```
Now, go back to master node and run the following to make sure all worker nodes are online.
```bash
$ kubectl get nodes -o wide
NAME           STATUS   ROLES    AGE   VERSION   INTERNAL-IP   EXTERNAL-IP   OS-IMAGE             KERNEL-VERSION      CONTAINER-RUNTIME
discover-1     Ready    master   13d   v1.14.3   192.168.1.2   <none>        Ubuntu 16.04.6 LTS   4.4.0-142-generic   docker://18.6.2
discover-2     Ready    <none>   13d   v1.14.3   192.168.1.3   <none>        Ubuntu 16.04.6 LTS   4.4.0-142-generic   docker://18.6.2
```

#### Reference
- Installing Kubernetes with deployment tools, https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/install-kubeadm/
- How to Install and Configure Kubernetes and Docker on Ubuntu 18.04 LTS, https://www.howtoforge.com/tutorial/how-to-install-kubernetes-on-ubuntu/
- How To Install Kubernetes Cluster On Ubuntu 16.04, https://www.edureka.co/blog/install-kubernetes-on-ubuntu
- kubeadm 1.9.2 doesn't work over proxy, https://github.com/kubernetes/kubeadm/issues/687
- Installing a pod network add-on, https://kubernetes.io/docs/setup/independent/create-cluster-kubeadm/#pod-network

## Istio
There are two different ways to install Istio: [script](https://istio.io/docs/setup/kubernetes/install/kubernetes/) and [Helm](https://istio.io/docs/setup/kubernetes/install/helm/). Script installs all Istio components including Prometheus and Kiali. With Helm, you can customize what components of Istio to install. Here we use script to install all Istio components.
First download Istio and add the binary to ```PATH```.
```bash
curl -L https://git.io/getLatestIstio | ISTIO_VERSION=1.2.0 sh -
cd istio-1.2.0
export PATH=$PWD/bin:$PATH
```
For persistent modification, add the following to ```~/.profile```.
```bash
PATH="$HOME/istio-1.2.0/bin:$HOME/bin:$HOME/.local/bin:$PATH"
```
Install Istio:
```bash
cd /home/ubuntu/istio-1.2.0
for i in install/kubernetes/helm/istio-init/files/crd*yaml; do kubectl apply -f $i; done
kubectl apply -f install/kubernetes/istio-demo.yaml
```
To verify if Istio is installed, run the following command:
```bash
$ kubectl get crds | grep 'istio.io\|certmanager.k8s.io' | wc -l
23
$ kubectl get pods -n istio-system -o wide
NAME                                      READY   STATUS      RESTARTS   AGE    IP            NODE           NOMINATED NODE   READINESS GATES
grafana-67c69bb567-sdgcl                  1/1     Running     0          14d    10.244.1.13   k8s-worker-1   <none>           <none>
istio-citadel-fc966574d-rhg2f             1/1     Running     0          14d    10.244.1.18   k8s-worker-1   <none>           <none>
istio-cleanup-secrets-1.1.7-dh9mb         0/1     Completed   0          14d    10.244.1.7    k8s-worker-1   <none>           <none>
istio-egressgateway-6b4cd4d9f-v8gmq       1/1     Running     0          14d    10.244.1.9    k8s-worker-1   <none>           <none>
istio-galley-cf776876f-dq959              1/1     Running     0          12d    10.244.3.8    k8s-worker-2   <none>           <none>
istio-grafana-post-install-1.1.7-xqwcc    0/1     Completed   0          14d    10.244.1.6    k8s-worker-1   <none>           <none>
istio-ingressgateway-59cc6ccbcb-mldfh     1/1     Running     0          7d6h   10.244.3.29   k8s-worker-2   <none>           <none>
istio-pilot-7b4dd9b748-nfq4c              2/2     Running     0          7d6h   10.244.3.28   k8s-worker-2   <none>           <none>
istio-policy-5bcc859488-fn49l             2/2     Running     0          7d6h   10.244.3.27   k8s-worker-2   <none>           <none>
istio-security-post-install-1.1.7-czhjk   0/1     Completed   0          14d    10.244.1.8    k8s-worker-1   <none>           <none>
istio-sidecar-injector-c8ddbb99c-jxrnd    1/1     Running     0          14d    10.244.1.21   k8s-worker-1   <none>           <none>
istio-telemetry-7678c9bb4d-wldck          2/2     Running     0          7d6h   10.244.3.26   k8s-worker-2   <none>           <none>
istio-tracing-5d8f57c8ff-665hc            1/1     Running     0          14d    10.244.1.10   k8s-worker-1   <none>           <none>
kiali-d4d886dd7-q6b84                     1/1     Running     0          14d    10.244.1.16   k8s-worker-1   <none>           <none>
prometheus-d8d46c5b5-v8m9l                1/1     Running     0          14d    10.244.1.20   k8s-worker-1   <none>           <none>
```
* The number of CRD for Istio may change for different version of Istio. For instace, in ```v1.1.7```, it is ```53``` or ```58```, while in ```v1.2.0```, it is ```23```.
* If you choose ```Flannel``` as the CNI (like what we do in this document), do make sure you use ```--pod-network-cidr=10.244.0.0/16``` for ```kubeadm init```. Otherwise, Istio pods may fail during creation.

## Remove

### Docker
```bash
sudo apt purge docker docker-ce docker.io docker-engine containerd runc
```

### Kubernetes
```bash
sudo kubeadm reset
sudo su -s /bin/bash -c "iptables -F && iptables -t nat -F && iptables -t mangle -F && iptables -X" root
sudo rm -rf /etc/kubernetes/
```
* Note that you may also need to reboot the server to completely remove the CNI.

### Istio
```bash
cd /home/ubuntu/istio-1.1.7
kubectl delete -f install/kubernetes/istio-demo.yaml
for i in install/kubernetes/helm/istio-init/files/crd*yaml; do kubectl delete -f $i; done
```

## Troubleshoot

