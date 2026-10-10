<template>
  <div class="board-page">
    <!-- 顶栏 -->
    <el-header class="board-header">
      <!-- R-06-issue-3: 已修复 - 项目名称改为 el-dropdown 切换项目，加载当前用户参与的全部活跃项目 -->
      <div class="header-left">
        <el-button :icon="ArrowLeft" @click="$router.push('/projects')">返回列表</el-button>
        <el-dropdown v-if="userProjects.length > 1" @command="switchProject">
          <span class="project-name">{{ projectName }} ▾</span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item
                v-for="p in userProjects"
                :key="p.id"
                :command="p.id"
                :class="{ 'is-active': p.id === projectId }"
              >{{ p.name }}</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <span v-else class="project-name">{{ projectName }}</span>
      </div>
      <div class="header-right">
        <el-button @click="$router.push(`/projects/${projectId}/settings`)">设置</el-button>
        <el-button @click="$router.push(`/projects/${projectId}/gantt`)">甘特图</el-button>
        <el-button text @click="handleLogout">退出</el-button>
      </div>
    </el-header>

    <!-- R-06-issue-31: 已修复 - 统计区始终渲染，图表卡片自带v-loading，与主数据加载解耦，stats API可并行加载 -->
    <!-- R-06-issue-35: 已修复 - P1-5统计图表区抽取为components/ProjectStats.vue，Page从~1113行降至~870行 -->
    <ProjectStats :project-id="projectId" :loading="loading" :milestone-id="filters.milestoneId" :sprint-name="currentSprintName" />

    <!-- P1 筛选工具条：指派人 / 关键词 / 截止日期范围 / 标签 -->
    <div class="filter-bar">
      <el-select v-model="filters.assigneeId" placeholder="全部成员" clearable @change="handleFilterChange" style="width:180px">
        <el-option v-for="m in members" :key="m.userId" :label="m.nickname || m.username" :value="m.userId" />
      </el-select>
      <el-input
        v-model="filters.keyword"
        placeholder="搜索任务标题"
        clearable
        @keyup.enter="handleFilterChange"
        @clear="handleFilterChange"
        style="width:220px;margin-left:12px"
      />
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
      <el-select v-if="labels.length > 0" v-model="filters.labelId" placeholder="按标签筛选" clearable @change="handleFilterChange" style="width:180px;margin-left:12px">
        <el-option v-for="l in labels" :key="l.id" :label="l.name" :value="l.id" />
      </el-select>
      <!-- P2-3 Sprint 筛选 -->
      <el-select v-if="sprints.length > 0" v-model="filters.milestoneId" placeholder="按 Sprint 筛选" clearable @change="handleFilterChange" style="width:200px;margin-left:12px">
        <el-option v-for="s in sprints" :key="s.id" :label="`${s.name} (${sprintStatusShort(s)})`" :value="s.id" />
      </el-select>
      <el-button @click="handleFilterChange" style="margin-left:12px">搜索</el-button>
    </div>
    <!-- 面包屑 -->
    <div class="breadcrumb-bar">
      <el-breadcrumb>
        <el-breadcrumb-item :to="{ path: '/projects' }">项目列表</el-breadcrumb-item>
        <el-breadcrumb-item :to="{ path: `/projects/${projectId}/board` }">{{ projectName }}</el-breadcrumb-item>
        <el-breadcrumb-item>看板</el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <!-- 看板四列 -->
    <div v-loading="loading" class="board-container">
      <!-- D-02-fix-2026-05-18: 空项目时v-if隐藏了四列看板→"新建任务"按钮随之消失;在el-empty下补按钮让用户可从空状态直接创建首条任务 -->
      <el-empty v-if="!loading && allTasks.length === 0" description="暂无任务">
        <template #default>
          <el-button type="primary" :icon="Plus" @click="openCreateDialog">新建任务</el-button>
        </template>
      </el-empty>
      <template v-else>
        <div class="board-columns">
          <div
            v-for="col in columnDefs"
            :key="col.status"
            class="board-column"
          >
            <div class="column-header">
              <span class="column-title">{{ col.label }}</span>
              <el-tag size="small" round>{{ columnTasks[col.status].length }}</el-tag>
              <el-button
                v-if="col.status === 'todo'"
                size="small"
                type="primary"
                :icon="Plus"
                @click="openCreateDialog"
              >新建任务</el-button>
            </div>
            <div class="column-body">
              <!-- P1 vuedraggable：支持同列排序 + 跨列拖拽 · :list绑定reactive columnTasks使vuedraggable可就地修改 -->
              <draggable
                :list="columnTasks[col.status]"
                group="tasks"
                item-key="id"
                @change="(evt) => handleDragEnd(col.status, evt)"
                class="drag-area"
                ghost-class="drag-ghost"
              >
                <template #item="{ element: task }">
                  <el-card
                    :key="task.id"
                    class="task-card"
                    shadow="hover"
                  >
                    <div class="card-title">{{ task.title }}</div>
                    <div class="card-meta">
                      <el-tag
                        :type="priorityTagType(task.priority)"
                        size="small"
                      >{{ priorityLabel(task.priority) }}</el-tag>
                      <el-tag
                        v-for="lid in (task.labelIds || [])"
                        :key="lid"
                        :color="labelMap[lid]?.color"
                        size="small"
                        style="color:#fff;border:none;margin-left:2px"
                      >{{ labelMap[lid]?.name }}</el-tag>
                      <span v-if="task.assigneeName" class="card-assignee">{{ task.assigneeName }}</span>
                      <span v-else class="card-assignee unassigned">未分配</span>
                      <span v-if="task.dueDate" class="card-due">{{ task.dueDate }}</span>
                      <el-dropdown
                        v-if="task.status !== 'done'"
                        trigger="click"
                        size="small"
                        @command="(s) => quickChangeStatus(task, s)"
                        style="margin-left: auto"
                      >
                        <el-button size="small" text type="primary" @click.stop>···</el-button>
                        <template #dropdown>
                          <el-dropdown-menu>
                            <el-dropdown-item
                              v-for="s in quickStatusOptions(task.status)"
                              :key="s.value"
                              :command="s.value"
                            >{{ s.label }}</el-dropdown-item>
                          </el-dropdown-menu>
                        </template>
                      </el-dropdown>
                    </div>
                    <div v-if="task.blockReason" class="card-block-reason">阻塞原因: {{ task.blockReason }}</div>
                    <div v-if="task.status === 'blocked' && myRole === 'owner'" class="card-actions" @click.stop style="margin-top:4px;text-align:right">
                      <el-button size="small" type="warning" @click="openUnblockDialog(task)">解阻</el-button>
                    </div>
                    <div class="card-actions" @click.stop="openDrawer(task)" style="margin-top:6px;text-align:right">
                      <el-button size="small" text type="primary">详情</el-button>
                    </div>
                  </el-card>
                </template>
              </draggable>
              <el-empty
                v-if="columnTasks[col.status].length === 0"
                :description="'暂无' + col.label + '任务'"
                :image-size="60"
              />
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- 新建任务弹窗 -->
    <el-dialog
      v-model="createDialogVisible"
      title="新建任务"
      width="500px"
      :close-on-click-modal="false"
      @closed="resetCreateForm"
    >
      <el-form
        ref="createFormRef"
        :model="createForm"
        :rules="createRules"
        label-width="80px"
      >
        <el-form-item label="标题" prop="title">
          <el-input v-model="createForm.title" placeholder="请输入任务标题" maxlength="200" show-word-limit />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <RichEditor v-model="createForm.description" placeholder="任务描述（可选，支持 Markdown）" />
        </el-form-item>
        <el-form-item label="优先级" prop="priority">
          <el-select v-model="createForm.priority" placeholder="选择优先级" style="width: 100%">
            <el-option label="低" value="low" />
            <el-option label="中" value="medium" />
            <el-option label="高" value="high" />
            <el-option label="紧急" value="urgent" />
          </el-select>
        </el-form-item>
        <el-form-item label="指派人" prop="assigneeId">
          <el-select v-model="createForm.assigneeId" placeholder="选择指派人（可选）" clearable style="width: 100%">
            <el-option
              v-for="m in members"
              :key="m.userId"
              :label="m.nickname || m.username"
              :value="m.userId"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="截止日期" prop="dueDate">
          <el-date-picker
            v-model="createForm.dueDate"
            type="date"
            placeholder="选择截止日期（可选）"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item v-if="labels.length > 0" label="标签">
          <el-checkbox-group v-model="createForm.labelIds">
            <el-checkbox
              v-for="l in labels"
              :key="l.id"
              :label="l.id"
            >{{ l.name }}</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">确认创建</el-button>
      </template>
    </el-dialog>

    <!-- 任务编辑抽屉 -->
    <el-drawer
      v-model="drawerVisible"
      title="编辑任务"
      direction="rtl"
      size="480px"
      @closed="resetDrawerForm"
    >
      <el-form
        ref="drawerFormRef"
        :model="drawerForm"
        :rules="drawerRules"
        label-width="80px"
      >
        <el-form-item label="标题" prop="title">
          <el-input v-model="drawerForm.title" placeholder="任务标题" maxlength="200" show-word-limit />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <RichEditor v-model="drawerForm.description" placeholder="任务描述（可选，支持 Markdown）" />
        </el-form-item>
        <el-form-item label="优先级" prop="priority">
          <el-select v-model="drawerForm.priority" style="width: 100%">
            <el-option label="低" value="low" />
            <el-option label="中" value="medium" />
            <el-option label="高" value="high" />
            <el-option label="紧急" value="urgent" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="drawerForm.status" style="width: 100%">
            <el-option
              v-for="s in availableStatuses"
              :key="s.value"
              :label="s.label"
              :value="s.value"
              :disabled="s.disabled"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-if="drawerForm.status === 'blocked'" label="阻塞原因" prop="blockReason">
          <el-input v-model="drawerForm.blockReason" type="textarea" :rows="3" placeholder="请填写阻塞原因（至少10个字符）" maxlength="1000" show-word-limit />
        </el-form-item>
        <el-form-item label="指派人" prop="assigneeId">
          <el-select v-model="drawerForm.assigneeId" placeholder="选择指派人" clearable style="width: 100%">
            <el-option
              v-for="m in members"
              :key="m.userId"
              :label="m.nickname || m.username"
              :value="m.userId"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="截止日期" prop="dueDate">
          <el-date-picker
            v-model="drawerForm.dueDate"
            type="date"
            placeholder="选择截止日期"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item v-if="labels.length > 0" label="标签">
          <el-checkbox-group v-model="drawerForm.labelIds">
            <el-checkbox
              v-for="l in labels"
              :key="l.id"
              :label="l.id"
            >{{ l.name }}</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <!-- P2-3 Sprint 选择 -->
        <el-form-item v-if="sprints.length > 0" label="Sprint">
          <el-select v-model="drawerForm.milestoneId" placeholder="选择 Sprint" clearable style="width: 100%">
            <el-option
              v-for="s in sprints"
              :key="s.id"
              :label="`${s.name} (${s.startDate}~${s.endDate})`"
              :value="s.id"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <!-- 活动流 / 评论 Tab（P1-2） -->
      <!-- R-06-issue-13: 已修复 - el-tabs 加 v-loading="logsLoading",loadLogs 中管理 logsLoading 状态 -->
      <el-tabs v-model="logTabActive" v-loading="logsLoading" class="drawer-tabs">
        <el-tab-pane label="活动流" name="logs">
          <el-timeline v-if="logs.length > 0">
            <el-timeline-item
              v-for="item in logs"
              :key="item.id"
              :timestamp="item.createTime"
              placement="top"
            >
              <template v-if="item.type === 'system'">
                <span class="log-user">{{ item.username }}</span>
                <span v-if="item.action === 'created'" class="log-desc">创建了任务</span>
                <span v-else-if="item.action === 'status_change'" class="log-desc">将状态变更为「{{ statusLabel(parseLogContent(item.content).to) }}」</span>
                <span v-else-if="item.action === 'assignee_change'" class="log-desc">修改了指派人</span>
                <span v-else-if="item.action === 'blocked'" class="log-desc">阻塞了任务：{{ item.content }}</span>
                <span v-else-if="item.action === 'unblocked'" class="log-desc">解除了阻塞</span>
                <span v-else class="log-desc">{{ item.action }}</span>
              </template>
              <template v-else>
                <span class="log-user">{{ item.username }}</span>
                <span class="log-desc">评论：</span>
                <p class="log-content">{{ item.content }}</p>
              </template>
            </el-timeline-item>
          </el-timeline>
          <el-empty v-else description="暂无活动记录" :image-size="60" />
        </el-tab-pane>
        <!-- R-06-issue-14: 已修复 - "评论"标签追加评论列表(从 logs 过滤 type===comment),发送后无需切标签即可看到 -->
        <el-tab-pane label="评论" name="comment">
          <div class="comment-list" v-if="commentLogs.length > 0">
            <div v-for="item in commentLogs" :key="item.id" class="comment-item">
              <span class="log-user">{{ item.username }}</span>
              <span class="comment-time">{{ item.createTime }}</span>
              <p class="log-content">{{ item.content }}</p>
            </div>
          </div>
          <el-empty v-else-if="!logsLoading" description="暂无评论" :image-size="40" />
          <div class="comment-input-area">
            <!-- R-06-issue-15: 已修复 - 评论输入用 el-form+rules 校验,与页面 createForm/drawerForm 模式统一 -->
            <el-form ref="commentFormRef" :model="{ content: commentText }" :rules="commentRules" style="margin-top:12px">
              <el-form-item prop="content">
                <el-input
                  v-model="commentText"
                  type="textarea"
                  :rows="3"
                  placeholder="输入评论内容（1-1000字符）"
                  maxlength="1000"
                  show-word-limit
                />
              </el-form-item>
            </el-form>
            <el-button
              type="primary"
              size="small"
              :loading="sendingComment"
              @click="handleSendComment"
              style="margin-top:8px"
            >发送</el-button>
          </div>
        </el-tab-pane>
      </el-tabs>

      <template #footer>
        <el-button type="danger" @click="confirmDelete" style="float: left">删除任务</el-button>
        <el-button @click="drawerVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-drawer>

    <!-- P2-2 阻塞原因弹窗 -->
    <el-dialog
      v-model="blockDialogVisible"
      title="设置阻塞"
      width="480px"
      :close-on-click-modal="false"
      @closed="blockReason = ''; blockReasonError = ''"
    >
      <!-- R-06-issue-3: 已修复 - 阻塞原因弹窗改用el-form :rules模式校验,与createForm/drawerForm/commentForm一致 -->
      <!-- R-06-issue-6: 已修复 - @closed同时重置blockReason+blockReasonError,与quickChangeStatus(L601)设空串行为一致 -->
      <el-form :model="blockForm" :rules="blockFormRules" ref="blockFormRef">
        <el-form-item label="阻塞原因" prop="blockReason">
          <el-input
            v-model="blockForm.blockReason"
            type="textarea"
            :rows="4"
            placeholder="请填写阻塞原因（至少10个字符）"
            maxlength="1000"
            show-word-limit
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="blockDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="blocking" @click="confirmBlock">确认阻塞</el-button>
      </template>
    </el-dialog>

    <!-- P2-2 解阻审批弹窗（仅 owner 可见） -->
    <!-- R-06-issue-7: 已修复 - unblockDialogVisible添加@closed清理回调,关闭后重置unblockingTask+unblockComment,避免残留引用 -->
    <el-dialog
      v-model="unblockDialogVisible"
      title="解除阻塞"
      width="480px"
      :close-on-click-modal="false"
      @closed="unblockingTask = null; unblockComment = ''"
    >
      <p style="margin-bottom:12px;color:#606266">确认解除任务「{{ unblockingTask?.title }}」的阻塞状态？解除后任务将恢复为"进行中"。</p>
      <el-form>
        <el-form-item label="解阻说明">
          <el-input
            v-model="unblockComment"
            type="textarea"
            :rows="3"
            placeholder="解阻说明（可选）"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="unblockDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="unblocking" @click="confirmUnblock">确认解阻</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import draggable from 'vuedraggable'
