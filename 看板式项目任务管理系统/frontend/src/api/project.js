import request from '@/api/request'

/**
 * 分页查询当前用户参与的项目列表
 * @param {Object} params - { pageNum, pageSize, includeArchived }
 * @returns {Promise<{records: Array, total: number, pageNum: number, pageSize: number}>}
 */
export const listProjects = (params) => request.get('/projects', { params })

/**
 * 创建项目
 * @param {Object} data - { name }
 * @returns {Promise<{id: number, name: string, ownerId: number, ownerName: string, archived: boolean, memberCount: number, taskCount: number, myRole: string, createTime: string, updateTime: string|null}>}
 */
export const createProject = (data) => request.post('/projects', data)

/**
 * 查看项目详情
 * @param {number} id - 项目ID
 * @returns {Promise<{id: number, name: string, ownerId: number, ownerName: string, archived: boolean, memberCount: number, taskCount: number, myRole: string, createTime: string, updateTime: string|null}>}
 */
export const getProject = (id) => request.get(`/projects/${id}`)

/**
 * 修改项目名称 / 归档项目
 * @param {number} id - 项目ID
 * @param {Object} data - { name?, archived? }
 * @returns {Promise<{id: number, name: string, ownerId: number, ownerName: string, archived: boolean, memberCount: number, taskCount: number, myRole: string, createTime: string, updateTime: string|null}>}
 */
export const updateProject = (id, data) => request.put(`/projects/${id}`, data)

/**
 * 查看项目成员列表
 * @param {number} projectId - 项目ID
 * @returns {Promise<Array<{userId: number, username: string, nickname: string|null, role: string}>>}
 */
export const listMembers = (projectId) => request.get(`/projects/${projectId}/members`)

/**
 * 整表替换项目成员
 * @param {number} projectId - 项目ID
 * @param {Array<{userId: number, role: string}>} members - 完整成员列表
 * @returns {Promise<void>}
 */
export const replaceMembers = (projectId, members) => request.put(`/projects/${projectId}/members`, { members })

/**
 * 按状态统计项目内任务数量
 * @param {number} projectId - 项目ID
 * @returns {Promise<{todo: number, in_progress: number, done: number, blocked: number}>}
 */
export const getStatusStats = (projectId) => request.get(`/projects/${projectId}/stats/status`)

/**
 * 燃尽图数据点（P2-3 可选 milestoneId 启用 Sprint 精确燃尽）
 * @param {number} projectId - 项目ID
 * @param {number} [milestoneId] - Sprint ID（可选）
 * @returns {Promise<Array<{date: string, remaining: number}>>}
 */
export const getBurndown = (projectId, milestoneId) => request.get(`/projects/${projectId}/stats/burndown`, { params: milestoneId ? { milestoneId } : {} })