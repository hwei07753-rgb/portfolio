<template>
  <el-card shadow="never">
    <div class="toolbar">
      <el-input
        v-model="keyword"
        placeholder="按敏感词搜索"
        clearable
        class="search-input"
        @keyup.enter="loadWords(1)"
        @clear="loadWords(1)"
      />
      <el-input
        v-model="newWord"
        placeholder="输入新敏感词"
        clearable
        class="search-input"
        @keyup.enter="handleAdd"
      />
      <el-button type="primary" @click="handleAdd">新增</el-button>
      <el-button @click="loadWords(1)">查询</el-button>
    </div>

    <el-table :data="records" v-loading="loading" stripe>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="word" label="敏感词" min-width="160" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'info'">
            {{ row.status === 1 ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="createdAt" label="创建时间" width="170" />
      <el-table-column label="操作" width="110" fixed="right">
        <template #default="{ row }">
          <el-button
            :type="row.status === 1 ? 'info' : 'success'"
            size="small"
            @click="toggle(row)"
          >
            {{ row.status === 1 ? '停用' : '启用' }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      class="pager"
      layout="total, prev, pager, next"
      :total="total"
      :current-page="page"
      :page-size="size"
      @current-change="loadWords"
    />
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getSensitiveWords,
  addSensitiveWord,
  updateSensitiveWordStatus
} from '../utils/request'

const records = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const keyword = ref('')
const newWord = ref('')
const loading = ref(false)

async function loadWords(p) {
  if (p) page.value = p
  loading.value = true
  try {
    const data = await getSensitiveWords({
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

async function handleAdd() {
  const word = newWord.value.trim()
  if (!word) {
    ElMessage.warning('请输入敏感词')
    return
  }
  try {
    await addSensitiveWord({ word })
    ElMessage.success('敏感词添加成功')
    newWord.value = ''
    loadWords(1)
  } catch (e) {
    // 错误提示由拦截统一处理
  }
}

async function toggle(row) {
  const target = row.status === 1 ? 0 : 1
  try {
    await updateSensitiveWordStatus(row.id, target)
    ElMessage.success(target === 1 ? '已启用' : '已停用')
    row.status = target
  } catch (e) {
    // 错误提示由拦截统一处理
  }
}

onMounted(() => loadWords())
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
}
.search-input {
  width: 220px;
}
.pager {
  margin-top: 14px;
  justify-content: flex-end;
}
</style>
