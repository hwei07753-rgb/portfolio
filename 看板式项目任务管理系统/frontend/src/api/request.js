import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: '/api',
  timeout: 10000
})

// 请求拦截器 —— 自动加 JWT token
request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器 —— 统一处理 Result<T>
request.interceptors.response.use(
  (res) => {
    const data = res.data
    // code === 200 走业务
    if (data.code === 200) {
      return data
    }
    // code === 401 未登录
    if (data.code === 401) {
      localStorage.removeItem('token')
      // R-06-issue-8: 已修复 - 401提示文案改为"登录已过期，请重新登录"，对token过期场景更准确
      ElMessage.error('登录已过期，请重新登录')
      // R-06-issue-2: 已修复 - 401跳转携带redirect查询参数，用户重新登录后可回到原页面
      window.location.href = '/login?redirect=' + encodeURIComponent(window.location.pathname + window.location.search)
      return Promise.reject(new Error(data.message || '未登录'))
    }
    // 其他业务异常
    ElMessage.error(data.message || '请求失败')
    return Promise.reject(new Error(data.message || '请求失败'))
  },
  (error) => {
    ElMessage.error('网络异常，请稍后重试')
    return Promise.reject(error)
  }
)

export default request