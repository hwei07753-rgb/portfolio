"""
HTML 消毒器单元测试

验证 sanitize_html 函数能正确防御各种 XSS 攻击向量。
"""

import pytest
from backend.utils.text_cleaner import sanitize_html, clean_text


class TestSanitizeHtml:
    """sanitize_html 函数测试"""

    def test_safe_html_preserved(self):
        """安全的简历 HTML 应被保留"""
        html = """
        <h1>张三</h1>
        <h2>工作经历</h2>
        <p>负责前端开发工作</p>
        <ul>
            <li>优化性能提升 50%</li>
            <li>主导重构核心模块</li>
        </ul>
        <table>
            <tr><th>技能</th><th>熟练度</th></tr>
            <tr><td>Python</td><td>精通</td></tr>
        </table>
        """
        result = sanitize_html(html)
        assert "<h1>张三</h1>" in result
        assert "<h2>工作经历</h2>" in result
        assert "<li>优化性能提升 50%</li>" in result
        assert "<td>Python</td>" in result

    def test_script_tag_stripped(self):
        """<script> 标签应被完全移除"""
        html = '<p>正常内容</p><script>alert("XSS")</script><p>后面内容</p>'
        result = sanitize_html(html)
        assert "<script>" not in result
        assert "alert" not in result
        assert "正常内容" in result
        assert "后面内容" in result

    def test_script_tag_with_attributes(self):
        """带属性的 <script> 标签应被移除"""
        html = '<script type="text/javascript" src="evil.js">alert(1)</script>'
        result = sanitize_html(html)
        assert "<script" not in result
        assert "alert" not in result

    def test_event_handler_stripped(self):
        """on* 事件处理器应被移除"""
        html = '<img src="photo.jpg" onerror="alert(1)" alt="照片">'
        result = sanitize_html(html)
        assert "onerror" not in result
        assert "alert" not in result
        assert "img" in result
        assert "photo.jpg" in result

    def test_onclick_stripped(self):
        """onclick 事件处理器应被移除"""
        html = '<div onclick="alert(1)">点击我</div>'
        result = sanitize_html(html)
        assert "onclick" not in result
        assert "alert" not in result
        assert "点击我" in result

    def test_onload_stripped(self):
        """onload 事件处理器应被移除"""
        html = '<body onload="alert(1)"><p>内容</p></body>'
        result = sanitize_html(html)
        assert "onload" not in result
        assert "alert" not in result

    def test_javascript_protocol_stripped(self):
        """javascript: 协议应被移除"""
        html = '<a href="javascript:alert(1)">点击</a>'
        result = sanitize_html(html)
        assert "javascript:" not in result
        assert "alert" not in result
        assert "点击" in result

    def test_vbscript_protocol_stripped(self):
        """vbscript: 协议应被移除"""
        html = '<a href="vbscript:MsgBox(1)">点击</a>'
        result = sanitize_html(html)
        assert "vbscript:" not in result

    def test_data_protocol_stripped(self):
        """data: 协议应被移除"""
        html = '<a href="data:text/html,<script>alert(1)</script>">点击</a>'
        result = sanitize_html(html)
        assert "data:" not in result

    def test_safe_url_preserved(self):
        """安全的 URL 应被保留"""
        html = '<a href="https://example.com">链接</a>'
        result = sanitize_html(html)
        assert "https://example.com" in result

    def test_relative_url_preserved(self):
        """相对 URL 应被保留"""
        html = '<a href="/page">链接</a>'
        result = sanitize_html(html)
        assert "/page" in result

    def test_mailto_preserved(self):
        """mailto: 协议应被保留"""
        html = '<a href="mailto:test@example.com">邮件</a>'
        result = sanitize_html(html)
        assert "mailto:test@example.com" in result

    def test_iframe_stripped(self):
        """<iframe> 标签应被完全移除"""
        html = '<p>内容</p><iframe src="evil.html"></iframe>'
        result = sanitize_html(html)
        assert "iframe" not in result
        assert "evil.html" not in result
        assert "内容" in result

    def test_style_tag_stripped(self):
        """<style> 标签应被完全移除"""
        html = '<style>body{background:red}</style><p>内容</p>'
        result = sanitize_html(html)
        assert "<style>" not in result
        assert "background" not in result
        assert "内容" in result

    def test_form_tag_stripped(self):
        """<form> 标签应被完全移除"""
        html = '<form action="evil.php"><input name="x"><button>提交</button></form>'
        result = sanitize_html(html)
        assert "<form" not in result
        assert "<input" not in result
        assert "<button" not in result

    def test_svg_stripped(self):
        """<svg> 标签应被完全移除"""
        html = '<svg onload="alert(1)"><circle r="10"/></svg><p>内容</p>'
        result = sanitize_html(html)
        assert "<svg" not in result
        assert "alert" not in result

    def test_disallowed_tag_content_preserved(self):
        """不在白名单中的标签应被移除但保留内容"""
        html = '<custom-tag>保留的内容</custom-tag>'
        result = sanitize_html(html)
        assert "<custom-tag" not in result
        assert "保留的内容" in result

    def test_html_comment_stripped(self):
        """HTML 注释应被移除"""
        html = '<p>内容</p><!-- 注释内容 --><p>后面</p>'
        result = sanitize_html(html)
        assert "<!--" not in result
        assert "注释内容" not in result
        assert "内容" in result
        assert "后面" in result

    def test_doctype_preserved(self):
        """<!DOCTYPE> 声明应被保留（对编码和渲染很重要）"""
        html = '<!DOCTYPE html><html><body><p>内容</p></body></html>'
        result = sanitize_html(html)
        assert "<!DOCTYPE html>" in result
        assert "内容" in result

    def test_meta_charset_preserved(self):
        """<meta charset> 标签应被保留（确保编码正确）"""
        html = '<html><head><meta charset="UTF-8"></head><body><p>内容</p></body></html>'
        result = sanitize_html(html)
        assert 'charset="UTF-8"' in result
        assert "内容" in result

    def test_meta_other_attrs_preserved(self):
        """<meta> 标签的其他允许属性应被保留"""
        html = '<meta name="viewport" content="width=device-width"><p>内容</p>'
        result = sanitize_html(html)
        assert 'name="viewport"' in result
        assert 'content="width=device-width"' in result

    def test_encoded_script_stripped(self):
        """HTML 实体编码的 <script> 应被移除"""
        # &#106;avascript: = javascript:
        html = '<a href="&#106;avascript:alert(1)">点击</a>'
        result = sanitize_html(html)
        assert "javascript:" not in result
        assert "alert" not in result

    def test_nested_script_stripped(self):
        """嵌套的 <script> 标签应被移除"""
        html = '<scr<script>ipt>alert(1)</scr</script>ipt>'
        result = sanitize_html(html)
        assert "alert" not in result

    def test_null_byte_injection(self):
        """空字节注入应被处理"""
        html = '<scr\x00ipt>alert(1)</script>'
        result = sanitize_html(html)
        assert "alert" not in result

    def test_empty_input(self):
        """空输入应返回空字符串"""
        assert sanitize_html("") == ""
        assert sanitize_html(None) == ""

    def test_class_attribute_preserved(self):
        """class 属性应被保留"""
        html = '<p class="resume-section">内容</p>'
        result = sanitize_html(html)
        assert 'class="resume-section"' in result

    def test_table_colspan_preserved(self):
        """表格 colspan/rowspan 属性应被保留"""
        html = '<td colspan="2" rowspan="3">内容</td>'
        result = sanitize_html(html)
        assert 'colspan="2"' in result
        assert 'rowspan="3"' in result

    def test_img_alt_preserved(self):
        """img 的 alt 属性应被保留"""
        html = '<img src="photo.jpg" alt="个人照片" width="100">'
        result = sanitize_html(html)
        assert 'alt="个人照片"' in result
        assert 'src="photo.jpg"' in result

    def test_multiple_attack_vectors(self):
        """同时包含多种攻击向量的 HTML"""
        html = """
        <h1>简历标题</h1>
        <script>alert("XSS1")</script>
        <p onclick="alert('XSS2')">正常内容</p>
        <a href="javascript:alert('XSS3')">链接</a>
        <img src="x" onerror="alert('XSS4')">
        <iframe src="evil.html"></iframe>
        <style>body{display:none}</style>
        <svg onload="alert('XSS5')"></svg>
        <p>结尾内容</p>
        """
        result = sanitize_html(html)
        assert "alert" not in result
        assert "XSS" not in result
        assert "javascript:" not in result
        assert "iframe" not in result
        assert "<style>" not in result
        assert "<svg" not in result
        assert "简历标题" in result
        assert "正常内容" in result
        assert "结尾内容" in result

    def test_real_resume_html(self):
        """真实的简历 HTML 应被正确处理"""
        html = """
        <h1>张三 - 前端工程师</h1>
        <h2>联系方式</h2>
        <p>手机：13800138000 | 邮箱：zhangsan@example.com</p>
        <h2>工作经历</h2>
        <h3>ABC科技有限公司 - 高级前端工程师（2022.06 - 至今）</h3>
        <ul>
            <li>主导公司核心产品的前端架构重构，<strong>页面加载速度提升 60%</strong></li>
            <li>设计并实现组件库，覆盖 80+ 通用组件，<em>团队开发效率提升 40%</em></li>
            <li>优化首屏渲染性能，FCP 从 3.2s 降至 1.1s，<strong>提升 65%</strong></li>
        </ul>
        <h2>教育背景</h2>
        <table>
            <tr><th>学校</th><th>专业</th><th>学历</th></tr>
            <tr><td>北京大学</td><td>计算机科学</td><td>本科</td></tr>
        </table>
        <h2>技能</h2>
        <p>React, Vue, TypeScript, Node.js, Webpack, Git</p>
        """
        result = sanitize_html(html)
        assert "张三" in result
        assert "<strong>" in result
        assert "<em>" in result
        assert "<table>" in result
        assert "<ul>" in result
        assert "React" in result


class TestCleanText:
    """clean_text 函数测试"""

    def test_removes_all_tags(self):
        """应移除所有 HTML 标签"""
        html = '<p class="test"><strong>加粗</strong>和<em>斜体</em></p>'
        result = clean_text(html)
        assert "<" not in result
        assert ">" not in result
        assert "加粗" in result
        assert "斜体" in result

    def test_empty_input(self):
        """空输入应返回空字符串"""
        assert clean_text("") == ""
        assert clean_text(None) == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