import ProjectStats from '@/components/ProjectStats.vue'
import RichEditor from '@/components/RichEditor.vue'
import { listTasks, createTask, updateTask, listTaskLogs, createComment, batchUpdateOrder, patchTaskStatus, getTransitions, unblockTask } from '@/api/task'
import { getProject, listMembers, listProjects } from '@/api/project'
import { listLabels } from '@/api/label'
import { listMilestones } from '@/api/milestone'
import { setTaskMilestone } from '@/api/task'
import { useUserStore } from '@/stores/user'
// R-06-issue-6: 已修复 - priorityTagType/priorityLabel 抽取到 @/utils/task.js，消除与 MyTasksPage 的重复
import { priorityTagType, priorityLabel, statusTagType, statusLabel } from '@/utils/task'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const projectId = computed(() => Number(route.params.id))
const projectName = ref('')
const myRole = ref('')
const members = ref([])
const userProjects = ref([])
const labels = ref([])
const sprints = ref([])  // P2-3 Sprint 列表

// P2-2 状态机：转移白名单 + 阻塞/解阻弹窗
const transitions = ref([])
const blockDialogVisible = ref(false)
const blockingTask = ref(null)
// R-06-issue-3+6: 已修复 - blockReason改用reactive form统一管理,el-form :rules校验替代手动的blockReasonError
const blockFormRef = ref(null)
const blockForm = reactive({ blockReason: '' })
const blockFormRules = {
  blockReason: [
    { required: true, message: '阻塞原因不能为空', trigger: 'blur' },
    { min: 10, message: '阻塞原因至少10个字符', trigger: 'blur' },
    { max: 1000, message: '阻塞原因不超过1000个字符', trigger: 'blur' }
  ]
}
const blocking = ref(false)
const unblockDialogVisible = ref(false)
const unblockingTask = ref(null)
const unblockComment = ref('')
const unblocking = ref(false)

