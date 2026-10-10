package com.example.project.service;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.service.IService;
import com.example.project.entity.Task;
import com.example.project.entity.dto.TaskCreateRequest;
import com.example.project.entity.dto.TaskUpdateRequest;
import com.example.project.entity.dto.TaskVO;
import com.example.project.entity.dto.TaskStatusPatchRequest;
import com.example.project.entity.dto.GanttTaskVO;
import com.example.project.entity.dto.TaskBatchOrderRequest;
import com.example.project.entity.dto.TaskDueDateRequest;

import com.example.project.entity.dto.TaskUnblockRequest;
import com.example.project.entity.dto.TaskTransitionVO;

import java.util.List;

public interface TaskService extends IService<Task> {

    IPage<TaskVO> listTasks(Long projectId, String status, Integer pageNum, Integer pageSize, String sortBy,
                            Long userId, Long assigneeId, String keyword, String dueDateFrom, String dueDateTo, Long labelId, Long milestoneId);

    TaskVO createTask(Long projectId, TaskCreateRequest request, Long userId);

    TaskVO updateTask(Long taskId, TaskUpdateRequest request, Long userId);

    void patchStatus(Long taskId, TaskStatusPatchRequest request, Long userId);

    void batchUpdateOrder(TaskBatchOrderRequest request, Long userId);

    /** P2-1 甘特图：获取项目任务时间线数据（含依赖边 + 关键路径标识） */
    List<GanttTaskVO> getGanttData(Long projectId, Long userId);

    /** P2-1 甘特图：拖拽时间条更新截止日期 */
    TaskVO updateDueDate(Long taskId, TaskDueDateRequest request, Long userId);

    /** P2-2 状态机：获取全局状态转移白名单 */
    List<TaskTransitionVO> getTransitions();

    /** P2-2 状态机：owner 专用解阻（blocked→in_progress）。role 参数用于前置权限校验。 */
    void unblockTask(Long taskId, TaskUnblockRequest request, Long userId, String role);

    /** P2-3 Sprint：设置任务所属 Sprint（传 null 取消关联） */
    void setTaskMilestone(Long taskId, Long milestoneId, Long userId);
}