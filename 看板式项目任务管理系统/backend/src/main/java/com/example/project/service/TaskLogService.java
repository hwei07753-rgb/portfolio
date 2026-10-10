package com.example.project.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.example.project.entity.TaskLog;
import com.example.project.entity.dto.TaskLogVO;

import java.util.List;

// R-05-issue-2: 已修复 - 继承 IService<TaskLog>,与项目其他 Service(auth/User/Project/Task)统一风格
public interface TaskLogService extends IService<TaskLog> {

    List<TaskLogVO> listLogs(Long taskId, Long userId);

    TaskLogVO createComment(Long taskId, String content, Long userId);
}