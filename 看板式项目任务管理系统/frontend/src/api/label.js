import request from '@/api/request'

/**
 * 获取项目内所有标签列表（全量返回不分页）
 * @param {number} projectId - 项目ID
 * @returns {Promise<Array<{id: number, name: string, color: string, createTime: string}>>}
 */
export const listLabels = (projectId) => request.get(`/projects/${projectId}/labels`)

/**
 * 创建标签
 * @param {number} projectId - 项目ID
 * @param {Object} data - { name, color? }
 * @returns {Promise<{id: number, name: string, color: string, createTime: string}>}
 */
export const createLabel = (projectId, data) => request.post(`/projects/${projectId}/labels`, data)

/**
 * 删除标签（级联删除 task_label 关联）
 * @param {number} projectId - 项目ID
 * @param {number} labelId - 标签ID
 * @returns {Promise<void>}
 */
export const deleteLabel = (projectId, labelId) => request.delete(`/projects/${projectId}/labels/${labelId}`)