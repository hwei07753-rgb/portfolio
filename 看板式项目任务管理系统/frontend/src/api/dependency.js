import request from '@/api/request'

/**
 * 创建任务依赖边（甘特图拖拽连线）
 * @param {number} projectId - 项目ID
 * @param {Object} data - { predecessorTaskId, successorTaskId, dependencyType? }
 * @returns {Promise<Object>} TaskDependencyVO
 */
export const createDependency = (projectId, data) => request.post(`/projects/${projectId}/dependencies`, data)

/**
 * 删除任务依赖边（甘特图右键删除连线）
 * @param {number} projectId - 项目ID
 * @param {number} dependencyId - 依赖ID
 * @returns {Promise<void>}
 */
export const deleteDependency = (projectId, dependencyId) => request.delete(`/projects/${projectId}/dependencies/${dependencyId}`)