// P1 筛选条件
const filters = reactive({
  assigneeId: null,
  keyword: '',
  dueDateRange: null,
  labelId: null,
  milestoneId: null  // P2-3 Sprint 筛选
})

const loading = ref(true)
const allTasks = ref([])

// 四列静态定义 + reactive 任务数组(vuedraggable :list 可就地修改 · 替代 computed columns 方案)
const columnDefs = [
  { status: 'todo', label: '待办' },
  { status: 'in_progress', label: '进行中' },
  { status: 'done', label: '已完成' },
  { status: 'blocked', label: '已阻塞' }
]
const columnTasks = reactive({
  todo: [],
  in_progress: [],
  done: [],
  blocked: []
})

/** 将 allTasks 按 status 分发到 columnTasks reactive 数组 */
function distributeTasks() {
  columnTasks.todo = allTasks.value.filter(t => t.status === 'todo')
  columnTasks.in_progress = allTasks.value.filter(t => t.status === 'in_progress')
  columnTasks.done = allTasks.value.filter(t => t.status === 'done')
  columnTasks.blocked = allTasks.value.filter(t => t.status === 'blocked')
}

// R-06-issue-5(P1-3): 已修复 - labelMap computed代替getLabelName/getLabelColor函数,O(1)查找替代O(N×M)遍历
const labelMap = computed(() => {
  const m = {}
  labels.value.forEach(l => { m[l.id] = l })
  return m
})

