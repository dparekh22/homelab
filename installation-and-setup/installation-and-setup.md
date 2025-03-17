# Homelab Installation and Setup

This document outlines the steps I followed to set up my homelab environment, including the installation of Ubuntu Server, OpenSSH, Docker, and Kubernetes (K8s) using `kubeadm`. It also includes troubleshooting steps for common issues encountered during the setup.

---

## **Linux**
For my home server setup, I chose **Ubuntu Server** due to its user-friendly nature and robust community support. I followed the official Ubuntu documentation for installation, which provides a clear and comprehensive guide. You can refer to the official tutorial here:  
[Install Ubuntu Server](https://ubuntu.com/tutorials/install-ubuntu-server#1-overview)

---

## **OpenSSH**
To enable secure remote access to the server from my Mac, I installed **OpenSSH** and implemented security best practices. This included:
- Disabling password-based authentication to reduce the risk of brute-force attacks.
- Configuring SSH key pairs for secure, passwordless login.

For a detailed guide on setting up SSH key-based authentication, refer to:  
[SSH Key Pair Setup](https://www.digitalocean.com/community/tutorials/how-to-configure-ssh-key-based-authentication-on-a-linux-server)

---

## **Docker**
I used **Docker** to manage and run containerized workloads. Following the official Docker installation guide for Ubuntu, I installed the following components:
- **docker-ce**: The Docker Community Edition engine for container runtime and management.
- **docker-ce-cli**: The Docker command-line interface for interacting with the Docker daemon.
- **containerd.io**: The underlying container runtime responsible for managing container lifecycle operations.
- **docker-buildx-plugin**: A tool for building multi-architecture Docker images.
- **docker-compose-plugin**: For defining and running multi-container applications using Docker Compose.

Refer to the official guide for installation:  
[Docker Installation for Ubuntu](https://docs.docker.com/engine/install/ubuntu/)

---

## **Bootstrapping Kubernetes (K8s)**

### **1. Install `kubeadm` Tool**
Before installing `kubeadm`, ensure all prerequisites are met. Refer to the official documentation:  
[Install `kubeadm`](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/install-kubeadm/)

#### **Key Steps:**
1. **Set Docker Cgroup Driver to `systemd`**:
   - Check the current Cgroup driver:
     ```bash
     docker info | grep -i cgroup
     ```
   - Edit `/etc/docker/daemon.json` and add:
     ```json
     {
       "exec-opts": ["native.cgroupdriver=systemd"]
     }

     #restart docker
     sudo systemctl restart docker

     #verify the change
     docker info | grep -i cgroup
     ```

2. **Disable Swap Memory**:
   - Kubernetes requires swap to be disabled. To turn off swap permanently:
     ```bash
     sudo swapoff -a
     sudo sed -i '/swap/d' /etc/fstab
     ```

3. **Install `kubeadm`, `kubelet`, and `kubectl`**:
   - Configure APT Repository: 
     ```bash
     #update the package index and install dependencies:
     sudo apt-get update
     sudo apt-get install -y apt-transport-https ca-certificates curl gpg

     #add the Kubernetes signing key:
     curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.32/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg

     #add the Kubernetes APT repository
     echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.32/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list
     ```

   - Install `kubeadm`, `kubelet`, and `kubectl`:
     ```bash
     sudo apt-get update
     sudo apt-get install -y kubelet kubeadm kubectl
     sudo apt-mark hold kubelet kubeadm kubectl
     ```
   - Enable and start the `kubelet` service:
     ```bash
     sudo systemctl enable --now kubelet
     ```

---

### **2. Create a Cluster with `kubeadm`**
Refer to the official documentation for creating a cluster with `kubeadm`:  
[Creating a Cluster with `kubeadm`](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/create-cluster-kubeadm/)

#### **Key Steps:**
1. **Initialize the Kubernetes Cluster**:
    ```bash
    sudo kubeadm init

    #on successful initialization, you will see a message like:
    Your Kubernetes control-plane has initialized successfully!
    ```
2. **Set Up kubectl:**
   - Configure kubectl to access the cluster:
     ```bash
     mkdir -p $HOME/.kube
     sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
     sudo chown $(id -u):$(id -g) $HOME/.kube/config
     ```
3. **Install a Pod Network:**
   - Install Calico:
     ```bash
     #create Calico K8s resources
     kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.26.1/manifests/calico.yaml

     #verify Calico installation
     kubectl get pods -n kube-system -l k8s-app=calico-node
     kubectl get pods -n kube-system -l k8s-app=calico-kube-controllers
     kubectl get nodes
     ```
4. **Allow Pods on the Control Plane**
   - By default, the control plane node is tainted to prevent pods from being scheduled. To allow pods on the control plane, remove the taint:
   ```bash
   kubectl taint nodes <control-plane-node-name> node-role.kubernetes.io/control-plane:NoSchedule-
   ```

### **3. Cluster Troubleshooting**
1. **Containerd Configuration Error**:
   - During kubeadm init, I encountered the following error:
     ```bash
     Some fatal errors occurred: failed to create new CRI runtime service: validate service connection: validate CRI v1 runtime API for endpoint "unix:///var/run/containerd/containerd.sock": rpc error: code = Unimplemented desc = unknown service runtime.v1.RuntimeService
     ```
   - Fix:
     Edit the containerd configuration file:
     ```bash
     sudo vi /etc/containerd/config.toml 

     #comment out the line below
     disabled_plugins = ["cri"]

     #restart continerd
     sudo systemctl restart containerd.service
     ```

2. **Control Plane Component Crashes**:
   - After completing kubeadm init, I experienced persistent crashes of control plane components. Upon investigation:
        - The kubelet logs indicated issues with the etcd pod receiving shutdown signals.
        - The root cause was related to the containerd configuration.

   - Fix:
        - I resolved the issue by following the steps outlined in this GitHub issue: [etcd Issue #13670](https://github.com/etcd-io/etcd/issues/13670)

## Conclusion
This setup provides a robust foundation for running containerized workloads and managing them at scale using Kubernetes. If you encounter issues, refer to the troubleshooting section or the official documentation for guidance.
