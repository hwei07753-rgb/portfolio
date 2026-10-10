<template>
  <div class="profile-page">
    <el-header class="page-header">
      <div class="header-left">
        <span class="logo">项目任务管理</span>
      </div>
      <div class="header-right">
        <el-button text @click="$router.push('/projects')">项目列表</el-button>
        <el-button text @click="$router.push('/my-tasks')">我的待办</el-button>
        <el-button text @click="handleLogout">退出</el-button>
      </div>
    </el-header>

    <div class="profile-container">
      <h2>个人中心</h2>

      <el-tabs v-model="activeTab">
        <!-- 修改资料 -->
        <el-tab-pane label="修改资料" name="profile">
          <el-form
            ref="profileFormRef"
            :model="profileForm"
            :rules="profileRules"
            label-width="80px"
            class="profile-form"
          >
            <el-form-item label="用户名">
              <el-input :model-value="userStore.username" disabled />
            </el-form-item>
            <el-form-item label="昵称" prop="nickname">
              <el-input
                v-model="profileForm.nickname"
                placeholder="请输入昵称"
                maxlength="50"
                clearable
              />
            </el-form-item>
            <el-form-item label="邮箱" prop="email">
              <el-input
                v-model="profileForm.email"
                placeholder="请输入邮箱"
                maxlength="100"
                clearable
              />
            </el-form-item>
            <el-form-item label="注册时间">
              <el-input :model-value="formatCreateTime" disabled />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="profileLoading" @click="handleUpdateProfile">
                保存修改
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 修改密码 -->
        <el-tab-pane label="修改密码" name="password">
          <el-form
            ref="passwordFormRef"
            :model="passwordForm"
            :rules="passwordRules"
            label-width="80px"
            class="profile-form"
          >
            <el-form-item label="原密码" prop="oldPassword">
              <el-input
                v-model="passwordForm.oldPassword"
                type="password"
                show-password
                placeholder="请输入原密码"
                maxlength="100"
              />
            </el-form-item>
            <el-form-item label="新密码" prop="newPassword">
              <el-input
                v-model="passwordForm.newPassword"
                type="password"
                show-password
                placeholder="请输入新密码（至少6位）"
                maxlength="100"
              />
            </el-form-item>
            <el-form-item label="确认密码" prop="confirmPassword">
              <el-input
                v-model="passwordForm.confirmPassword"
                type="password"
                show-password
                placeholder="请再次输入新密码"
                maxlength="100"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="passwordLoading" @click="handleChangePassword">
                保存密码
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { updateProfile, changePassword } from '@/api/user'
import { ElMessage } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()

const activeTab = ref('profile')

const profileLoading = ref(false)
const passwordLoading = ref(false)

const profileFormRef = ref(null)
const passwordFormRef = ref(null)

const profileForm = reactive({
  nickname: '',
  email: ''
})

const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const profileRules = {
  nickname: [
    { max: 50, message: '昵称长度不能超过50字符', trigger: 'blur' }
  ],
  email: [
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
    { max: 100, message: '邮箱长度不能超过100字符', trigger: 'blur' }
  ]
}

const validateConfirmPassword = (rule, value, callback) => {
  if (value !== passwordForm.newPassword) {
    callback(new Error('两次密码不一致'))
  } else {
    callback()
  }
}

const passwordRules = {
  oldPassword: [
    { required: true, message: '请输入原密码', trigger: 'blur' }
  ],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, max: 100, message: '新密码长度需在6-100字符之间', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

// R-06-issue-13: 已修复 - formatCreateTime从userStore.createTime读取并格式化展示注册时间
const formatCreateTime = computed(() => {
  if (userStore.createTime) {
    return new Date(userStore.createTime).toLocaleDateString('zh-CN')
  }
  return ''
})

// R-06-issue-11: 已修复 - onMounted调用fetchUserInfo()加载最新用户数据(email/createTime)，然后从store初始化表单
onMounted(async () => {
  await userStore.fetchUserInfo()
  profileForm.nickname = userStore.nickname || ''
  profileForm.email = userStore.email || ''
})

async function handleUpdateProfile() {
  const valid = await profileFormRef.value.validate().catch(() => false)
  if (!valid) return

  profileLoading.value = true
  try {
    await updateProfile({
      nickname: profileForm.nickname || null,
      email: profileForm.email || null
    })
    ElMessage.success('修改成功')
    userStore.nickname = profileForm.nickname || ''
    userStore.email = profileForm.email || ''
    // R-06-issue-12: 已修复 - email包含在localStorage userInfo持久化中
    localStorage.setItem('userInfo', JSON.stringify({
      userId: userStore.userId,
      username: userStore.username,
      nickname: profileForm.nickname || '',
      email: profileForm.email || ''
    }))
  } catch {
    // 拦截器已统一处理
  } finally {
    profileLoading.value = false
  }
}

async function handleChangePassword() {
  const valid = await passwordFormRef.value.validate().catch(() => false)
  if (!valid) return

  passwordLoading.value = true
  try {
    await changePassword({
      oldPassword: passwordForm.oldPassword,
      newPassword: passwordForm.newPassword
    })
    ElMessage.success('密码修改成功')
    passwordFormRef.value.resetFields()
  } catch {
    // 拦截器已统一处理
  } finally {
    passwordLoading.value = false
  }
}

function handleLogout() {
  userStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.profile-page {
  min-height: 100vh;
  background: var(--el-bg-color-page);
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid var(--el-border-color-light);
  padding: 0 24px;
  height: 60px;
}

.header-left .logo {
  font-size: 18px;
  font-weight: 600;
  color: var(--el-color-primary);
}

.header-right {
  display: flex;
  gap: 4px;
}

.profile-container {
  max-width: 520px;
  margin: 40px auto;
  padding: 32px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.profile-container h2 {
  margin: 0 0 24px;
  font-size: 22px;
  color: var(--el-text-color-primary);
}

.profile-form {
  margin-top: 16px;
  max-width: 400px;
}
</style>