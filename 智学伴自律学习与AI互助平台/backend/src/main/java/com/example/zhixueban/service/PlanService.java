package com.example.zhixueban.service;

import com.example.zhixueban.entity.dto.StudyPlanRequest;
import com.example.zhixueban.entity.dto.StudyPlanVO;
import com.example.zhixueban.entity.dto.StudyTaskRequest;
import com.example.zhixueban.entity.dto.StudyTaskVO;
import com.example.zhixueban.entity.dto.TodayTasksSummaryVO;

import java.util.List;

/**
 * 阶段性学业计划与每日任务清单服务接口
 */
public interface PlanService {

    /** 获取用户所有学习计划及其子任务列表 */
    List<StudyPlanVO> getMyPlans(Long userId);

    /** 获取今日待办任务概览看板数据（首页小组件） */
    TodayTasksSummaryVO getTodayTasksSummary(Long userId);

    /** 创建自定义学习计划及批量子任务 */
    StudyPlanVO createPlan(Long userId, StudyPlanRequest request);

    /** 为计划添加单项每日任务 */
    StudyTaskVO createTask(Long userId, StudyTaskRequest request);

    /** 打勾 / 取消打勾完成任务（原子联动增减自律学分） */
    StudyTaskVO toggleTask(Long userId, Long taskId);

    /** 删除阶段计划（级联删除子任务） */
    void deletePlan(Long userId, Long planId);

    /** 删除单个日常任务项 */
    void deleteTask(Long userId, Long taskId);

    /** 一键导入经典学业模板（四六级 / 考研 / 期末冲刺） */
    StudyPlanVO applyTemplate(Long userId, String templateType);
}
