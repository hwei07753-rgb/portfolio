"""
文本清洗工具模块

提供 HTML 消毒功能，用于清洗 LLM 返回的 HTML 内容，
防止存储型 XSS 攻击。

策略：白名单机制 — 只保留安全的 HTML 标签和属性，移除一切潜在危险内容。
"""

import re
from html import unescape


# 允许的 HTML 标签（简历内容安全子集）
ALLOWED_TAGS = {
    # 文档结构
    "html", "head", "body", "meta", "title",
    # 标题
    "h1", "h2", "h3", "h4", "h5", "h6",
    # 文本
    "p", "br", "hr", "span", "div", "pre", "blockquote",
    # 格式化
    "strong", "b", "em", "i", "u", "s", "del", "mark", "small", "sub", "sup",
    # 列表
    "ul", "ol", "li", "dl", "dt", "dd",
    # 表格
    "table", "thead", "tbody", "tfoot", "tr", "th", "td", "caption", "colgroup", "col",
    # 链接（仅 http/https）
    "a",
    # 图片
    "img",
    # 区块
    "section", "article", "header", "footer", "nav", "main", "aside",
    # 其他
    "abbr", "address", "code", "kbd", "var", "samp", "time",
}

# 允许的属性（按标签分组）
ALLOWED_ATTRS = {
    "a": {"href", "title", "name", "id"},
    "img": {"src", "alt", "width", "height", "title"},
    "td": {"colspan", "rowspan", "headers"},
    "th": {"colspan", "rowspan", "scope", "headers"},
    "col": {"span"},
    "colgroup": {"span"},
    "meta": {"charset", "name", "content", "http-equiv"},
    "*": {"class", "id", "dir", "lang", "title", "role"},
}

# 危险的 URL 协议
DANGEROUS_PROTOCOLS = re.compile(
    r"""(javascript|vbscript|data|file|ftp):""",
    re.IGNORECASE,
)


def _is_safe_url(url: str) -> bool:
    """检查 URL 是否使用安全协议"""
    if not url:
        return True
    url = url.strip().lower()
    if url.startswith(("#", "/")):
        return True
    if url.startswith(("http://", "https://", "mailto:", "tel:")):
        return True
    return not DANGEROUS_PROTOCOLS.search(url)


