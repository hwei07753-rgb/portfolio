<template>
  <div>
    <el-row :gutter="16">
      <el-col v-for="card in cards" :key="card.label" :span="8">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" :style="{ background: card.color }">
            {{ card.icon }}
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ card.value }}</div>
            <div class="stat-label">{{ card.label }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="tip-card" shadow="never">
      <template #header>数据说明</template>
      <ul class="tip-list">
        <li>注册用户：平台用户总数（含管理员）</li>
        <li>社区帖子：已发布帖子（不含已删除）</li>
        <li>今日打卡：当天提交的打卡记录数</li>
        <li>打卡总数：每日打卡累计记录</li>
        <li>AI 调用次数：AI 复盘生成条数（ai_review 表）</li>
        <li>专注总时长：全部"完成"状态专注记录之和（分钟）</li>
      </ul>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { getAdminStats } from '../utils/request'

const stats = ref(null)

const cards = computed(() => {
  const s = stats.value
  return [
    { label: '注册用户', value: s ? s.userCount : '-', icon: '👥', color: '#4a7bb5' },
    { label: '社区帖子', value: s ? s.postCount : '-', icon: '📝', color: '#67a35e' },
    { label: '今日打卡', value: s ? s.todayCheckinCount : '-', icon: '📅', color: '#e8a33d' },
    { label: '打卡总数', value: s ? s.checkinCount : '-', icon: '✅', color: '#2b4c7e' },
    { label: 'AI 调用次数', value: s ? s.aiReviewCount : '-', icon: '🤖', color: '#8e7cc3' },
    { label: '专注总时长(分)', value: s ? s.focusTotalMinutes : '-', icon: '⏱', color: '#d9534f' }
  ]
})

async function loadStats() {
  try {
    stats.value = await getAdminStats()
  } catch (e) {
    // 错误提示由拦截统一处理
  }
}

onMounted(loadStats)
</script>

<style scoped>
.stat-card {
  text-align: center;
  margin-bottom: 16px;
}
.stat-icon {
  width: 48px;
  height: 48px;
  line-height: 48px;
  border-radius: 10px;
  color: #fff;
  font-size: 22px;
  margin: 0 auto 10px;
}
.stat-value {
  font-size: 26px;
  font-weight: 700;
  color: #303133;
}
.stat-label {
  margin-top: 4px;
  color: #909399;
  font-size: 13px;
}
.tip-card {
  margin-top: 4px;
}
.tip-list {
  margin: 0;
  padding-left: 18px;
  color: #606266;
  line-height: 1.9;
}
</style>
