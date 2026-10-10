<template>
  <el-container class="layout">
    <el-aside width="200px" class="aside">
      <div class="logo">智学伴后台</div>
      <el-menu
        :default-active="activeMenu"
        router
        background-color="#2b4c7e"
        text-color="#cfd8e6"
        active-text-color="#ffffff"
      >
        <el-menu-item index="/dashboard">📊 平台概览</el-menu-item>
        <el-menu-item index="/users">👥 用户管理</el-menu-item>
        <el-menu-item index="/audit">🛡️ 内容审核</el-menu-item>
        <el-menu-item index="/sensitive-words">🚫 敏感词管理</el-menu-item>
        <el-menu-item index="/audit-logs">📜 审核记录</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <span class="page-title">{{ route.meta.title }}</span>
        <el-dropdown @command="handleCommand">
          <span class="user-name">
            {{ authStore.userInfo?.nickname || '管理员' }} ▾
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../store/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const activeMenu = computed(() => route.path)

function handleCommand(command) {
  if (command === 'logout') {
    authStore.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.layout {
  height: 100vh;
}
.aside {
  background: #2b4c7e;
}
.logo {
  height: 60px;
  line-height: 60px;
  text-align: center;
  color: #fff;
  font-weight: bold;
  font-size: 16px;
}
.aside :deep(.el-menu) {
  border-right: none;
}
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
}
.page-title {
  font-size: 16px;
  font-weight: 600;
}
.user-name {
  cursor: pointer;
  color: #2b4c7e;
}
.main {
  background: #f5f7fa;
}
</style>
