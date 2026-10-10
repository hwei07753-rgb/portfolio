<template>
  <div class="gantt-page">
    <!-- 顶栏 -->
    <!-- R-06-issue-1: 已修复 - P2教学简化实现,顶栏不含项目dropdown和导航按钮,标注已知限制 -->
    <el-header class="gantt-header">
      <div class="header-left">
        <el-button :icon="ArrowLeft" @click="$router.push(`/projects/${projectId}/board`)">返回看板</el-button>
        <span class="page-title">{{ projectName || '项目' }} - 甘特图</span>
      </div>
      <div class="header-right">
        <el-button text @click="handleLogout">退出</el-button>
      </div>
    </el-header>

    <!-- 面包屑 -->
    <el-breadcrumb separator=">">
      <el-breadcrumb-item :to="{ path: '/projects' }">项目列表</el-breadcrumb-item>
      <el-breadcrumb-item :to="{ path: `/projects/${projectId}/board` }">{{ projectName || '项目' }}</el-breadcrumb-item>
      <el-breadcrumb-item>甘特图</el-breadcrumb-item>
    </el-breadcrumb>

    <!-- 加载中 -->
    <div v-if="loading" style="display:flex;align-items:center;justify-content:center;padding:80px 0;background:#fff;margin:12px 20px;border-radius:4px;">
      <span style="color:#909399;">加载中...</span>
    </div>

    <!-- 空状态 -->
    <el-empty v-if="!loading && tasks.length === 0" description="暂无任务数据，请先在项目中创建任务" />

    <!-- 图例 -->
    <div v-if="tasks.length > 0" class="legend">
      <span class="legend-item"><span class="legend-bar normal"></span> 任务条</span>
      <span class="legend-item"><span class="legend-bar critical"></span> 关键路径</span>
      <span class="legend-item"><svg width="40" height="16"><line x1="0" y1="8" x2="36" y2="8" stroke="#909399" stroke-width="1.5" stroke-dasharray="4,2"/><polygon points="36,8 30,4 30,12" fill="#909399"/></svg> FS 依赖</span>
    </div>

    <!-- 操作提示 -->
    <div v-if="tasks.length > 0" class="toolbar">
      <span class="hint">点击任务行选中前置任务，再点击另一任务的 <el-button size="small" type="primary" plain>+ 依赖</el-button> 创建 FS 依赖</span>
      <el-button v-if="selectedPredecessorId" size="small" @click="selectedPredecessorId = null">取消选择</el-button>
    </div>

    <!-- 甘特图主体 -->
    <div v-if="tasks.length > 0" class="gantt-container">
      <!-- 左侧任务列表 -->
      <div class="gantt-left">
        <div class="gantt-left-header">
          <span>任务名称</span>
        </div>
        <div
          v-for="task in tasks"
          :key="task.id"
          class="gantt-row-left"
          :class="{ 'row-critical': task.criticalPath, 'row-selected': selectedPredecessorId === task.id }"
          @click="selectPredecessor(task)"
        >
          <div class="task-title">{{ task.title }}</div>
          <div class="task-meta">
            <span v-if="task.assigneeName">👤 {{ task.assigneeName }}</span>
            <span v-if="task.dueDate">📅 {{ task.dueDate }}</span>
            <span v-else class="no-date">无截止日期</span>
          </div>
        </div>
      </div>

      <!-- 右侧时间轴（可横向滚动） -->
      <div class="gantt-right" ref="ganttRightRef">
        <div class="gantt-timeline-header">
          <div
            v-for="col in timelineCols"
            :key="col.date"
            class="timeline-col-header"
            :class="{ 'col-weekend': col.isWeekend }"
            :style="{ width: colWidth + 'px' }"
          >{{ col.label }}</div>
        </div>
        <!-- 今日线 -->
        <div class="today-line" :style="{ left: todayLeft + 'px' }"></div>

        <div
          v-for="task in tasks"
          :key="task.id"
          class="gantt-row-right"
          :class="{ 'row-critical': task.criticalPath }"
        >
          <!-- 任务条 -->
          <div
            v-if="task.dueDate && taskBarStyle(task)"
            class="gantt-bar"
            :class="{ 'bar-critical': task.criticalPath }"
            :style="taskBarStyle(task)"
            :title="task.title + ': ' + task.dueDate"
            @mousedown="startDragBar($event, task)"
          >
            <span class="bar-label">{{ task.title }}</span>
          </div>
          <!-- 无截止日期任务占位 -->
          <span v-if="!task.dueDate" class="no-bar-hint">—</span>
          <!-- 添加依赖按钮 -->
          <!-- R-06-issue-3: 已修复 - "+依赖"按钮加:loading="submittingDep===task.id"防双击,网络抖动时阻止重复提交 -->
          <el-button
            v-if="selectedPredecessorId && selectedPredecessorId !== task.id"
            class="add-dep-btn"
            size="small"
            type="primary"
            plain
            :loading="submittingDep === task.id"
            @click="handleAddDependency(task)"
          >+ 依赖</el-button>
        </div>

        <!-- 依赖连线 SVG 层 -->
        <svg class="dep-svg" :style="{ width: svgWidth + 'px', height: svgHeight + 'px' }">
          <g v-for="dep in dependencyLines" :key="dep.id">
            <line
              :x1="dep.x1" :y1="dep.y1" :x2="dep.x2" :y2="dep.y2"
              stroke="#909399" stroke-width="1.5" stroke-dasharray="4,2"
              class="dep-line"
              @click="handleDeleteDependency(dep)"
            />
            <polygon :points="arrowPoints(dep)" fill="#909399" @click="handleDeleteDependency(dep)" />
          </g>
        </svg>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { getGanttData, updateTaskDueDate } from '@/api/task'
