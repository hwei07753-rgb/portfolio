package com.example.project.controller;

import com.example.project.common.Result;
import com.example.project.entity.dto.LabelCreateRequest;
import com.example.project.entity.dto.LabelVO;
import com.example.project.service.LabelService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestAttribute;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequiredArgsConstructor
@RequestMapping("/api")
public class LabelController {

    private final LabelService labelService;

    /** 项目标签列表（全量返回不分页） */
    @GetMapping("/projects/{projectId}/labels")
    public Result<List<LabelVO>> list(
            @PathVariable Long projectId,
            @RequestAttribute("userId") Long userId) {
        List<LabelVO> labels = labelService.listLabels(projectId, userId);
        return Result.success(labels);
    }

    /** 创建标签 */
    @PostMapping("/projects/{projectId}/labels")
    public Result<LabelVO> create(
            @PathVariable Long projectId,
            @RequestBody @Valid LabelCreateRequest request,
            @RequestAttribute("userId") Long userId) {
        LabelVO vo = labelService.createLabel(projectId, request, userId);
        return Result.success(vo, "标签创建成功");
    }

    /** 删除标签（级联删除 task_label 关联） */
    @DeleteMapping("/projects/{projectId}/labels/{id}")
    public Result<Void> delete(
            @PathVariable Long projectId,
            @PathVariable Long id,
            @RequestAttribute("userId") Long userId) {
        labelService.deleteLabel(projectId, id, userId);
        return Result.success(null, "标签已删除");
    }
}