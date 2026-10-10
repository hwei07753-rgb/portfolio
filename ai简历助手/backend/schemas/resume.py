"""
简历相关 Schema

定义简历创建、详情响应、列表分页、用户反馈的请求/响应模型。
"""

import json
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ResumeCreate(BaseModel):
    """简历创建/上传请求模型"""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(..., min_length=1, max_length=100, description="简历标题")
    original_text: str = Field(..., min_length=1, description="原始简历文本")
    target_city: str | None = Field(None, max_length=50, description="目标城市")
    target_salary: str | None = Field(None, max_length=50, description="期望薪资")
    target_jd: str | None = Field(None, description="目标岗位 JD")
    extra_details: str | None = Field(None, description="补充细节")
    tags: list[str] | None = Field(None, description="标签列表")


class ResumeUpdate(BaseModel):
    """简历更新请求模型（部分更新）"""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(None, min_length=1, max_length=100, description="简历标题")
    original_text: str | None = Field(None, min_length=1, description="原始简历文本")
    target_city: str | None = Field(None, max_length=50, description="目标城市")
    target_salary: str | None = Field(None, max_length=50, description="期望薪资")
    target_jd: str | None = Field(None, description="目标岗位 JD")
    extra_details: str | None = Field(None, description="补充细节")
    tags: list[str] | None = Field(None, description="标签列表")


class ResumeResponse(BaseModel):
    """简历详情响应模型（支持从 SQLAlchemy ORM 自动转换）"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    original_text: str
    optimized_text: str | None = None
    target_city: str | None = None
    target_salary: str | None = None
    target_jd: str | None = None
    extra_details: str | None = None
    tags: list[str] | None = None
    model_used: str | None = None
    status: str = "pending"
    version: int = 1
    parent_id: int | None = None
    optimization_score: float | None = None
    star_rewrites: int = 0
    quantifications: int = 0
    keywords_matched: int = 0
    created_at: datetime

    @field_validator("tags", mode="before")
    @classmethod
    def parse_tags(cls, v):
        """将数据库中的 JSON 字符串转换为列表"""
        if v is None or isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        return v


class ResumeListResponse(BaseModel):
    """简历列表响应模型（分页）"""

    total: int
    page: int
    page_size: int
    items: list[ResumeResponse]


class FeedbackCreate(BaseModel):
    """用户反馈创建请求模型"""

    model_config = ConfigDict(str_strip_whitespace=True)

    rating: int = Field(..., ge=1, le=5, description="评分（1-5 星）")
    comment: str | None = Field(None, max_length=1000, description="文字反馈")


class FeedbackResponse(BaseModel):
    """用户反馈响应模型"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    resume_id: int
    rating: int
    comment: str | None = None
    created_at: datetime