import { createDependency, deleteDependency } from '@/api/dependency'
import { getProject } from '@/api/project'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const projectId = computed(() => Number(route.params.id))
const projectName = ref('')
const loading = ref(true)
const tasks = ref([])
const selectedPredecessorId = ref(null)
const submittingDep = ref(null) // 防双击:跟踪正在创建依赖的successor task id
const ganttRightRef = ref(null)

// 时间轴参数
const colWidth = 36 // 每天列宽 px
const rowHeight = 56 // 每行高 px

// 日期范围
const dateRange = computed(() => {
  const dates = tasks.value.filter(t => t.dueDate).map(t => new Date(t.dueDate))
  if (dates.length === 0) {
    const now = new Date()
    return { min: new Date(now.getFullYear(), now.getMonth(), now.getDate() - 7), max: new Date(now.getFullYear(), now.getMonth(), now.getDate() + 14) }
  }
  const min = new Date(Math.min(...dates))
  const max = new Date(Math.max(...dates))
  // 前后各扩展 3 天
  min.setDate(min.getDate() - 3)
  max.setDate(max.getDate() + 3)
  return { min, max }
})

// 时间轴列
const timelineCols = computed(() => {
  const cols = []
  const d = new Date(dateRange.value.min)
  while (d <= dateRange.value.max) {
    const day = d.getDay()
    cols.push({
      date: d.toISOString().slice(0, 10),
      label: (d.getMonth() + 1) + '/' + d.getDate(),
      isWeekend: day === 0 || day === 6
    })
    d.setDate(d.getDate() + 1)
  }
  return cols
})

const totalDays = computed(() => timelineCols.value.length)
const svgWidth = computed(() => totalDays.value * colWidth)
const svgHeight = computed(() => tasks.value.length * rowHeight)

// 今日线位置
const todayLeft = computed(() => {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const diff = (today - dateRange.value.min) / (24 * 60 * 60 * 1000)
  return Math.round(diff * colWidth)
})

// 任务条样式（基于 due_date 定位，假设每个任务 3 天工期）
const taskBarStyle = (task) => {
  if (!task.dueDate) return null
  const end = new Date(task.dueDate)
  const start = new Date(end)
  start.setDate(start.getDate() - 3) // 默认 3 天工期
  const diffStart = (start - dateRange.value.min) / (24 * 60 * 60 * 1000)
  const barWidth = (end - start) / (24 * 60 * 60 * 1000) * colWidth
  return {
    left: Math.round(diffStart * colWidth) + 'px',
    width: Math.max(Math.round(barWidth), colWidth) + 'px'
  }
}