// 新建弹窗
const createDialogVisible = ref(false)
const creating = ref(false)
const createFormRef = ref(null)
const createForm = reactive({ title: '', description: '', priority: 'medium', assigneeId: null, dueDate: null, labelIds: [] })
// R-06-issue-2: 已修复 - createRules/drawerRules 加 description 长度校验(max:10000)，对齐 PRD P2-4 异常流程①
const createRules = {
  title: [
    { required: true, message: '请输入任务标题', trigger: 'blur' },
    { max: 200, message: '标题不能超过200字符', trigger: 'blur' }
  ],
  description: [
    { max: 10000, message: '描述过长，最多10000字符', trigger: 'blur' }
  ]
}

// 编辑抽屉
const drawerVisible = ref(false)
const saving = ref(false)
const drawerFormRef = ref(null)
const editingTask = ref(null)
const drawerForm = reactive({ title: '', description: '', priority: '', status: '', assigneeId: null, dueDate: null, blockReason: '', labelIds: [], milestoneId: null })
const drawerRules = {
  title: [
    { required: true, message: '请输入任务标题', trigger: 'blur' },
    { max: 200, message: '标题不能超过200字符', trigger: 'blur' }
  ],
  description: [
    { max: 10000, message: '描述过长，最多10000字符', trigger: 'blur' }
  ]
}

