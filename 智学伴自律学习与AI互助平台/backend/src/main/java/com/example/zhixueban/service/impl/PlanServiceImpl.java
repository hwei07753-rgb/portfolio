package com.example.zhixueban.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.example.zhixueban.common.BusinessException;
import com.example.zhixueban.common.ErrorCode;
import com.example.zhixueban.entity.StudyPlan;
import com.example.zhixueban.entity.StudyTask;
import com.example.zhixueban.entity.User;
import com.example.zhixueban.entity.dto.StudyPlanRequest;
import com.example.zhixueban.entity.dto.StudyPlanVO;
import com.example.zhixueban.entity.dto.StudyTaskRequest;
import com.example.zhixueban.entity.dto.StudyTaskVO;
import com.example.zhixueban.entity.dto.TodayTasksSummaryVO;
import com.example.zhixueban.mapper.StudyPlanMapper;
import com.example.zhixueban.mapper.StudyTaskMapper;
import com.example.zhixueban.mapper.UserMapper;
import com.example.zhixueban.service.PlanService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * 阶段性学业计划与每日任务清单服务实现
 */
@Service
public class PlanServiceImpl implements PlanService {

    private static final Logger log = LoggerFactory.getLogger(PlanServiceImpl.class);

    private final StudyPlanMapper studyPlanMapper;
    private final StudyTaskMapper studyTaskMapper;
    private final UserMapper userMapper;

    public PlanServiceImpl(StudyPlanMapper studyPlanMapper,
                           StudyTaskMapper studyTaskMapper,
                           UserMapper userMapper) {
        this.studyPlanMapper = studyPlanMapper;
        this.studyTaskMapper = studyTaskMapper;
        this.userMapper = userMapper;
    }

    @Override
    public List<StudyPlanVO> getMyPlans(Long userId) {
        List<StudyPlan> plans = studyPlanMapper.selectList(
                new LambdaQueryWrapper<StudyPlan>()
                        .eq(StudyPlan::getUserId, userId)
                        .orderByAsc(StudyPlan::getStatus)
                        .orderByDesc(StudyPlan::getCreatedAt)
        );

        // 若用户首次访问且没有任何计划，自动贴心初始化四级冲刺模板
        if (plans.isEmpty()) {
            StudyPlanVO defaultPlan = applyTemplate(userId, "cet4");
            return List.of(defaultPlan);
        }

        // 查询该用户的所有任务项
        List<StudyTask> allTasks = studyTaskMapper.selectList(
                new LambdaQueryWrapper<StudyTask>()
                        .eq(StudyTask::getUserId, userId)
                        .orderByAsc(StudyTask::getId)
        );

        Map<Long, List<StudyTask>> tasksByPlanId = allTasks.stream()
                .filter(t -> t.getPlanId() != null)
                .collect(Collectors.groupingBy(StudyTask::getPlanId));

        List<StudyPlanVO> result = new ArrayList<>();
        for (StudyPlan plan : plans) {
            List<StudyTask> planTasks = tasksByPlanId.getOrDefault(plan.getId(), Collections.emptyList());
            result.add(buildPlanVO(plan, planTasks));
        }
        return result;
    }