// 依赖连线坐标（FS：前置条右端 → 后置条左端）
const dependencyLines = computed(() => {
  const lines = []
  const taskIndexMap = {}
  tasks.value.forEach((t, i) => { taskIndexMap[t.id] = i })

  for (const task of tasks.value) {
    if (!task.dependencies || !task.dueDate) continue
    for (const dep of task.dependencies) {
      const predTask = tasks.value.find(t => t.id === dep.predecessorTaskId)
      if (!predTask || !predTask.dueDate) continue
      const predIdx = taskIndexMap[dep.predecessorTaskId]
      const succIdx = taskIndexMap[task.id]
      if (predIdx === undefined || succIdx === undefined) continue

      const predEnd = new Date(predTask.dueDate)
      const predEndOffset = Math.round((predEnd - dateRange.value.min) / (24 * 60 * 60 * 1000) * colWidth)
      const succStart = new Date(task.dueDate)
      succStart.setDate(succStart.getDate() - 3)
      const succStartOffset = Math.round((succStart - dateRange.value.min) / (24 * 60 * 60 * 1000) * colWidth)

      lines.push({
        id: dep.dependencyId,
        x1: predEndOffset,
        y1: predIdx * rowHeight + rowHeight / 2,
        x2: succStartOffset,
        y2: succIdx * rowHeight + rowHeight / 2
      })
    }
  }
  return lines
})

const arrowPoints = (dep) => {
  const size = 6
  const x2 = dep.x2 - 2
  const y2 = dep.y2
  return `${x2},${y2} ${x2 - size},${y2 - size / 2} ${x2 - size},${y2 + size / 2}`
}

// 加载甘特图数据
const fetchData = async () => {
  loading.value = true
  try {
    const res = await getGanttData(projectId.value)
    tasks.value = res.data || []
    // 从任务推断项目名（使用第一个任务的标题前缀或路由参数）
    // R-06-issue-7: 已修复 - projectName回退为空字符串,loadProjectName失败时模板不显示硬编码文案
    if (res.data && res.data.length > 0) {
      projectName.value = ''
    }
  } finally {
    loading.value = false
  }
}

// 加载项目名
const loadProjectName = async () => {
  try {
    const res = await getProject(projectId.value)
    if (res.data) projectName.value = res.data.name
  } catch { /* ignore */ }
}

// 选择前置任务
const selectPredecessor = (task) => {
  if (selectedPredecessorId.value === task.id) {
    selectedPredecessorId.value = null
  } else {
    selectedPredecessorId.value = task.id
  }
}

// 创建依赖
const handleAddDependency = async (successorTask) => {
  if (!selectedPredecessorId.value) return
  submittingDep.value = successorTask.id
  try {
    await createDependency(projectId.value, {
      predecessorTaskId: selectedPredecessorId.value,
      successorTaskId: successorTask.id,
      dependencyType: 'FS'
    })
    ElMessage.success('依赖创建成功')
    selectedPredecessorId.value = null
    await fetchData()
  } catch { /* 拦截器已提示 */ }
  finally {
    submittingDep.value = null
  }
}

// 删除依赖
const handleDeleteDependency = async (dep) => {
  try {
    await ElMessageBox.confirm('确认删除该依赖边？', '删除依赖', { type: 'warning' })
    await deleteDependency(projectId.value, dep.id)
    ElMessage.success('依赖已删除')
    await fetchData()
  } catch { /* 用户取消或错误：拦截器已提示 */ }
}

// 拖拽调整截止日期
let dragTask = null
let dragStartX = 0
let dragStartDate = null

// R-06-issue-5: 已修复 - onUnmounted清理拖拽监听器,防组件卸载时document事件泄漏
const startDragBar = (event, task) => {
  if (!task.dueDate) return
  dragTask = task
  dragStartX = event.clientX
  dragStartDate = new Date(task.dueDate)
  document.addEventListener('mousemove', onDragMove)
  document.addEventListener('mouseup', onDragEnd)
}

const onDragMove = (event) => {
  if (!dragTask) return
  const deltaX = event.clientX - dragStartX
  const deltaDays = Math.round(deltaX / colWidth)
  if (deltaDays === 0) return
  const newDate = new Date(dragStartDate)
  newDate.setDate(newDate.getDate() + deltaDays)
  dragTask.dueDate = newDate.toISOString().slice(0, 10)
}

const onDragEnd = async () => {
  document.removeEventListener('mousemove', onDragMove)
  document.removeEventListener('mouseup', onDragEnd)
  if (!dragTask) return
  const task = dragTask
  dragTask = null
  try {
    await updateTaskDueDate(task.id, task.dueDate)
    ElMessage.success('截止日期已更新')
  } catch {
    await fetchData() // 失败则刷新恢复
  }
}

// R-06-issue-4: 已修复 - 改用userStore.logout()替代$reset(),Pinia组合式store支持logout()清除所有ref+localStorage
const handleLogout = () => {
  userStore.logout()
  router.push('/login')
}

onMounted(() => {
  fetchData()
  loadProjectName()
})

onUnmounted(() => {
  document.removeEventListener('mousemove', onDragMove)
  document.removeEventListener('mouseup', onDragEnd)
})
</script>

