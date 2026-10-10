"""
配置管理模块

读取 settings.json 配置文件，支持环境变量覆盖。
提供全局 settings 单例供其他模块使用。
"""

import json
import os
from pathlib import Path
from typing import Optional


class Settings:
    """应用配置类

    优先级：环境变量 > settings.json > 默认值
    """

    def __init__(self, settings_path: Optional[str] = None) -> None:
        """初始化配置

        Args:
            settings_path: settings.json 文件路径，默认为项目根目录下的 settings.json
        """
        if settings_path is None:
            # 从当前文件向上查找项目根目录的 settings.json
            root_dir = Path(__file__).parent.parent
            settings_path = str(root_dir / "settings.json")

        config = self._load_settings(settings_path)
        env = config.get("env", {})

        # LLM API 配置 - settings.json 优先，环境变量作为后备
        # 这样确保项目配置不被系统环境变量覆盖
        self.ANTHROPIC_AUTH_TOKEN: str = env.get(
            "ANTHROPIC_AUTH_TOKEN",
            os.getenv("ANTHROPIC_AUTH_TOKEN", "")
        )
        self.ANTHROPIC_BASE_URL: str = env.get(
            "ANTHROPIC_BASE_URL",
            os.getenv("ANTHROPIC_BASE_URL", "")
        )
        self.ANTHROPIC_MODEL: str = env.get(
            "ANTHROPIC_MODEL",
            os.getenv("ANTHROPIC_MODEL", "")
        )
        self.ANTHROPIC_VL_MODEL: str = env.get(
            "ANTHROPIC_VL_MODEL",
            os.getenv("ANTHROPIC_VL_MODEL", "qwen-vl-max")
        )
        self.ANTHROPIC_DEFAULT_SONNET_MODEL: str = env.get(
            "ANTHROPIC_DEFAULT_SONNET_MODEL",
            os.getenv("ANTHROPIC_DEFAULT_SONNET_MODEL", "")
        )
        self.ANTHROPIC_DEFAULT_OPUS_MODEL: str = env.get(
            "ANTHROPIC_DEFAULT_OPUS_MODEL",
            os.getenv("ANTHROPIC_DEFAULT_OPUS_MODEL", "")
        )
        self.ANTHROPIC_DEFAULT_HAIKU_MODEL: str = env.get(
            "ANTHROPIC_DEFAULT_HAIKU_MODEL",
            os.getenv("ANTHROPIC_DEFAULT_HAIKU_MODEL", "")
        )
        self.API_TIMEOUT_MS: int = int(env.get(
            "API_TIMEOUT_MS",
            os.getenv("API_TIMEOUT_MS", "300000")
        ))

        # JWT 认证配置
        self.JWT_SECRET_KEY: str = os.getenv(
            "JWT_SECRET_KEY",
            env.get("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        )
        self.JWT_ALGORITHM: str = os.getenv(
            "JWT_ALGORITHM",
            env.get("JWT_ALGORITHM", "HS256")
        )
        self.JWT_EXPIRE_MINUTES: int = int(os.getenv(
            "JWT_EXPIRE_MINUTES",
            env.get("JWT_EXPIRE_MINUTES", "1440")
        ))

        # 数据库配置
        self.DATABASE_URL: str = os.getenv(
            "DATABASE_URL",
            env.get("DATABASE_URL", "sqlite:///./ai_resume_optimizer.db")
        )

        # 文件上传配置
        self.MAX_UPLOAD_SIZE_MB: int = int(os.getenv(
            "MAX_UPLOAD_SIZE_MB",
            env.get("MAX_UPLOAD_SIZE_MB", "10")
        ))
        self.ALLOWED_EXTENSIONS: list[str] = env.get(
            "ALLOWED_EXTENSIONS",
            ["jpg", "jpeg", "png"]
        )

        # 点数系统配置
        self.NEW_USER_GIFT_POINTS: int = int(os.getenv(
            "NEW_USER_GIFT_POINTS",
            env.get("NEW_USER_GIFT_POINTS", "3")
        ))
        self.POINTS_PER_OPTIMIZATION: int = int(os.getenv(
            "POINTS_PER_OPTIMIZATION",
            env.get("POINTS_PER_OPTIMIZATION", "1")
        ))

    @staticmethod
    def _load_settings(settings_path: str) -> dict:
        """加载 settings.json 配置文件

        Args:
            settings_path: 配置文件路径

        Returns:
            解析后的配置字典，文件不存在时返回空字典
        """
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"[Warning] Settings file not found: {settings_path}")
            return {}
        except json.JSONDecodeError as e:
            print(f"[Error] Invalid JSON in settings file: {e}")
            return {}


# 全局配置实例
settings = Settings()
