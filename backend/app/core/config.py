"""全局配置：从项目根目录 .env 读取。"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> parents[2] = backend/
BACKEND_DIR = Path(__file__).resolve().parents[2]
# 项目根目录（.env 所在位置）
PROJECT_DIR = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(PROJECT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # DeepSeek (OpenAI 兼容协议)
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    deepseek_temperature: float = 0.3
    deepseek_max_tokens: int = 4096
    deepseek_top_p: float = 1.0

    # GLM embedding-3
    glm_api_key: str = ""
    glm_base_url: str = "https://open.bigmodel.cn/api/paas/v4/embeddings"
    glm_model: str = "embedding-3"
    glm_embedding_dimensions: int = 2048
    glm_embedding_batch_size: int = 32

    # ChromaDB
    # mode: local=进程内持久化客户端 | http=独立 server（便于 VectorDBZ 等工具可视化）
    chroma_mode: str = "local"
    chroma_persist_dir: str = str(DATA_DIR / "chroma")
    chroma_collection: str = "campus_kb"
    chroma_http_host: str = "127.0.0.1"
    chroma_http_port: int = 8001

    # MySQL
    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_database: str = "cityu_rag"

    # 应用与认证
    app_secret_key: str = "please-change-me"
    access_token_expire_minutes: int = 720
    admin_username: str = "admin"
    admin_password: str = "admin123"
    # CORS 允许的前端来源，逗号分隔；留 * 表示不限制(不建议生产使用)
    allowed_origins: str = "*"
    # 上传文件大小上限(MB)
    max_upload_mb: int = 20
    # IP 限流(每分钟): 问答流式接口 / 普通接口
    rate_limit_chat_per_min: int = 5
    rate_limit_api_per_min: int = 120

    # 检索
    retrieval_top_k: int = 8
    hybrid_enabled: bool = True
    rrf_k: int = 60
    rerank_enabled: bool = False

    # 分块与文档预处理
    chunk_size: int = 600
    chunk_overlap: int = 120
    doc_clean_enabled: bool = True

    # 记忆
    memory_window_messages: int = 12
    memory_summary_trigger: int = 20

    @property
    def mysql_dsn(self) -> str:
        # 注意: MySQL 5.1 无 utf8mb4，使用 utf8(3字节)，入库前需过滤4字节字符
        return (
            f"mysql+aiomysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8"
        )


settings = Settings()
