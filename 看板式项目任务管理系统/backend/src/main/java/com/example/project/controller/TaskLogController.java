package com.example.project.controller;

import com.example.project.common.Result;
import com.example.project.entity.dto.CommentCreateRequest;
import com.example.project.entity.dto.TaskLogVO;
import com.example.project.service.TaskLogService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestAttribute;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

// R-05-issue-1: 已修复 - 添加 @RequestMapping("/api") + 方法级路径移除 /api 前缀,与 AuthController/ProjectController/TaskController 风格对齐
@RestController
@RequiredArgsConstructor
@RequestMapping("/api")
public class TaskLogController {

    private final TaskLogService taskLogService;

    /** 活动流列表（按时间倒序） */
    @GetMapping("/tasks/{taskId}/logs")
    public Result<List<TaskLogVO>> listLogs(
            @PathVariable Long taskId,
            @RequestAttribute("userId") Long userId) {
        List<TaskLogVO> logs = taskLogService.listLogs(taskId, userId);
        return Result.success(logs);
    }

    /** 添加评论 */
    @PostMapping("/tasks/{taskId}/comments")
    public Result<TaskLogVO> createComment(
            @PathVariable Long taskId,
            @RequestBody @Valid CommentCreateRequest request,
            @RequestAttribute("userId") Long userId) {
        TaskLogVO vo = taskLogService.createComment(taskId, request.getContent(), userId);
        return Result.success(vo, "评论发送成功");
    }
}