# 内容管理系统Pay模块

内容管理系统Pay相关模块。

<p align="center">
  <a href="./README.md">简体中文</a> | 
  <a href="./README_cn.md">English</a>
</p>

**体验地址**：[https://ai.umi6.com](https://ai.umi6.com)

## 一、环境准备  

### 1. 配置项补全  
- **操作说明**：项目中已通过`TODO`注释标记待配置项  
  - **PyCharm用户**：左下角点击`TODO`面板快速定位  
  - **其他IDE**：搜索全局`TODO`关键词或使用快捷键（如VSCode：`Ctrl+Shift+F`搜索`TODO`）  
- **关键配置**：数据库连接、API密钥、加密证书等敏感信息建议通过环境变量管理  


### 2. Python环境要求  
- **版本**：必须使用 **Python 3.10**  
  ```bash
  # 验证版本（推荐使用pyenv管理多版本）
  python --version  # 需输出Python 3.10.x
  ```
- **依赖工具**：确保已安装`pip`、`setuptools`、`wheel`  


## 🎉 Stay Tuned

⭐️ Star our repository to stay up-to-date with exciting new features and improvements! Get instant notifications for new
releases! 🌟

<div align="center" style="margin-top:20px;margin-bottom:20px;">
<img src="https://github.com/UMIntelligence/platform_multimodal_frontend/blob/main/assets/3ed4e296-fbf2-4618-9011-8eca26fe3462.gif" width="1200"/>
</div>



### 3. 端口配置  
需提前放行以下端口（根据系统差异操作）：  
| 端口号   | 用途                 | 配置示例（Linux）               |
|----------|----------------------|---------------------------------|
| 29090    | 主服务端口           | `firewall-cmd --add-port=29090/tcp --permanent` |
| 28083    | OpenSearch通信端口   | `firewall-cmd --add-port=28083/tcp --permanent` |
| 28060    | 数据同步端口         | `firewall-cmd --add-port=28060/tcp --permanent` |  
- **验证**：`sudo firewall-cmd --reload` 生效后，使用`telnet localhost <端口>`测试连通性  


### 4. 工作进程配置  
- **配置文件**：在`start_umi`脚本中修改`WORKER_COUNT`参数  
  ```python
  # 示例：设置4个工作进程（根据服务器CPU核心数调整，建议为核心数2倍）
  export WORKER_COUNT=4
  ```


### 5. OpenSearch向量数据库准备  
#### 方案一：云服务（推荐）  
- **操作步骤**：  
  1. 登录阿里云/腾讯云等云厂商控制台  
  2. 选择OpenSearch服务，创建实例（需配置公网IP）  
  3. 记录访问地址、用户名和密码  


#### 方案二：本地Docker部署  
**前置条件**：已安装[Docker](https://docs.docker.com/get-docker/)和[Docker Compose](https://docs.docker.com/compose/install/)  
```bash
# 1. 下载安装脚本
wget https://raw.githubusercontent.com/ymzn3820/umi_platform_pay_module/master/install_opensearch.yml

# 2. 构建并启动（后台运行）
docker compose -f install_opensearch.yml build
docker compose -f install_opensearch.yml up -d

# 3. 验证启动状态
docker ps | grep opensearch  # 需显示2个容器（主节点+数据节点）
curl http://localhost:28083  # 应返回OpenSearch集群信息
```


## 二、快速部署流程  

### 1. 拉取项目代码  
```bash
git clone https://github.com/ymzn3820/umi_platform_pay_module.git
cd umi_platform_pay_module
```


### 2. 构建Docker镜像  
```bash
# 生产环境构建（自动优化镜像大小）
docker compose -f production.yml build --no-cache
```


### 3. 启动服务（后台运行）  
```bash
docker compose -f production.yml up -d

# 推荐：添加--remove-orphans清理无效容器
docker compose -f production.yml up -d --remove-orphans
```


### 4. 状态检查  
#### 方式一：日志监控  
```bash
# 获取容器ID（推荐用服务名称过滤，如pay-service）
CONTAINER_ID=$(docker ps -qf "name=pay-service")

# 实时查看日志（无报错即部署成功）
docker logs -f $CONTAINER_ID
```

#### 方式二：服务健康检查  
```bash
curl http://localhost:29090/healthz  # 应返回{"status":"healthy"}
```


## 模块导航

### 多端及功能模块仓库
| 模块类型       | 模块名称       | 代码仓库链接                          | 说明                  |
|----------------|----------------|---------------------------------------|-----------------------|
| 前端平台       | PC 端前端      | [platform_multimodal_frontend](https://github.com/UMIntelligence/platform_multimodal_frontend)        | PC 端前端代码仓库     |
|                | 小程序端       | [umi_platform_mini_program](https://github.com/ymzn3820/umi_platform_mini_program)    | 微信小程序代码仓库    |
|                | H5 端          | [umi_platform_h5](https://github.com/ymzn3820/umi_platform_h5)                     | H5 移动端代码仓库     |
| 后端功能模块   | 支付模块       | [umi_platform_pay_module](https://github.com/ymzn3820/umi_platform_pay_module)       | 支付系统核心模块      |
|                | 用户模块       | [umi_platform_user_module](https://github.com/ymzn3820/umi_platform_user_module)       | 用户中心服务模块      |
|                | Chat 模块      | [umi_platform_chat_module](https://github.com/ymzn3820/umi_platform_chat_module)      | 即时通讯核心模块      |



## 许可证
本项目采用 **BSD 3 - Clause License** 开源协议，详情见 [LICENSE](LICENSE) 文件。

