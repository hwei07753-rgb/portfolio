<template>
  <div class="stats-section">
    <div class="stats-header">
      <span class="stats-title">项目统计</span>
      <el-button size="small" :icon="Refresh" :loading="statsLoading" @click="loadStats">刷新图表</el-button>
    </div>
    <div class="charts-row">
      <el-card class="chart-card" shadow="never" v-loading="statsLoading || loading">
        <template #header><span>任务状态分布</span></template>
        <div v-if="statusLoadFailed" style="height:260px">
          <el-empty description="加载失败">
            <template #default>
              <el-button size="small" @click="loadStats">重试</el-button>
            </template>
          </el-empty>
        </div>
        <div v-else-if="statusStatsEmpty" style="height:260px">
          <el-empty description="暂无任务数据" :image-size="80" />
        </div>
        <div ref="statusChartRef" v-show="!statusStatsEmpty && !statusLoadFailed" class="chart-box"></div>
      </el-card>
      <el-card class="chart-card" shadow="never" v-loading="statsLoading || loading">
        <!-- R-06-issue-2: 已修复 - Sprint筛选激活时燃尽图标题标注当前Sprint名称 -->
        <template #header><span>燃尽图{{ props.sprintName ? ' · ' + props.sprintName : '' }}</span></template>
        <div v-if="burndownLoadFailed" style="height:260px">
          <el-empty description="加载失败">
            <template #default>
              <el-button size="small" @click="loadStats">重试</el-button>
            </template>
          </el-empty>
        </div>
        <div v-else-if="burndownEmpty" style="height:260px">
          <el-empty description="暂无燃尽图数据" :image-size="80" />
        </div>
        <div ref="burndownChartRef" v-show="!burndownEmpty && !burndownLoadFailed" class="chart-box"></div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { getStatusStats, getBurndown } from '@/api/project'

const props = defineProps({
  projectId: { type: Number, required: true },
  loading: { type: Boolean, default: false },
  /** P2-3 Sprint ID，传入时启用 Sprint 精确燃尽图 */
  milestoneId: { type: Number, default: null },
  /** P2-3 Sprint 名称，用于燃尽图标题标注（R-06-issue-2 修复） */
  sprintName: { type: String, default: '' }
})

const statusChartRef = ref(null)
const burndownChartRef = ref(null)
let statusChart = null
let burndownChart = null
const statsLoading = ref(false)
const statusStatsEmpty = ref(false)
const burndownEmpty = ref(false)
// R-06-issue-33: 已修复 - 区分API失败与"真·无数据"，失败时提示"加载失败"并提供重试按钮
const statusLoadFailed = ref(false)
const burndownLoadFailed = ref(false)

// R-06-issue-32: 已修复 - 抽取STATUS_COLORS模块级常量替代硬编码hex字面量
const STATUS_COLORS = {
  todo: '#909399',
  in_progress: '#409EFF',
  done: '#67C23A',
  blocked: '#F56C6C'
}

let resizePending = false

async function loadStats() {
  statsLoading.value = true
  statusLoadFailed.value = false
  burndownLoadFailed.value = false
  try {
    const [statusRes, burndownRes] = await Promise.all([
      getStatusStats(props.projectId).catch(() => { statusLoadFailed.value = true; return null }),
      getBurndown(props.projectId, props.milestoneId).catch(() => { burndownLoadFailed.value = true; return null })
    ])
    nextTick(() => {
      renderStatusChart(statusRes ? statusRes.data : null)
      renderBurndownChart(burndownRes ? burndownRes.data : null)
    })
  } finally {
    statsLoading.value = false
  }
}

function renderStatusChart(data) {
  if (!data || Object.values(data).every(v => v === 0)) {
    statusStatsEmpty.value = true
    disposeChart('status')
    return
  }
  statusStatsEmpty.value = false
  if (!statusChartRef.value) return
  if (!statusChart) {
    statusChart = echarts.init(statusChartRef.value)
  }
  statusChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['待办', '进行中', '已完成', '已阻塞'] },
    yAxis: { type: 'value', minInterval: 1 },
    series: [{
      name: '任务数', type: 'bar',
      data: [
        { value: data.todo || 0, itemStyle: { color: STATUS_COLORS.todo } },
        { value: data.in_progress || 0, itemStyle: { color: STATUS_COLORS.in_progress } },
        { value: data.done || 0, itemStyle: { color: STATUS_COLORS.done } },
        { value: data.blocked || 0, itemStyle: { color: STATUS_COLORS.blocked } }
      ]
    }]
  }, { notMerge: true })
}

function renderBurndownChart(data) {
  if (!data || data.length === 0) {
    burndownEmpty.value = true
    disposeChart('burndown')
    return
  }
  burndownEmpty.value = false
  if (!burndownChartRef.value) return
  if (!burndownChart) {
    burndownChart = echarts.init(burndownChartRef.value)
  }
  burndownChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: data.map(d => d.date), axisLabel: { rotate: 30 } },
    yAxis: { type: 'value', minInterval: 1 },
    series: [{
      name: '剩余任务', type: 'line',
      data: data.map(d => d.remaining),
      smooth: true, lineStyle: { color: '#409EFF' },
      itemStyle: { color: '#409EFF' },
      areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: 'rgba(64,158,255,0.3)' },
        { offset: 1, color: 'rgba(64,158,255,0.05)' }
      ]) }
    }]
  }, { notMerge: true })
}

function disposeChart(type) {
  if (type === 'status' && statusChart) {
    statusChart.dispose()
    statusChart = null
  }
  if (type === 'burndown' && burndownChart) {
    burndownChart.dispose()
    burndownChart = null
  }
}

function disposeAllCharts() {
  if (statusChart) { statusChart.dispose(); statusChart = null }
  if (burndownChart) { burndownChart.dispose(); burndownChart = null }
}

// R-06-issue-34: 已修复 - requestAnimationFrame防抖替代高频resize重绘
function handleResize() {
  if (resizePending) return
  resizePending = true
  requestAnimationFrame(() => {
    if (statusChart) statusChart.resize()
    if (burndownChart) burndownChart.resize()
    resizePending = false
  })
}

watch(() => props.milestoneId, () => {
  loadStats()
})

onMounted(() => {
  loadStats()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  disposeAllCharts()
})
</script>

<style scoped>
.stats-section {
  padding: 12px 24px;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
}

.stats-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.stats-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.charts-row {
  display: flex;
  gap: 16px;
}

.chart-card {
  flex: 1;
  min-width: 0;
}

.chart-box {
  width: 100%;
  height: 260px;
}
</style>