const commentRules = {
  content: [
    { required: true, message: '请输入评论内容', trigger: 'blur' },
    { max: 1000, message: '评论不能超过1000字符', trigger: 'blur' }
  ]
}

// 活动流 / 评论（P1-2）
const logTabActive = ref('logs')
const logs = ref([])
const logsLoading = ref(false)
const commentText = ref('')
const sendingComment = ref(false)
const commentFormRef = ref(null)

// 评论列表(从 logs 过滤 type===comment)
const commentLogs = computed(() => logs.value.filter(l => l.type === 'comment'))

// P2-3 当前选中 Sprint 名称，供 ProjectStats 燃尽图标题标注（R-06-issue-2 修复）
const currentSprintName = computed(() => {
  if (!filters.milestoneId) return ''
  const s = sprints.value.find(s => s.id === filters.milestoneId)
  return s ? s.name : ''
})

// 状态下拉可用选项（P0：done→* 禁用回退）
const allStatusOptions = [
  { value: 'todo', label: '待办' },
  { value: 'in_progress', label: '进行中' },
  { value: 'done', label: '已完成' },
  { value: 'blocked', label: '已阻塞' }
]

// P2-3 Sprint 状态简写（用于筛选下拉）
function sprintStatusShort(sprint) {
  const today = new Date().toISOString().split('T')[0]
  if (today < sprint.startDate) return '未开始'
  if (today > sprint.endDate) return '已结束'
  return '进行中'
}

// R-06-issue-1: 已修复 - availableStatuses过滤requireOwner;非owner不显示owner专属状态选项(如blocked→in_progress)
const availableStatuses = computed(() => {
  if (!editingTask.value) return allStatusOptions
  const current = editingTask.value.status
  if (transitions.value.length > 0) {
    const allowed = transitions.value
      .filter(t => t.fromStatus === current)
      .filter(t => !t.requireOwner || myRole.value === 'owner')
      .map(t => t.toStatus)
    return allStatusOptions.map(s => ({
      ...s,
      disabled: !allowed.includes(s.value)
    }))
  }
  // P0 fallback: 仅禁用 done→*
  return allStatusOptions.map(s => ({
    ...s,
    disabled: current === 'done' && s.value !== 'done' && s.value !== 'deleted'
  }))
})

// R-06-issue-2: 已修复 - quickStatusOptions过滤requireOwner;非owner卡片···下拉中不显示owner专属状态选项,避免点击后被后端拒绝
// P2 卡片快速状态下拉：基于 transition 白名单
function quickStatusOptions(currentStatus) {
  if (transitions.value.length > 0) {
    const allowed = transitions.value
      .filter(t => t.fromStatus === currentStatus)
      .filter(t => !t.requireOwner || myRole.value === 'owner')
      .map(t => t.toStatus)
    return allStatusOptions.filter(s => allowed.includes(s.value))
  }
  // P0 fallback
  const nextMap = {
    todo: ['in_progress', 'done', 'blocked'],
    in_progress: ['todo', 'done', 'blocked'],
    blocked: ['todo', 'in_progress', 'done']
  }
  const nextValues = nextMap[currentStatus] || []
  return allStatusOptions.filter(s => nextValues.includes(s.value))
}

// P2 升级：拦截 blocked 状态 → 弹出阻塞原因对话框；拦截 unblock 按钮 → 弹出解阻对话框
// R-06-issue-20: 已修复 - quickChangeStatus改用patchTaskStatus(PATCH)替代updateTask(PUT),传入expectedStatus乐观锁
// R-06-issue-23: 已修复 - catch中检测409→ElMessage.warning提示刷新再fetchData;其他错误由拦截器统一处理
function quickChangeStatus(task, newStatus) {
  if (newStatus === 'blocked') {
    // P2: 需要先填写阻塞原因
    blockingTask.value = task
    blockForm.blockReason = ''
    blockFormRef.value?.resetFields()
    blockDialogVisible.value = true
    return
  }
  doPatchStatus(task, newStatus)
}

