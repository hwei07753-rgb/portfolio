package com.example.project.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.example.project.entity.TaskDependency;
import com.example.project.entity.dto.DependencyCreateRequest;
import com.example.project.entity.dto.TaskDependencyVO;

public interface TaskDependencyService extends IService<TaskDependency> {

    TaskDependencyVO createDependency(Long projectId, DependencyCreateRequest request, Long userId);

    void deleteDependency(Long projectId, Long dependencyId, Long userId);
}
