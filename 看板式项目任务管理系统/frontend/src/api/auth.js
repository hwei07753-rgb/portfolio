import request from '@/api/request'

/**
 * 注册
 * @param {Object} data - { username, password }
 * @returns {Promise<null>}
 */
export const registerUser = (data) => request.post('/auth/register', data)

/**
 * 登录
 * @param {Object} data - { username, password }
 * @returns {Promise<{token: string, userId: number, username: string, nickname: string|null}>}
 */
export const loginUser = (data) => request.post('/auth/login', data)

/**
 * 获取当前登录用户信息
 * @returns {Promise<{id: number, username: string, nickname: string|null, email: string|null, createTime: string}>}
 */
// R-06-issue-6(P1-3): 已修复 - searchUsers已移至api/user.js(命中UserController:/api/users/search),auth.js只保留认证相关(login/register/getCurrentUser)
export const getCurrentUser = () => request.get('/users/me')