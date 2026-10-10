import { defineStore } from 'pinia'
import { login as apiLogin, logout } from '../utils/request'

/**
 * 后台登录态管理（Pinia）
 * token 持久化到 localStorage，路由守卫依赖它判断是否已登录
 */
export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('admin_token') || '',
    userInfo: JSON.parse(localStorage.getItem('admin_user') || 'null')
  }),
  actions: {
    /**
     * 后台管理员登录：调用 /api/admin/login（账号密码，SRS §3.2.1）
     * @param {string} username 管理员账号
     * @param {string} password 密码
     */
    async login(username, password) {
      const data = await apiLogin({ username, password })
      this.token = data.token
      this.userInfo = { nickname: data.nickname, username: data.username, adminId: data.adminId }
      localStorage.setItem('admin_token', data.token)
      localStorage.setItem('admin_user', JSON.stringify(this.userInfo))
      return this.userInfo
    },
    /** 退出登录：清理本地登录态 */
    logout() {
      logout()
      this.token = ''
      this.userInfo = null
      localStorage.removeItem('admin_token')
      localStorage.removeItem('admin_user')
    }
  }
})
