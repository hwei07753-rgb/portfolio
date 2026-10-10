package com.example.project.enums;

import java.util.Set;

/**
 * P0 任务状态枚举：仅拒绝已完成回退（done→*），其余任意转移放行
 */
public enum TaskStatusEnum {

    TODO("todo", "待办"),
    IN_PROGRESS("in_progress", "进行中"),
    DONE("done", "已完成"),
    BLOCKED("blocked", "已阻塞"),
    DELETED("deleted", "已删除");

    private final String value;
    private final String label;

    TaskStatusEnum(String value, String label) {
        this.value = value;
        this.label = label;
    }

    public String getValue() { return value; }
    public String getLabel() { return label; }

    /**
     * P0 策略：仅拒绝已完成回退（done → todo/in_progress/blocked），其余任意转移放行
     */
    public boolean canTransitTo(TaskStatusEnum target) {
        if (this == DONE && target != DELETED) {
            return false;
        }
        if (target == DELETED && this == DELETED) {
            return false;
        }
        return true;
    }

    public static TaskStatusEnum fromValue(String value) {
        for (TaskStatusEnum s : values()) {
            if (s.value.equals(value)) return s;
        }
        return null;
    }

    /** P0 合法状态值集合（不含 deleted，deleted 是软删标记不参与看板展示） */
    public static final Set<String> BOARD_STATUSES = Set.of("todo", "in_progress", "done", "blocked");
}