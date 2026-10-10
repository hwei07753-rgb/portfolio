package com.example.project.entity.dto;

import lombok.Data;

import java.time.LocalDate;
import java.util.List;

@Data
public class GanttTaskVO {

    private Long id;
    private String title;
    private LocalDate dueDate;
    private String assigneeName;
    private String status;
    private boolean criticalPath;

    /** 本任务作为后继的依赖边列表 */
    private List<DependencyEdge> dependencies;

    @Data
    public static class DependencyEdge {
        private Long dependencyId;
        private Long predecessorTaskId;
        private String dependencyType;
    }
}