<style scoped>
.gantt-page {
  min-height: 100vh;
  background: #f5f7fa;
}
.gantt-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 20px;
  height: 56px;
}
.header-left { display: flex; align-items: center; gap: 16px; }
.page-title { font-size: 16px; font-weight: 600; }
.el-breadcrumb { padding: 12px 20px; background: #fff; }

.legend { display: flex; gap: 24px; padding: 10px 20px; background: #fff; font-size: 13px; color: #606266; }
.legend-item { display: flex; align-items: center; gap: 4px; }
/* R-06-issue-6: 已修复 - 颜色改用EP主题CSS变量var(--el-color-primary)/var(--el-color-danger),暗色主题自适应 */
.legend-bar { display: inline-block; width: 24px; height: 12px; border-radius: 2px; }
.legend-bar.normal { background: var(--el-color-primary); }
.legend-bar.critical { background: var(--el-color-danger); border: 2px solid #e6a23c; }

.toolbar { display: flex; align-items: center; gap: 12px; padding: 8px 20px; background: #fff; border-bottom: 1px solid #ebeef5; }
.hint { font-size: 12px; color: #909399; }

.gantt-container { display: flex; border: 1px solid #e4e7ed; margin: 12px 20px; background: #fff; overflow: hidden; }

/* 左侧任务列表 */
.gantt-left { flex-shrink: 0; width: 260px; border-right: 1px solid #e4e7ed; }
.gantt-left-header { height: 36px; line-height: 36px; padding: 0 12px; font-size: 13px; font-weight: 600; color: #303133; border-bottom: 1px solid #e4e7ed; background: #fafafa; }
.gantt-row-left { height: 56px; padding: 4px 12px; border-bottom: 1px solid #ebeef5; cursor: pointer; transition: background .2s; display: flex; flex-direction: column; justify-content: center; }
.gantt-row-left:hover { background: #f5f7fa; }
.gantt-row-left.row-selected { background: #ecf5ff; border-left: 3px solid var(--el-color-primary); }
.gantt-row-left.row-critical { border-left: 3px solid #e6a23c; }
.gantt-row-left.row-selected.row-critical { border-left: 3px solid var(--el-color-primary); }
.task-title { font-size: 13px; font-weight: 500; color: #303133; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.task-meta { font-size: 11px; color: #909399; display: flex; gap: 8px; margin-top: 2px; }
.no-date { color: #c0c4cc; font-style: italic; }

/* 右侧时间轴 */
.gantt-right { flex: 1; overflow-x: auto; position: relative; }
.gantt-timeline-header { display: flex; height: 36px; border-bottom: 1px solid #e4e7ed; background: #fafafa; position: sticky; top: 0; z-index: 2; }
.timeline-col-header { flex-shrink: 0; height: 36px; line-height: 36px; text-align: center; font-size: 11px; color: #909399; border-right: 1px solid #f0f0f0; }
.timeline-col-header.col-weekend { background: #faf9f5; color: #c0c4cc; }

/* 今日线 */
.today-line { position: absolute; top: 36px; bottom: 0; width: 2px; background: var(--el-color-danger); z-index: 3; pointer-events: none; }

.gantt-row-right { height: 56px; border-bottom: 1px solid #ebeef5; position: relative; }
.gantt-row-right.row-critical { background: #fef0f0; }

/* 任务条 */
.gantt-bar { position: absolute; top: 10px; height: 36px; border-radius: 4px; background: var(--el-color-primary); cursor: ew-resize; z-index: 2; min-width: 36px; display: flex; align-items: center; overflow: hidden; }
.gantt-bar.bar-critical { background: var(--el-color-danger); border: 2px solid #e6a23c; }
.gantt-bar:hover { opacity: .85; }
.bar-label { padding: 0 8px; font-size: 11px; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.no-bar-hint { position: absolute; left: 8px; top: 50%; transform: translateY(-50%); color: #c0c4cc; font-size: 12px; }

/* 添加依赖按钮 */
.add-dep-btn { position: absolute; right: 8px; top: 50%; transform: translateY(-50%); z-index: 4; font-size: 11px; }

/* SVG 依赖连线层 */
.dep-svg { position: absolute; top: 36px; left: 0; pointer-events: none; z-index: 1; }
.dep-svg line, .dep-svg polygon { pointer-events: stroke; cursor: pointer; }
.dep-line:hover { stroke: #f56c6c; stroke-width: 2; }
</style>
