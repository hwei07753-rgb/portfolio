<template>
  <div class="login-container">
    <!-- R-06-issue-1: 已修复 - 添加系统标题，对齐TECH_DESIGN.md §6原型 -->
    <div class="system-title">项目任务管理系统（看板式）</div>
    <div class="login-card">
      <h2 class="card-title">用户登录</h2>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="0" size="large">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" maxlength="50" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="请输入密码" maxlength="100" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" class="login-btn" :loading="loading" @click="handleLogin">
            登 录
          </el-button>
        </el-form-item>
      </el-form>
      <div class="card-footer">
        还没有账号？<el-link type="primary" @click="$router.push('/register')">立即注册</el-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { loginUser } from '@/api/auth'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  username: route.query.username || '',
  password: ''
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_]{2,50}$/, message: '用户名格式不正确（2-50字符，字母/数字/下划线）', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 100, message: '密码至少6位', trigger: 'blur' }
  ]
}

async function handleLogin() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const res = await loginUser({ username: form.username, password: form.password })
    userStore.setUser({
      token: res.data.token,
      userId: res.data.userId,
      username: res.data.username,
      nickname: res.data.nickname
    })
    ElMessage.success('登录成功')
    router.push(route.query.redirect || '/projects')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: #f0f2f5;
}
.system-title {
  font-size: 20px;
  color: #303133;
  margin-bottom: 20px;
  font-weight: 500;
}
.login-card {
  width: 400px;
  padding: 40px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}
.card-title {
  text-align: center;
  margin: 0 0 30px;
  font-size: 20px;
  color: #303133;
}
.login-btn {
  width: 100%;
}
.card-footer {
  text-align: center;
  font-size: 14px;
  color: #909399;
}
</style>