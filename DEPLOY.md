# CityU Campus RAG — 部署文档（保姆级）

本手册面向第一次部署本项目的同学，覆盖两条完整路线：

- **路线 A：本地部署**（开发调试用，在自己电脑上跑起来）
- **路线 B：云服务器 Docker 部署**（展示/上线用，服务器一键跑起来）

> 拿到代码后你会发现项目里**没有 `.env` 文件**——它包含密钥，被 `.gitignore` 排除在仓库外了，
> 这是正常现象。本文档第二章会带你从零创建它。
>
> 管理后台（知识库入库、提示词、模型配置）的操作说明见文末第七章。

---

## 目录

- [一、准备工作](#一准备工作)
- [二、配置 .env 环境变量](#二配置-env-环境变量路线-a-和-b-都要做)
- [三、路线 A：本地部署（Windows）](#三路线-a本地部署windows)
- [四、路线 B：云服务器 Docker 部署](#四路线-b云服务器-docker-部署)
- [五、后续更新代码怎么重新部署](#五后续更新代码怎么重新部署)
- [六、常见问题 FAQ](#六常见问题-faq)
- [七、管理员后台操作（待补充）](#七管理员后台操作待补充)

---

## 一、准备工作

### 1. 拿到代码

两种方式任选：

**方式一：git 克隆（推荐）**

```bash
git clone https://github.com/lihaoyan25/cityu-campus-rag.git
cd cityu-campus-rag
```

**方式二：网页下载**

打开仓库页面 → 绿色 `Code` 按钮 → `Download ZIP` → 解压到任意目录。

### 2. 检查项目结构

拿到代码后，根目录应该长这样（不需要全部看懂，混个眼熟）：

```
cityu-campus-rag/
├── backend/               # Python 后端(FastAPI + RAG 全流程)
│   ├── app/               # 后端源码
│   ├── requirements.txt   # 后端依赖清单
│   └── Dockerfile         # 后端容器构建文件
├── frontend/              # Vue3 前端
│   ├── src/               # 前端源码
│   ├── package.json       # 前端依赖清单
│   ├── Dockerfile         # 前端容器构建文件
│   └── nginx.conf         # 前端容器内 nginx 配置
├── docker-compose.yml     # 服务器一键部署编排文件
├── .env.example           # 环境变量模板(你要复制它)
├── .gitignore             # git 忽略清单
└── README.md              # 项目说明
```

### 3. 两条路线各自需要准备的东西

| 准备项 | 路线 A(本地) | 路线 B(服务器 Docker) |
|---|---|---|
| DeepSeek API Key（问答生成） | 需要 | 需要 |
| 智谱 GLM API Key（向量化） | 需要 | 需要 |
| Python 3.12 | 需要 | 不需要 |
| Node.js 20 | 需要 | 不需要 |
| MySQL 数据库 | 需要(本机安装) | 不需要(容器自动起) |
| 云服务器(装 Docker) | 不需要 | 需要 |

---

## 二、配置 .env 环境变量（路线 A 和 B 都要做）

### 1. 复制模板

在项目根目录复制一份 `.env.example`，**改名为 `.env`**，保存在项目根目录。

- Windows：文件资源管理器中复制粘贴后重命名（注意别变成 `.env.txt`，需在「查看」中打开「文件扩展名」）
- macOS / Linux / 服务器：`cp .env.example .env`

> Windows 用户推荐用 VS Code / 记事本打开编辑；Linux 服务器用 `nano .env` 编辑，`Ctrl+O` 保存、`Ctrl+X` 退出。

### 2. 获取 DeepSeek API Key（LLM，负责生成回答）

1. 打开 DeepSeek 开放平台：`https://platform.deepseek.com/`，注册/登录
2. 左侧菜单进入 **API keys** 页面，点击 **创建 API key**
3. 名称随便填（例如 `cityu-rag`），点击确定
4. **弹窗里的 key 只显示这一次**，立刻复制！
5. 粘贴到 `.env` 中：

```
DEEPSEEK_API_KEY=sk-****************************5f6d
```

> 示例为脱敏展示，你只需完整粘贴自己的 key。
> ⚠️ DeepSeek 是付费 API，新账户需在左侧「充值」页面充值后才能调用（几块钱够测试很多轮）。

### 3. 获取智谱 GLM API Key（Embedding，负责文档向量化）

1. 打开智谱开放平台：`https://bigmodel.cn/`，注册/登录
2. 右上角头像 → 进入控制台，找到 **API keys**（密钥管理）
3. 点击 **创建 API Key**，名称填 `cityu-rag` 即可
4. 复制生成的 key（形如 `xxxxxxxx.yyyyyyyy` 的两段式）
5. 粘贴到 `.env` 中：

```
GLM_API_KEY=****************************.**********
```

> 智谱对新用户有免费额度，嵌入模型 embedding-3 的费用很低。

### 4. ChromaDB 配置（向量数据库）——保持默认即可

```
CHROMA_MODE=http
CHROMA_PERSIST_DIR=./data/chroma
CHROMA_COLLECTION=campus_kb
CHROMA_HTTP_HOST=127.0.0.1
CHROMA_HTTP_PORT=8001
```

本地部署保持上面默认值不动。Docker 部署时 `CHROMA_HTTP_HOST/PORT` 会被 docker-compose 自动覆盖为容器地址，**同样不用改**。

### 5. MySQL 配置（路线 A 需要填真实密码）

```
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=你的数据库root密码
MYSQL_DATABASE=cityu_rag
```

- 路线 A：填你本机 MySQL 的 root 密码（本地 MySQL 安装见第三章）
- 路线 B：`MYSQL_HOST`、`MYSQL_PASSWORD` 会被 docker-compose 自动覆盖为容器值，**不用改**

### 6. Docker 容器 MySQL 密码（路线 B 需要设置）

```
MYSQL_ROOT_PASSWORD=cityu_rag_root
```

这是 Docker 部署时自动创建的 MySQL 容器的 root 密码，只存在于服务器内部网络，外部访问不到。
可以保持默认，也可以改成一个自己的强密码（改完后 backend 容器会自动复用它，无需改别处）。

### 7. 管理员账号与 JWT 密钥（务必修改！）

```
APP_SECRET_KEY=please-generate-a-64-hex-random-string
ACCESS_TOKEN_EXPIRE_MINUTES=720
ADMIN_USERNAME=admin
ADMIN_PASSWORD=please-use-a-strong-password
```

- `APP_SECRET_KEY`：登录态签名密钥，必须换成随机值。生成方法——任选其一：
  - 本机有 Python：`python -c "import secrets;print(secrets.token_hex(32))"`
  - 服务器上：`openssl rand -hex 32`
  - 把输出的一长串十六进制粘贴进来
- `ADMIN_USERNAME` / `ADMIN_PASSWORD`：**前台页面右上角登录管理后台的账号密码**，上线前务必改成强密码（≥16 位，混合大小写/数字/符号）

> ⚠️ **`ADMIN_PASSWORD` 绝对不能包含 `$` 符号**！Docker 读取 .env 时会把 `$xxx` 当作变量替换掉，
> 导致登录一直提示密码错误。`! # % @ & - _` 等其他符号都安全，只有 `$` 不行。

### 8. 其余配置（可以先用默认值）

| 配置 | 默认值 | 说明 |
|---|---|---|
| `ALLOWED_ORIGINS` | `*` | CORS 白名单；Docker 部署走 nginx 同源反代，保持 `*` 即可 |
| `MAX_UPLOAD_MB` | `20` | 上传文档大小上限(MB) |
| `RATE_LIMIT_CHAT_PER_MIN` | `5` | 每个访客 IP 每分钟提问次数上限 |
| `RATE_LIMIT_API_PER_MIN` | `120` | 每个访客 IP 每分钟普通请求上限 |
| `RETRIEVAL_TOP_K` | `8` | 检索召回条数 |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `600` / `120` | 分块大小/重叠 |
| `MEMORY_WINDOW_MESSAGES` | `12` | 会话记忆窗口 |

---

## 三、路线 A：本地部署（Windows）

### 1. 安装基础环境

按顺序安装以下软件（一路下一步即可）：

1. **Python 3.12**：`https://www.python.org/downloads/` 下载 3.12.x
   ⚠️ 安装第一屏务必勾选 **Add python.exe to PATH**
2. **Node.js 20**：`https://nodejs.org/` 下载 LTS 版本（20.x）
3. **MySQL 8.0**：`https://dev.mysql.com/downloads/installer/` 下载安装
   - 安装时设置 root 密码，**记牢它**，填到 `.env` 的 `MYSQL_PASSWORD`
   - 装完打开 MySQL 命令行客户端（或 Workbench），执行建库：

   ```sql
   CREATE DATABASE cityu_rag DEFAULT CHARACTER SET utf8;
   ```

   > 项目已兼容 MySQL 5.1 ~ 8.x（utf8 + InnoDB），学校老版本 MySQL 也能用。

### 2. 启动后端（开一个终端）

打开 PowerShell / CMD，`cd` 进项目的 `backend` 目录：

```powershell
cd C:\你的路径\cityu-campus-rag\backend

# 1) 创建虚拟环境(首次)
py -3.12 -m venv .venv

# 2) 安装依赖(首次, 用清华源加速)
.venv\Scripts\pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3) 启动 ChromaDB 向量库(每次开机后要启动)
.venv\Scripts\chroma.exe run --path data/chroma --port 8001
```

> ⚠️ **必须先 `cd` 进 `backend` 目录再启动 ChromaDB**！`--path data/chroma` 是相对路径，
> 在别的目录启动会创建一个空数据库，导致向量丢失。

**再开第二个终端**，启动 FastAPI 后端：

```powershell
cd C:\你的路径\cityu-campus-rag\backend
.venv\Scripts\python -m uvicorn app.main:app --port 8000
```

看到 `Application startup complete` 即成功（启动时会自动建表、重建 BM25 索引、自检向量库）。
验证：浏览器打开 `http://127.0.0.1:8000/docs` 能看到接口文档页面。

### 3. 启动前端（开第三个终端）

```powershell
cd C:\你的路径\cityu-campus-rag\frontend
npm install --registry=https://registry.npmmirror.com   # 首次
npm run dev
```

看到 `Local: http://localhost:5173/` 即成功。

### 4. 验证

浏览器打开 `http://localhost:5173`：

1. 随便问一个问题（此时知识库是空的，能回答但引用为空，正常）
2. 右上角「管理员」→ 用 `.env` 里的 `ADMIN_USERNAME/ADMIN_PASSWORD` 登录 → 进入管理后台 → 知识库管理 → 上传几份文档 → 状态变「已入库」
3. 回到对话页再问文档相关问题，应能命中引用来源

---

## 四、路线 B：云服务器 Docker 部署

> 只需要一台装好 Docker 的服务器，不需要装 Python/Node/MySQL。
> 以下以 **阿里云/腾讯云轻量应用服务器 + Ubuntu 22.04/24.04** 为例。

### 1. 购买服务器

- **配置建议**：2核4GB 起步（2核2GB 跑 MySQL 容器偏紧，务必按第 3 步加 swap）、系统盘 40GB+
- **镜像**：直接选纯 Ubuntu 系统镜像即可（下面会装 Docker）；选「应用镜像 - Docker」也行，可跳过安装步骤
- **地域**：离学校近的国内节点（访问 DeepSeek/智谱 API 国内直连无障碍）

### 2. SSH 登录服务器

在**你自己的电脑**上打开终端（Windows 用 PowerShell）：

```powershell
ssh root@服务器公网IP
```

首次连接输入 `yes`，然后输入控制台设置的密码（输密码时屏幕不显示，输完回车）。
看到 `root@xxx:~#` 提示符即登录成功。以下所有命令都在这个窗口执行。

### 3. 安装 Docker（选了 Docker 应用镜像的跳过本步）

```bash
# 安装 Docker CE(阿里云内网源, ECS 上速度极快; 腾讯云把 mirrors.aliyun.com 换成 mirrors.cloud.tencent.com)
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://mirrors.aliyun.com/docker-ce/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

配置镜像加速（Docker Hub 国内直连已失效，必须配）：

```bash
sudo tee /etc/docker/daemon.json <<'EOF'
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://docker.1ms.run",
    "https://docker.1panel.live"
  ]
}
EOF
sudo systemctl enable --now docker
sudo systemctl restart docker
```

让当前用户免 sudo 使用 docker（用 root 登录的可跳过）：

```bash
sudo usermod -aG docker $USER
exit    # 退出后重新 ssh 登录生效
```

验证：

```bash
docker --version && docker compose version
docker pull mysql:8.0
docker pull chromadb/chroma:1.5.9
```

两个 pull 都成功说明环境畅通。

### 4. 加 2G swap（2GB 内存的小服务器必做！）

swap 用硬盘充当内存缓冲，不花一分钱，防止构建前端时内存耗尽卡死：

```bash
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile && echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab && free -h
```

看到 `Swap: 2.0Gi` 即成功（重启后依然生效）。

### 5. 把代码上传到服务器

**方式一：git 克隆（推荐，方便后续更新）**

项目是公开仓库，服务器上直接克隆即可，不需要注册或登录 GitHub：

```bash
sudo mkdir -p /opt/cityu-rag && sudo chown $USER:$USER /opt/cityu-rag
git clone https://github.com/lihaoyan25/cityu-campus-rag.git /opt/cityu-rag
cd /opt/cityu-rag
```

**方式二：scp 直传（本地已有项目文件夹时）**

如果你是在自己电脑上下载/修改过项目（例如下载的 ZIP 解压后），在**本地电脑**的 PowerShell
执行上传（路径按实际调整，`admin` 换成你的服务器用户名）：

```powershell
scp -r C:\你的路径\cityu-campus-rag admin@服务器IP:/opt/cityu-rag
```

### 6. 配置服务器的 .env

`.env` 不会随 git 走，需要单独传。在**本地电脑**执行：

```powershell
scp C:\你的路径\cityu-campus-rag\.env root@服务器IP:/opt/cityu-rag/.env
```

或者直接在服务器上创建：`nano /opt/cityu-rag/.env`，按第二章内容填写后保存。

传完验证：`cat /opt/cityu-rag/.env | head -5`，能看到 DEEPSEEK 配置即成功。

### 7. 一键构建启动

```bash
cd /opt/cityu-rag
docker compose up -d --build
```

首次构建约 5-15 分钟（下载镜像 + 安装依赖 + npm 打包）。看到如下输出即成功：

```
[+] up 6/6
 ✔ Image cityu-rag-backend    Built
 ✔ Image cityu-rag-nginx      Built
 ✔ Container cityu-rag-mysql-1    Healthy
 ✔ Container cityu-rag-chroma-1   Started
 ✔ Container cityu-rag-backend-1  Started
 ✔ Container cityu-rag-nginx-1    Started
```

### 8. 放行 80 端口（最容易漏的一步！）

云控制台 → 你的服务器 → **防火墙 / 安全组** → 添加规则：
**协议 TCP、端口 80、来源 0.0.0.0/0、允许**。

### 9. 浏览器验证

访问 `http://服务器公网IP`：

- 能看到智能助手首页 → 发一条消息测试流式回答
- 右上角管理员登录 → 进入管理后台（后续操作见第七章）

### 10. 日常运维命令速查

```bash
cd /opt/cityu-rag
docker compose ps                    # 容器状态(mysql 应为 Healthy)
docker compose logs -f backend       # 后端日志(Ctrl+C 退出查看)
docker compose restart backend       # 重启某个服务
docker compose stop                  # 全部停止(数据保留)
docker compose up -d                 # 启动(数据保留)
docker compose down                  # 删除容器(数据仍在卷中保留)
docker compose down -v               # ⚠️ 连数据卷一起删除(向量/文档/会话全没, 慎用!)
docker compose up -d --build         # 改代码后重新构建部署
```

> 数据持久化说明：MySQL 数据、向量库、上传的文档分别存在
> `mysql-data` / `chroma-data` / `backend-data` 三个 Docker 卷中，
> `stop`/`down`/重启服务器都不会丢，服务器重启后容器会自动拉起（`restart: unless-stopped`）。

---

## 五、后续更新代码怎么重新部署

1. 本地改好代码，推送到 GitHub
2. 服务器上：

```bash
cd /opt/cityu-rag
git pull
docker compose up -d --build
```

> 只改了前端：`docker compose up -d --build nginx` 更快；
> 只改了后端：`docker compose up -d --build backend`。
>
> 若 `git pull` 报 `Your local changes ... would be overwritten`，说明服务器上有手改过的文件
> （比如曾用 nano 改配置），确认 GitHub 上已包含该修改后执行
> `git checkout -- 文件名` 丢弃服务器手改，再 `git pull`。

---

## 六、常见问题 FAQ

**Q1：上传文档报 HTTP 413**
nginx 默认请求体上限 1MB。仓库内 `frontend/nginx.conf` 已配置 `client_max_body_size 20m`，
若仍出现说明服务器代码不是最新，`git pull` 后重新 build。

**Q2：管理员登录一直提示密码错误**
检查 `.env` 中 `ADMIN_PASSWORD` 是否包含 `$` 符号（会被 Docker 吞掉），换成不含 `$` 的密码，
然后 `docker compose up -d` 重建 backend 容器。
验证容器内实际收到的密码：`docker compose exec backend printenv ADMIN_PASSWORD`。

**Q3：构建时卡在 `RUN npm run build` 很久 / 服务器卡死**
内存不足。确认已加 swap（`free -h` 看 Swap 行），或构建前 `docker compose stop` 停掉运行中的容器腾内存。

**Q4：`docker pull` 拉不动镜像**
镜像加速器失效，更换 `/etc/docker/daemon.json` 中 `registry-mirrors` 地址后
`sudo systemctl restart docker`。

**Q5：文档上传后一直是「解析中/清洗中」**
正常现象，LLM 清洗+分块+向量化需要时间（300KB 文档约 1-3 分钟），状态会自动轮询到「已入库」。

**Q6：提问报「Could not connect to a Chroma server」**
本地部署：ChromaDB 没启动（见第三章第 2 步），或启动目录不对导致连到了空库；
Docker 部署：`docker compose ps` 看 chroma 容器是否在运行，`docker compose logs chroma` 查报错。

**Q7：本地能跑，部署后中文乱码 / 时间不对**
compose 已内置 `TZ=Asia/Shanghai` 与 utf8mb4，一般不会出现；若自建 MySQL 遇到乱码，
建库时指定 `DEFAULT CHARACTER SET utf8`。

---

## 七、管理员后台操作（待补充）

> 本节后续补充：知识库文档上传与管理、系统提示词修改、模型配置热更新、仪表盘数据解读等。
