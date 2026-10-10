"""
OCR 服务模块

使用 Qwen 多模态 API 实现图片文字识别功能。
支持 JPG/PNG 格式的简历图片，自动提取文本内容。
"""

import base64
import logging
from pathlib import Path
from typing import Optional

import httpx

from ..config import Settings

# 配置日志
logger = logging.getLogger(__name__)

# 支持的图片格式
SUPPORTED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
}

# 最大文件大小 (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024


class OCRError(Exception):
    """OCR 服务异常基类"""

    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class OCRImageError(OCRError):
    """图片格式或大小错误"""
    pass


class OCRAPIError(OCRError):
    """OCR API 调用错误"""
    pass


class OCRService:
    """OCR 服务

    使用 Qwen 多模态 API 进行图片文字识别。

    Attributes:
        base_url: API 基础 URL
        api_key: API 密钥
        model: 使用的多模态模型
        timeout: 请求超时时间（秒）
    """

    def __init__(self, config: Settings) -> None:
        """初始化 OCR 服务

        Args:
            config: 应用配置对象
        """
        self.base_url = config.ANTHROPIC_BASE_URL.rstrip("/")
        self.api_key = config.ANTHROPIC_AUTH_TOKEN
        self.model = config.ANTHROPIC_VL_MODEL  # 使用多模态视觉模型 (qwen-vl-max)
        self.timeout = config.API_TIMEOUT_MS / 1000

    def _validate_image(self, image_data: bytes, content_type: str) -> None:
        """验证图片格式和大小

        Args:
            image_data: 图片二进制数据
            content_type: 图片 MIME 类型

        Raises:
            OCRImageError: 图片格式不支持或大小超限
        """
        # 检查格式
        if content_type not in SUPPORTED_IMAGE_TYPES:
            supported = ", ".join(SUPPORTED_IMAGE_TYPES.keys())
            raise OCRImageError(
                f"不支持的图片格式: {content_type}，支持的格式: {supported}"
            )

        # 检查大小
        if len(image_data) > MAX_FILE_SIZE:
            size_mb = len(image_data) / (1024 * 1024)
            raise OCRImageError(
                f"图片大小 ({size_mb:.1f}MB) 超过限制 ({MAX_FILE_SIZE / (1024 * 1024):.0f}MB)"
            )

    def _image_to_base64(self, image_data: bytes) -> str:
        """将图片数据转换为 base64 编码

        Args:
            image_data: 图片二进制数据

        Returns:
            base64 编码的字符串
        """
        return base64.b64encode(image_data).decode("utf-8")

    def _build_messages(self, base64_image: str, content_type: str) -> list:
        """构建多模态消息

        Args:
            base64_image: base64 编码的图片
            content_type: 图片 MIME 类型

        Returns:
            消息列表
        """
        return [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{content_type};base64,{base64_image}"
                        }
                    },
                    {
                        "type": "text",
                        "text": "请识别这张图片中的所有文字内容。这是一份简历/文档，请按照原始格式输出文字，保持段落结构。只输出识别到的文字内容，不要添加任何解释或说明。"
                    }
                ]
            }
        ]

    async def recognize_text(
        self,
        image_data: bytes,
        content_type: str
    ) -> str:
        """识别图片中的文字

        Args:
            image_data: 图片二进制数据
            content_type: 图片 MIME 类型 (image/jpeg 或 image/png)

        Returns:
            识别出的文字内容

        Raises:
            OCRImageError: 图片格式或大小错误
            OCRAPIError: API 调用失败
        """
        # 验证图片
        self._validate_image(image_data, content_type)

        # 转换为 base64
        base64_image = self._image_to_base64(image_data)
        logger.info(f"开始 OCR 识别，图片大小: {len(image_data) / 1024:.1f}KB")

        # 构建请求
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        messages = self._build_messages(base64_image, content_type)
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "temperature": 0.1,  # 低温度以获得更稳定的识别结果
            "messages": messages
        }

        # 调用 API
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers, json=payload)

                if response.status_code != 200:
                    error_text = response.text
                    logger.error(
                        f"OCR API 返回非 200 状态码: {response.status_code}, "
                        f"响应: {error_text}"
                    )
                    raise OCRAPIError(
                        f"OCR API 调用失败: {response.status_code}",
                        status_code=response.status_code
                    )

                # 解析响应
                data = response.json()
                choices = data.get("choices", [])
                if not choices:
                    raise OCRAPIError("OCR API 返回空响应")

                content = choices[0].get("message", {}).get("content", "")
                if not content:
                    raise OCRAPIError("OCR API 未返回识别结果")

                logger.info(f"OCR 识别完成，识别文字长度: {len(content)} 字符")
                return content.strip()

        except httpx.TimeoutException as e:
            logger.error(f"OCR API 请求超时: {e}")
            raise OCRAPIError(f"OCR 请求超时，请稍后重试")

        except httpx.RequestError as e:
            logger.error(f"OCR API 请求错误: {e}")
            raise OCRAPIError(f"OCR 请求失败: {str(e)}")

        except OCRAPIError:
            raise

        except Exception as e:
            logger.error(f"OCR 识别异常: {e}")
            raise OCRAPIError(f"OCR 识别失败: {str(e)}")


# 全局 OCR 服务实例（延迟初始化）
_ocr_service: Optional[OCRService] = None


def get_ocr_service() -> OCRService:
    """获取 OCR 服务单例

    Returns:
        OCRService 实例
    """
    global _ocr_service
    if _ocr_service is None:
        from ..config import settings
        _ocr_service = OCRService(settings)
    return _ocr_service
