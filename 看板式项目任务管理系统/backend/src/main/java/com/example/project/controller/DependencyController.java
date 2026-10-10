package com.example.project.controller;

import com.example.project.common.Result;
import com.example.project.entity.dto.DependencyCreateRequest;
import com.example.project.entity.dto.TaskDependencyVO;
import com.example.project.service.TaskDependencyService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestAttribute;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequiredArgsConstructor
public class DependencyController {

    private final TaskDependencyService taskDependencyService;

    /** 创建任务依赖边（甘特图拖拽连线） */
    @PostMapping("/api/projects/{projectId}/dependencies")
    public Result<TaskDependencyVO> create(
            @PathVariable Long projectId,
            @RequestBody @Valid DependencyCreateRequest request,
            @RequestAttribute("userId") Long userId) {
        TaskDependencyVO vo = taskDependencyService.createDependency(projectId, request, userId);
        return Result.success(vo, "依赖创建成功");
    }

    /** 删除任务依赖边（甘特图右键删除连线） */
    @DeleteMapping("/api/projects/{projectId}/dependencies/{id}")
    public Result<Void> delete(
            @PathVariable Long projectId,
            @PathVariable Long id,
            @RequestAttribute("userId") Long userId) {
        taskDependencyService.deleteDependency(projectId, id, userId);
        return Result.success(null, "依赖已删除");
    }
}
