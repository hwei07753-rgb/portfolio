<template>
  <div class="mytasks-page">
    <!-- 顶栏 -->
    <el-header class="app-header">
      <div class="header-left">
        <span class="header-logo">项目任务管理</span>
      </div>
      <div class="header-right">
        <el-button text @click="$router.push('/projects')">项目列表</el-button>
        <el-button text @click="$router.push('/profile')">个人中心</el-button>
        <el-button text @click="handleLogout">退出</el-button>
      </div>
    </el-header>

    <div class="main-content">
      <h2 class="page-title">我的待办</h2>

      <!-- P1 筛选工具条 -->
      <!-- R-06-issue-25: 已修复 - P1-4筛选工具条新增截止日期范围+关键词搜索,对齐PRD§3筛选要求 -->
      <div class="filter-bar">
        <el-select v-model="filters.projectId" placeholder="全部项目" clearable @change="handleFilterChange" style="width:180px">
          <el-option v-for="p in userProjects" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
        <el-select v-model="filters.status" placeholder="全部状态" clearable @change="handleFilterChange" style="width:140px;margin-left:12px">
          <el-option label="待办" value="todo" />
          <el-option label="进行中" value="in_progress" />
          <el-option label="已完成" value="done" />
          <el-option label="已阻塞" value="blocked" />
        </el-select>
        <el-select v-model="filters.priority" placeholder="全部优先级" clearable @change="handleFilterChange" style="width:140px;margin-left:12px">
          <el-option label="低" value="low" />
          <el-option label="中" value="medium" />
          <el-option label="高" value="high" />
          <el-option label="紧急" value="urgent" />
        </el-select>
        <el-date-picker
          v-model="filters.dueDateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="截止日期起"
          end-placeholder="截止日期止"
          value-format="YYYY-MM-DD"
          @change="handleFilterChange"
          style="margin-left:12px"
        />
        <el-input
          v-model="filters.keyword"
          placeholder="搜索任务标题"
          clearable
          @keyup.enter="handleFilterChange"
          @clear="handleFilterChange"
          style="width:200px;margin-left:12px"
        />
      </div>

      <div v-loading="loading">
        <el-empty v-if="!loading && myTasks.length === 0" description="暂无待办任务" />
        <template v-else>
          <el-table :data="myTasks" stripe style="width: 100%">
            <el-table-column type="index" label="#" width="60" />
            <el-table-column prop="title" label="任务标题" min-width="200">
              <template #default="{ row }">
                <!-- R-06-issue-2: 已修复 - goToBoard 传递 taskId query 参数，ProjectBoardPage onMounted 读取自动打开抽屉 -->
                <el-button link type="primary" @click="goToBoard(row)">
                  {{ row.title }}
                </el-button>
              </template>
            </el-table-column>
            <el-table-column label="所属项目" width="160">
              <template #default="{ row }">
                {{ projectNameMap[row.projectId] || '项目' + row.projectId }}
              </template>
            </el-table-column>
            <el-table-column label="优先级" width="90" align="center">
              <template #default="{ row }">
                <el-tag :type="priorityTagType(row.priority)" size="small">
                  {{ priorityLabel(row.priority) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="statusTagType(row.status)" size="small">
                  {{ statusLabel(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="dueDate" label="截止日期" width="120" align="center">
              <template #default="{ row }">
                <span :class="{ 'overdue': isOverdue(row.dueDate) }">{{ row.dueDate || '-' }}</span>
              </template>
            </el-table-column>
          </el-table>
          <!-- R-06-issue-1: 已修复 - 添加 el-pagination 分页组件，P0 客户端过滤场景下大数据量时分页展示 -->
          <!-- R-06-issue-24: 已修复 - myTasks computed末尾加.slice()切片,分页切换从此生效 -->
          <!-- R-06-issue-26: 已修复 - el-pagination加@current-change(重置pageNum)+@size-change(重置pageNum再刷新);客户端分页场景v-model双向绑定驱动slice -->
          <el-pagination
            v-if="myTasks.length > 0"
            v-model:current-page="pageNum"
            v-model:page-size="pageSize"
            :total="myTasks.length"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            @current-change="(val) => pageNum = val"
            @size-change="(val) => { pageSize = val; pageNum = 1 }"
            style="margin-top: 16px; justify-content: flex-end"
          />
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
// R-06-issue-29: 已修复 - 移除未使用的ElMessage导入
import { listTasks } from '@/api/task'
import { listProjects } from '@/api/project'
import { useUserStore } from '@/stores/user'
// R-06-issue-6: 已修复 - priorityTagType/priorityLabel/statusTagType/statusLabel 抽取到 @/utils/task.js，消除重复定义
import { priorityTagType, priorityLabel, statusTagType, statusLabel } from '@/utils/task'

const router = useRouter()
const userStore = useUserStore()

const loading = ref(true)
const allTasks = ref([])
const projectNameMap = ref({})
const userProjects = ref([])
const pageNum = ref(1)
const pageSize = ref(10)

// P1 筛选条件
const filters = reactive({
  projectId: null,
  status: null,
  priority: null,
  dueDateRange: null,
  keyword: ''
})

const myTasks = computed(() => {
  let tasks = allTasks.value.filter(t => t.status !== 'deleted')
  // P1 升级：服务端筛选为主，客户端补充优先级筛选
  if (filters.priority) {
    tasks = tasks.filter(t => t.priority === filters.priority)
  }
  // R-06-issue-24: 已修复 - computed末尾slice切片,分页切换从此生效
  const start = (pageNum.value - 1) * pageSize.value
  return tasks.slice(start, start + pageSize.value)
})

function isOverdue(dueDate) {
  if (!dueDate) return false
  return new Date(dueDate) < new Date()
}

function goToBoard(task) {
  router.push({ path: `/projects/${task.projectId}/board`, query: { taskId: task.id } })
}

async function fetchData() {
  loading.value = true
  try {
    // 加载用户参与的所有项目（用于筛选下拉）
    const projectsRes = await listProjects({ pageSize: 100 })
    const projects = projectsRes.data.records || []
    userProjects.value = projects

    // 构建项目名映射
    const nameMap = {}
    projects.forEach(p => { nameMap[p.id] = p.name })
    projectNameMap.value = nameMap

    // P1 升级：服务端 assigneeId 筛选代替 P0 客户端过滤
    const queryProjects = filters.projectId ? [filters.projectId] : projects.map(p => p.id)
    if (queryProjects.length === 0) {
      allTasks.value = []
      return
    }

    const params = { pageSize: 200, assigneeId: userStore.userId }
    if (filters.status) params.status = filters.status
    // R-06-issue-25跨层: 已修复 - 新增dueDateFrom/dueDateTo/keyword参数传递,后端listTasks已支持
    if (filters.dueDateRange) {
      params.dueDateFrom = filters.dueDateRange[0]
      params.dueDateTo = filters.dueDateRange[1]
    }
    if (filters.keyword) params.keyword = filters.keyword

    const taskResults = await Promise.all(
      queryProjects.map(pId => listTasks(pId, params).catch(() => ({ data: { records: [] } })))
    )
    const tasks = taskResults.flatMap(r => r.data.records || [])
    allTasks.value = tasks
  } catch {
    // 拦截器已处理
  } finally {
    loading.value = false
  }
}

function handleFilterChange() {
  pageNum.value = 1
  fetchData()
}

function handleLogout() {
  userStore.logout()
  router.push('/login')
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.mytasks-page {
  min-height: 100vh;
  background: #f5f7fa;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 24px;
  height: 56px;
}

.header-logo {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.header-right {
  display: flex;
  gap: 8px;
}

.main-content {
  max-width: 1100px;
  margin: 0 auto;
  padding: 24px;
}

.page-title {
  margin: 0 0 20px 0;
  font-size: 22px;
  color: #303133;
}

.filter-bar {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
  padding: 12px 16px;
  background: #fff;
  border-radius: 4px;
}

.overdue {
  color: #f56c6c;
  font-weight: 500;
}
</style>