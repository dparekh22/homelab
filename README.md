# Homelab

## Goal 
My goal for this project is to create a cost-effective, self-learning lab where I can dive deeper into the tools and technologies I’m passionate about. I believe that having a personal lab for hands-on experimentation and practice is invaluable for building expertise and confidence.

To achieve this, I plan to set up a single control plane Kubernetes (K8s) environment. This will serve as a platform for me to continue honing my DevOps practices, exploring container orchestration, and experimenting with automation, CI/CD pipelines, and other cloud-native technologies.

## Cloud Lab Vs Home Lab?

In this section, I aim to delve into the workflow of designing a solution that best fits my needs while simulating real-world business or customer requirements. My goal is to create a cost-effective environment that balances functionality, scalability, and affordability. To make an informed decision, I conducted a detailed cost-benefit analysis comparing a home lab setup with a cloud-based solution on AWS. This analysis considered factors such as:

- Hardware Costs: Servers, networking equipment, storage devices, and other physical infrastructure.
- Software Costs: Licensing, subscriptions, and open-source tools.
- Operational Costs: Power consumption, cooling, maintenance, and potential downtime.

By evaluating these factors, I aim to determine the most efficient and scalable approach for my learning and experimentation needs.

### At-Home DevOps Lab

**Hardware Costs:**
- Compute: $108.66 (one-time cost) HP EliteDesk 800 G2 Desktop Mini Business PC, Intel Quad-Core i5-6500T up to 3.1G,16G DDR4,240G SSD
- Networking: $0 (using an existing router)
- Storage: $0 (no external storage needed)

**Software Costs:** 
- $0 (using open-source tools)

**Operational Costs:**
- Internet:
  - $0 Sunk cost as I am already paying for it at home
- Electricity Consumption: $3.53/month
  - Average cost of electricity in my hometown: 12-14c per kWh
  - Daily Energy Consumption=Power (kW)×Hours Used Per Day
    - 035kW×24hours=0.84kWh/day
  - Monthly Energy Consumption=Daily Consumption×30days
    - 0.84kWh/day×30days=25.2kWh/month
    - 25.2kWh×$0.14/kWh=$3.53/month
- **Total At-Home Lab Costs:**
    - Compute: $108.66
    - Storage: $0
    - Networking: $0
    - Software: $0
    - Electricity: $0
    - Total: $108.66 one time cost, $3.53/month recurring expenses, $151.02 for the first year

### Cloud DevOps Lab
**Hardware Costs:** 
- Compute: t3.xlarge (4 vCPU, 16GB RAM) = $.1664 USD per hour
  - $.1664 x 24 hours = $3.9936 per day
  - $3.9936 * 30 days = $119.808 per month
- Networking:
  - NAT Gateway: Cost: 0.045perhour + 0.045 per GB of data processed.
  - 0.045 x 24hours x 30days = $32.40
  - networking costs will be variable based on data transfer and data processed
- Storage: 240GB GP3: GP3 storage cost: $0.08 per GB per month.
  - Monthly storage cost = 240 GB × $0.08 / G B = $19.20

- **Total Cloud Lab Costs**
  - Compute: $119.808/month
  - Storage: $19.20
  - Networking: $32.40
  - Software: $0
  - Total: $180.408/month or $2,164.90/year

| **Cost Component**       | **At-Home Lab**               | **Cloud Lab**                |
|--------------------------|-------------------------------|------------------------------|
| **Compute**              | $108.66 (One-Time)            | $119.808/month               |
| **Storage**              | $0                            | $19.20/month                 |
| **Software**             | $0                            | $0                           |
| **Networking**           | $0                            | $41.40/month                 |
| **Electricity**          | $3.53/month                   | $0                           |
| **Total (First Year)**   | ~$151.02/year                 | ~$2,164.90/year              |
    
Cloud solutions mainly benefit from economies of scale, so I already knew running the at-home lab at this workload would be cheaper. However, I thought it would be a good exercise to sit down and compare the two side by side. This analysis has helped me better understand the trade-offs between cost, scalability, and functionality for my learning and experimentation needs.

### Installation and Setup
**Linux**
For my home server setup, I opted to install Ubuntu Server due to its user-friendly nature and robust community support. I followed a process closely aligned with the official Ubuntu documentation, which provides a clear and comprehensive guide for installation. You can refer to the official tutorial here: [Install Ubuntu Server](https://ubuntu.com/tutorials/install-ubuntu-server#1-overview)


**OpenSSH**
To enable secure remote access to the server from my Mac, I installed OpenSSH and implemented security best practices. This included disabling password-based authentication to reduce the risk of brute-force attacks and configuring SSH key pairs for secure, passwordless login. If you're interested in setting up SSH key-based authentication for your own server, I recommend following this detailed guide:  [SSH Key Pair](https://www.digitalocean.com/community/tutorials/how-to-configure-ssh-key-based-authentication-on-a-linux-server). This approach ensures a more secure and streamlined remote access experience.

**Docker**
I will be using Docker to manage and run my containerized workloads. Following the official [Docker installation for Ubuntu](https://docs.docker.com/engine/install/ubuntu/), I successfully installed the core components, including:

- docker-ce: The Docker Community Edition engine, which powers container runtime and management.

- docker-ce-cli: The Docker command-line interface for interacting with the Docker daemon.

- containerd.io: The underlying container runtime responsible for managing container lifecycle operations.

- docker-buildx-plugin: A tool for building multi-architecture Docker images.

- docker-compose-plugin: For defining and running multi-container applications using Docker Compose.

This setup provides a robust foundation for containerization and will serve as a stepping stone for my Kubernetes setup, where I can launch containers at scale.
