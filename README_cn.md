# Content Management System Pay Module

This module is related to the Pay function of the content management system.

<p align="center">
  <a href="./README.md">简体中文</a> | 
  <a href="./README_cn.md">English</a>
</p>


**Experience Address**: [https://ai.umi6.com](https://ai.umi6.com)

## I. Environment Preparation

### 1. Completion of Configuration Items
- **Operation Instructions**: The items to be configured in the project are marked with `TODO` comments.
  - **For PyCharm Users**: Click the `TODO` panel at the bottom - left corner to quickly locate the items.
  - **For Other IDEs**: Search for the global `TODO` keyword or use shortcuts (e.g., in VSCode: `Ctrl + Shift + F` to search for `TODO`).
- **Key Configurations**: Sensitive information such as database connections, API keys, and encryption certificates is recommended to be managed through environment variables.

### 2. Python Environment Requirements
- **Version**: You must use **Python 3.10**.
  ```bash
  # Verify the version (it is recommended to use pyenv to manage multiple versions)
  python --version  # The output should be Python 3.10.x
  ```
- **Dependent Tools**: Ensure that `pip`, `setuptools`, and `wheel` are installed.

## 🎉 Stay Tuned

⭐️ Star our repository to stay up - to - date with exciting new features and improvements! Get instant notifications for new releases! 🌟

<div align="center" style="margin-top:20px;margin-bottom:20px;">
<img src="https://github.com/UMIntelligence/platform_multimodal_frontend/blob/main/assets/3ed4e296-fbf2-4618-9011-8eca26fe3462.gif" width="1200"/>
</div>

### 3. Port Configuration
You need to release the following ports in advance (the operations may vary depending on the system):
| Port Number | Purpose | Configuration Example (Linux) |
|----------|----------------------|---------------------------------|
| 29090 | Main service port | `firewall-cmd --add-port=29090/tcp --permanent` |
| 28083 | OpenSearch communication port | `firewall-cmd --add-port=28083/tcp --permanent` |
| 28060 | Data synchronization port | `firewall-cmd --add-port=28060/tcp --permanent` |
- **Verification**: After `sudo firewall-cmd --reload` takes effect, use `telnet localhost <port>` to test the connectivity.

### 4. Worker Process Configuration
- **Configuration File**: Modify the `WORKER_COUNT` parameter in the `start_umi` script.
  ```python
  # Example: Set 4 worker processes (adjust according to the number of CPU cores of the server. It is recommended to be twice the number of cores)
  export WORKER_COUNT = 4
  ```

### 5. Preparation of OpenSearch Vector Database
#### Option 1: Cloud Service (Recommended)
- **Operation Steps**:
  1. Log in to the console of cloud providers such as Alibaba Cloud or Tencent Cloud.
  2. Select the OpenSearch service and create an instance (you need to configure a public IP).
  3. Record the access address, username, and password.

#### Option 2: Local Docker Deployment
**Prerequisites**: [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) are installed.
```bash
# 1. Download the installation script
wget https://raw.githubusercontent.com/ymzn3820/umi_platform_pay_module/master/install_opensearch.yml

# 2. Build and start (run in the background)
docker compose -f install_opensearch.yml build
docker compose -f install_opensearch.yml up -d

# 3. Verify the startup status
docker ps | grep opensearch  # Two containers (master node + data node) should be displayed
curl http://localhost:28083  # OpenSearch cluster information should be returned
```

## II. Quick Deployment Process

### 1. Pull the Project Code
```bash
git clone https://github.com/ymzn3820/umi_platform_pay_module.git
cd umi_platform_pay_module
```

### 2. Build the Docker Image
```bash
# Build for the production environment (automatically optimize the image size)
docker compose -f production.yml build --no-cache
```

### 3. Start the Service (Run in the Background)
```bash
docker compose -f production.yml up -d

# Recommendation: Add --remove-orphans to clean up invalid containers
docker compose -f production.yml up -d --remove-orphans
```

### 4. Status Check
#### Method 1: Log Monitoring
```bash
# Get the container ID (it is recommended to filter by the service name, such as pay-service)
CONTAINER_ID=$(docker ps -qf "name=pay-service")

# View the logs in real - time (no errors indicate successful deployment)
docker logs -f $CONTAINER_ID
```

#### Method 2: Service Health Check
```bash
curl http://localhost:29090/healthz  # {"status":"healthy"} should be returned
```

## Module Navigation

### Repositories of Multi - terminal and Function Modules
| Module Type | Module Name | Code Repository Link | Description |
|----------------|----------------|---------------------------------------|-----------------------|
| Front - end Platform | PC Front - end | [platform_multimodal_frontend](https://github.com/UMIntelligence/platform_multimodal_frontend) | Code repository for the PC front - end |
|  | Mini - Program | [umi_platform_mini_program](https://github.com/ymzn3820/umi_platform_mini_program) | Code repository for the WeChat mini - program |
|  | H5 | [umi_platform_h5](https://github.com/ymzn3820/umi_platform_h5) | Code repository for the H5 mobile terminal |
| Back - end Function Modules | Payment Module | [umi_platform_pay_module](https://github.com/ymzn3820/umi_platform_pay_module) | Core module of the payment system |
|  | User Module | [umi_platform_user_module](https://github.com/ymzn3820/umi_platform_user_module) | Service module for the user center |
|  | Chat Module | [umi_platform_chat_module](https://github.com/ymzn3820/umi_platform_chat_module) | Core module of the instant messaging system |

## License
This project uses the **BSD 3 - Clause License** open - source protocol. For details, please refer to the [LICENSE](LICENSE) file.