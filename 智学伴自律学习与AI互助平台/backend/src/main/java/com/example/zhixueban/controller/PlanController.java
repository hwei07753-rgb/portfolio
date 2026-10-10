package com.example.zhixueban.controller;

import com.example.zhixueban.common.Result;
import com.example.zhixueban.entity.dto.StudyPlanRequest;
import com.example.zhixueban.entity.dto.StudyPlanVO;
import com.example.zhixueban.entity.dto.StudyTaskRequest;
import com.example.zhixueban.entity.dto.StudyTaskVO;
import com.example.zhixueban.entity.dto.TodayTasksSummaryVO;
import com.example.zhixueban.service.PlanService;
import com.example.zhixueban.util.UserContext;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 阶段性学业计划与每日任务清单控制器
 */
@RestController
@RequestMapping("/api/plan")
public class PlanController {

    private final PlanService planService;

    public PlanController(PlanService planService) {
        this.planService = planService;
    }

    /** 获取当前用户的所有阶段计划与子任务列表 */
    @GetMapping("/list")
    public Result<List<StudyPlanVO>> list() {
        return Result.success(planService.getMyPlans(UserContext.getUserId()));
    }

    /** 获取今日待办任务看板概览数据（首页交互小组件） */
    @GetMapping("/today-summary")
    public Result<TodayTasksSummaryVO> todaySummary() {
        return Result.success(planService.getTodayTasksSummary(UserContext.getUserId()));
    }

    /** 创建自定义阶段学习计划 */
    @PostMapping
    public Result<StudyPlanVO> createPlan(@Valid @RequestBody StudyPlanRequest request) {
        return Result.success(planService.createPlan(UserContext.getUserId(), request), "阶段计划创建成功");
    }

    /** 为计划添加单项每日任务 */
    @PostMapping("/task")
    public Result<StudyTaskVO> createTask(@Valid @RequestBody StudyTaskRequest request) {
        return Result.success(planService.createTask(UserContext.getUserId(), request), "任务项添加成功");
    }

    /** 打勾 / 取消打勾完成任务（原子联动增减自律学分） */
    @PostMapping("/task/{id}/toggle")
    public Result<StudyTaskVO> toggleTask(@PathVariable Long id) {
        StudyTaskVO vo = planService.toggleTask(UserContext.getUserId(), id);
        String msg = vo.getIsCompleted() == 1 ? "太棒了！已打勾完成 (+5 自律学分 🪙)" : "已取消完成";
        return Result.success(vo, msg);
    }

    /** 删除阶段计划及所属子任务 */
    @DeleteMapping("/{id}")
    public Result<Void> deletePlan(@PathVariable Long id) {
        planService.deletePlan(UserContext.getUserId(), id);
        return Result.success(null, "学习计划已删除");
    }

    /** 删除单个任务项 */
    @DeleteMapping("/task/{id}")
    public Result<Void> deleteTask(@PathVariable Long id) {
        planService.deleteTask(UserContext.getUserId(), id);
        return Result.success(null, "任务项已删除");
    }

    /** 一键套用经典学业备考模板（cet4 / kaoyan / final_exam / self_discipline） */
    @PostMapping("/template/{type}")
    public Result<StudyPlanVO> applyTemplate(@PathVariable String type) {
        return Result.success(planService.applyTemplate(UserContext.getUserId(), type), "经典学业模版已成功套用");
    }
}
