import request from '@/api/request'

// R-06-issue-18: 已修复 - 后端TaskController+TaskServiceImpl已新增labelId查询参数,前端标签筛选从此生效
/**
 * 分页查询项目内任务列表（P1 增强：新增 assigneeId/keyword/dueDateFrom/dueDateTo/labelId 筛选参数）
 * @param {number} projectId - 项目ID
 * @param {Object} params - { status?, pageNum?, pageSize?, sortBy?, assigneeId?, keyword?, dueDateFrom?, dueDateTo?, labelId? }
 * @returns {Promise<{records: Array, total: number, pageNum: number, pageSize: number}>}
 */
export const listTasks = (projectId, params) => request.get(`/projects/${projectId}/tasks`, { params })

/**
 * 创建任务
 * @param {number} projectId - 项目ID
 * @param {Object} data - { title, description?, priority?, assigneeId?, dueDate?, labelIds? }
 * @returns {Promise<Object>} TaskVO
 */
// R-06-issue-5: 已修复 - createTask JSDoc @returns 改为具体 TaskVO 字段,对齐 API_DESIGN §3.4 成功响应
export const createTask = (projectId, data) => request.post(`/projects/${projectId}/tasks`, data)

/**
 * 编辑任务（全部字段 + 状态变更 + 软删设 status=deleted）
 * @param {number} id - 任务ID
 * @param {Object} data - { title?, description?, priority?, assigneeId?, dueDate?, status?, labelIds? }
 * @returns {Promise<Object>} TaskVO
 */
export const updateTask = (id, data) => request.put(`/tasks/${id}`, data)

/**
 * 获取任务活动流列表（系统记录 + 评论，按时间倒序）
 * @param {number} taskId - 任务ID
 * @returns {Promise<TaskLogVO[]>}
 */
// R-06-issue-16: 已修复 - @returns 改为 {Promise<TaskLogVO[]>} 与 createComment 风格对齐
export const listTaskLogs = (taskId) => request.get(`/tasks/${taskId}/logs`)

/**
 * 添加评论
 * @param {number} taskId - 任务ID
 * @param {string} content - 评论内容 1-1000字符
 * @returns {Promise<Object>} TaskLogVO
 */
export const createComment = (taskId, content) => request.post(`/tasks/${taskId}/comments`, { content })

// R-06-issue-19: 已修复 - quickChangeStatus(ProjectBoardPage.vue)已改用patchTaskStatus(PATCH)替代updateTask(PUT),P1-4幂等乐观锁已生效
/**
 * 幂等状态变更（P1-4 拖拽跨列触发）
 * @param {number} id - 任务ID
 * @param {Object} data - { status, expectedStatus }
 * @returns {Promise<void>}
 */
export const patchTaskStatus = (id, data) => request.patch(`/tasks/${id}/status`, data)

/**
 * 批量更新排序（P1-4 拖拽完成后同步 order_no + status）
 * @param {Object} data - { items: [{taskId, orderNo, status}] }
 * @returns {Promise<void>}
 */
export const batchUpdateOrder = (data) => request.put('/tasks/batch-order', data)

/**
 * 获取甘特图数据（含依赖边 + 关键路径标识）
 * @param {number} projectId - 项目ID
 * @returns {Promise<Array<{id, title, dueDate, assigneeName, status, criticalPath, dependencies}>>}
 */
export const getGanttData = (projectId) => request.get(`/projects/${projectId}/gantt`)

/**
 * 拖拽甘特图时间条 → 更新截止日期
 * @param {number} taskId - 任务ID
 * @param {string|null} dueDate - 截止日期 ISO 8601 格式，null 清除截止日期
 * @returns {Promise<Object>} TaskVO
 */
export const updateTaskDueDate = (taskId, dueDate) => request.put(`/tasks/${taskId}/due-date`, { dueDate })

/**
 * P2-2 状态机：获取全局状态转移白名单
 * @returns {Promise<Array<{fromStatus: string, toStatus: string, requireOwner: boolean}>>}
 */
export const getTransitions = () => request.get('/tasks/transitions')

/**
 * P2-2 状态机：owner 专用解阻（blocked→in_progress）
 * @param {number} id - 任务ID
 * @param {string} [comment] - 解阻说明（可选）
 * @returns {Promise<void>}
 */
export const unblockTask = (id, comment) => request.patch(`/tasks/${id}/unblock`, { comment })

/**
 * P2-3 Sprint：设置任务所属 Sprint（传 null 取消关联）
 * @param {number} taskId - 任务ID
 * @param {number|null} milestoneId - Sprint ID，null 取消关联
 * @returns {Promise<void>}
 */
export const setTaskMilestone = (taskId, milestoneId) => request.put(`/tasks/${taskId}/milestone`, { milestoneId })