import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'

/** 后端接口基础路径（CorsConfig 已开启全量跨域） */
const BASE_URL = 'http://localhost:8080/api'

const service = axios.create({
  baseURL: BASE_URL,
  timeout: 15000
})

// 请求拦截：自动注入 Bearer Token
service.interceptors.request.use((config) => {
  const token = localStorage.getItem('admin_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截：统一处理 Result<T> 契约与 401
service.interceptors.response.use(
  (response) => {
    const body = response.data
    // 后端统一结构：{ code, message, data }
    if (body.code === 200) {
      return body.data
    }
    // 业务失败（如 1002 无权操作 / 1004 已封禁）
    if (body.code === 401) {
      handleUnauthorized()
    } else {
      ElMessage.error(body.message || '操作失败')
    }
    return Promise.reject(new Error(body.message || '业务异常'))
  },
  (error) => {
    if (error.response && error.response.status === 401) {
      handleUnauthorized()
    } else {
      ElMessage.error('网络请求失败，请检查后端服务')
    }
    return Promise.reject(error)
  }
)

/** 401 统一处理：清登录态并跳转登录页 */
function handleUnauthorized() {
  localStorage.removeItem('admin_token')
  localStorage.removeItem('admin_user')
  if (router.currentRoute.value.path !== '/login') {
    router.push('/login')
  }
}

/** 管理员登录（账号密码 → /api/admin/login，SRS §3.2.1） */
export function login(payload) {
  return service.post('/admin/login', payload)
}

/** 平台核心宏观指标 */
export function getAdminStats() {
  return service.get('/admin/stats')
}

/** 分页用户列表 */
export function getAdminUsers(params) {
  return service.get('/admin/users', { params })
}

/** 变更用户状态（封禁 status=1 / 解封 status=0） */
export function updateUserStatus(id, status) {
  return service.put(`/admin/user/${id}/status`, { status })
}

/** 分页打卡审核列表（status 可选 0/1/2） */
export function getAdminCheckins(params) {
  return service.get('/admin/checkins', { params })
}

/** 打卡审核（status=1 通过 / 2 删除） */
export function updateCheckinStatus(id, payload) {
  return service.put(`/admin/checkin/${id}/status`, payload)
}

/** 分页帖子审核列表 */
export function getAdminPosts(params) {
  return service.get('/admin/posts', { params })
}

/** 帖子审核（status=1 通过 / 2 删除） */
export function updatePostStatus(id, payload) {
  return service.put(`/admin/post/${id}/status`, payload)
}

/** 分页审核记录 */
export function getAdminAuditLogs(params) {
  return service.get('/admin/audit-logs', { params })
}

/** 分页敏感词列表 */
export function getSensitiveWords(params) {
  return service.get('/admin/sensitive-words', { params })
}

/** 新增敏感词 */
export function addSensitiveWord(payload) {
  return service.post('/admin/sensitive-words', payload)
}

/** 敏感词启停（status=1 启用 / 0 停用） */
export function updateSensitiveWordStatus(id, status) {
  return service.put(`/admin/sensitive-word/${id}/status`, null, { params: { status } })
}

export function logout() {}
