# CityU Campus RAG — 校园智能问答助手

基于 **FastAPI + ChromaDB + MySQL + DeepSeek + GLM embedding-3** 的校园智能问答系统(R-A-G)

## 架构总览

```
入库链路(后台):
上传文档 → 格式解析(PDF/Word/MD/TXT/HTML) → LLM预处理编排(可开关)
        → 结构感知分块 → GLM embedding-3 向量化 → ChromaDB
                                    └→ 分片文本同步落 MySQL

问答链路(前台):
用户提问 → 查询改写(DeepSeek) → 混合检索(向量 + BM25, RRF融合)
        → Rerank插槽(当前Noop直通) → 组装上下文(检索结果+记忆摘要+滑窗历史)
        → Agent(function-calling) → DeepSeek 流式生成 → SSE 推送
```

## 目录结构

```
backend/
├── app/
│   ├── main.py                  # 入口(lifespan: 建表 + BM25索引重建)
│   ├── core/                    # config(.env) / security(JWT) / deps(依赖注入)
│   ├── db/                      # async engine + ORM 模型
│   ├── llm/                     # deepseek客户端 / GLM embedding客户端 / prompts集中管理
│   ├── rag/
│   │   ├── parsers/             # pdf / docx / markdown / html 解析器 + 工厂
│   │   ├── cleaner.py           # LLM预处理编排(分段清洗, 单段失败不中断)
│   │   ├── chunker.py           # 标题层级切节 + 段落聚合分块(带重叠)
│   │   ├── vector_store.py      # ChromaDB 封装(cosine, 持久化)
│   │   ├── pipeline.py          # 入库编排 + 文档状态机
│   │   ├── query_rewriter.py    # 查询改写
│   │   ├── retrievers/          # base / vector / bm25(jieba) / hybrid(RRF)
│   │   └── rerank/              # Reranker 接口预留 + Noop 直通
│   ├── agent/
│   │   ├── agent.py             # 流式 function-calling 循环
│   │   ├── tools/               # 工具注册表 + kb_search / get_current_time
│   │   └── memory.py            # 滑窗历史 + LLM 摘要压缩
│   ├── services/                # chat_service(会话CRUD + 问答编排)
│   └── api/                     # admin(JWT) / chat(SSE, 开放)
├── scripts/smoke.py             # 端到端冒烟测试
└── data/                        # 运行时数据(chroma/uploads), 已 gitignore

docker-compose.yml              # 一键容器化部署编排(mysql/chroma/backend/nginx)
backend/Dockerfile              # 后端镜像(python:3.12-slim)
frontend/Dockerfile             # 前端镜像(多阶段: node 构建 → nginx 托管)
frontend/nginx.conf             # 前端容器内 nginx(SPA 路由 + /api 反代)
```

## 快速开始(本地开发)

