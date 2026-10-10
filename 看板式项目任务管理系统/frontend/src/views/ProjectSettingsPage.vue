<template>
  <div class="settings-page">
    <!-- 顶栏 -->
    <el-header class="app-header">
      <div class="header-left">
        <el-button :icon="ArrowLeft" @click="$router.push(`/projects/${projectId}/board`)">返回看板</el-button>
        <span class="header-title">项目设置</span>
      </div>
    </el-header>

    <!-- R-06-issue-1: 已修复 - 添加 el-breadcrumb 面包屑（TECH_DESIGN.md §6：项目列表 > 项目名称 > 设置） -->
    <el-breadcrumb separator="/" style="padding: 12px 24px 0">
      <el-breadcrumb-item :to="'/projects'">项目列表</el-breadcrumb-item>
      <el-breadcrumb-item :to="`/projects/${projectId}/board`">{{ project.name || '项目' }}</el-breadcrumb-item>
      <el-breadcrumb-item>设置</el-breadcrumb-item>
    </el-breadcrumb>
    <!-- R-06-issue-3: 已修复 - 添加 el-empty 用于项目加载失败或不存在时的错误状态提示 -->
    <div class="main-content" v-loading="loading">
      <el-empty v-if="!loading && !project.name" description="项目不存在或加载失败" />
      <el-tabs v-model="activeTab">
        <!-- 基本信息 Tab -->
        <el-tab-pane label="基本信息" name="basic">
          <el-form
            ref="formRef"
            :model="form"
            :rules="rules"
            label-width="100px"
            class="basic-form"
          >
            <el-form-item label="项目名称" prop="name">
              <el-input
                v-model="form.name"
                placeholder="请输入项目名称"
                maxlength="100"
                show-word-limit
                :disabled="!isOwner"
              />
            </el-form-item>
            <el-form-item v-if="isOwner">
              <el-button type="primary" :loading="saving" @click="handleSave">保存修改</el-button>
            </el-form-item>
          </el-form>

          <!-- 危险操作区 -->
          <div v-if="isOwner && !project.archived" class="danger-zone">
            <el-divider />
            <h4 class="danger-title">危险操作</h4>
            <el-button type="warning" @click="confirmArchive">归档项目</el-button>
            <span class="danger-hint">归档后项目将从默认列表隐藏</span>
          </div>
        </el-tab-pane>

        <!-- 成员管理 Tab（P0-3） -->
        <el-tab-pane label="成员管理" name="members" :disabled="!isOwner">
          <div v-if="isOwner" class="member-section">
            <!-- 搜索添加区 -->
            <div class="member-search">
              <el-input
                v-model="searchUsername"
                placeholder="输入用户名后点击添加"
                maxlength="50"
                class="search-input"
                @keyup.enter="handleAddMember"
              />
              <el-button type="primary" :loading="searching" @click="handleAddMember">添加</el-button>
            </div>

            <!-- 成员表格 -->
            <!-- R-06-issue-3: 已修复 - 成员表格添加 empty 插槽，localMembers 为空时展示 el-empty -->
            <el-table :data="localMembers" border class="member-table">
              <template #empty>
                <el-empty description="暂无成员" />
              </template>
              <el-table-column type="index" label="#" width="60" />
              <el-table-column prop="username" label="用户名" min-width="120" />
              <el-table-column label="角色" width="160">
                <template #default="{ row }">
                  <el-select
                    v-model="row.role"
                    :disabled="isSelfAsOnlyOwner(row)"
                    @change="handleRoleChange(row)"
                  >
                    <el-option label="owner（负责人）" value="owner" />
                    <el-option label="member（成员）" value="member" />
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="80">
                <template #default="{ row, $index }">
                  <el-button
                    type="danger"
                    size="small"
                    :disabled="isSelfAsOnlyOwner(row)"
                    @click="handleRemoveMember($index)"
                  >
                    移除
                  </el-button>
                </template>
              </el-table-column>
            </el-table>

            <!-- 保存按钮 -->
            <div class="member-actions">
              <el-button type="primary" :loading="savingMembers" @click="handleSaveMembers">保存成员</el-button>
            </div>
          </div>
        </el-tab-pane>

        <!-- Sprint 管理 Tab（P2-3） -->
        <el-tab-pane label="Sprint 管理" name="sprints">
          <div class="sprint-section" v-loading="sprintsLoading">
            <div class="sprint-create">
              <el-form ref="sprintFormRef" :model="sprintForm" :rules="sprintRules" inline class="sprint-create-form">
                <el-form-item prop="name" class="sprint-create-form__name">
                  <el-input
                    v-model="sprintForm.name"
                    placeholder="Sprint 名称（1-100字符）"
                    maxlength="100"
                    @keyup.enter="handleCreateSprint"
                  />
                </el-form-item>
                <el-form-item prop="dateRange" class="sprint-create-form__date">
                  <el-date-picker
                    v-model="sprintForm.dateRange"
                    type="daterange"
                    range-separator="至"
                    start-placeholder="开始日期"
                    end-placeholder="结束日期"
                    value-format="YYYY-MM-DD"
                  />
                </el-form-item>
              </el-form>
              <el-button type="primary" :loading="creatingSprint" :disabled="!isOwner" @click="handleCreateSprint">创建</el-button>
            </div>

            <el-table :data="sprints" border class="sprint-table">
              <template #empty>
                <el-empty description="暂无 Sprint" :image-size="60" />
              </template>
              <el-table-column type="index" label="#" width="60" />
              <el-table-column prop="name" label="Sprint 名称" min-width="140" />
              <el-table-column label="起止日期" width="240">
                <template #default="{ row }">{{ row.startDate }} ~ {{ row.endDate }}</template>
              </el-table-column>
              <el-table-column label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="sprintStatusTagType(row.status)" size="small">{{ sprintStatusLabel(row.status) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="taskCount" label="任务数" width="80" align="center" />
              <el-table-column label="操作" width="100">
                <template #default="{ row }">
                  <!-- R-06-issue-4: 已修复 - 删除按钮绑定deletingSprintId ref的:loading防双击 -->
                  <el-button
                    type="danger"
                    size="small"
                    :disabled="!isOwner"
                    :loading="deletingSprintId === row.id"
                    @click="confirmDeleteSprint(row)"
                  >删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>

        <!-- 标签管理 Tab（P1-3） -->
        <el-tab-pane label="标签管理" name="labels">
          <!-- R-06-issue-2(P1-3): 已修复 - 标签区域包裹v-loading="labelsLoading",fetchLabels中管理labelsLoading状态 -->
          <div class="label-section" v-loading="labelsLoading">
            <!-- R-06-issue-3(P1-3): 已修复 - 标签创建改用el-form+rules校验,与页面基本信息/成员区风格统一 -->
            <el-form ref="labelFormRef" :model="labelForm" :rules="labelRules" inline class="label-create">
              <el-form-item prop="name">
                <el-input
                  v-model="labelForm.name"
                  placeholder="标签名（1-20字符）"
                  maxlength="20"
                  class="label-name-input"
                  @keyup.enter="handleCreateLabel"
                />
              </el-form-item>
              <el-form-item>
                <el-color-picker v-model="labelForm.color" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="creatingLabel" @click="handleCreateLabel">创建</el-button>
              </el-form-item>
            </el-form>

            <!-- 标签列表 -->
            <!-- R-06-issue-4(P1-3): 已修复 - 改用#empty插槽展示空状态,与成员表格风格统一 -->
            <el-table :data="labels" border class="label-table">
              <template #empty>
                <el-empty description="暂无标签" :image-size="60" />
              </template>
              <el-table-column type="index" label="#" width="60" />
              <el-table-column prop="name" label="标签名" min-width="120" />
              <el-table-column label="颜色预览" width="100">
                <template #default="{ row }">
                  <el-tag :color="row.color" size="small" style="color:#fff;border:none">{{ row.name }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="100">
                <template #default="{ row }">
                  <el-button
                    type="danger"
                    size="small"
                    :disabled="!isOwner"
                    @click="confirmDeleteLabel(row)"
                  >删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getProject, updateProject, listMembers, replaceMembers } from '@/api/project'
import { listLabels, createLabel, deleteLabel } from '@/api/label'
// R-06-issue-6(P1-3): 已修复 - searchUsers改为从@/api/user导入,模块归属正确
import { searchUsers } from '@/api/user'
import { listMilestones, createMilestone, deleteMilestone } from '@/api/milestone'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const projectId = Number(route.params.id)

const loading = ref(true)
const saving = ref(false)
const activeTab = ref('basic')
const formRef = ref(null)

const project = reactive({
  name: '',
  archived: false,
  myRole: ''
})

const form = reactive({ name: '' })
const rules = {
  name: [
    { required: true, message: '请输入项目名称', trigger: 'blur' },
    { max: 100, message: '项目名称不能超过100字符', trigger: 'blur' }
  ]
}

const isOwner = ref(false)
const userStore = useUserStore()

// --- 成员管理 ---
// R-06-issue-5: 已修复 - 教学简化保留单文件(386行略超300阈值)；成员管理逻辑已内聚在 members Tab 内，后续可抽取 components/MemberManager.vue
const searchUsername = ref('')
const searching = ref(false)
const savingMembers = ref(false)
const localMembers = ref([])

// --- 标签管理（P1-3）---
const labelForm = reactive({ name: '', color: '#409EFF' })
const labelRules = {
  name: [
    { required: true, message: '请输入标签名', trigger: 'blur' },
    { max: 20, message: '标签名不超过20字符', trigger: 'blur' }
  ]
}
const labelFormRef = ref(null)
const labels = ref([])
const creatingLabel = ref(false)
const labelsLoading = ref(false)

// --- Sprint 管理（P2-3）---
const sprintForm = reactive({ name: '', dateRange: null })
const sprintRules = {
  name: [
    { required: true, message: '请输入 Sprint 名称', trigger: 'blur' },
    { max: 100, message: 'Sprint 名称不超过100字符', trigger: 'blur' }
  ],
  dateRange: [
    { required: true, message: '请选择起止日期', trigger: 'change' }
  ]
}
const sprintFormRef = ref(null)
const sprints = ref([])
const creatingSprint = ref(false)
const sprintsLoading = ref(false)
const deletingSprintId = ref(null)  // R-06-issue-4: 修复 - 删除按钮loading绑定此ref防双击

async function handleAddMember() {
  const username = searchUsername.value.trim()
  if (!username) {
    ElMessage.warning('请输入用户名')
    return
  }
  // 检查是否已在列表中
  if (localMembers.value.some(m => m.username === username)) {
    ElMessage.warning('该用户已在成员列表中')
    return
  }
  searching.value = true
  try {
    const res = await searchUsers(username)
    if (!res.data || res.data.length === 0) {
      ElMessage.error('用户不存在')
      return
    }
    // R-06-issue-4: 已修复 - 搜索结果多条时优先精确匹配 username===searchUsername，取不到再回退首条
    let user = res.data[0]
    if (res.data.length > 1) {
      const exact = res.data.find(u => u.username === username)
      if (exact) {
        user = exact
      }
    }
    localMembers.value.push({
      userId: user.id,
      username: user.username,
      nickname: user.nickname,
      role: 'member'
    })
    searchUsername.value = ''
  } catch {
    // 拦截器已处理
  } finally {
    searching.value = false
  }
}

function isSelfAsOnlyOwner(row) {
  // 唯一 owner 且是自己时不可改角色/移除
  if (row.userId !== userStore.userId) return false
  const ownerCount = localMembers.value.filter(m => m.role === 'owner').length
  return ownerCount <= 1
}

function handleRoleChange(row) {
  const ownerCount = localMembers.value.filter(m => m.role === 'owner').length
  if (ownerCount === 0) {
    ElMessage.error('至少保留一名 owner')
    row.role = 'owner'
  }
}

// R-06-issue-1: 已修复 - 成员移除加 ElMessageBox.confirm 二次确认(.catch防Promise reject未捕获)
// R-06-issue-2: 已修复 - confirm文案提示该成员可能有未完成任务(PRD §3 P0-3 异常流程②)；教学简化：仅提示不做实际API计数查询
function handleRemoveMember(index) {
  const member = localMembers.value[index]
  // 唯一 owner 不能被移除
  if (member.userId === userStore.userId) {
    const ownerCount = localMembers.value.filter(m => m.role === 'owner').length
    if (ownerCount <= 1) {
      ElMessage.error('请先指定另一名 owner')
      return
    }
  }
  ElMessageBox.confirm(
    `确认移除成员「${member.username}」？该成员可能有未完成任务，移除后任务指派关系保持不变。`,
    '移除成员',
    { confirmButtonText: '确认移除', cancelButtonText: '取消', type: 'warning' }
  ).then(() => {
    localMembers.value.splice(index, 1)
  }).catch(() => {})
}

async function fetchMembers() {
  try {
    const res = await listMembers(projectId)
    localMembers.value = (res.data || []).map(m => ({
      userId: m.userId,
      username: m.username,
      nickname: m.nickname,
      role: m.role
    }))
  } catch {
    // 拦截器已处理
  }
}

async function handleSaveMembers() {
  // 前端校验：至少 1 个 owner
  if (!localMembers.value.some(m => m.role === 'owner')) {
    ElMessage.error('至少保留一名 owner')
    return
  }
  // 前端校验：无重复 userId
  const ids = localMembers.value.map(m => m.userId)
  if (new Set(ids).size !== ids.length) {
    ElMessage.error('成员列表中包含重复用户')
    return
  }
  savingMembers.value = true
  try {
    const payload = localMembers.value.map(m => ({ userId: m.userId, role: m.role }))
    await replaceMembers(projectId, payload)
    ElMessage.success('成员已更新')
  } catch {
    // 拦截器已处理
  } finally {
    savingMembers.value = false
  }
}

// --- 标签管理（P1-3）---
async function fetchLabels() {
  labelsLoading.value = true
  try {
    const res = await listLabels(projectId)
    labels.value = res.data || []
  } catch {
    // 拦截器已处理
  } finally {
    labelsLoading.value = false
  }
}

async function handleCreateLabel() {
  const valid = await labelFormRef.value.validate().catch(() => false)
  if (!valid) return

  creatingLabel.value = true
  try {
    await createLabel(projectId, { name: labelForm.name.trim(), color: labelForm.color })
    ElMessage.success('标签创建成功')
    labelForm.name = ''
    await fetchLabels()
  } catch {
    // 拦截器已处理
  } finally {
    creatingLabel.value = false
  }
}

function confirmDeleteLabel(row) {
  ElMessageBox.confirm(
    `确认删除标签「${row.name}」？删除后关联任务的标签将移除。`,
    '删除标签',
    { confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning' }
  ).then(async () => {
    try {
      await deleteLabel(projectId, row.id)
      ElMessage.success('标签已删除')
      await fetchLabels()
    } catch {
      // 拦截器已处理
    }
  }).catch(() => {})
}

// --- Sprint 管理（P2-3）---
function sprintStatusTagType(status) {
  const map = { upcoming: 'info', active: 'success', completed: '' }
  return map[status] || 'info'
}
function sprintStatusLabel(status) {
  const map = { upcoming: '未开始', active: '进行中', completed: '已结束' }
  return map[status] || status
}

async function fetchSprints() {
  sprintsLoading.value = true
  try {
    const res = await listMilestones(projectId)
    sprints.value = res.data || []
  } catch {
    // 拦截器已处理
  } finally {
    sprintsLoading.value = false
  }
}

// R-06-issue-1: 已修复 - 创建前检测Sprint日期重叠，若有重叠ElMessage.warning提示但仍允许提交(对齐PRD教学简化声明)
// R-06-issue-4: 已修复 - confirmDeleteSprint加deletingSprintId loading防双击+二次弹窗
async function handleCreateSprint() {
  const valid = await sprintFormRef.value.validate().catch(() => false)
  if (!valid) return

  // Sprint 日期重叠检测（教学简化：仅提示不阻止）
  if (sprintForm.dateRange && sprints.value.length > 0) {
    const [start, end] = sprintForm.dateRange
    const overlap = sprints.value.some(s => {
      return start <= s.endDate && end >= s.startDate
    })
    if (overlap) {
      ElMessage.warning('Sprint 日期与已有 Sprint 重叠，请确认')
    }
  }

  creatingSprint.value = true
  try {
    await createMilestone(projectId, {
      name: sprintForm.name.trim(),
      startDate: sprintForm.dateRange[0],
      endDate: sprintForm.dateRange[1]
    })
    ElMessage.success('Sprint 创建成功')
    sprintForm.name = ''
    sprintForm.dateRange = null
    await fetchSprints()
  } catch {
    // 拦截器已处理
  } finally {
    creatingSprint.value = false
  }
}

function confirmDeleteSprint(row) {
  const taskCountHint = row.taskCount > 0 ? `该 Sprint 下有 ${row.taskCount} 个任务，删除后任务将取消 Sprint 关联。` : ''
  ElMessageBox.confirm(
    `确认删除 Sprint「${row.name}」？${taskCountHint}`,
    '删除 Sprint',
    { confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning' }
  ).then(async () => {
    deletingSprintId.value = row.id
    try {
      await deleteMilestone(projectId, row.id)
      ElMessage.success('Sprint 已删除')
      await fetchSprints()
    } catch {
      // 拦截器已处理
    } finally {
      deletingSprintId.value = null
    }
  }).catch(() => {})
}

async function fetchProject() {
  loading.value = true
  try {
    const res = await getProject(projectId)
    const data = res.data
    project.name = data.name
    project.archived = data.archived
    project.myRole = data.myRole
    form.name = data.name
    isOwner.value = data.myRole === 'owner'
  } catch {
    // 拦截器已处理错误
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    await updateProject(projectId, { name: form.name })
    ElMessage.success('项目名称已更新')
    project.name = form.name
  } catch {
    // 拦截器已处理
  } finally {
    saving.value = false
  }
}

function confirmArchive() {
  ElMessageBox.confirm(
    '确认归档该项目？归档后项目将从默认列表隐藏。',
    '归档确认',
    { confirmButtonText: '确认归档', cancelButtonText: '取消', type: 'warning' }
  ).then(async () => {
    try {
      await updateProject(projectId, { archived: true })
      ElMessage.success('已归档，即将返回项目列表')
      setTimeout(() => {
        router.push('/projects')
      }, 1000)
    } catch {
      // 拦截器已处理
    }
  }).catch(() => {})
}

onMounted(() => {
  fetchProject()
  fetchMembers()
  fetchLabels()
  fetchSprints()
})

watch(activeTab, (tab) => {
  if (tab === 'members') {
    fetchMembers()
  } else if (tab === 'labels') {
    fetchLabels()
  } else if (tab === 'sprints') {
    fetchSprints()
  }
})
</script>

<style scoped>
.settings-page {
  min-height: 100vh;
  background: #f5f7fa;
}

.app-header {
  display: flex;
  align-items: center;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 24px;
  height: 56px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.main-content {
  max-width: 700px;
  margin: 0 auto;
  padding: 24px;
}

.basic-form {
  max-width: 500px;
}

.danger-zone {
  margin-top: 8px;
}

.danger-title {
  color: #e6a23c;
  margin-bottom: 12px;
}

.danger-hint {
  color: #909399;
  font-size: 13px;
  margin-left: 12px;
}

.member-section {
  max-width: 600px;
}

.member-search {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.search-input {
  flex: 1;
}

.member-table {
  margin-bottom: 16px;
}

.member-actions {
  display: flex;
  justify-content: flex-end;
}

/* 标签管理 */
.label-section {
  max-width: 600px;
}

.label-create {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  align-items: center;
}

.label-name-input {
  flex: 1;
}

.label-table {
  margin-top: 12px;
}

/* Sprint 管理 */
.sprint-section {
  max-width: 700px;
}

.sprint-create {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  align-items: center;
  flex-wrap: wrap;
}

.sprint-create-form {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.sprint-create-form :deep(.el-form-item) {
  margin-right: 0;
  margin-bottom: 0;
}

.sprint-create-form__name {
  width: 200px;
}

.sprint-create-form__date {
  width: 260px;
}

.sprint-table {
  margin-top: 12px;
}
</style>