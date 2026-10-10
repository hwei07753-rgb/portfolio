<template>
  <el-card shadow="never">
    <el-table :data="records" v-loading="loading" stripe>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column label="审核对象" width="100">
        <template #default="{ row }">
          <el-tag :type="row.bizType === 1 ? 'primary' : 'warning'">
            {{ row.bizType === 1 ? '打卡' : '帖子' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="bizId" label="业务ID" width="90" />
      <el-table-column label="动作" width="90">
        <template #default="{ row }">
          <el-tag :type="row.action === 1 ? 'success' : 'danger'">
            {{ row.action === 1 ? '通过' : '删除' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="adminName" label="操作管理员" width="130" />
      <el-table-column prop="reason" label="原因" min-width="160" show-overflow-tooltip />
      <el-table-column prop="createdAt" label="操作时间" width="170" />
    </el-table>

    <el-pagination
      class="pager"
      layout="total, prev, pager, next"
      :total="total"
      :current-page="page"
      :page-size="size"
      @current-change="loadLogs"
    />
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getAdminAuditLogs } from '../utils/request'

const records = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const loading = ref(false)

async function loadLogs(p) {
  if (p) page.value = p
  loading.value = true
  try {
    const data = await getAdminAuditLogs({ page: page.value, size: size.value })
    records.value = data.records
    total.value = data.total
  } catch (e) {
    // 错误提示由拦截统一处理
  } finally {
    loading.value = false
  }
}

onMounted(() => loadLogs())
</script>

<style scoped>
.pager {
  margin-top: 14px;
  justify-content: flex-end;
}
</style>
