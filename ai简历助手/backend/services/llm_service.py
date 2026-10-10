"""
LLM 服务模块

封装大语言模型 API 调用，支持：
- OpenAI Chat Completions 兼容协议（DashScope Compatible Mode）
- 简历优化主流程
- 知识点自动提取
- 错误处理与重试机制
"""

import json
import asyncio
import logging
from typing import Optional

import httpx

from ..config import Settings

# 配置日志
logger = logging.getLogger(__name__)


class LLMServiceError(Exception):
    """LLM 服务异常基类"""

    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class LLMAPIError(LLMServiceError):
    """LLM API 调用错误"""
    pass


class LLMTimeoutError(LLMServiceError):
    """LLM 请求超时"""
    pass


class LLMResponseError(LLMServiceError):
    """LLM 响应解析错误"""
    pass


class LLMService:
    """大语言模型服务

    封装 OpenAI Chat Completions 兼容 API 调用（DashScope Compatible Mode），
    提供简历优化和知识提取功能。

    Attributes:
        base_url: API 基础 URL
        api_key: API 密钥
        default_model: 默认模型名称
        timeout: 请求超时时间（秒）
        max_retries: 最大重试次数
    """

    # 默认重试配置
    MAX_RETRIES = 3
    RETRY_DELAY_BASE = 1.0  # 基础重试延迟（秒）
    RETRY_DELAY_MAX = 10.0  # 最大重试延迟（秒）

    # 可重试的 HTTP 状态码
    RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

    def __init__(self, config: Settings) -> None:
        """初始化 LLM 服务

        Args:
            config: 应用配置对象
        """
        self.base_url = config.ANTHROPIC_BASE_URL.rstrip("/")
        self.api_key = config.ANTHROPIC_AUTH_TOKEN
        self.default_model = config.ANTHROPIC_MODEL
        self.timeout = config.API_TIMEOUT_MS / 1000  # 转换为秒
        self.max_retries = self.MAX_RETRIES
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建复用的 httpx 客户端

        Returns:
            httpx.AsyncClient 实例
        """
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        """关闭 httpx 客户端连接

        应在应用关闭时调用，释放连接资源。
        """
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def chat(
        self,
        messages: list,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 8192
    ) -> str:
        """调用 LLM API（OpenAI Chat Completions 兼容格式）

        使用 DashScope Compatible Mode 的 OpenAI 兼容接口。
        Base URL 示例: https://dashscope.aliyuncs.com/compatible-mode/v1

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            model: 模型名称，默认使用配置中的模型
            temperature: 温度参数，控制输出随机性 (0-1)
            max_tokens: 最大输出 token 数

        Returns:
            模型生成的文本内容

        Raises:
            LLMAPIError: API 调用失败
            LLMTimeoutError: 请求超时
            LLMResponseError: 响应解析失败
        """
        model = model or self.default_model
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages
        }

        last_error: Optional[LLMServiceError] = None
        client = await self._get_client()

        for attempt in range(self.max_retries + 1):
            try:
                logger.info(f"发送 LLM API 请求: {url}, 模型: {model}, 尝试: {attempt + 1}/{self.max_retries + 1}")
                response = await client.post(url, headers=headers, json=payload)
                logger.info(f"收到 LLM API 响应: 状态码={response.status_code}")

                # 检查响应状态
                if response.status_code != 200:
                    error_text = response.text
                    logger.warning(
                        f"LLM API 返回非 200 状态码: {response.status_code}, "
                        f"响应: {error_text}"
                    )

                    # 判断是否可重试
                    if response.status_code in self.RETRYABLE_STATUS_CODES:
                        last_error = LLMAPIError(
                            f"API 调用失败: {response.status_code} - {error_text}",
                            status_code=response.status_code
                        )
                        if attempt < self.max_retries:
                            delay = self._calculate_retry_delay(attempt)
                            logger.info(f"将在 {delay:.1f} 秒后重试 (第 {attempt + 1} 次)")
                            await asyncio.sleep(delay)
                            continue
                    else:
                        raise LLMAPIError(
                            f"API 调用失败: {response.status_code} - {error_text}",
                            status_code=response.status_code
                        )

                # 解析响应
                data = response.json()
                return self._extract_response_text(data)

            except httpx.TimeoutException as e:
                logger.warning(f"LLM API 请求超时: {e}")
                last_error = LLMTimeoutError(f"请求超时: {e}")
                if attempt < self.max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    logger.info(f"将在 {delay:.1f} 秒后重试 (第 {attempt + 1} 次)")
                    await asyncio.sleep(delay)
                    continue

            except httpx.RequestError as e:
                logger.error(f"LLM API 请求错误: {e}")
                last_error = LLMAPIError(f"请求错误: {e}")
                if attempt < self.max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    logger.info(f"将在 {delay:.1f} 秒后重试 (第 {attempt + 1} 次)")
                    await asyncio.sleep(delay)
                    continue

        # 所有重试都失败
        raise last_error

    def _extract_response_text(self, data: dict) -> str:
        """从 API 响应中提取文本内容

        支持 OpenAI Chat Completions 格式（DashScope 兼容模式）。

        Args:
            data: API 响应数据

        Returns:
            提取的文本内容

        Raises:
            LLMResponseError: 响应格式异常
        """
        try:
            # OpenAI Chat Completions 格式
            choices = data.get("choices", [])
            if not choices:
                raise LLMResponseError("响应内容为空")

            message = choices[0].get("message", {})
            content = message.get("content", "")

            if not content:
                raise LLMResponseError("响应中未找到文本内容")

            return content

        except (KeyError, TypeError, IndexError) as e:
            logger.error(f"解析 LLM 响应失败: {e}, 响应数据: {data}")
            raise LLMResponseError(f"响应解析失败: {e}")

    def _calculate_retry_delay(self, attempt: int) -> float:
        """计算重试延迟时间（指数退避）

        Args:
            attempt: 当前重试次数 (从 0 开始)

        Returns:
            延迟时间（秒）
        """
        delay = min(
            self.RETRY_DELAY_BASE * (2 ** attempt),
            self.RETRY_DELAY_MAX
        )
        return delay

    async def optimize_resume(
        self,
        original_text: str,
        jd: str,
        city: Optional[str] = None,
        salary: Optional[str] = None,
        details: Optional[str] = None,
        knowledge_context: Optional[str] = None,
        strength: int = 3
    ) -> dict:
        """简历优化主流程

        Args:
            original_text: 原始简历文本
            jd: 目标岗位 JD
            city: 目标城市
            salary: 期望薪资
            details: 补充信息
            knowledge_context: 知识库上下文

        Returns:
            dict 包含:
            - optimized_html: 优化后的 HTML
            - optimization_score: 优化分数 (0-100)
            - changes_summary: 修改摘要列表
            - pros: 优点列表
            - cons: 缺点列表
            - star_rewrites: STAR 重写数
            - quantifications: 量化数据数
            - keywords_matched: 关键词匹配数
        """
        system_prompt = self._build_system_prompt(knowledge_context)
        user_prompt = self._build_optimize_prompt(
            original_text, jd, city, salary, details, strength
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        logger.info(f"调用 LLM 优化简历，模型: {self.default_model}, 超时: {self.timeout}s")
        result = await self.chat(messages, temperature=0.7)
        logger.info(f"LLM 响应长度: {len(result)} 字符")
        return self._parse_optimize_response(result)

    def _parse_optimize_response(self, raw: str) -> dict:
        """解析 LLM 优化响应，提取结构化数据

        尝试从 LLM 响应中解析 JSON 结构。若解析失败，
        将整段响应作为 HTML 返回，其余字段使用默认值。

        Args:
            raw: LLM 原始响应文本

        Returns:
            结构化的优化结果字典
        """
        default_stats = {
            "optimization_score": 75.0,
            "changes_summary": ["已完成简历优化"],
            "pros": ["已完成基础优化"],
            "cons": ["建议根据目标岗位进一步调整"],
            "star_rewrites": 0,
            "quantifications": 0,
            "keywords_matched": 0,
        }

        # 尝试从响应中提取 JSON 块
        json_str = None
        if "```json" in raw:
            json_str = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            json_str = raw.split("```")[1].split("```")[0].strip()

        if json_str:
            try:
                data = json.loads(json_str)
                return {
                    "optimized_html": data.get("optimized_html", ""),
                    "optimization_score": data.get("optimization_score", 75.0),
                    "changes_summary": data.get("changes_summary", default_stats["changes_summary"]),
                    "pros": data.get("pros", default_stats["pros"]),
                    "cons": data.get("cons", default_stats["cons"]),
                    "star_rewrites": data.get("star_rewrites", 0),
                    "quantifications": data.get("quantifications", 0),
                    "keywords_matched": data.get("keywords_matched", 0),
                }
            except json.JSONDecodeError:
                logger.warning("JSON 解析失败，尝试直接解析")

        # 回退：尝试将整段响应直接解析为 JSON
        try:
            data = json.loads(raw.strip())
            return {
                "optimized_html": data.get("optimized_html", ""),
                "optimization_score": data.get("optimization_score", 75.0),
                "changes_summary": data.get("changes_summary", default_stats["changes_summary"]),
                "pros": data.get("pros", default_stats["pros"]),
                "cons": data.get("cons", default_stats["cons"]),
                "star_rewrites": data.get("star_rewrites", 0),
                "quantifications": data.get("quantifications", 0),
                "keywords_matched": data.get("keywords_matched", 0),
            }
        except json.JSONDecodeError:
            pass

        # 最终回退：将整段响应当作 HTML
        logger.warning("LLM 响应非 JSON 格式，将整段作为 HTML 返回")
        return {
            "optimized_html": raw,
            **default_stats,
        }

    async def extract_knowledge(
        self,
        original: str,
        optimized: str,
        jd: str,
        rating: Optional[int] = None
    ) -> dict:
        """知识点提取

        从简历优化的前后对比中提取可复用的知识点。

        Args:
            original: 原始简历文本
            optimized: 优化后简历文本
            jd: 目标岗位 JD
            rating: 用户评分 (1-5)

        Returns:
            提取的知识点字典
        """
        # 默认空结构
        empty_result = {
            "patterns": [],
            "jd_keywords": [],
            "industry": "unknown",
            "job_level": "mid"
        }

        prompt = self._build_knowledge_prompt(original, optimized, jd, rating)

        messages = [
            {"role": "user", "content": prompt}
        ]

        try:
            result = await self.chat(messages, temperature=0.3)
        except (LLMAPIError, LLMTimeoutError, LLMResponseError) as e:
            logger.error(f"知识提取 LLM 调用失败: {e}")
            return empty_result
        except Exception as e:
            logger.error(f"知识提取调用异常: {e}")
            return empty_result

        # 解析 JSON 响应
        try:
            # 尝试提取 JSON 块（可能被 markdown 代码块包裹）
            json_str = result
            if "```json" in result:
                json_str = result.split("```json")[1].split("```")[0].strip()
            elif "```" in result:
                json_str = result.split("```")[1].split("```")[0].strip()

            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"解析知识提取结果失败: {e}, 原始响应: {result}")
            return empty_result

    async def chat_conversation(
        self,
        system_prompt: str,
        conversation_history: list,
        user_message: str,
        temperature: float = 0.7
    ) -> str:
        """多轮对话

        用于 AI 预检和对话微调功能。

        Args:
            system_prompt: 系统提示词
            conversation_history: 对话历史
            user_message: 用户新消息

        Returns:
            AI 回复内容
        """
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_message})

        return await self.chat(messages, temperature=temperature)

    def _build_system_prompt(self, knowledge_context: Optional[str] = None) -> str:
        """构建系统提示词

        Args:
            knowledge_context: 知识库上下文

        Returns:
            系统提示词
        """
        base_prompt = """你是一位拥有 15 年经验的资深简历优化顾问，精通以下领域：