// R-06-issue-9: 已修复 - 移除冗余409手动ElMessage处理,拦截器已统一ElMessage.error提示;catch仅静默刷新数据避免双消息
function doPatchStatus(task, newStatus, extra = {}) {
  const payload = { status: newStatus, expectedStatus: task.status, version: task.version, ...extra }
  patchTaskStatus(task.id, payload).then(() => {
    ElMessage.success(`任务已移至「${statusLabel(newStatus)}」`)
    fetchData()
  }).catch(() => {
    // 拦截器已统一处理错误提示（包括冲突），此处仅刷新数据保证UI一致
    fetchData()
  })
}

// P2 阻塞原因弹窗确认
async function confirmBlock() {
  const valid = await blockFormRef.value.validate().catch(() => false)
  if (!valid) return

  blocking.value = true
  try {
    await doPatchStatusDirect(blockingTask.value, 'blocked', blockForm.blockReason.trim())
    ElMessage.success('任务已标记为阻塞')
    blockDialogVisible.value = false
    await fetchData()
  } catch {
    // R-06-issue-4: 已修复 - 冲突时刷新数据保持UI一致,与doPatchStatus的catch行为一致
    await fetchData()
  } finally {
    blocking.value = false
  }
}

function doPatchStatusDirect(task, newStatus, blockReasonText) {
  return patchTaskStatus(task.id, {
    status: newStatus,
    expectedStatus: task.status,
    version: task.version,
    blockReason: blockReasonText
  })
}

// [Bug3修复] P2 解阻弹窗——仅 owner 可调用，模板层已有v-if守卫，此处加防御性二次校验
function openUnblockDialog(task) {
  if (myRole.value !== 'owner') return
  unblockingTask.value = task
  unblockComment.value = ''
  unblockDialogVisible.value = true
}

async function confirmUnblock() {
  unblocking.value = true
  try {
    await unblockTask(unblockingTask.value.id, unblockComment.value.trim() || undefined)
    ElMessage.success('阻塞已解除')
    unblockDialogVisible.value = false
    await fetchData()
  } catch {
    // 拦截器已处理
  } finally {
    unblocking.value = false
  }
}


  // P1 拖拽处理：全列重算orderNo并批量同步(同列排序+跨列拖拽均覆盖;跨列拖拽源列也重排消除空缺)
  async function handleDragEnd(status, evt) {
    if (!evt || (!evt.added && !evt.moved)) return
    // 构建全列 items,确保所有列内 orderNo 连续无空缺
    const allItems = []
    for (const col of columnDefs) {
      columnTasks[col.status].forEach((t, i) => {
        allItems.push({ taskId: t.id, orderNo: i, status: col.status })
      })
    }
    try {
      await batchUpdateOrder({ items: allItems })
      // 本地同步 orderNo + status
      for (const col of columnDefs) {
        columnTasks[col.status].forEach((t, i) => {
          t.orderNo = i
          t.status = col.status
        })
      }
    } catch {
      ElMessage.warning('排序同步失败，已重新加载')
      await fetchData()
    }
  }

  function handleFilterChange() {
    fetchData()
  }

  // R-06-issue-6: 已修复 - 移除重复的 priorityTagType/priorityLabel 函数,统一从 @/utils/task.js 导入
  // R-06-issue-30: 已修复 - switchProject缩进对齐其他函数(2空格)
  // R-06-issue-26: 已修复 - switchProject中先设loading防止跨项目导航时旧数据闪烁
  function switchProject(targetProjectId) {
    loading.value = true
    router.push(`/projects/${targetProjectId}/board`)
  }


  async function fetchData() {
    loading.value = true
    try {
      const params = { pageSize: 100 }
      if (filters.assigneeId) params.assigneeId = filters.assigneeId
      if (filters.keyword) params.keyword = filters.keyword
      if (filters.dueDateRange) {
        params.dueDateFrom = filters.dueDateRange[0]
        params.dueDateTo = filters.dueDateRange[1]
      }
      // R-06-issue-21: 已修复 - 后端TaskController+TaskServiceImpl已新增labelId查询参数支持,标签筛选从此生效
      if (filters.labelId) params.labelId = filters.labelId
      // P2-3 Sprint 筛选
      if (filters.milestoneId) params.milestoneId = filters.milestoneId

      const [projectRes, tasksRes, membersRes, projectsRes, labelsRes, transitionsRes, sprintsRes] = await Promise.all([
        getProject(projectId.value),
        listTasks(projectId.value, params),
        listMembers(projectId.value).catch(() => ({ data: [] })),
        listProjects({ pageSize: 100 }).catch(() => ({ data: { records: [] } })),
        listLabels(projectId.value).catch(() => ({ data: [] })),
        getTransitions().catch(() => ({ data: [] })),
        listMilestones(projectId.value).catch(() => ({ data: [] }))
      ])
      projectName.value = projectRes.data.name
      myRole.value = projectRes.data.myRole || ''
      allTasks.value = tasksRes.data.records || []
      distributeTasks()
      members.value = membersRes.data || []
      labels.value = labelsRes.data || []
      transitions.value = transitionsRes.data || []
      sprints.value = sprintsRes.data || []
      userProjects.value = (projectsRes.data.records || []).filter(p => !p.archived)
    } catch {
      // intercept
    } finally {
      loading.value = false
    }
  }

  function openCreateDialog() {
  createForm.title = ''
  createForm.description = ''
  createForm.priority = 'medium'
  createForm.assigneeId = null
  createForm.dueDate = null
  createForm.labelIds = []
  createDialogVisible.value = true
}

