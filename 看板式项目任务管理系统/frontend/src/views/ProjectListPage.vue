<template>
  <div class="project-list-page">
    <!-- 顶栏 -->
    <el-header class="app-header">
      <div class="header-left">
        <span class="header-logo">项目任务管理</span>
      </div>
      <div class="header-right">
        <el-button text @click="$router.push('/my-tasks')">我的待办</el-button>
        <el-button text @click="$router.push('/profile')">个人中心</el-button>
        <el-button text @click="handleLogout">退出</el-button>
      </div>
    </el-header>

    <!-- 主区域 -->
    <div class="main-content">
      <div class="toolbar">
        <el-button type="primary" :icon="Plus" @click="openCreateDialog">新建项目</el-button>
      </div>

      <!-- 表格 -->
      <div v-loading="loading">
        <el-empty v-if="!loading && projects.length === 0" description="暂无项目，点击上方按钮创建第一个项目" />
        <template v-else>
          <el-table :data="projects" stripe style="width: 100%">
            <el-table-column type="index" label="#" width="60" />
            <el-table-column prop="name" label="项目名" min-width="200">
              <template #default="{ row }">
                <el-button link type="primary" @click="$router.push(`/projects/${row.id}/board`)">
                  {{ row.name }}
                </el-button>
              </template>
            </el-table-column>
            <el-table-column prop="memberCount" label="成员数" width="100" align="center" />
            <el-table-column label="状态" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="row.archived ? 'info' : 'success'">
                  {{ row.archived ? '已归档' : '活跃' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="220" align="center">
              <template #default="{ row }">
                <el-button size="small" @click="$router.push(`/projects/${row.id}/board`)">进入</el-button>
                <el-button
                  v-if="!row.archived"
                  size="small"
                  @click="$router.push(`/projects/${row.id}/settings`)"
                >设置</el-button>
                <el-button
                  v-if="!row.archived && row.myRole === 'owner'"
                  size="small"
                  type="warning"
                  @click="confirmArchive(row)"
                >归档</el-button>
              </template>
            </el-table-column>
          </el-table>

          <!-- 分页 -->
          <div class="pagination-wrapper">
            <!-- R-06-issue-2: 已修复 - el-pagination 改用 v-model:page-size 双向绑定 + 添加 @size-change 事件处理 -->
          <el-pagination
              v-model:current-page="pageNum"
              v-model:page-size="pageSize"
              :total="total"
              layout="total, prev, pager, next"
              @current-change="fetchProjects"
              @size-change="fetchProjects"
            />
          </div>
        </template>
      </div>
    </div>

    <!-- 新建项目弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      title="新建项目"
      width="450px"
      :close-on-click-modal="false"
      @closed="resetForm"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="80px"
        @submit.prevent
      >
        <el-form-item label="项目名称" prop="name">
          <el-input
            v-model="form.name"
            placeholder="请输入项目名称"
            maxlength="100"
            show-word-limit
            @keyup.enter="handleCreate"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">确认创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
// R-06-issue-4: 已修复 - import 顺序调整：@/api/project 在 @/stores/user 之前（vue→vue-router→element-plus→@/api→@/stores）
import { listProjects, createProject, updateProject } from '@/api/project'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const router = useRouter()

const loading = ref(true)
const projects = ref([])
const pageNum = ref(1)
const pageSize = ref(10)
const total = ref(0)

// 新建弹窗
const dialogVisible = ref(false)
const creating = ref(false)
const formRef = ref(null)
const form = reactive({ name: '' })
const rules = {
  name: [
    { required: true, message: '请输入项目名称', trigger: 'blur' },
    { max: 100, message: '项目名称不能超过100字符', trigger: 'blur' }
  ]
}

async function fetchProjects() {
  loading.value = true
  try {
    const res = await listProjects({ pageNum: pageNum.value, pageSize: pageSize.value })
    projects.value = res.data.records || []
    total.value = res.data.total || 0
  } catch {
    // 拦截器已处理错误提示
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  form.name = ''
  dialogVisible.value = true
}

function resetForm() {
  formRef.value?.resetFields()
}

async function handleCreate() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  creating.value = true
  try {
    await createProject({ name: form.name })
    ElMessage.success('项目创建成功')
    dialogVisible.value = false
    pageNum.value = 1
    await fetchProjects()
  } catch {
    // 拦截器已处理错误提示
  } finally {
    creating.value = false
  }
}

function confirmArchive(row) {
  ElMessageBox.confirm(
    '确认归档该项目？归档后项目将从默认列表隐藏。',
    '归档确认',
    { confirmButtonText: '确认归档', cancelButtonText: '取消', type: 'warning' }
  ).then(async () => {
    try {
      await updateProject(row.id, { archived: true })
      ElMessage.success('已归档')
      await fetchProjects()
    } catch {
      // 拦截器已处理错误提示
    }
  }).catch(() => {})
}

function handleLogout() {
  userStore.logout()
  router.push('/login')
}

onMounted(() => {
  fetchProjects()
})
</script>

<style scoped>
.project-list-page {
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

.toolbar {
  margin-bottom: 16px;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}
</style>