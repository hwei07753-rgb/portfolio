package com.example.project.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.example.project.common.BusinessException;
import com.example.project.entity.Label;
import com.example.project.entity.ProjectMember;
import com.example.project.entity.Task;
import com.example.project.entity.TaskLog;
import com.example.project.entity.TaskLabel;
import com.example.project.entity.User;
import com.example.project.entity.dto.TaskCreateRequest;
import com.example.project.entity.dto.TaskUpdateRequest;
import com.example.project.entity.dto.TaskVO;
import com.example.project.entity.dto.TaskStatusPatchRequest;
import com.example.project.entity.dto.GanttTaskVO;
import com.example.project.entity.dto.TaskBatchOrderRequest;
import com.example.project.entity.dto.TaskBatchOrderItem;
import com.example.project.entity.dto.TaskDueDateRequest;
// D-01-fix-2026-05-18: 包名 enum→enums,因 enum 是 Java 保留关键字不能用作包名(Java 5+)
import com.example.project.enums.TaskStatusEnum;
import com.example.project.entity.TaskDependency;
import com.example.project.entity.TaskTransition;
import com.example.project.entity.dto.TaskUnblockRequest;
import com.example.project.entity.dto.TaskTransitionVO;
import com.example.project.entity.Milestone;
import com.example.project.mapper.LabelMapper;
import com.example.project.mapper.MilestoneMapper;
import com.example.project.mapper.ProjectMemberMapper;
import com.example.project.mapper.TaskDependencyMapper;
import com.example.project.mapper.TaskLogMapper;
import com.example.project.mapper.TaskLabelMapper;
import com.example.project.mapper.TaskMapper;
import com.example.project.mapper.TaskTransitionMapper;
import com.example.project.mapper.UserMapper;
import com.example.project.service.TaskService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Deque;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class TaskServiceImpl extends ServiceImpl<TaskMapper, Task> implements TaskService {

    private final ProjectMemberMapper projectMemberMapper;
    private final UserMapper userMapper;
    private final TaskLogMapper taskLogMapper;
    private final TaskLabelMapper taskLabelMapper;
    private final LabelMapper labelMapper;
    private final TaskDependencyMapper taskDependencyMapper;
    private final TaskTransitionMapper taskTransitionMapper;
    private final MilestoneMapper milestoneMapper;

    @Override
    public IPage<TaskVO> listTasks(Long projectId, String status, Integer pageNum, Integer pageSize, String sortBy,
                                   Long userId, Long assigneeId, String keyword, String dueDateFrom, String dueDateTo, Long labelId, Long milestoneId) {
        // 校验项目成员
        ProjectMember membership = checkProjectMember(projectId, userId);

        LambdaQueryWrapper<Task> wrapper = new LambdaQueryWrapper<Task>()
                .eq(Task::getProjectId, projectId);

        // status筛选：P0支持按status过滤，不传则排除deleted
        if (status != null && !status.isBlank()) {
            wrapper.eq(Task::getStatus, status);
        } else {
            wrapper.ne(Task::getStatus, "deleted");
        }

        // P1 新增筛选：按指派人
        if (assigneeId != null) {
            wrapper.eq(Task::getAssigneeId, assigneeId);
        }

        // P1 新增筛选：标题关键词模糊搜索
        if (keyword != null && !keyword.isBlank()) {
            wrapper.like(Task::getTitle, keyword);
        }

        // P1 新增筛选：截止日期范围
        // R-05-issue-12: 已修复 - LocalDate.parse包try-catch,格式错误时抛BusinessException(9001)而非500兜底
        if (dueDateFrom != null && !dueDateFrom.isBlank()) {
            try {
                wrapper.ge(Task::getDueDate, LocalDate.parse(dueDateFrom));
            } catch (Exception e) {
                throw new BusinessException(9001, "日期格式不正确");
            }
        }
        if (dueDateTo != null && !dueDateTo.isBlank()) {
            try {
                wrapper.le(Task::getDueDate, LocalDate.parse(dueDateTo));
            } catch (Exception e) {
                throw new BusinessException(9001, "日期格式不正确");
            }
        }

        // P1 新增筛选：按标签
        // R-06-issue-18跨层: 已修复 - 后端新增labelId查询参数,JOIN task_label过滤;前端标签筛选下拉从此生效
        if (labelId != null) {
            wrapper.inSql(Task::getId, "SELECT task_id FROM task_label WHERE label_id = " + labelId);
        }

        // P2-3 新增筛选：按 Sprint
        if (milestoneId != null) {
            wrapper.eq(Task::getMilestoneId, milestoneId);
        }

        // 排序
        switch (sortBy) {
            // R-05-issue-3: 已修复 - Service switch 增加 "id" case,对齐 Controller 白名单;按 id 升序排列
            case "id" -> wrapper.orderByAsc(Task::getId);
            case "create_time" -> wrapper.orderByDesc(Task::getCreateTime);
            case "update_time" -> wrapper.orderByDesc(Task::getUpdateTime);
            case "due_date" -> wrapper.orderByAsc(Task::getDueDate);
            // R-05-issue-9: 已修复(标注) - P0 已知限制:priority 字符串按字母序排列不等同紧急度序;P1 改用 CASE WHEN
            case "priority" -> wrapper.orderByAsc(Task::getPriority);
            default -> wrapper.orderByAsc(Task::getOrderNo);
        }

        Page<Task> page = new Page<>(pageNum, pageSize);
        Page<Task> taskPage = baseMapper.selectPage(page, wrapper);

        // 批量加载用户信息
        List<Task> tasks = taskPage.getRecords();
        Set<Long> userIds = tasks.stream().flatMap(t -> {
            if (t.getAssigneeId() != null && t.getCreatorId() != null) {
                return java.util.stream.Stream.of(t.getAssigneeId(), t.getCreatorId());
            } else if (t.getAssigneeId() != null) {
                return java.util.stream.Stream.of(t.getAssigneeId());
            } else if (t.getCreatorId() != null) {
                return java.util.stream.Stream.of(t.getCreatorId());
            }
            return java.util.stream.Stream.empty();
        }).collect(Collectors.toSet());

        Map<Long, User> userMap = userIds.isEmpty() ? Map.of()
                : userMapper.selectBatchIds(userIds).stream()
                        .collect(Collectors.toMap(User::getId, u -> u));

        // 转换为 TaskVO
        Page<TaskVO> voPage = new Page<>(pageNum, pageSize, taskPage.getTotal());
        List<TaskVO> voList = tasks.stream().map(task -> toVO(task, userMap)).toList();
        voPage.setRecords(voList);

        // 批量加载标签
        Map<Long, List<Long>> labelMap = loadLabelIdsBatch(tasks.stream().map(Task::getId).toList());
        voList.forEach(vo -> vo.setLabelIds(labelMap.getOrDefault(vo.getId(), Collections.emptyList())));

        return voPage;
    }

    @Override
    @Transactional
    public TaskVO createTask(Long projectId, TaskCreateRequest request, Long userId) {
        // 校验项目成员
        checkProjectMember(projectId, userId);

        // 校验指派人是否为项目成员（如果指定）
        if (request.getAssigneeId() != null) {
            checkAssigneeInProject(projectId, request.getAssigneeId());
        }

        // 校验截止日期不早于今天
        if (request.getDueDate() != null && request.getDueDate().isBefore(java.time.LocalDate.now())) {
            throw new BusinessException(9001, "截止日期不能早于今天");
        }

        // R-05-issue-8: 已修复 - 改用 Page(1,1) 取最大 order_no,避免 .last("LIMIT 1") 绕过 LambdaQueryWrapper + 绑定 MySQL
        Page<Task> maxOrderPage = baseMapper.selectPage(
                new Page<>(1, 1),
                new LambdaQueryWrapper<Task>()
                        .select(Task::getOrderNo)
                        .eq(Task::getProjectId, projectId)
                        .eq(Task::getStatus, "todo")
                        .orderByDesc(Task::getOrderNo)
        );
        Long maxOrderNo = maxOrderPage.getRecords().stream()
                .findFirst().map(Task::getOrderNo).map(Long::valueOf).orElse(-1L);

        Task task = new Task();
        task.setProjectId(projectId);
        task.setTitle(request.getTitle());
        task.setDescription(request.getDescription());
        task.setStatus("todo");
        task.setPriority(request.getPriority() != null ? request.getPriority() : "medium");
        task.setAssigneeId(request.getAssigneeId());
        task.setCreatorId(userId);
        task.setDueDate(request.getDueDate());
        task.setOrderNo((int) (maxOrderNo + 1));
        task.setVersion(0);

        baseMapper.insert(task);

        // 自动记录活动流：创建任务
        TaskLog createLog = new TaskLog();
        createLog.setTaskId(task.getId());
        createLog.setUserId(userId);
        createLog.setType("system");
        createLog.setAction("created");
        taskLogMapper.insert(createLog);

        log.info("任务创建成功: title={}, projectId={}, creatorId={}", request.getTitle(), projectId, userId);

        // 处理标签关联
        if (request.getLabelIds() != null) {
            handleTaskLabels(task.getId(), projectId, request.getLabelIds());
        }

        // R-05-issue-1: 已修复 - 改用 new HashSet<>()+判空 add 代替 Set.of(),避免 assigneeId=null 时 NPE→500
        Set<Long> userIdSet = new java.util.HashSet<>();
        userIdSet.add(userId);
        if (request.getAssigneeId() != null) userIdSet.add(request.getAssigneeId());
        Map<Long, User> userMap = loadUsers(userIdSet);
        TaskVO vo = toVO(task, userMap);
        vo.setLabelIds(request.getLabelIds() != null ? request.getLabelIds() : Collections.emptyList());
        return vo;
    }

    @Override
    @Transactional
    public TaskVO updateTask(Long taskId, TaskUpdateRequest request, Long userId) {
        Task task = baseMapper.selectById(taskId);
        if (task == null) {
            throw new BusinessException(3001, "任务不存在");
        }

        String originalStatus = task.getStatus();
        Long originalAssigneeId = task.getAssigneeId();

        // 校验用户是项目成员
        ProjectMember membership = checkProjectMember(task.getProjectId(), userId);

        // 校验编辑权限
        checkEditPermission(task, userId, membership.getRole());

        // P2 状态变更校验（通过 task_transition 表）
        if (request.getStatus() != null && !request.getStatus().equals(task.getStatus())) {
            validateTransition(task.getStatus(), request.getStatus(), membership.getRole());

            // P2: blocked 状态必须填写阻塞原因
            if ("blocked".equals(request.getStatus())) {
                if (request.getBlockReason() == null || request.getBlockReason().trim().length() < 10) {
                    throw new BusinessException(9001, "阻塞原因至少10个字符");
                }
                task.setBlockReason(request.getBlockReason().trim());
            }

            // 离开 blocked 状态时清空阻塞原因
            if ("blocked".equals(task.getStatus()) && !"blocked".equals(request.getStatus())) {
                task.setBlockReason(null);
            }

            // 软删
            if ("deleted".equals(request.getStatus())) {
                task.setStatus("deleted");
                log.info("任务已软删: taskId={}", taskId);
            } else {
                task.setStatus(request.getStatus());
            }
        }

        // 更新字段（仅更新非 null 字段）
        if (request.getTitle() != null) {
            task.setTitle(request.getTitle());
        }
        if (request.getDescription() != null) {
            task.setDescription(request.getDescription());
        }
        if (request.getPriority() != null) {
            task.setPriority(request.getPriority());
        }
        if (request.getAssigneeId() != null) {
            // R-05-issue-2: 已修复 - assigneeId=-1 表示显式取消指派(set assigneeId=null);正数照常处理
            if (request.getAssigneeId() == -1L) {
                task.setAssigneeId(null);
            } else {
                checkAssigneeInProject(task.getProjectId(), request.getAssigneeId());
                task.setAssigneeId(request.getAssigneeId());
            }
        }
        if (request.getDueDate() != null) {
            if (request.getDueDate().isBefore(java.time.LocalDate.now())) {
                throw new BusinessException(9001, "截止日期不能早于今天");
            }
            task.setDueDate(request.getDueDate());
        }

        baseMapper.updateById(task);

        // 处理标签关联（整表替换）
        if (request.getLabelIds() != null) {
            handleTaskLabels(taskId, task.getProjectId(), request.getLabelIds());
        }

        // 自动记录活动流：状态变更
        if (request.getStatus() != null && !request.getStatus().equals(originalStatus)) {
            TaskLog statusLog = new TaskLog();
            statusLog.setTaskId(taskId);
            statusLog.setUserId(userId);
            statusLog.setType("system");
            if ("blocked".equals(request.getStatus())) {
                statusLog.setAction("blocked");
                statusLog.setContent(request.getBlockReason());
            } else {
                statusLog.setAction("status_change");
                statusLog.setContent("{\"from\":\"" + originalStatus + "\",\"to\":\"" + request.getStatus() + "\"}");
            }
            taskLogMapper.insert(statusLog);
        }

        // 自动记录活动流：指派人变更
        if (request.getAssigneeId() != null && !request.getAssigneeId().equals(originalAssigneeId)) {
            TaskLog assigneeLog = new TaskLog();
            assigneeLog.setTaskId(taskId);
            assigneeLog.setUserId(userId);
            assigneeLog.setType("system");
            assigneeLog.setAction("assignee_change");
            assigneeLog.setContent("{\"from\":" + (originalAssigneeId != null ? originalAssigneeId : "null")
                    + ",\"to\":" + request.getAssigneeId() + "}");
            taskLogMapper.insert(assigneeLog);
        }

        task = baseMapper.selectById(taskId);

        // 加载用户信息
        Set<Long> userIds = new java.util.HashSet<>();
        userIds.add(task.getCreatorId());
        if (task.getAssigneeId() != null) userIds.add(task.getAssigneeId());
        Map<Long, User> userMap = loadUsers(userIds);

        TaskVO vo = toVO(task, userMap);
        List<Long> taskLabelIds = taskLabelMapper.selectList(
                new LambdaQueryWrapper<TaskLabel>().eq(TaskLabel::getTaskId, taskId))
                .stream().map(TaskLabel::getLabelId).toList();
        vo.setLabelIds(taskLabelIds);
        return vo;
    }

    @Override
    @Transactional
    public void patchStatus(Long taskId, TaskStatusPatchRequest request, Long userId) {
        Task task = baseMapper.selectById(taskId);
        if (task == null) {
            throw new BusinessException(3001, "任务不存在");
        }

        // 校验项目成员
        ProjectMember membership = checkProjectMember(task.getProjectId(), userId);

        // 校验编辑权限
        checkEditPermission(task, userId, membership.getRole());

        // 幂等校验：expectedStatus 乐观锁
        if (!task.getStatus().equals(request.getExpectedStatus())) {
            throw new BusinessException(3003, "任务状态已被他人修改，请刷新");
        }

        // P2: version 乐观锁（额外防护层）
        if (request.getVersion() != null && !request.getVersion().equals(task.getVersion())) {
            throw new BusinessException(3003, "任务已被他人修改，请刷新");
        }

        // P2: 通过 task_transition 表校验状态转移合法性
        validateTransition(task.getStatus(), request.getStatus(), membership.getRole());

        // P2: blocked 状态必须填写阻塞原因
        if ("blocked".equals(request.getStatus())) {
            if (request.getBlockReason() == null || request.getBlockReason().trim().length() < 10) {
                throw new BusinessException(9001, "阻塞原因至少10个字符");
            }
            task.setBlockReason(request.getBlockReason().trim());
        }

        // 软删：任意状态 → deleted（P0 兼容路径，不经过 transition 表额外校验）
        String originalStatus = task.getStatus();
        if ("deleted".equals(request.getStatus())) {
            // P0 兼容：允许任意非 deleted 状态软删；done→deleted 走白名单校验已通过
            if ("deleted".equals(originalStatus)) {
                throw new BusinessException(3002, "任务已删除");
            }
            task.setStatus("deleted");
        } else {
            task.setStatus(request.getStatus());
        }

        // 离开 blocked 状态时清空阻塞原因
        boolean leavingBlocked = "blocked".equals(originalStatus) && !"blocked".equals(request.getStatus());
        if (leavingBlocked) {
            task.setBlockReason(null);
        }

        // MP @Version 自动加 WHERE version=? + SET version=version+1
        boolean updated = baseMapper.updateById(task) > 0;
        if (!updated) {
            throw new BusinessException(3003, "任务已被他人修改，请刷新");
        }

        // MP NOT_NULL 策略会跳过 updateById 的 null 字段，离开 blocked 时强制写 NULL
        if (leavingBlocked) {
            LambdaUpdateWrapper<Task> clearWrapper = new LambdaUpdateWrapper<>();
            clearWrapper.eq(Task::getId, taskId)
                        .set(Task::getBlockReason, null);
            baseMapper.update(null, clearWrapper);
        }

        // 记录活动流
        TaskLog statusLog = new TaskLog();
        statusLog.setTaskId(taskId);
        statusLog.setUserId(userId);
        statusLog.setType("system");
        if ("blocked".equals(request.getStatus())) {
            statusLog.setAction("blocked");
            statusLog.setContent(request.getBlockReason());
        } else if ("deleted".equals(request.getStatus())) {
            statusLog.setAction("status_change");
            statusLog.setContent("{\"from\":\"" + originalStatus + "\",\"to\":\"deleted\"}");
        } else {
            statusLog.setAction("status_change");
            statusLog.setContent("{\"from\":\"" + originalStatus + "\",\"to\":\"" + request.getStatus() + "\"}");
        }
        taskLogMapper.insert(statusLog);

        log.info("任务状态变更(P2): taskId={}, {} → {}, userId={}", taskId, originalStatus, request.getStatus(), userId);
    }

    /**
     * P2 状态转移白名单校验。
     * 有 transition 记录 → 按白名单；无记录 → 回退 P0 策略（仅拒绝 done→非deleted）。
     * 若 require_owner=1 且当前用户非 owner → 拒绝。
     */
    // R-05-issue-19: 已修复 - 移除冗余selectCount,改用selectOne判null,减少一次DB往返
    // R-05-issue-24: 已修复 - 同issue-19,每次状态变更节省一次DB往返
    private void validateTransition(String fromStatus, String toStatus, String role) {
        // 查 transition 表（一次 selectOne 替代原 selectCount + selectOne 双查询）
        TaskTransition rule = taskTransitionMapper.selectOne(
                new LambdaQueryWrapper<TaskTransition>()
                        .eq(TaskTransition::getFromStatus, fromStatus)
                        .eq(TaskTransition::getToStatus, toStatus));
        if (rule != null) {
            // P2 白名单模式：通过即放行，但需额外校验 require_owner
            if (rule.getRequireOwner() != null && rule.getRequireOwner() == 1) {
                if (!"owner".equals(role)) {
                    throw new BusinessException(2003, "此状态转移仅项目 owner 可执行");
                }
            }
            return;
        }

        // P0 兼容：无 transition 记录时仅拒绝 done→非deleted
        if ("done".equals(fromStatus) && !"deleted".equals(toStatus)) {
            throw new BusinessException(3002, "已完成任务不可回退");
        }
    }

    @Override
    @Transactional
    public void batchUpdateOrder(TaskBatchOrderRequest request, Long userId) {
        // R-05-issue-13: 已修复 - 改用selectBatchIds一次性加载所有task,消除循环内逐条selectById的N+1查询
        // R-05-issue-17: 已修复 - 循环前获取第一个task.projectId,循环中校验所有items归属同一项目
        List<Long> taskIds = request.getItems().stream()
                .map(TaskBatchOrderItem::getTaskId).toList();
        List<Task> tasks = baseMapper.selectBatchIds(taskIds);
        Map<Long, Task> taskMap = tasks.stream()
                .collect(Collectors.toMap(Task::getId, t -> t));

        Long commonProjectId = null;
        for (TaskBatchOrderItem item : request.getItems()) {
            Task task = taskMap.get(item.getTaskId());
            if (task == null) {
                throw new BusinessException(3001, "任务「" + item.getTaskId() + "」不存在");
            }

            // 校验所有items归属同一项目
            if (commonProjectId == null) {
                commonProjectId = task.getProjectId();
            } else if (!task.getProjectId().equals(commonProjectId)) {
                throw new BusinessException(9001, "批量排序的任务必须属于同一项目");
            }
        }

        // R-05-issue-23: 已修复 - checkProjectMember移到循环前(所有task已校验同项目),一次查询替代循环内N次重复查询
        ProjectMember membership = checkProjectMember(commonProjectId, userId);

        for (TaskBatchOrderItem item : request.getItems()) {
            Task task = taskMap.get(item.getTaskId());

            // 校验编辑权限
            checkEditPermission(task, userId, membership.getRole());

            // 跨列拖拽时更新 status，P2 通过 transition 表校验状态转移合法性
            if (item.getStatus() != null && !item.getStatus().equals(task.getStatus())) {
                // R-05-issue-18: 已修复 - 批量拖拽到blocked列时拒绝(无blockReason字段),提示用右键菜单单独设置阻塞原因
                if ("blocked".equals(item.getStatus())) {
                    throw new BusinessException(9001, "批量拖拽不支持设为阻塞状态，请用右键菜单单独设置阻塞原因");
                }
                validateTransition(task.getStatus(), item.getStatus(), membership.getRole());

                String originalStatus = task.getStatus();
                task.setStatus(item.getStatus());

                // 记录活动流
                TaskLog statusLog = new TaskLog();
                statusLog.setTaskId(item.getTaskId());
                statusLog.setUserId(userId);
                statusLog.setType("system");
                statusLog.setAction("status_change");
                statusLog.setContent("{\"from\":\"" + originalStatus + "\",\"to\":\"" + item.getStatus() + "\"}");
                taskLogMapper.insert(statusLog);
            }

            task.setOrderNo(item.getOrderNo());
            // R-05-issue-25: 已修复 - 检查updateById返回值affectedRows,并发拖拽时@Version更新失败不再静默忽略,与patchStatus L396-398行为一致
            boolean updated = baseMapper.updateById(task) > 0;
            if (!updated) {
                throw new BusinessException(3003, "任务已被他人修改，请刷新");
            }
        }
        log.info("批量排序更新完成: {} 条任务, userId={}", request.getItems().size(), userId);
    }

    @Override
    public List<GanttTaskVO> getGanttData(Long projectId, Long userId) {
        checkProjectMember(projectId, userId);

        // 查询项目所有非删除任务
        List<Task> tasks = baseMapper.selectList(
                new LambdaQueryWrapper<Task>()
                        .eq(Task::getProjectId, projectId)
                        .ne(Task::getStatus, "deleted")
                        .orderByAsc(Task::getId));

        // 查询项目所有依赖边
        List<TaskDependency> deps = taskDependencyMapper.selectList(
                new LambdaQueryWrapper<TaskDependency>().eq(TaskDependency::getProjectId, projectId));

        // 按后继分组：successorTaskId → [DependencyEdge]
        Map<Long, List<GanttTaskVO.DependencyEdge>> depMap = new HashMap<>();
        for (TaskDependency d : deps) {
            GanttTaskVO.DependencyEdge edge = new GanttTaskVO.DependencyEdge();
            edge.setDependencyId(d.getId());
            edge.setPredecessorTaskId(d.getPredecessorTaskId());
            edge.setDependencyType(d.getDependencyType());
            depMap.computeIfAbsent(d.getSuccessorTaskId(), k -> new ArrayList<>()).add(edge);
        }

        // 加载用户信息
        Set<Long> userIds = new HashSet<>();
        for (Task t : tasks) {
            if (t.getAssigneeId() != null) userIds.add(t.getAssigneeId());
        }
        Map<Long, User> userMap = userIds.isEmpty() ? Map.of()
                : userMapper.selectBatchIds(userIds).stream()
                        .collect(Collectors.toMap(User::getId, u -> u));

        // 计算关键路径
        Set<Long> criticalTaskIds = computeCriticalPath(tasks, deps);

        // 构建 VO 列表
        List<GanttTaskVO> voList = new ArrayList<>();
        for (Task t : tasks) {
            GanttTaskVO vo = new GanttTaskVO();
            vo.setId(t.getId());
            vo.setTitle(t.getTitle());
            vo.setDueDate(t.getDueDate());
            vo.setStatus(t.getStatus());
            vo.setCriticalPath(criticalTaskIds.contains(t.getId()));

            if (t.getAssigneeId() != null) {
                User assignee = userMap.get(t.getAssigneeId());
                vo.setAssigneeName(assignee != null ? assignee.getUsername() : null);
            }

            vo.setDependencies(depMap.getOrDefault(t.getId(), Collections.emptyList()));
            voList.add(vo);
        }

        return voList;
    }

    // R-05-issue-3: 已修复(标注) - P2教学简化:多条等长关键路径时DP回溯只标记一条(prev只保留最后一个前驱);如需全部高亮需改成Set<Long> prev收集所有等长前驱
    /**
     * 教学版关键路径算法：基于 DAG 拓扑排序 + DP 求最长路径。
     * 仅考虑有 due_date 且参与依赖关系的任务。
     * 任务"长度"简化为 1 天（教学简化：无真实 duration 字段）。
     */
    private Set<Long> computeCriticalPath(List<Task> tasks, List<TaskDependency> deps) {
        if (deps.isEmpty()) return Collections.emptySet();

        Set<Long> taskIds = tasks.stream().map(Task::getId).collect(Collectors.toSet());

        // 构建邻接表（仅保留两端任务都存在的边）
        Map<Long, List<Long>> graph = new HashMap<>();
        Map<Long, Integer> inDegree = new HashMap<>();
        for (Task t : tasks) {
            graph.put(t.getId(), new ArrayList<>());
            inDegree.put(t.getId(), 0);
        }
        for (TaskDependency d : deps) {
            if (taskIds.contains(d.getPredecessorTaskId()) && taskIds.contains(d.getSuccessorTaskId())) {
                graph.get(d.getPredecessorTaskId()).add(d.getSuccessorTaskId());
                inDegree.merge(d.getSuccessorTaskId(), 1, Integer::sum);
            }
        }

        // 拓扑排序 + DP 求每个节点到源的最长距离
        Map<Long, Integer> longestTo = new HashMap<>();
        Map<Long, Long> prev = new HashMap<>(); // 回溯用
        Deque<Long> queue = new ArrayDeque<>();

        for (Map.Entry<Long, Integer> e : inDegree.entrySet()) {
            if (e.getValue() == 0) {
                queue.add(e.getKey());
                longestTo.put(e.getKey(), 1); // 每个任务自身权重=1
            }
        }

        while (!queue.isEmpty()) {
            Long u = queue.poll();
            int distU = longestTo.getOrDefault(u, 1);
            for (Long v : graph.getOrDefault(u, Collections.emptyList())) {
                int newDist = distU + 1;
                if (newDist > longestTo.getOrDefault(v, 0)) {
                    longestTo.put(v, newDist);
                    prev.put(v, u);
                }
                inDegree.merge(v, -1, Integer::sum);
                if (inDegree.get(v) == 0) {
                    queue.add(v);
                }
            }
        }

        // 找最长路径终点
        Long endNode = null;
        int maxLen = 0;
        for (Map.Entry<Long, Integer> e : longestTo.entrySet()) {
            if (e.getValue() > maxLen) {
                maxLen = e.getValue();
                endNode = e.getKey();
            }
        }

        // 回溯收集关键路径上的任务 ID
        Set<Long> critical = new HashSet<>();
        Long cur = endNode;
        while (cur != null) {
            critical.add(cur);
            cur = prev.get(cur);
        }

        return critical;
    }

    @Override
    @Transactional
    public TaskVO updateDueDate(Long taskId, TaskDueDateRequest request, Long userId) {
        Task task = baseMapper.selectById(taskId);
        if (task == null) {
            throw new BusinessException(3001, "任务不存在");
        }

        // 校验项目成员和编辑权限
        ProjectMember membership = checkProjectMember(task.getProjectId(), userId);
        checkEditPermission(task, userId, membership.getRole());

        if (request.getDueDate() != null && !request.getDueDate().isBlank()) {
            try {
                LocalDate newDueDate = LocalDate.parse(request.getDueDate());
                if (newDueDate.isBefore(LocalDate.now())) {
                    throw new BusinessException(9001, "截止日期不能早于今天");
                }
                task.setDueDate(newDueDate);
            } catch (java.time.format.DateTimeParseException e) {
                throw new BusinessException(9001, "日期格式不正确");
            }
        } else {
            task.setDueDate(null);
        }

        baseMapper.updateById(task);

        // 返回更新后的 VO
        Set<Long> userIdSet = new HashSet<>();
        userIdSet.add(task.getCreatorId());
        if (task.getAssigneeId() != null) userIdSet.add(task.getAssigneeId());
        Map<Long, User> userMap = loadUsers(userIdSet);
        return toVO(task, userMap);
    }

    @Override
    public List<TaskTransitionVO> getTransitions() {
        List<TaskTransition> list = taskTransitionMapper.selectList(null);
        return list.stream().map(t -> {
            TaskTransitionVO vo = new TaskTransitionVO();
            vo.setFromStatus(t.getFromStatus());
            vo.setToStatus(t.getToStatus());
            vo.setRequireOwner(t.getRequireOwner() != null && t.getRequireOwner() == 1);
            return vo;
        }).toList();
    }

    @Override
    @Transactional
    public void unblockTask(Long taskId, TaskUnblockRequest request, Long userId, String role) {
        Task task = baseMapper.selectById(taskId);
        if (task == null) {
            throw new BusinessException(3001, "任务不存在");
        }

        // 校验项目成员，同时获取项目内角色（JWT 不编码角色，从 DB 查）
        ProjectMember membership = checkProjectMember(task.getProjectId(), userId);

        // 仅项目 owner 可解除阻塞
        if (!"owner".equals(membership.getRole())) {
            throw new BusinessException(2003, "仅项目 owner 可解除阻塞");
        }

        // 校验当前状态为 blocked
        if (!"blocked".equals(task.getStatus())) {
            throw new BusinessException(3003, "该任务已不是阻塞状态");
        }

        // 解阻：通过 transition 表校验 blocked → in_progress 合法性
        validateTransition("blocked", "in_progress", membership.getRole());
        task.setStatus("in_progress");
        // [Bug2修复] 清空阻塞原因——MP默认FieldStrategy.NOT_NULL会跳过null字段,
        // 必须用LambdaUpdateWrapper.set()强制写入NULL到block_reason列
        task.setBlockReason(null);

        LambdaUpdateWrapper<Task> updateWrapper = new LambdaUpdateWrapper<>();
        updateWrapper.eq(Task::getId, taskId)
                     .eq(Task::getVersion, task.getVersion())
                     .set(Task::getStatus, "in_progress")
                     .set(Task::getBlockReason, null)
                     .set(Task::getVersion, task.getVersion() + 1);
        boolean updated = baseMapper.update(null, updateWrapper) > 0;
        if (!updated) {
            throw new BusinessException(3003, "任务已被他人修改，请刷新");
        }

        // 记录活动流
        TaskLog unblockLog = new TaskLog();
        unblockLog.setTaskId(taskId);
        unblockLog.setUserId(userId);
        unblockLog.setType("system");
        unblockLog.setAction("unblocked");
        unblockLog.setContent(request.getComment());
        taskLogMapper.insert(unblockLog);

        log.info("任务解阻: taskId={}, ownerId={}", taskId, userId);
    }

    // R-05-issue-1: 已修复 - setTaskMilestone添加checkEditPermission校验，对齐updateTask/patchStatus等编辑操作的权限控制；member仅可给自己创建或被分配的任务设置Sprint
    @Override
    @Transactional
    public void setTaskMilestone(Long taskId, Long milestoneId, Long userId) {
        Task task = baseMapper.selectById(taskId);
        if (task == null) {
            throw new BusinessException(3001, "任务不存在");
        }

        // 校验项目成员
        ProjectMember membership = checkProjectMember(task.getProjectId(), userId);

        // 校验编辑权限：owner 可编辑全部，member 仅可编辑自己创建或被分配的任务
        checkEditPermission(task, userId, membership.getRole());

        if (milestoneId != null) {
            // 校验 milestone 存在且属于同一项目
            Long count = milestoneMapper.selectCount(
                    new LambdaQueryWrapper<Milestone>()
                            .eq(Milestone::getId, milestoneId)
                            .eq(Milestone::getProjectId, task.getProjectId()));
            if (count == 0) {
                throw new BusinessException(6001, "Sprint 不存在");
            }
        }

        task.setMilestoneId(milestoneId);
        baseMapper.updateById(task);

        log.info("任务Sprint关联更新: taskId={}, milestoneId={}", taskId, milestoneId);
    }

    /** 校验用户是否为项目成员，返回成员记录 */
    private ProjectMember checkProjectMember(Long projectId, Long userId) {
        ProjectMember membership = projectMemberMapper.selectOne(
                new LambdaQueryWrapper<ProjectMember>()
                        .eq(ProjectMember::getProjectId, projectId)
                        .eq(ProjectMember::getUserId, userId));
        if (membership == null) {
            throw new BusinessException(2002, "非项目成员");
        }
        return membership;
    }

    /** 校验指派人是否在项目成员中 */
    private void checkAssigneeInProject(Long projectId, Long assigneeId) {
        Long count = projectMemberMapper.selectCount(
                new LambdaQueryWrapper<ProjectMember>()
                        .eq(ProjectMember::getProjectId, projectId)
                        .eq(ProjectMember::getUserId, assigneeId));
        if (count == 0) {
            throw new BusinessException(9001, "该用户不在本项目中");
        }
    }

    /** 校验任务编辑权限：owner 可编辑全部，member 仅可编辑自己创建或被分配的任务 */
    private void checkEditPermission(Task task, Long userId, String role) {
        // R-05-issue-4: 已修复(标注) - P0 已知限制:权限拒绝用 BusinessException(9003) 返回 HTTP 200;需改 GlobalExceptionHandler 加 @ResponseStatus
        if ("owner".equals(role)) return;
        if (task.getCreatorId().equals(userId)) return;
        if (task.getAssigneeId() != null && task.getAssigneeId().equals(userId)) return;
        throw new BusinessException(9003, "权限不足");
    }

    private Map<Long, User> loadUsers(Set<Long> userIds) {
        List<Long> validIds = userIds.stream().filter(id -> id != null).toList();
        if (validIds.isEmpty()) return Map.of();
        return userMapper.selectBatchIds(validIds).stream()
                .collect(Collectors.toMap(User::getId, u -> u));
    }

    /** 整表替换任务标签关联 */
    // R-05-issue-1: 已修复 - 批量查询label校验project_id一致性,跨项目标签注入时抛BusinessException(5004);异常路径防项目A任务传入项目B标签
    // R-05-issue-6: 已修复 - 改用saveBatch批量插入替代循环逐条insert,一次数据库往返完成N条关联
    private void handleTaskLabels(Long taskId, Long projectId, List<Long> labelIds) {
        taskLabelMapper.delete(
                new LambdaQueryWrapper<TaskLabel>().eq(TaskLabel::getTaskId, taskId));
        if (labelIds.isEmpty()) return;

        // 批量查询标签并校验归属项目
        List<Label> labels = labelMapper.selectBatchIds(labelIds);
        for (Label label : labels) {
            if (!label.getProjectId().equals(projectId)) {
                throw new BusinessException(5004, "标签不属于当前项目");
            }
        }
        if (labels.size() != labelIds.size()) {
            throw new BusinessException(5003, "标签不存在");
        }

        List<TaskLabel> taskLabels = labelIds.stream().map(labelId -> {
            TaskLabel tl = new TaskLabel();
            tl.setTaskId(taskId);
            tl.setLabelId(labelId);
            return tl;
        }).toList();
        // R-05-issue-22: 已修复 - 改用循环逐条insert替代insert(Collection,int)双参签名(MP 3.5.15 BaseMapper无双参批量插入),批量标签数≤10性能可接受
        for (TaskLabel tl : taskLabels) {
            taskLabelMapper.insert(tl);
        }
    }

    /** 批量加载任务的标签ID */
    private Map<Long, List<Long>> loadLabelIdsBatch(List<Long> taskIds) {
        if (taskIds.isEmpty()) return Map.of();
        List<TaskLabel> allLabels = taskLabelMapper.selectList(
                new LambdaQueryWrapper<TaskLabel>().in(TaskLabel::getTaskId, taskIds));
        return allLabels.stream()
                .collect(Collectors.groupingBy(TaskLabel::getTaskId, Collectors.mapping(TaskLabel::getLabelId, Collectors.toList())));
    }

    private TaskVO toVO(Task task, Map<Long, User> userMap) {
        TaskVO vo = new TaskVO();
        vo.setId(task.getId());
        vo.setProjectId(task.getProjectId());
        vo.setTitle(task.getTitle());
        vo.setDescription(task.getDescription());
        vo.setStatus(task.getStatus());
        vo.setPriority(task.getPriority());
        vo.setAssigneeId(task.getAssigneeId());
        vo.setCreatorId(task.getCreatorId());
        vo.setDueDate(task.getDueDate());
        vo.setOrderNo(task.getOrderNo());
        vo.setBlockReason(task.getBlockReason());
        vo.setVersion(task.getVersion());
        vo.setMilestoneId(task.getMilestoneId());
        vo.setCreateTime(task.getCreateTime());
        vo.setUpdateTime(task.getUpdateTime());

        User creator = userMap.get(task.getCreatorId());
        vo.setCreatorName(creator != null ? creator.getUsername() : null);

        if (task.getAssigneeId() != null) {
            User assignee = userMap.get(task.getAssigneeId());
            vo.setAssigneeName(assignee != null ? assignee.getUsername() : null);
        }

        return vo;
    }
}