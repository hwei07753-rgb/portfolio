"""
知识库相关 Schema

定义知识库条目创建、详情响应的请求/响应模型。
tags 字段在数据库中以 JSON 字符串存储，schema 层自动完成序列化/反序列化。
"""

import json
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class KnowledgeCreate(BaseModel):
    """知识库条目创建请求模型"""

    model_config = ConfigDict(str_strip_whitespace=True)

    category: str = Field(
        ...,
        max_length=50,
        description="分类：industry_practice/resume_template/optimization_case/jd_keyword",
    )
    title: str = Field(..., min_length=1, max_length=200, description="知识标题")
    content: str = Field(..., min_length=1, description="知识内容（Markdown 格式）")
    tags: list[str] | None = Field(None, description="额外标签列表")

    @field_validator("tags", mode="before")
    @classmethod
    def parse_tags(cls, v: str | list | None) -> list[str] | None:
        """兼容 JSON 字符串和列表两种输入格式"""
        if v is None:
            return v
        if isinstance(v, str):
            return json.loads(v)
        return v


class KnowledgeUpdate(BaseModel):
    """知识库条目更新请求模型（所有字段可选）"""

    model_config = ConfigDict(str_strip_whitespace=True)

    category: str | None = Field(None, max_length=50, description="分类")
    title: str | None = Field(None, min_length=1, max_length=200, description="知识标题")
    content: str | None = Field(None, min_length=1, description="知识内容")
    tags: list[str] | None = Field(None, description="额外标签列表")
    industry: str | None = Field(None, max_length=50, description="行业标签")
    job_title: str | None = Field(None, max_length=100, description="岗位标签")
    status: str | None = Field(None, description="状态：active/review_needed/archived")

    @field_validator("tags", mode="before")
    @classmethod
    def parse_tags(cls, v: str | list | None) -> list[str] | None:
        """兼容 JSON 字符串和列表两种输入格式"""
        if v is None:
            return v
        if isinstance(v, str):
            return json.loads(v)
        return v


class KnowledgeResponse(BaseModel):
    """知识库条目响应模型（支持从 SQLAlchemy ORM 自动转换）"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    category: str
    title: str
    content: str
    source: str = "system"
    resume_id: int | None = None
    industry: str | None = None
    job_title: str | None = None
    tags: list[str] | None = None
    status: str = "active"
    usage_count: int = 0
    effectiveness: float = 0.0
    created_at: datetime
    updated_at: datetime

    @field_validator("tags", mode="before")
    @classmethod
    def parse_tags(cls, v: str | list | None) -> list[str] | None:
        """将数据库中的 JSON 字符串解析为列表"""
        if v is None:
            return v
        if isinstance(v, str):
            return json.loads(v)
        return v
