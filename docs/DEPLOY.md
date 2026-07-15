# Open WebUI 部署指南 (学生 AI 创作平台)

## 服务器要求

| 项目 | 最低配置 |
|---|---|
| CPU | 2 核 |
| 内存 | 4 GB |
| 磁盘 | 20 GB（系统 + 学生作品存储） |
| 系统 | Ubuntu 22.04 / Debian 12 / CentOS 8+ |
| 网络 | 公网 IP，开放 3000 端口 |

## 步骤 1: 安装 Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo systemctl enable docker --now
sudo usermod -aG docker $USER
newgrp docker
```

## 步骤 2: 获取代码

```bash
git clone <your-repo-url> open-webui
cd open-webui
```

## 步骤 3: 配置环境变量

```bash
cp .env.example .env
nano .env
```

必填项：

```env
# DeepSeek API Key (从 platform.deepseek.com 获取)
OPENAI_API_KEY='sk-your-deepseek-key'

# Seedream API Key (从火山引擎控制台获取)
SEEDREAM_API_KEY='your-ark-api-key'

# JWT 签名密钥 (生成一个随机字符串)
WEBUI_SECRET_KEY='随机字符串至少32位'
```

生成随机密钥：
```bash
openssl rand -hex 32
```

## 步骤 4: 创建学生账号

启动服务后，进入容器批量创建：

```bash
# 创建管理员 (设置环境变量后启动时自动创建)
export WEBUI_ADMIN_EMAIL='admin@school.edu.cn'
export WEBUI_ADMIN_PASSWORD='your-admin-password'
export WEBUI_ADMIN_NAME='管理员'
```

或在启动后用 API 批量创建：

```bash
#!/bin/bash
TOKEN="<管理员登录后获取的 token>"
for i in $(seq -w 1 50); do
  curl -X POST http://localhost:3000/api/v1/auths/add \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"email\": \"student$i@school.edu.cn\",
      \"password\": \"password$i\",
      \"name\": \"学生$i\"
    }"
done
```

## 步骤 5: 启动

```bash
docker compose up -d
```

首次启动会构建镜像（约 5-10 分钟）。之后访问 `http://<服务器IP>:3000`。

## 步骤 6: 初始化设置

管理员登录后在 **Admin Panel > Settings** 进行以下设置:

### 关闭注册

Settings > General > Enable Signup → **关闭**

### 模型管理

Workspace > Models 中确认只有 DeepSeek 模型可见（环境变量自动配置）。

### 配额设置

如需调整配额默认值，编辑 `.env`:

```env
QUOTA_DEFAULT_DAILY_TOKEN_BUDGET_RMB=1.0   # 每人每天 token 费用上限
QUOTA_DEFAULT_DAILY_IMAGE_LIMIT=10          # 每人每天生图次数
```

重建容器生效。

## 端口映射

| 服务 | 端口 | 说明 |
|---|---|---|
| Open WebUI | 3000 | 学生和管理员访问 |
| Playwright | — | 容器内网，不对外暴露 |

如需改端口，编辑 `.env` 设置 `OPEN_WEBUI_PORT=8080`。

## 防火墙

```bash
# Ubuntu / Debian
sudo ufw allow 3000/tcp
sudo ufw enable

# CentOS
sudo firewall-cmd --add-port=3000/tcp --permanent
sudo firewall-cmd --reload
```

## 目录结构

```
/opt/open-webui/
|-- .env                      # 环境变量 (API keys, 密钥)
|-- docker-compose.yaml        # 服务编排
|-- Dockerfile                 # 镜像构建
`-- data/                      # 持久化数据 (Docker volume)
    |-- webui.db               # SQLite 数据库
    |-- uploads/               # 学生上传和生成的图片
    `-- cache/                 # 模型缓存
```

## 运维

### 更新

```bash
git pull
docker compose up -d --build
```

### 备份

```bash
# 停止服务后复制数据卷
docker compose down
docker cp open-webui:/app/backend/data ./backup_$(date +%Y%m%d)
docker compose up -d
```

### 查看日志

```bash
docker compose logs -f --tail=100 open-webui
```

### 重启

```bash
docker compose restart
```

## 故障排查

| 问题 | 解决 |
|---|---|
| 无法访问 | 检查防火墙和端口映射 |
| 生图失败 | 检查 `SEEDREAM_API_KEY` 是否有效 |
| Token 统计异常 | 检查 `OPENAI_API_KEY` 和 `stream_options` 注入 |
| Playwright 搜索失败 | `docker compose logs playwright` 检查服务状态 |