- 各行业（互联网/金融/医疗/教育/制造）的简历写作规范
- ATS（Applicant Tracking System）简历筛选算法的关键词匹配逻辑
- STAR 原则（Situation-Task-Action-Result）的深度应用
- 量化数据的提炼与包装技巧
- 不同职级（初级/中级/高级/管理层）的简历差异化策略

你的核心原则：
1. 真实性：绝不虚构经历，只优化表达方式
2. 针对性：根据目标 JD 定制优化方向
3. 数据化：尽可能将模糊描述转化为量化数据
4. 结构化：输出清晰、层次分明的简历结构
5. ATS 友好：确保关键词密度和格式兼容主流 ATS 系统
6. 隐式优化：STAR 原则等写作技巧必须内化到文字中，严禁在简历正文中出现任何方法论标记（如 STAR、S/T/A/R 等标签）"""

        if knowledge_context:
            base_prompt += f"""

## 参考知识库（以下是与当前优化任务相关的历史最佳实践）
{knowledge_context}"""

        return base_prompt

    def _build_optimize_prompt(
        self,
        original_text: str,
        jd: str,
        city: Optional[str] = None,
        salary: Optional[str] = None,
        details: Optional[str] = None,
        strength: int = 3
    ) -> str:
        """构建优化任务提示词

        Args:
            original_text: 原始简历文本
            jd: 目标岗位 JD
            city: 目标城市
            salary: 期望薪资
            details: 补充信息
            strength: 优化强度 (1-5)，1=轻度润色，5=深度重构

        Returns:
            优化任务提示词
        """
        # 优化强度描述
        strength_desc = {
            1: "轻度润色：仅修正语法错误、调整格式，保持原文风格和内容不变",
            2: "偏轻优化：修正错误、优化措辞，小幅调整结构",
            3: "标准优化：使用 STAR 原则重写、补充量化数据、匹配 JD 关键词",
            4: "偏强优化：深度重写工作经历、大幅优化结构、强化关键词匹配",
            5: "深度重构：完全重新组织简历结构、重写所有内容、最大化 ATS 友好度",
        }
        strength_text = strength_desc.get(strength, strength_desc[3])

        prompt = f"""请对以下简历进行优化。

