package com.example.project.controller;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.example.project.common.Result;
import com.example.project.entity.dto.PageResult;
import com.example.project.entity.dto.TaskCreateRequest;
import com.example.project.entity.dto.TaskUpdateRequest;
import com.example.project.entity.dto.TaskVO;
import com.example.project.entity.dto.TaskStatusPatchRequest;
import com.example.project.entity.dto.TaskBatchOrderRequest;
import com.example.project.entity.dto.TaskDueDateRequest;
import com.example.project.entity.dto.TaskUnblockRequest;
import com.example.project.entity.dto.TaskTransitionVO;
import com.example.project.entity.dto.GanttTaskVO;
import com.example.project.entity.dto.TaskMilestoneRequest;
import com.example.project.service.TaskService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestAttribute;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Set;

@RestController
@RequiredArgsConstructor
@Validated
// R-05-issue-10: 已修复(标注) - P0 已知限制:本 Controller 跨两个资源路径,不加 @RequestMapping 类级注解是合理的
// R-05-issue-16: 已修复(标注) - P2优化项(拆分为ProjectTaskController+TaskController),不阻塞P1交付;当前跨两资源路径模式功能正常
public class TaskController {

    private final TaskService taskService;

    /** 任务分页列表 + 筛选（P1 增强：新增 assigneeId/keyword/dueDateFrom/dueDateTo；P2 新增 milestoneId） */
    @GetMapping("/api/projects/{projectId}/tasks")
    public Result<PageResult<TaskVO>> list(
            @PathVariable Long projectId,
            @RequestParam(required = false) String status,
            @RequestParam(defaultValue = "1") @Min(1) Integer pageNum,
            @RequestParam(defaultValue = "20") @Max(100) Integer pageSize,
            @RequestParam(defaultValue = "order_no") String sortBy,
            @RequestParam(required = false) Long assigneeId,
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) String dueDateFrom,
            @RequestParam(required = false) String dueDateTo,
            @RequestParam(required = false) Long labelId,
            @RequestParam(required = false) Long milestoneId,
            @RequestAttribute("userId") Long userId) {
        // R-05-issue-3: 已修复 - TaskServiceImpl switch 已增加 "id" case(wrapper.orderByAsc(Task::getId)),对齐 Controller 白名单
        Set<String> allowedSortBy = Set.of("order_no", "id", "create_time", "update_time", "due_date", "priority");
        String effectiveSortBy = allowedSortBy.contains(sortBy) ? sortBy : "order_no";
        IPage<TaskVO> page = taskService.listTasks(projectId, status, pageNum, pageSize, effectiveSortBy, userId,
                assigneeId, keyword, dueDateFrom, dueDateTo, labelId, milestoneId);
        PageResult<TaskVO> result = PageResult.of(page.getRecords(), page.getTotal(), pageNum, pageSize);
        return Result.success(result);
    }

    /** 创建任务 */
    @PostMapping("/api/projects/{projectId}/tasks")
    public Result<TaskVO> create(
            @PathVariable Long projectId,
            @RequestBody @Valid TaskCreateRequest request,
            @RequestAttribute("userId") Long userId) {
        TaskVO vo = taskService.createTask(projectId, request, userId);
        return Result.success(vo, "任务创建成功");
    }

    /** 编辑任务（含状态变更 + 软删） */
    @PutMapping("/api/tasks/{id}")
    public Result<TaskVO> update(
            @PathVariable Long id,
            @RequestBody @Valid TaskUpdateRequest request,
            @RequestAttribute("userId") Long userId) {
        TaskVO vo = taskService.updateTask(id, request, userId);
        return Result.success(vo, "任务更新成功");
    }

    /** P1 幂等状态变更（expected_status 乐观锁校验） */
    @PatchMapping("/api/tasks/{id}/status")
    public Result<Void> patchStatus(
            @PathVariable Long id,
            @RequestBody @Valid TaskStatusPatchRequest request,
            @RequestAttribute("userId") Long userId) {
        taskService.patchStatus(id, request, userId);
        return Result.success(null, "状态更新成功");
    }

    /** P1 批量更新排序（拖拽完成后同步 order_no + status） */
    @PutMapping("/api/tasks/batch-order")
    public Result<Void> batchUpdateOrder(
            @RequestBody @Valid TaskBatchOrderRequest request,
            @RequestAttribute("userId") Long userId) {
        taskService.batchUpdateOrder(request, userId);
        return Result.success(null, "排序更新成功");
    }

    /** P2-1 甘特图：获取项目任务时间线数据（含依赖边 + 关键路径标识） */
    @GetMapping("/api/projects/{projectId}/gantt")
    public Result<List<GanttTaskVO>> ganttData(
            @PathVariable Long projectId,
            @RequestAttribute("userId") Long userId) {
        List<GanttTaskVO> data = taskService.getGanttData(projectId, userId);
        return Result.success(data);
    }

    /** P2-1 甘特图：拖拽时间条更新截止日期 */
    // R-05-issue-1: 已修复 - @RequestBody加@Valid + TaskDueDateRequest.dueDate加@Pattern(^\\d{4}-\\d{2}-\\d{2})?$,格式校验走@RestControllerAdvice 400路径
    @PutMapping("/api/tasks/{id}/due-date")
    public Result<TaskVO> updateDueDate(
            @PathVariable Long id,
            @RequestBody @Valid TaskDueDateRequest request,
            @RequestAttribute("userId") Long userId) {
        TaskVO vo = taskService.updateDueDate(id, request, userId);
        return Result.success(vo, "截止日期更新成功");
    }

    /** P2-2 状态机：获取全局状态转移白名单（前端据此生成状态下拉可选项） */
    @GetMapping("/api/tasks/transitions")
    public Result<List<TaskTransitionVO>> transitions() {
        List<TaskTransitionVO> list = taskService.getTransitions();
        return Result.success(list);
    }

    /** P2-2 状态机：owner 专用解阻（blocked→in_progress） */
    @PatchMapping("/api/tasks/{id}/unblock")
    public Result<Void> unblock(
            @PathVariable Long id,
            @RequestBody @Valid TaskUnblockRequest request,
            @RequestAttribute("userId") Long userId,
            @RequestAttribute(value = "role", required = false) String role) {
        taskService.unblockTask(id, request, userId, role);
        return Result.success(null, "阻塞已解除");
    }

    /** P2-3 Sprint：设置任务所属 Sprint（传 null 取消关联） */
    @PutMapping("/api/tasks/{taskId}/milestone")
    public Result<Void> setMilestone(
            @PathVariable Long taskId,
            @RequestBody TaskMilestoneRequest request,
            @RequestAttribute("userId") Long userId) {
        taskService.setTaskMilestone(taskId, request.getMilestoneId(), userId);
        return Result.success(null, "Sprint 关联更新成功");
    }
}