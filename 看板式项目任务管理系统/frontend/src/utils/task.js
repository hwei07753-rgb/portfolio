/**
 * 优先级标签类型映射
 * @param {string} p - priority 值 (low/medium/high/urgent)
 * @returns {string} Element Plus tag type
 */
export function priorityTagType(p) {
  return { low: 'info', medium: 'warning', high: 'danger', urgent: 'danger' }[p] || 'info'
}

/**
 * 优先级中文标签
 * @param {string} p - priority 值
 * @returns {string} 中文标签
 */
export function priorityLabel(p) {
  return { low: '低', medium: '中', high: '高', urgent: '紧急' }[p] || p
}

/**
 * 任务状态标签类型映射
 * @param {string} s - status 值 (todo/in_progress/done/blocked)
 * @returns {string} Element Plus tag type
 */
export function statusTagType(s) {
  return { todo: 'info', in_progress: 'primary', done: 'success', blocked: 'danger' }[s] || 'info'
}

/**
 * 任务状态中文标签
 * @param {string} s - status 值
 * @returns {string} 中文标签
 */
export function statusLabel(s) {
  return { todo: '待办', in_progress: '进行中', done: '已完成', blocked: '已阻塞' }[s] || s
}