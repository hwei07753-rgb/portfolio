<template>
  <el-card shadow="never">
    <div class="toolbar">
      <el-input
        v-model="keyword"
        placeholder="按昵称搜索"
        clearable
        class="search-input"
        @keyup.enter="loadUsers(1)"
        @clear="loadUsers(1)"
      />
      <el-button type="primary" @click="loadUsers(1)">查询</el-button>
    </div>

    <el-table :data="records" v-loading="loading" stripe>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="nickname" label="昵称" min-width="110" />
      <el-table-column prop="openid" label="OpenID(脱敏)" min-width="150" />
      <el-table-column label="角色" width="90">
        <template #default="{ row }">
          <el-tag :type="row.role === 1 ? 'danger' : 'info'">
            {{ row.role === 1 ? '管理员' : '学员' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === 1 ? 'danger' : 'success'">
            {{ row.status === 1 ? '封禁' : '正常' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="createdAt" label="注册时间" width="170" />
      <el-table-column label="操作" width="110" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.role !== 1"
            :type="row.status === 1 ? 'success' : 'danger'"
            size="small"
            :loading="row._changing"
            @click="toggleStatus(row)"
          >
            {{ row.status === 1 ? '解封' : '封禁' }}
          </el-button>
          <span v-else class="admin-tag">—</span>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      class="pager"
      layout="total, prev, pager, next"
      :total="total"
      :current-page="page"
      :page-size="size"
      @current-change="loadUsers"
    />
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAdminUsers, updateUserStatus } from '../utils/request'

const records = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const keyword = ref('')
const loading = ref(false)

async function loadUsers(p) {
  if (p) {
    page.value = p
  }
  loading.value = true
  try {
    const data = await getAdminUsers({
      page: page.value,
      size: size.value,
      keyword: keyword.value || undefined
    })
    records.value = data.records
    total.value = data.total
  } catch (e) {
    // 错误提示由拦截统一处理
  } finally {
    loading.value = false
  }
}

async function toggleStatus(row) {
  const action = row.status === 1 ? '解封' : '封禁'
  try {
    await ElMessageBox.confirm(
      `确定要${action}用户「${row.nickname}」吗？`,
      '操作确认',
      { type: 'warning', confirmButtonText: action, cancelButtonText: '取消' }
    )
  } catch (e) {
    return // 用户取消
  }

  row._changing = true
  try {
    const targetStatus = row.status === 1 ? 0 : 1
    await updateUserStatus(row.id, targetStatus)
    ElMessage.success(`${action}成功`)
    row.status = targetStatus
  } catch (e) {
    // 错误提示由拦截统一处理
  } finally {
    row._changing = false
  }
}

onMounted(() => loadUsers())
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
}
.search-input {
  width: 240px;
}
.pager {
  margin-top: 14px;
  justify-content: flex-end;
}
.admin-tag {
  color: #c0c4cc;
}
</style>
