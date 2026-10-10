<template>
  <el-card shadow="never">
    <el-tabs v-model="activeTab" @tab-change="onTabChange">
      <!-- 打卡审核 -->
      <el-tab-pane label="打卡审核" name="checkin">
        <div class="toolbar">
          <el-radio-group v-model="checkinStatus" @change="loadCheckins(1)">
            <el-radio-button :value="undefined">全部</el-radio-button>
            <el-radio-button :value="0">待审核</el-radio-button>
            <el-radio-button :value="1">已通过</el-radio-button>
            <el-radio-button :value="2">已删除</el-radio-button>
          </el-radio-group>
        </div>
        <el-table :data="checkinRecords" v-loading="checkinLoading" stripe>
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="userNickname" label="作者" width="100" />
          <el-table-column prop="content" label="打卡内容" min-width="180" show-overflow-tooltip />
          <el-table-column label="AI 复盘" min-width="200" show-overflow-tooltip>
            <template #default="{ row }">
              <span class="ai-text">{{ row.aiReview || '—' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="createdAt" label="提交时间" width="165" />
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <el-button
                v-if="row.status === 0"
                type="success"
                size="small"
                @click="auditCheckin(row, 1)"
              >通过</el-button>
              <el-button
                v-if="row.status !== 2"
                type="danger"
                size="small"
                plain
                @click="auditCheckin(row, 2)"
              >删除</el-button>
              <span v-else class="admin-tag">—</span>
            </template>
          </el-table-column>
        </el-table>
        <el-pagination
          class="pager"
          layout="total, prev, pager, next"
          :total="checkinTotal"
          :current-page="checkinPage"
          :page-size="size"
          @current-change="loadCheckins"
        />
      </el-tab-pane>

      <!-- 帖子审核 -->
      <el-tab-pane label="帖子审核" name="post">
        <div class="toolbar">
          <el-radio-group v-model="postStatus" @change="loadPosts(1)">
            <el-radio-button :value="undefined">全部</el-radio-button>
            <el-radio-button :value="0">待审核</el-radio-button>
            <el-radio-button :value="1">已通过</el-radio-button>
            <el-radio-button :value="2">已删除</el-radio-button>
          </el-radio-group>
        </div>
        <el-table :data="postRecords" v-loading="postLoading" stripe>
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="userNickname" label="作者" width="100" />
          <el-table-column prop="category" label="分类" width="90" />
          <el-table-column prop="title" label="标题" min-width="160" show-overflow-tooltip />
          <el-table-column prop="content" label="内容" min-width="200" show-overflow-tooltip />
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="createdAt" label="发布时间" width="165" />
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <el-button
                v-if="row.status === 0"
                type="success"
                size="small"
                @click="auditPost(row, 1)"
              >通过</el-button>
              <el-button
                v-if="row.status !== 2"
                type="danger"
                size="small"
                plain
                @click="auditPost(row, 2)"
              >删除</el-button>
              <span v-else class="admin-tag">—</span>
            </template>
          </el-table-column>
        </el-table>
        <el-pagination
          class="pager"
          layout="total, prev, pager, next"
          :total="postTotal"
          :current-page="postPage"
          :page-size="size"
          @current-change="loadPosts"
        />
      </el-tab-pane>
    </el-tabs>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getAdminCheckins,
  updateCheckinStatus,
  getAdminPosts,
  updatePostStatus
} from '../utils/request'

const activeTab = ref('checkin')
const size = ref(10)

// 打卡审核
const checkinRecords = ref([])
const checkinTotal = ref(0)
const checkinPage = ref(1)
const checkinStatus = ref(0)
const checkinLoading = ref(false)

// 帖子审核
const postRecords = ref([])
const postTotal = ref(0)
const postPage = ref(1)
const postStatus = ref(0)
const postLoading = ref(false)

function statusText(s) {
  return s === 0 ? '待审核' : s === 1 ? '已通过' : '已删除'
}
function statusType(s) {
  return s === 0 ? 'warning' : s === 1 ? 'success' : 'danger'
}

async function loadCheckins(p) {
  if (p) checkinPage.value = p
  checkinLoading.value = true
  try {
    const data = await getAdminCheckins({
      page: checkinPage.value,
      size: size.value,
      status: checkinStatus.value === undefined ? undefined : checkinStatus.value
    })
    checkinRecords.value = data.records
    checkinTotal.value = data.total
  } catch (e) {
    // 错误提示由拦截统一处理
  } finally {
    checkinLoading.value = false
  }
}

async function loadPosts(p) {
  if (p) postPage.value = p
  postLoading.value = true
  try {
    const data = await getAdminPosts({
      page: postPage.value,
      size: size.value,
      status: postStatus.value === undefined ? undefined : postStatus.value
    })
    postRecords.value = data.records
    postTotal.value = data.total
  } catch (e) {
    // 错误提示由拦截统一处理
  } finally {
    postLoading.value = false
  }
}

function onTabChange() {
  if (activeTab.value === 'checkin') loadCheckins(1)
  else loadPosts(1)
}

async function auditCheckin(row, status) {
  const action = status === 1 ? '通过' : '删除'
  let reason = ''
  try {
    const confirm = await ElMessageBox.confirm(
      `确定要${action}这条打卡吗？`,
      '审核确认',
      { type: 'warning', confirmButtonText: action, cancelButtonText: '取消' }
    )
    if (status === 2) {
      const { value } = await ElMessageBox.prompt('请输入删除原因（可空）', '删除打卡', {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        inputPlaceholder: '例如：内容违规'
      })
      reason = value || ''
    }
  } catch (e) {
    return // 用户取消
  }
  try {
    await updateCheckinStatus(row.id, { status, reason })
    ElMessage.success(`${action}成功`)
    loadCheckins()
  } catch (e) {
    // 错误提示由拦截统一处理
  }
}

async function auditPost(row, status) {
  const action = status === 1 ? '通过' : '删除'
  let reason = ''
  try {
    await ElMessageBox.confirm(
      `确定要${action}这条帖子吗？`,
      '审核确认',
      { type: 'warning', confirmButtonText: action, cancelButtonText: '取消' }
    )
    if (status === 2) {
      const { value } = await ElMessageBox.prompt('请输入删除原因（可空）', '删除帖子', {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        inputPlaceholder: '例如：内容违规'
      })
      reason = value || ''
    }
  } catch (e) {
    return // 用户取消
  }
  try {
    await updatePostStatus(row.id, { status, reason })
    ElMessage.success(`${action}成功`)
    loadPosts()
  } catch (e) {
    // 错误提示由拦截统一处理
  }
}

onMounted(() => loadCheckins())
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
}
.pager {
  margin-top: 14px;
  justify-content: flex-end;
}
.ai-text {
  color: #67a35e;
  font-size: 12px;
}
.admin-tag {
  color: #c0c4cc;
}
</style>