def _clean_tag_attrs(tag_html: str, tag_name: str) -> str:
    """清洗单个标签的属性，只保留白名单内的属性

    Args:
        tag_html: 完整的标签 HTML 字符串，如 '<a href="..." onclick="...">'
        tag_name: 标签名（小写）

    Returns:
        清洗后的标签 HTML
    """
    allowed = ALLOWED_ATTRS.get(tag_name, set()) | ALLOWED_ATTRS["*"]

    def _attr_filter(match: re.Match) -> str:
        attr_name = match.group(1).lower().strip()
        if attr_name not in allowed:
            return ""
        # 检查属性值安全性
        attr_value = match.group(3) or ""
        if attr_name in ("href", "src") and not _is_safe_url(attr_value):
            return ""
        return match.group(0)

    # 匹配属性：name="value" 或 name='value' 或 name=value
    cleaned = re.sub(
        r"""(\w[\w-]*)(\s*=\s*(?:"([^"]*)"|'([^']*)'|(\S+)))?""",
        _attr_filter,
        tag_html,
    )
    # 清除多余空格
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _strip_markdown_code_blocks(text: str) -> str:
    """剥离 LLM 输出中的 markdown 代码块标记

    LLM 经常将 HTML 包裹在 ```html ... ``` 中，此函数去除这些标记。

    Args:
        text: 可能包含 markdown 代码块标记的文本

    Returns:
        去除代码块标记后的纯内容
    """
    text = text.strip()
    # 匹配 ```html 或 ``` 开头，``` 结尾的代码块
    pattern = r"^```(?:html|HTML)?\s*\n?(.*?)\n?\s*```$"
    match = re.match(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


def sanitize_html(html: str) -> str:
    """消毒 HTML 内容

    使用白名单策略，只保留安全的 HTML 标签和属性。
    适用于清洗 LLM 返回的简历 HTML，防止存储型 XSS。

    处理流程：
    0. 剥离 markdown 代码块标记（```html ... ```）
    1. 移除空字节（防止空字节注入绕过）
    2. HTML 实体解码（防止编码绕过）
    3. 移除 <script>、<style>、<iframe> 等危险标签及内容
    4. 移除所有 on* 事件属性
    5. 移除 javascript: 等危险协议
    6. 移除不在白名单中的标签（保留内容）
    7. 清洗白名单标签的属性

    Args:
        html: 原始 HTML 字符串

    Returns:
        消毒后的安全 HTML 字符串
    """
    if not html or not isinstance(html, str):
        return html or ""

    # 0. 剥离 markdown 代码块标记（LLM 常将 HTML 包裹在 ```html ... ``` 中）
    html = _strip_markdown_code_blocks(html)

    # 1. 移除空字节（防止空字节注入绕过）
    html = html.replace("\x00", "")

    # 2. 解码 HTML 实体，防止 &#106;avascript: 等编码绕过
    html = unescape(html)

    # 3. 移除危险标签及其全部内容
    # 注意：meta 不在危险列表中，它在 ALLOWED_TAGS 中，通过白名单机制处理
    html = re.sub(
        r"<\s*(script|style|iframe|object|embed|applet|form|input|button"
        r"|textarea|select|link|base|svg|math|canvas|audio|video"
        r"|source|track|map|area|datalist|output|progress|meter"
        r"|template|slot|portal|fencedframe)\b[^>]*>.*?<\s*/\s*\1\s*>",
        "",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    # 自闭合的危险标签
    html = re.sub(
        r"<\s*(script|style|iframe|object|embed|applet|form|input|button"
        r"|textarea|select|link|base|svg|math|canvas|audio|video"
        r"|source|track|map|area|datalist|output|progress|meter"
        r"|template|slot|portal|fencedframe)\b[^>]*/?\s*>",
        "",
        html,
        flags=re.IGNORECASE,
    )

    # 4. 移除所有 on* 事件处理器属性（防止 <img onerror=...> 等）
    html = re.sub(
        r"""\s+on\w+\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]*)""",
        "",
        html,
        flags=re.IGNORECASE,
    )

    # 5. 移除 javascript: 等危险协议
    html = re.sub(
        r"""(href|src|action|formaction|data|codebase)\s*=\s*"""
        r"""(?:"(javascript|vbscript|data|file|ftp)[^"]*"|"""
        r"""'(javascript|vbscript|data|file|ftp)[^']*')""",
        r'\1=""',
        html,
        flags=re.IGNORECASE,
    )

    # 6. 移除不在白名单中的标签，保留标签内容
    def _strip_tag(match: re.Match) -> str:
        closing = match.group(1)  # '/' 表示闭合标签
        tag_name = match.group(2).lower().strip()
        rest = match.group(3) or ""

        if tag_name in ALLOWED_TAGS:
            if closing:
                return f"</{tag_name}>"
            cleaned = _clean_tag_attrs(rest, tag_name)
            return f"<{tag_name}{cleaned}>"
        # 不在白名单中，移除标签但保留内容（由调用方处理）
        return ""

    html = re.sub(
        r"<(/?)(\w[\w-]*)((?:\s+[^>]*)?)\s*/?>",
        _strip_tag,
        html,
        flags=re.IGNORECASE,
    )

    # 7. 移除 HTML 注释（可能包含条件执行代码）
    html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)

    # 8. 保留 <!DOCTYPE> 声明（对编码和渲染很重要，不做移除）

    # 9. 清除多余空白
    html = re.sub(r"\n\s*\n\s*\n+", "\n\n", html)

    return html.strip()


def clean_text(text: str) -> str:
    """清洗纯文本，移除所有 HTML 标签

    用于处理不需要 HTML 格式的文本字段。

    Args:
        text: 原始文本

    Returns:
        纯文本字符串
    """
    if not text or not isinstance(text, str):
        return text or ""
    return re.sub(r"<[^>]+>", "", text).strip()
