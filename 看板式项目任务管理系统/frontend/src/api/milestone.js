import request from '@/api/request'

/**
 * 获取项目 Sprint 列表
 * @param {number} projectId - 项目ID
 * @returns {Promise<Array<{id: number, name: string, startDate: string, endDate: string, status: string, taskCount: number, createTime: string}>>}
 */
export const listMilestones = (projectId) => request.get(`/projects/${projectId}/milestones`)

/**
 * 创建 Sprint
 * @param {number} projectId - 项目ID
 * @param {Object} data - { name, startDate, endDate }
 * @returns {Promise<{id: number, name: string, startDate: string, endDate: string, status: string, taskCount: number, createTime: string}>}
 */
export const createMilestone = (projectId, data) => request.post(`/projects/${projectId}/milestones`, data)

/**
 * 删除 Sprint + 解关联任务
 * @param {number} projectId - 项目ID
 * @param {number} id - Sprint ID
 * @returns {Promise<void>}
 */
export const deleteMilestone = (projectId, id) => request.delete(`/projects/${projectId}/milestones/${id}`)