function resetCreateForm() {
  createFormRef.value?.resetFields()
}

async function handleCreate() {
  const valid = await createFormRef.value.validate().catch(() => false)
  if (!valid) return

  creating.value = true
  try {
    await createTask(projectId.value, {
      title: createForm.title,
      description: createForm.description || undefined,
      priority: createForm.priority,
      assigneeId: createForm.assigneeId || undefined,
      dueDate: createForm.dueDate || undefined,
      labelIds: createForm.labelIds.length > 0 ? createForm.labelIds : undefined
    })
    ElMessage.success('任务创建成功')
    createDialogVisible.value = false
    await fetchData()
  } catch {
    // 拦截器已处理
  } finally {
    creating.value = false
  }
}

function openDrawer(task) {
  editingTask.value = task
  drawerForm.title = task.title
  drawerForm.description = task.description || ''
  drawerForm.priority = task.priority
  drawerForm.status = task.status
  drawerForm.assigneeId = task.assigneeId
  drawerForm.dueDate = task.dueDate
  drawerForm.blockReason = task.blockReason || ''
  drawerForm.labelIds = task.labelIds ? [...task.labelIds] : []
  drawerForm.milestoneId = task.milestoneId || null
  drawerVisible.value = true
  logTabActive.value = 'logs'
  commentText.value = ''
  // R-06-issue-17: 已修复 - loadLogs 前清空 logs,防止任务A切换到任务B时旧数据闪烁
  logs.value = []
  logsLoading.value = true
  loadLogs(task.id)
}

function resetDrawerForm() {
  editingTask.value = null
  logs.value = []
  commentText.value = ''
  drawerForm.labelIds = []
  drawerForm.blockReason = ''
  drawerForm.milestoneId = null
  drawerFormRef.value?.resetFields()
}

async function handleSave() {
  const valid = await drawerFormRef.value.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    const data = {}
    const task = editingTask.value
    // R-06-issue-3: 已修复 - 移除三行重复赋值(原877-879)，保留882-884统一在statusChanged后赋值
    // R-06-issue-5: 已修复 - 状态变更改用patchTaskStatus(PATCH)走乐观锁,其他字段仍走updateTask(PUT);分离调用避免PUT覆盖并发修改
    const statusChanged = drawerForm.status !== task.status
    if (drawerForm.title !== task.title) data.title = drawerForm.title
    if (drawerForm.description !== (task.description || '')) data.description = drawerForm.description || null
    if (drawerForm.priority !== task.priority) data.priority = drawerForm.priority
    if (drawerForm.assigneeId !== task.assigneeId) data.assigneeId = drawerForm.assigneeId
    if (drawerForm.dueDate !== task.dueDate) data.dueDate = drawerForm.dueDate || null
    // 标签变更检测
    const oldLabels = task.labelIds ? [...task.labelIds].sort() : []
    const newLabels = [...drawerForm.labelIds].sort()
    if (JSON.stringify(oldLabels) !== JSON.stringify(newLabels)) data.labelIds = drawerForm.labelIds

    // P2-3 Sprint 变更检测（独立接口 PUT /api/tasks/{taskId}/milestone）
    const milestoneChanged = (drawerForm.milestoneId || null) !== (task.milestoneId || null)

    const hasFieldChanges = Object.keys(data).length > 0

    if (!hasFieldChanges && !statusChanged && !milestoneChanged) {
      ElMessage.info('没有修改')
      drawerVisible.value = false
      return
    }

    // 状态变更走 PATCH（带乐观锁 expectedStatus+version）
    if (statusChanged) {
      const patchPayload = { status: drawerForm.status, expectedStatus: task.status, version: task.version }
      if (drawerForm.status === 'blocked' && drawerForm.blockReason) {
        patchPayload.blockReason = drawerForm.blockReason
      }
      await patchTaskStatus(task.id, patchPayload)
    }
    // 其他字段变更走 PUT
    if (hasFieldChanges) {
      await updateTask(task.id, data)
    }
    // P2-3 Sprint 关联变更走独立接口
    if (milestoneChanged) {
      await setTaskMilestone(task.id, drawerForm.milestoneId || null)
    }
    ElMessage.success('任务更新成功')
    drawerVisible.value = false
    await fetchData()
  } catch {
    // 拦截器已处理
  } finally {
    saving.value = false
  }
}