## 优化强度
{strength_text}

## 原始简历内容
{original_text}

## 目标岗位 JD
{jd or "未提供"}

## 求职意向
- 目标城市：{city or "未指定"}
- 期望薪资：{salary or "未指定"}

## 补充信息
{details or "无"}

## 优化要求
1. 使用 STAR 原则重写每段工作/项目经历
2. 为每段经历补充至少 1 个量化数据（百分比、金额、数量等）
3. 提取 JD 中的核心关键词，在简历中自然融入
4. 个人信息模块：姓名、联系方式、求职意向
5. 教育背景模块：学校、专业、学历、时间
6. 工作/项目经历模块：STAR 格式，倒序排列
7. 技能模块：与 JD 匹配的技能优先展示
8. 输出为纯 HTML，白底黑字，适合 A4 打印
9. 使用语义化 HTML 标签（h1/h2/h3/p/ul/li）
10. 不要使用任何 CSS 框架，使用内联样式控制排版
11. 保持信息真实性，不虚构经历
12. STAR 原则是内部写作方法论，严禁在简历正文中出现任何 STAR 相关标记，包括但不限于：（STAR）、（S/T）、（A）、（R）、"情境与任务"、"行动"、"结果"等标签文字。经历描述应直接以自然段落呈现，不要用 STAR 字母分段

