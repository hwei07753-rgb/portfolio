import request from '@/api/request'

// R-06-issue-6(P1-3): 已修复 - searchUsers从api/auth.js移至api/user.js,命中UserController:/api/users/search,模块归属正确
/**
 * 按用户名精确搜索用户
 * @param {string} keyword - 用户名关键词
 * @returns {Promise<Array<{id: number, username: string, nickname: string|null}>>}
 */
export const searchUsers = (keyword) => request.get('/users/search', { params: { keyword } })

// R-06-issue-14: 已修复 - @returns改为{Promise<void>}，void更准确表达Result<Void>无数据返回语义
/**
 * 修改个人资料（昵称 + 邮箱）
 * @param {Object} data - { nickname, email }
 * @returns {Promise<void>}
 */
export const updateProfile = (data) => request.put('/users/me', data)

/**
 * 修改密码
 * @param {Object} data - { oldPassword, newPassword }
 * @returns {Promise<void>}
 */
export const changePassword = (data) => request.put('/users/me/password', data)