    @Override
    public TodayTasksSummaryVO getTodayTasksSummary(Long userId) {
        List<StudyPlanVO> myPlans = getMyPlans(userId);
        StudyPlanVO activePlan = myPlans.stream()
                .filter(p -> p.getStatus() != null && p.getStatus() == 0)
                .findFirst()
                .orElse(myPlans.isEmpty() ? null : myPlans.get(0));

        List<StudyTask> todayTasks = studyTaskMapper.selectList(
                new LambdaQueryWrapper<StudyTask>()
                        .eq(StudyTask::getUserId, userId)
                        .orderByAsc(StudyTask::getIsCompleted)
                        .orderByAsc(StudyTask::getId)
        );

        List<StudyTaskVO> taskVOs = todayTasks.stream()
                .map(t -> {
                    StudyTaskVO vo = StudyTaskVO.fromEntity(t);
                    if (activePlan != null && activePlan.getId().equals(t.getPlanId())) {
                        vo.setPlanTitle(activePlan.getTitle());
                    }
                    return vo;
                })
                .toList();

        int completed = (int) todayTasks.stream().filter(t -> t.getIsCompleted() != null && t.getIsCompleted() == 1).count();
        int total = todayTasks.size();
        int percent = total > 0 ? (completed * 100 / total) : 0;
        int earnedCoins = todayTasks.stream()
                .filter(t -> t.getIsCompleted() != null && t.getIsCompleted() == 1)
                .mapToInt(t -> t.getRewardCoins() != null ? t.getRewardCoins() : 5)
                .sum();

        return TodayTasksSummaryVO.builder()
                .activePlanTitle(activePlan != null ? activePlan.getTitle() : "我的学业自律清单")
                .daysRemaining(activePlan != null ? activePlan.getDaysRemaining() : 30)
                .progressPercent(percent)
                .completedCount(completed)
                .totalCount(total)
                .earnedCoinsToday(earnedCoins)
                .tasks(taskVOs)
                .build();
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public StudyPlanVO createPlan(Long userId, StudyPlanRequest request) {
        int totalDays = request.getTotalDays() != null && request.getTotalDays() > 0 ? request.getTotalDays() : 30;
        LocalDate targetDate = request.getTargetDate() != null
                ? request.getTargetDate()
                : LocalDate.now().plusDays(totalDays);

        StudyPlan plan = StudyPlan.builder()
                .userId(userId)
                .title(request.getTitle().trim())
                .category(StringUtils.hasText(request.getCategory()) ? request.getCategory().trim() : "四六级")
                .targetDate(targetDate)
                .totalDays(totalDays)
                .status(0)
                .createdAt(LocalDateTime.now())
                .updatedAt(LocalDateTime.now())
                .build();
        studyPlanMapper.insert(plan);

        List<StudyTask> createdTasks = new ArrayList<>();
        if (request.getTaskTitles() != null && !request.getTaskTitles().isEmpty()) {
            for (String title : request.getTaskTitles()) {
                if (StringUtils.hasText(title)) {
                    StudyTask task = StudyTask.builder()
                            .planId(plan.getId())
                            .userId(userId)
                            .title(title.trim())
                            .rewardCoins(5)
                            .isCompleted(0)
                            .continuousDays(0)
                            .createdAt(LocalDateTime.now())
                            .build();
                    studyTaskMapper.insert(task);
                    createdTasks.add(task);
                }
            }
        }
        log.info("创建学习计划成功: id={}, userId={}, title={}, taskCount={}", plan.getId(), userId, plan.getTitle(), createdTasks.size());
        return buildPlanVO(plan, createdTasks);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public StudyTaskVO createTask(Long userId, StudyTaskRequest request) {
        StudyTask task = StudyTask.builder()
                .planId(request.getPlanId())
                .userId(userId)
                .title(request.getTitle().trim())
                .rewardCoins(request.getRewardCoins() != null && request.getRewardCoins() > 0 ? request.getRewardCoins() : 5)
                .isCompleted(0)
                .continuousDays(0)
                .createdAt(LocalDateTime.now())
                .build();
        studyTaskMapper.insert(task);
        log.info("新增任务项成功: id={}, planId={}, userId={}, title={}", task.getId(), task.getPlanId(), userId, task.getTitle());
        return StudyTaskVO.fromEntity(task);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public StudyTaskVO toggleTask(Long userId, Long taskId) {
        StudyTask task = studyTaskMapper.selectById(taskId);
        if (task == null || !task.getUserId().equals(userId)) {
            throw new BusinessException(ErrorCode.PARAM_ERROR, "任务项不存在或无权操作");
        }

        User user = userMapper.selectById(userId);
        int rewardCoins = task.getRewardCoins() != null ? task.getRewardCoins() : 5;

        if (task.getIsCompleted() == null || task.getIsCompleted() == 0) {
            // 标记已完成：连续天数+1，发放自律金币
            task.setIsCompleted(1);
            task.setCompletedAt(LocalDateTime.now());
            task.setContinuousDays((task.getContinuousDays() != null ? task.getContinuousDays() : 0) + 1);
            if (user != null) {
                user.setCoins((user.getCoins() != null ? user.getCoins() : 0) + rewardCoins);
                userMapper.updateById(user);
            }
            log.info("任务打勾完成，奖励积分: userId={}, taskId={}, earnedCoins={}", userId, taskId, rewardCoins);
        } else {
            // 取消完成状态：回退金币
            task.setIsCompleted(0);
            task.setContinuousDays(Math.max(0, (task.getContinuousDays() != null ? task.getContinuousDays() : 1) - 1));
            if (user != null) {
                user.setCoins(Math.max(0, (user.getCoins() != null ? user.getCoins() : 0) - rewardCoins));
                userMapper.updateById(user);
            }
            log.info("任务取消勾选，扣回积分: userId={}, taskId={}", userId, taskId);
        }

        studyTaskMapper.updateById(task);
        return StudyTaskVO.fromEntity(task);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deletePlan(Long userId, Long planId) {
        StudyPlan plan = studyPlanMapper.selectById(planId);
        if (plan != null && plan.getUserId().equals(userId)) {
            studyTaskMapper.delete(new LambdaQueryWrapper<StudyTask>().eq(StudyTask::getPlanId, planId));
            studyPlanMapper.deleteById(planId);
            log.info("删除学习计划及子任务成功: planId={}, userId={}", planId, userId);
        }
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteTask(Long userId, Long taskId) {
        StudyTask task = studyTaskMapper.selectById(taskId);
        if (task != null && task.getUserId().equals(userId)) {
            studyTaskMapper.deleteById(taskId);
            log.info("删除单项任务成功: taskId={}, userId={}", taskId, userId);
        }
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public StudyPlanVO applyTemplate(Long userId, String templateType) {
        StudyPlanRequest req;
        if ("kaoyan".equalsIgnoreCase(templateType)) {
            req = StudyPlanRequest.builder()
                    .title("2027 考研高数与专业课自律筑基计划")
                    .category("考研")
                    .totalDays(60)
                    .taskTitles(List.of(
                            "📐 高等数学强化题型演练 2 小时",
                            "📚 专业课核心教材精读 20 页并整理框架导图",
                            "⏱️ 番茄钟沉浸专注完成 2 轮（共 90 分钟）",
                            "💡 撰写今日高数错题心得并在平台打卡复盘"
                    ))
                    .build();
        } else if ("final_exam".equalsIgnoreCase(templateType)) {
            req = StudyPlanRequest.builder()
                    .title("大学期末考试通关不挂科冲刺计划")
                    .category("期末")
                    .totalDays(21)
                    .taskTitles(List.of(
                            "📑 梳理重点课程考试大纲与核心考点思维导图",
                            "✍️ 独立完成近 3 年期末真题卷 1 套",
                            "⏱️ 番茄钟专注沉浸学习 60 分钟",
                            "🤝 在社区互助广场交流讨论疑难考点"
                    ))
                    .build();
        } else if ("self_discipline".equalsIgnoreCase(templateType)) {
            req = StudyPlanRequest.builder()
                    .title("大学自律微习惯 30 天养成计划")
                    .category("自律")
                    .totalDays(30)
                    .taskTitles(List.of(
                            "🌅 早起 7:30 前完成洗漱并晨读英语 20 分钟",
                            "⏱️ 完成至少 1 轮番茄钟沉浸式专注",
                            "🏃 操场或健身房有氧运动打卡 30 分钟",
                            "✨ 睡前远离手机，整理书桌与明日计划"
                    ))
                    .build();
        } else {
            // 默认四级备考冲刺
            req = StudyPlanRequest.builder()
                    .title("大学英语四级(CET-4) 40天高分通关计划")
                    .category("四六级")
                    .totalDays(40)
                    .taskTitles(List.of(
                            "📖 在扇贝/百词斩背诵 50 个四级核心词汇",
                            "🎧 完成 1 篇历年四级听力真题精听",
                            "⏱️ 番茄钟沉浸专注阅读与真题训练 45 分钟",
                            "📝 睡前整理今日错题并在智学伴打卡复盘"
                    ))
                    .build();
        }
        return createPlan(userId, req);
    }

    private StudyPlanVO buildPlanVO(StudyPlan plan, List<StudyTask> tasks) {
        long daysRemaining = 0;
        if (plan.getTargetDate() != null) {
            daysRemaining = ChronoUnit.DAYS.between(LocalDate.now(), plan.getTargetDate());
            if (daysRemaining < 0) {
                daysRemaining = 0;
            }
        }

        int totalTasks = tasks.size();
        int completedTasks = (int) tasks.stream().filter(t -> t.getIsCompleted() != null && t.getIsCompleted() == 1).count();
        int progress = totalTasks > 0 ? (completedTasks * 100 / totalTasks) : 0;

        List<StudyTaskVO> taskVOs = tasks.stream()
                .map(t -> {
                    StudyTaskVO vo = StudyTaskVO.fromEntity(t);
                    vo.setPlanTitle(plan.getTitle());
                    return vo;
                })
                .toList();

        return StudyPlanVO.builder()
                .id(plan.getId())
                .userId(plan.getUserId())
                .title(plan.getTitle())
                .category(plan.getCategory())
                .targetDate(plan.getTargetDate())
                .totalDays(plan.getTotalDays())
                .daysRemaining((int) daysRemaining)
                .status(plan.getStatus())
                .progressPercent(progress)
                .completedTaskCount(completedTasks)
                .totalTaskCount(totalTasks)
                .createdAt(plan.getCreatedAt())
                .tasks(taskVOs)
                .build();
    }
}
