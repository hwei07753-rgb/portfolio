<template>
  <div class="login-wrap">
    <el-card class="login-card">
      <h2 class="title">智学伴 · 管理后台</h2>
      <p class="subtitle">自律学习与 AI 互助平台</p>
      <el-form @submit.prevent>
        <el-form-item label="账号">
          <el-input v-model="username" placeholder="管理员账号（默认 admin）" clearable />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="password"
            type="password"
            placeholder="管理员密码（默认 123456）"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-button type="primary" class="login-btn" :loading="loading" @click="handleLogin">
          {{ loading ? '登录中...' : '管理员登录' }}
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../store/auth'

const router = useRouter()
const authStore = useAuthStore()

// 演示默认管理员账号（对应 admin 表种子，SRS §3.2.1）
const username = ref('admin')
const password = ref('')
const loading = ref(false)

async function handleLogin() {
  if (!username.value.trim() || !password.value) {
    ElMessage.warning('请输入账号和密码')
    return
  }
  loading.value = true
  try {
    const user = await authStore.login(username.value.trim(), password.value)
    ElMessage.success(`欢迎回来，${user.nickname}`)
    router.push('/dashboard')
  } catch (e) {
    // 错误提示已由响应拦截统一处理
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  background: linear-gradient(135deg, #2b4c7e 0%, #4a7bb5 100%);
}
.login-card {
  width: 360px;
  padding: 12px 8px;
}
.title {
  margin: 0 0 4px;
  text-align: center;
  color: #2b4c7e;
}
.subtitle {
  margin: 0 0 20px;
  text-align: center;
  color: #909399;
  font-size: 13px;
}
.login-btn {
  width: 100%;
}
</style>
