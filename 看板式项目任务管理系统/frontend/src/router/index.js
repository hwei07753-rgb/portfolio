import { createRouter, createWebHistory } from 'vue-router'
import LoginPage from '../views/LoginPage.vue'
import RegisterPage from '../views/RegisterPage.vue'
import ProjectListPage from '../views/ProjectListPage.vue'
import ProjectSettingsPage from '../views/ProjectSettingsPage.vue'
import ProjectBoardPage from '../views/ProjectBoardPage.vue'
import MyTasksPage from '../views/MyTasksPage.vue'
import UserProfilePage from '../views/UserProfilePage.vue'
import GanttPage from '../views/GanttPage.vue'

// R-06-issue-6: 已修复 - 为所有路由补meta.title字段，确保浏览器标签页标题正确显示
const routes = [
  {
    path: '/login',
    name: 'Login',
    component: LoginPage,
    meta: { title: '登录', requiresAuth: false }
  },
  {
    path: '/register',
    name: 'Register',
    component: RegisterPage,
    meta: { title: '注册', requiresAuth: false }
  },
  {
    path: '/projects',
    name: 'ProjectList',
    component: ProjectListPage,
    meta: { title: '项目列表', requiresAuth: true }
  },
  {
    path: '/projects/:id/settings',
    name: 'ProjectSettings',
    component: ProjectSettingsPage,
    meta: { title: '项目设置', requiresAuth: true }
  },
  {
    path: '/projects/:id/board',
    name: 'ProjectBoard',
    component: ProjectBoardPage,
    meta: { title: '项目看板', requiresAuth: true }
  },
  {
    path: '/projects/:id/gantt',
    name: 'Gantt',
    component: GanttPage,
    meta: { title: '甘特图', requiresAuth: true }
  },
  {
    path: '/my-tasks',
    name: 'MyTasks',
    component: MyTasksPage,
    meta: { title: '我的待办', requiresAuth: true }
  },
  {
    path: '/profile',
    name: 'UserProfile',
    component: UserProfilePage,
    meta: { title: '个人中心', requiresAuth: true }
  },
  {
    path: '/',
    redirect: '/projects'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// R-06-issue-10: 已修复 - beforeEach 放行前设置 document.title，利用路由 meta.title 字段
router.beforeEach((to) => {
  document.title = (to.meta && to.meta.title) || '项目任务管理'
  const token = localStorage.getItem('token')

  // ① 已登录用户访问 /login 或 /register → 自动跳转 /projects
  if (token && (to.path === '/login' || to.path === '/register')) {
    return '/projects'
  }

  // ② 公开页面直接放行
  if (!to.meta.requiresAuth) return true

  // ③ 需登录页面：未登录 → 跳登录页（带 redirect 参数）
  if (!token) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  // ④ 已登录 → 放行
  return true
})

export default router