> 服务器生产部署请直接看下方 [Docker 一键部署](#服务器部署), 无需 Python/Node 环境

```bash
# ---------- 后端 ----------
cd backend

# 1. 创建虚拟环境(Python 3.12)
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 2. 配置项目根目录 .env(API key、MySQL 连接等)

# 3. 启动 ChromaDB server(.env 中 CHROMA_MODE=http 时需要)
#    警告: 必须先 cd 到 backend 目录再启动! 否则 --path 相对路径会指到错误的数据目录
cd backend
.venv\Scripts\chroma.exe run --path data/chroma --port 8001

# 4. 启动后端(在 backend/ 目录下运行; 生产环境/演示时不建议加上 --reload)
.venv\Scripts\python -m uvicorn app.main:app --port 8000

# 5. 冒烟测试(另开终端, 在 backend/ 目录下)
# .venv\Scripts\python scripts\smoke.py

# ---------- 前端 ----------
cd frontend
npm install --registry=https://registry.npmmirror.com
npm run dev        # http://localhost:5173(已代理 /api 到 8000)
```

启动时自动完成: MySQL 建表 + 缺失列自动补齐、BM25 索引全量重建、DB 配置覆盖重放、**ChromaDB 与 MySQL 分片数一致性自检**(不一致会打告警, 提示可能连错数据目录)

## 前端功能

**用户端**(免登录, 直接对话): 
- 多会话管理(左侧列表, 记忆按会话独立)
- 首轮对话输入框居中, 开始对话后固定底部
- 深度思考开关(持久化记忆), 思考过程折叠展示
- SSE 流式回答 + Markdown 渲染 + 代码高亮 + 引用来源卡片
- 查询改写(多轮指代消解)+ 工具调用(知识库检索/时间)

**管理后台**(右上角管理员登录, 侧栏出现入口): 
- 仪表盘: 访问量/问答次数/Token 消耗/平均响应时间, 按日趋势图, 30s 自动刷新
- 知识库: 上传入库(PDF/Word/MD/TXT/HTML)、状态跟踪、分片预览、删除/重试
- 系统提示词: 在线编辑 agent_system, 保存即时生效
- 模型配置: .env 中 RAG 全流程配置热更新(API Key 脱敏, 重启自动重放)

## API 一览

FastAPI 交互式文档: http://127.0.0.1:8000/docs

### 管理端(需 JWT, `Authorization: Bearer <token>`)

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/admin/auth/login` | 登录, 返回 JWT |
| GET | `/api/admin/auth/me` | 当前管理员信息 |
| POST | `/api/admin/documents/upload` | 上传文档, 后台异步入库(md5 去重) |
| GET | `/api/admin/documents` | 文档列表(支持 status 过滤 + 分页) |
| GET | `/api/admin/documents/{id}` | 文档详情(含处理状态) |
| GET | `/api/admin/documents/{id}/chunks` | 查看分片内容 |
| DELETE | `/api/admin/documents/{id}` | 删除文档(级联清空向量与分片) |
| POST | `/api/admin/documents/{id}/retry` | 重试失败/重新处理 |

### 对话端(开放访问, 无需登录)

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/chat/sessions` | 创建会话 |
| GET | `/api/chat/sessions` | 会话列表 |
| GET | `/api/chat/sessions/{id}/messages` | 历史消息 |
| DELETE | `/api/chat/sessions/{id}` | 删除会话 |
| POST | `/api/chat/sessions/{id}/stream` | **流式问答(SSE)** |

### SSE 事件格式

请求体 `{"question": "..."}`, 响应为 `text/event-stream`, 每行 `data: {json}\n\n`: 

| type | 字段 | 说明 |
|---|---|---|
| `sources` | `sources[]` | 检索到的引用(文件名/章节/得分) |
| `delta` | `content` | 正文文本增量 |
| `tool` | `name, arguments` | Agent 发起工具调用 |
| `tool_result` | `name, brief` | 工具执行完成 |
| `done` | `content, sources` | 完整回复 + 引用 |
| `error` | `message` | 出错终止 |
| `[DONE]` | — | 流结束标记 |

## 关键设计

- **文档状态机**: `pending → parsing → cleaning → chunking → embedding → done | failed`, 前端可轮询进度; 失败保留 `error` 可重试
- **双写一致性**: 分片同时写入 ChromaDB(向量+元数据)与 MySQL(文本+`chroma_id`); MySQL 是分片的事实来源, BM25 索引启动时从 MySQL 重建
- **混合检索**: 向量(语义)+ BM25(关键词, jieba 分词)两路召回, RRF(k=60) 融合; `.env` 的 `HYBRID_ENABLED` 可关闭
- **Rerank 预留**: 实现 `BaseReranker` 接入 `app/rag/rerank/`, 改 `get_reranker()` 即可插拔(智谱 rerank API / 本地 BGE)
- **记忆机制**: 全量消息落库; 上下文 = 摘要(窗口外消息由 LLM 压缩, 水位线防重复)+ 最近 12 条滑窗
- **工具扩展**: `@register_tool` 装饰器注册, Agent 自动获得新工具
- **Prompt 管理**: 全部集中在 `app/llm/prompts.py`, 调优只改一个文件

## 配置说明(.env)

| 配置 | 说明 |
|---|---|
| `DEEPSEEK_*` | DeepSeek API(OpenAI 兼容协议), 生成+改写+清洗+摘要共用 |
| `GLM_*` | GLM embedding-3; `GLM_EMBEDDING_DIMENSIONS=2048`, 批大小可调 |
| `MYSQL_*` | MySQL 连接(分片/文档/会话存储); 已适配 5.1(utf8 + InnoDB + 应用层时间戳) |
| `MYSQL_ROOT_PASSWORD` | Docker 部署时容器 MySQL 的 root 密码(backend 自动复用作连接密码) |
| `CHROMA_MODE` | `local`=进程内持久化; `http`=独立 server(推荐, 便于 VectorDBZ 等工具可视化) |
| `CHROMA_HTTP_HOST` / `CHROMA_HTTP_PORT` | http 模式连接参数(默认 127.0.0.1:8001, 勿用 8000 会与后端冲突) |
| `CHROMA_PERSIST_DIR` / `CHROMA_COLLECTION` | 向量库数据目录(server 启动参数 `--path` 用同一目录)与集合名 |
| `APP_SECRET_KEY` / `ADMIN_*` | JWT 签名密钥与管理员凭证(首次部署务必修改, 密钥需 ≥32 字符随机串) |
| `ALLOWED_ORIGINS` | CORS 允许的前端来源(逗号分隔), 上线时改为前端域名, 勿用 `*` |
| `MAX_UPLOAD_MB` | 上传文件大小上限(MB) |
| `RATE_LIMIT_CHAT_PER_MIN` / `RATE_LIMIT_API_PER_MIN` | 每 IP 每分钟问答/普通请求次数上限(超出返回 429) |
| `HYBRID_ENABLED` / `RRF_K` / `RETRIEVAL_TOP_K` | 检索策略 |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` / `DOC_CLEAN_ENABLED` | 分块与 LLM 清洗开关 |
| `MEMORY_WINDOW_MESSAGES` / `MEMORY_SUMMARY_TRIGGER` | 记忆策略 |

## 服务器部署

### 方式一: Docker 一键部署(推荐)

服务器只需安装 Docker(含 compose 插件), 无需 Python/Node/MySQL/Chroma 环境
四个容器自动编排: `mysql` + `chroma` + `backend` + `nginx`(对外暴露 80):

```bash
# 1. 上传项目到服务器(注意 .env 不在 git 里, 需单独上传)
#    并在服务器上检查 .env: API Key、ADMIN_PASSWORD、APP_SECRET_KEY、MYSQL_ROOT_PASSWORD

# 2. 项目根目录一键构建启动
docker compose up -d --build

# 3. 浏览器直接访问
http://服务器IP
```

常用运维命令:

```bash
docker compose ps                     # 容器状态
docker compose logs -f backend        # 后端日志(建表/BM25重建/入库进度)
docker compose restart backend        # 重启单个服务
docker compose down                   # 停止(数据保留在具名卷, 不丢失)
docker compose up -d --build          # 改代码后重新构建部署
```

说明:

- 数据全部持久化在具名卷 `mysql-data` / `chroma-data` / `backend-data`(上传文件), `down` 不丢数据; 彻底清空用 `docker compose down -v`
- 前端经 nginx 同源反代 `/api`, 浏览器无跨域, `.env` 的 `ALLOWED_ORIGINS` 无需修改
- nginx 已透传 `X-Forwarded-For`, backend 以 `--proxy-headers` 启动, 限流按真实访客 IP 计数
- 国内服务器拉取镜像慢/失败时, 配置镜像加速(`/etc/docker/daemon.json` 的 `registry-mirrors`), 或提前手动 `docker pull mysql:8.0` 与 `chromadb/chroma:1.5.9`
- 管理后台地址: 前端页面右上角管理员登录进入

### 方式二: 手动部署(nginx 同源反代)

服务器上运行 ChromaDB(8001) 与 FastAPI(8000), 二者仅监听本机; 前端 `npm run build`
后把 `frontend/dist/` 交给 nginx 托管, `/api` 反代到 8000:

```nginx
server {
    listen 80;
    server_name 你的域名或IP;

    location / {
        root /path/to/dist;                          # frontend/dist
        try_files $uri $uri/ /index.html;
    }
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_buffering off;                         # SSE 必须关闭缓冲
        proxy_read_timeout 300s;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;   # 传真实访客IP
    }
}
```

uvicorn 启动加代理头参数, 使限流按**真实访客 IP** 计数(否则经 nginx 后所有人都算
127.0.0.1, 共享同一个限流桶):

```bash
.venv\Scripts\python -m uvicorn app.main:app --port 8000 --proxy-headers --forwarded-allow-ips 127.0.0.1
```

`--forwarded-allow-ips` 只允许填 nginx 所在本机地址; 若填了其他值, 访客可伪造
X-Forwarded-For 头绕过限流, 学校如有 HTTPS 证书, 在此 server 上加 443 配置即可

## 已知边界与后续演进

- 入库用 FastAPI BackgroundTasks, 大文件高并发场景可换 Celery/ARQ 任务队列
- 建表用 `create_all`, 后续迭代建议引入 Alembic 做迁移管理
- 管理员为 .env 单账号, 多管理员需加用户表
- Rerank、混合检索均可按上文接口插槽平滑接入
- ChromaDB http 模式下, 可用 VectorDBZ 等桌面工具连接 `http://127.0.0.1:8001` 查看集合与向量入库质量