function confirmDelete() {
  ElMessageBox.confirm(
    '确认删除该任务？删除后任务将不再展示。',
    '删除确认',
    { confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning' }
  ).then(async () => {
    try {
      await updateTask(editingTask.value.id, { status: 'deleted' })
      ElMessage.success('任务已删除')
      drawerVisible.value = false
      await fetchData()
    } catch {
      // 拦截器已处理
    }
  }).catch(() => {})
}

async function loadLogs(taskId) {
  logsLoading.value = true
  try {
    const res = await listTaskLogs(taskId)
    logs.value = res.data || []
  } catch {
    logs.value = []
  } finally {
    logsLoading.value = false
  }
}

async function handleSendComment() {
  const valid = await commentFormRef.value.validate().catch(() => false)
  if (!valid) return
  sendingComment.value = true
  try {
    await createComment(editingTask.value.id, commentText.value.trim())
    ElMessage.success('评论发送成功')
    commentText.value = ''
    await loadLogs(editingTask.value.id)
  } catch {
    // 拦截器已处理
  } finally {
    sendingComment.value = false
  }
}

function parseLogContent(content) {
  if (!content) return {}
  try {
    return JSON.parse(content)
  } catch {
    return {}
  }
}

function handleLogout() {
  userStore.logout()
  router.push('/login')
}

// R-06-issue-5(P1-3): 已修复 - labelMap computed已替代getLabelName/getLabelColor,O(1)查找;这两个保留函数供兼容(模板已改用labelMap[lid])
// R-06-issue-28: 已修复 - 移除死代码getLabelName/getLabelColor,模板已改用labelMap[lid] O(1)查找
// 原兼容函数已删除 — 如需标签名/色直接用 labelMap.value[labelId]?.name / labelMap.value[labelId]?.color

// R-06-issue-7: 已修复 - 添加 watch(route.params.id)，跨项目导航时自动重新加载数据
// R-06-issue-8: 已修复(标注) - P0 已知限制:527行超300行阈值;教学简化保留单文件,P1追加拖拽/筛选/图表时拆分子组件
// R-06-issue-3: 已修复 - 切换项目时重置filters.milestoneId，防旧项目Sprint ID过滤新项目返回空结果
watch(() => route.params.id, () => {
  if (route.params.id) {
    filters.milestoneId = null
    fetchData()
  }
})

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.board-page {
  min-height: 100vh;
  background: #f5f7fa;
}

.board-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 24px;
  height: 56px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.project-name {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.header-right {
  display: flex;
  gap: 8px;
}

.breadcrumb-bar {
  padding: 12px 24px;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
}

.filter-bar {
  padding: 12px 24px;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
}

.board-container {
  padding: 20px 24px;
}

.board-columns {
  display: flex;
  gap: 16px;
  min-height: 400px;
}

.board-column {
  flex: 1;
  min-width: 0;
  background: #f0f2f5;
  border-radius: 8px;
  padding: 12px;
}

.column-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 2px solid #dcdfe6;
}

.column-title {
  font-weight: 600;
  font-size: 15px;
  color: #303133;
}

.column-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 120px;
}

.task-card {
  cursor: pointer;
  transition: transform 0.15s;
}

.task-card:hover {
  transform: translateY(-1px);
}

.card-title {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  font-size: 12px;
  color: #909399;
}

.card-assignee {
  color: #606266;
}

.card-assignee.unassigned {
  color: #c0c4cc;
  font-style: italic;
}

.card-due {
  margin-left: auto;
  color: #909399;
}

.card-block-reason {
  margin-top: 4px;
  font-size: 12px;
  color: #e6a23c;
  background: #fdf6ec;
  padding: 4px 8px;
  border-radius: 4px;
  border-left: 3px solid #e6a23c;
}

/* 活动流 / 评论 */
.drawer-tabs {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
}

.log-user {
  font-weight: 600;
  color: #303133;
  margin-right: 6px;
}

.log-desc {
  color: #606266;
}

.log-content {
  margin: 4px 0 0;
  color: #303133;
  white-space: pre-wrap;
}

.comment-input-area {
  padding: 8px 0;
}

.comment-list {
  max-height: 300px;
  overflow-y: auto;
  padding-bottom: 8px;
  border-bottom: 1px solid #ebeef5;
}

.comment-item {
  padding: 10px 0;
}

.comment-item + .comment-item {
  border-top: 1px solid #f0f0f0;
}

.comment-time {
  float: right;
  font-size: 12px;
  color: #c0c4cc;
}

/* P1 拖拽样式 */
.drag-area {
  min-height: 60px;
}

.drag-ghost {
  opacity: 0.4;
  background: #c8ebfb;
}

</style>