请以 JSON 格式返回结果，包含以下字段：
```json
{{
  "optimized_html": "完整的优化后 HTML 代码",
  "optimization_score": 85.0,
  "changes_summary": ["修改项1", "修改项2", "..."],
  "pros": ["优点1", "优点2", "..."],
  "cons": ["改进建议1", "改进建议2", "..."],
  "star_rewrites": 3,
  "quantifications": 5,
  "keywords_matched": 8
}}
```

字段说明：
- optimized_html: 完整的 HTML 简历代码
- optimization_score: 优化质量评分 (0-100)
- changes_summary: 具体的修改项列表（3-8 条）
- pros: 优化后的优点（3-5 条）
- cons: 仍需改进的地方（2-4 条）
- star_rewrites: 使用 STAR 原则重写的段落数
- quantifications: 补充的量化数据个数
- keywords_matched: 匹配的 JD 关键词数量"""

        return prompt

    def _build_knowledge_prompt(
        self,
        original: str,
        optimized: str,
        jd: str,
        rating: Optional[int] = None
    ) -> str:
        """构建知识提取提示词

        Args:
            original: 原始简历文本
            optimized: 优化后简历文本
            jd: 目标岗位 JD
            rating: 用户评分

        Returns:
            知识提取提示词
        """
        prompt = f"""分析以下简历优化的前后对比，提取可复用的优化知识点：

## 原始简历
{original[:2000]}

## 优化后简历
{optimized[:2000]}

## 目标 JD
{jd[:1000]}

## 用户反馈评分
{rating}/5

请以 JSON 格式返回提取的知识点：
```json
{{
  "patterns": [
    {{
      "type": "quantification|star_rewrite|keyword_match|structure",
      "title": "知识点标题",
      "content": "详细描述",
      "before_example": "优化前的表述",
      "after_example": "优化后的表述",
      "tags": ["标签1", "标签2"]
    }}
  ],
  "jd_keywords": ["关键词1", "关键词2"],
  "industry": "推断的行业",
  "job_level": "junior|mid|senior|lead"
}}
```

注意：
1. patterns 数组包含 1-5 个最有价值的优化模式
2. jd_keywords 提取 JD 中的核心关键词（最多 10 个）
3. industry 根据 JD 和简历内容推断所属行业
4. job_level 推断岗位级别
5. 确保返回有效的 JSON 格式"""

        return prompt


# 全局 LLM 服务实例（延迟初始化）
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """获取 LLM 服务单例

    Returns:
        LLMService 实例
    """
    global _llm_service
    if _llm_service is None:
        from ..config import settings
        _llm_service = LLMService(settings)
    return _llm_service
