"""ORM 模型：documents / chunks / chat_sessions / messages。

兼容 MySQL 5.1：
- 无 JSON 列类型 -> JSONAsText(TEXT 存储，ensure_ascii 序列化)
- 无 utf8mb4 -> 全表 utf8，配合 app/core/textutil.py 过滤 4 字节字符
- 默认引擎可能为 MyISAM -> 强制 InnoDB（支持事务与外键级联）
"""
import json
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator


class JSONAsText(TypeDecorator):
    """跨版本 JSON 存储：TEXT 列 + JSON 字符串。"""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        # ensure_ascii: 非 ASCII 转 \uXXXX，彻底规避 utf8mb3 限制
        return json.dumps(value, ensure_ascii=True)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return json.loads(value)


class Base(DeclarativeBase):
    pass


_MYSQL_TABLE_ARGS = {"mysql_engine": "InnoDB", "mysql_charset": "utf8"}


class Document(Base):
    """上传的原始文档及其处理状态。"""

    __tablename__ = "documents"
    __table_args__ = _MYSQL_TABLE_ARGS

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[str] = mapped_column(String(20))  # pdf/docx/markdown/txt/html
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    md5: Mapped[str] = mapped_column(String(32), index=True)
    size: Mapped[int] = mapped_column(Integer, default=0)  # 字节
    # 状态机: pending -> parsing -> cleaning -> chunking -> embedding -> done | failed
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    char_count: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 清洗后字符数
    doc_meta: Mapped[dict | None] = mapped_column("meta", JSONAsText, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="noload",  # 列表/详情接口不需要分片正文，需要时用 /chunks 接口分页查
        passive_deletes=True,  # 删除依赖 DB 级 ondelete CASCADE，避免 ORM 全量加载
    )


class Chunk(Base):
    """分片文本：与 ChromaDB 中的向量通过 chroma_id 一一对应。"""

    __tablename__ = "chunks"
    __table_args__ = _MYSQL_TABLE_ARGS

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    chroma_id: Mapped[str] = mapped_column(String(64), unique=True)
    chunk_meta: Mapped[dict | None] = mapped_column("meta", JSONAsText, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    document: Mapped[Document] = relationship(back_populates="chunks")


class ChatSession(Base):
    """对话会话：不归属用户（开放使用），summary 为压缩记忆。"""

    __tablename__ = "chat_sessions"
    __table_args__ = _MYSQL_TABLE_ARGS

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), default="新对话")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)  # LLM 压缩的历史摘要
    # 已被摘要覆盖到的最大 message id（水位线，避免重复压缩）
    summarized_until_id: Mapped[int] = mapped_column(BigInteger, default=0)
    # 匿名访客标识(前端 localStorage UUID)：会话按访客隔离，互不可见
    visitor_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class Message(Base):
    """对话消息。tool_calls/sources 仅在相应角色时有值。"""

    __tablename__ = "messages"
    __table_args__ = _MYSQL_TABLE_ARGS

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20))  # user/assistant/tool
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)  # 深度思考过程
    tool_calls: Mapped[dict | None] = mapped_column(JSONAsText, nullable=True)
    tool_call_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sources: Mapped[list | None] = mapped_column(JSONAsText, nullable=True)  # 引用的分片信息
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    session: Mapped[ChatSession] = relationship(back_populates="messages")


class SystemPrompt(Base):
    """系统提示词（DB 化，管理后台可在线编辑，key 对应 prompts.py 中的默认值）。"""

    __tablename__ = "system_prompts"
    __table_args__ = _MYSQL_TABLE_ARGS

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), unique=True)
    content: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )


class AppConfig(Base):
    """运行时配置覆盖（热更新 .env 中的可调项，重启后自动重新应用）。"""

    __tablename__ = "app_configs"
    __table_args__ = _MYSQL_TABLE_ARGS

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), unique=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )


class StatsEvent(Base):
    """统计埋点事件：api 访问 / chat 问答(token+耗时) / embedding 入库消耗。"""

    __tablename__ = "stats_events"
    __table_args__ = _MYSQL_TABLE_ARGS

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(20), index=True)  # api/chat/embedding
    path: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
