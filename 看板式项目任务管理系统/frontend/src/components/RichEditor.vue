<template>
  <div class="rich-editor">
    <div class="editor-toolbar">
      <el-radio-group v-model="mode" size="small">
        <el-radio-button value="edit">编辑</el-radio-button>
        <el-radio-button value="preview">预览</el-radio-button>
      </el-radio-group>
      <span class="toolbar-hint">支持 Markdown 语法 · 可用 @用户名 提及成员</span>
    </div>

    <div v-show="mode === 'edit'" class="editor-pane">
      <!-- R-06-issue-2: 已修复 - textarea 加 maxlength="10000"，富文本描述超长前端第一道防线 -->
      <textarea
        class="editor-textarea"
        :value="modelValue"
        :placeholder="placeholder"
        :disabled="disabled"
        maxlength="10000"
        @input="onInput"
      ></textarea>
    </div>

    <div v-show="mode === 'preview'" class="preview-pane markdown-body" v-html="renderedHtml"></div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const props = defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: '输入 Markdown 内容...' },
  disabled: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue'])

const mode = ref('edit')

// D-01-fix-2026-05-21: DOMPurify v3.x 无静态 sanitize()，需 DOMPurify(window) 创建实例后调用 .sanitize()
const purify = DOMPurify(window)

// D-01-fix-2026-05-21: marked v18 ESM 无 new marked.Marked() 构造函数,改用 singleton marked.setOptions() + marked.parse()
marked.setOptions({ breaks: true, gfm: true })

// R-06-issue-4: 已修复 - 移除未使用的 renderer.text/paragraph 覆盖，改用 HTML 后处理 @mention（兼容 marked v18，不依赖 parser 内部 API）
// R-06-issue-1: 已修复 - 移除自定义 renderer 覆盖，marked 原生渲染所有 Markdown 内联格式(粗体/斜体/链接/代码)，@mention 在完整 HTML 输出后处理
const AT_MENTION_RE = /@(\w[\w-]{0,49})/g

const renderedHtml = computed(() => {
  if (!props.modelValue) return '<p style="color:#c0c4cc">暂无内容</p>'
  try {
    const raw = marked.parse(props.modelValue)
    // Post-process @mentions in the rendered HTML (compatible with all marked versions)
    const withMentions = raw.replace(AT_MENTION_RE, '<span class="at-mention">@$1</span>')
    const clean = purify.sanitize(withMentions, {
      ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'del', 'a', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'code', 'pre', 'blockquote', 'hr', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'img', 'span', 'div'],
      ALLOWED_ATTR: ['href', 'target', 'src', 'alt', 'class', 'title']
    })
    return clean
  } catch {
    return '<p style="color:#f56c6c">Markdown 渲染失败</p>'
  }
})

function onInput(e) {
  emit('update:modelValue', e.target.value)
}
</script>

<style scoped>
.rich-editor {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  overflow: hidden;
}

.editor-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-bottom: 1px solid #ebeef5;
}

.toolbar-hint {
  font-size: 12px;
  color: #909399;
}

.editor-pane {
  min-height: 160px;
}

.editor-textarea {
  width: 100%;
  min-height: 160px;
  padding: 12px;
  border: none;
  outline: none;
  resize: vertical;
  font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.6;
  color: #303133;
  background: #fff;
}

.editor-textarea:disabled {
  background: #f5f7fa;
  color: #c0c4cc;
}

.editor-textarea::placeholder {
  color: #c0c4cc;
}

.preview-pane {
  min-height: 160px;
  padding: 12px 16px;
  background: #fff;
  font-size: 14px;
  line-height: 1.7;
  color: #303133;
  word-break: break-word;
}

/* Minimalist markdown-body styles */
.preview-pane :deep(h1) { font-size: 1.5em; margin: 0.5em 0; border-bottom: 1px solid #ebeef5; padding-bottom: 0.3em; }
.preview-pane :deep(h2) { font-size: 1.3em; margin: 0.5em 0; }
.preview-pane :deep(h3) { font-size: 1.1em; margin: 0.4em 0; }
.preview-pane :deep(p) { margin: 0.4em 0; }
.preview-pane :deep(ul), .preview-pane :deep(ol) { padding-left: 1.8em; margin: 0.3em 0; }
.preview-pane :deep(li) { margin: 0.2em 0; }
.preview-pane :deep(code) { background: #f0f2f5; padding: 2px 6px; border-radius: 3px; font-size: 0.9em; font-family: monospace; }
.preview-pane :deep(pre) { background: #f0f2f5; padding: 12px; border-radius: 4px; overflow-x: auto; }
.preview-pane :deep(pre code) { background: none; padding: 0; }
.preview-pane :deep(blockquote) { border-left: 3px solid #409eff; padding: 4px 12px; margin: 0.4em 0; color: #606266; background: #f9fafc; }
.preview-pane :deep(a) { color: #409eff; }
.preview-pane :deep(table) { border-collapse: collapse; width: 100%; margin: 0.5em 0; }
.preview-pane :deep(th), .preview-pane :deep(td) { border: 1px solid #ebeef5; padding: 6px 12px; text-align: left; }
.preview-pane :deep(th) { background: #f5f7fa; }
.preview-pane :deep(hr) { border: none; border-top: 1px solid #ebeef5; margin: 1em 0; }
.preview-pane :deep(del) { color: #909399; }

/* @mention 高亮样式 */
.preview-pane :deep(.at-mention) {
  color: #409eff;
  background: rgba(64, 158, 255, 0.1);
  padding: 0 2px;
  border-radius: 2px;
  font-weight: 500;
}
</style>
