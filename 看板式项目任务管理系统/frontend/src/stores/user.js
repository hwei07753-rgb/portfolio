import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getCurrentUser } from '@/api/auth'

export const useUserStore = defineStore('user', () => {
  // R-06-issue-5: 已修复 - 初始化时从localStorage恢复完整userInfo，解决页面刷新后userId/username/nickname丢失问题
  const savedUserInfo = JSON.parse(localStorage.getItem('userInfo') || 'null')
  const token = ref(localStorage.getItem('token') || '')
  // R-06-issue-3: 已修复 - userId初始值统一从userInfo恢复或设为0(数字类型)，消除null/number类型不一致
  const userId = ref(savedUserInfo ? savedUserInfo.userId : 0)
  const username = ref(savedUserInfo ? savedUserInfo.username : '')
  const nickname = ref(savedUserInfo ? savedUserInfo.nickname : '')
  // R-06-issue-12: 已修复 - email从savedUserInfo恢复，页面刷新后不再丢失
  const email = ref(savedUserInfo ? (savedUserInfo.email || '') : '')
  const createTime = ref(savedUserInfo ? (savedUserInfo.createTime || '') : '')

  const isLoggedIn = computed(() => !!token.value)

  const displayName = computed(() => nickname.value || username.value)

  // R-06-issue-5: 已修复 - setUser同步持久化userInfo JSON到localStorage，页面刷新后从userInfo恢复所有字段
  function setUser(data) {
    token.value = data.token || token.value
    userId.value = data.userId
    username.value = data.username
    nickname.value = data.nickname || ''
    if (data.token) {
      localStorage.setItem('token', data.token)
    }
    // R-06-issue-12: 已修复 - setUser持久化userInfo到localStorage时包含email+createTime字段
    localStorage.setItem('userInfo', JSON.stringify({
      userId: data.userId,
      username: data.username,
      nickname: data.nickname || '',
      email: data.email || email.value,
      createTime: data.createTime || createTime.value
    }))
  }

  async function fetchUserInfo() {
    try {
      const res = await getCurrentUser()
      // R-06-issue-5跨层: UserController已修复返回UserVO(不包含isDeleted等内部字段)，字段名对齐API_DESIGN §3.1
      userId.value = res.data.id
      username.value = res.data.username
      nickname.value = res.data.nickname || ''
      email.value = res.data.email || ''
      createTime.value = res.data.createTime || ''
      // 同步持久化到localStorage(含email+createTime)，页面刷新后可恢复
      localStorage.setItem('userInfo', JSON.stringify({
        userId: res.data.id,
        username: res.data.username,
        nickname: res.data.nickname || '',
        email: res.data.email || '',
        createTime: res.data.createTime || ''
      }))
    } catch {
      // 获取失败不处理，拦截器已提示
    }
  }

  function logout() {
    token.value = ''
    userId.value = 0
    username.value = ''
    nickname.value = ''
    email.value = ''
    createTime.value = ''
    localStorage.removeItem('token')
    localStorage.removeItem('userInfo')
  }

  return { token, userId, username, nickname, email, createTime, isLoggedIn, displayName, setUser, fetchUserInfo, logout }
})