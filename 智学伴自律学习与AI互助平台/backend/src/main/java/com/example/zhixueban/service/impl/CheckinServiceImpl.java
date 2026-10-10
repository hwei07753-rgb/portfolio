package com.example.zhixueban.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.example.zhixueban.common.BusinessException;
import com.example.zhixueban.common.ErrorCode;
import com.example.zhixueban.entity.AiReview;
import com.example.zhixueban.entity.Checkin;
import com.example.zhixueban.entity.dto.CheckinRequest;
import com.example.zhixueban.entity.dto.CheckinVO;
import com.example.zhixueban.mapper.AiReviewMapper;
import com.example.zhixueban.mapper.CheckinMapper;
import com.example.zhixueban.service.CheckinService;
import com.example.zhixueban.service.SensitiveWordService;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * 每日打卡服务实现（提交打卡 + 同步 AI 复盘）
 * <p>
 * AI 复盘策略（从简、可演示）：
 * 1. 配置了 {@code llm.api-key} 时，调用 OpenAI 兼容的 Chat Completions 接口（DeepSeek/通义等）；
 * 2. 未配置或调用失败时，自动降级为本地模板点评，保证接口始终可用（课设演示不依赖外部额度）。
 */
@Service
public class CheckinServiceImpl implements CheckinService {

    private static final Logger log = LoggerFactory.getLogger(CheckinServiceImpl.class);

    private static final String SYSTEM_PROMPT =
            "你是“智学伴”自律学习平台的 AI 学习教练。用户每天提交学习打卡心得，"
                    + "请用 2~3 句话给出温暖的肯定和 1 条可执行的学习建议。语气亲切、口语化，不要超过 120 字。";

    private final CheckinMapper checkinMapper;
    private final AiReviewMapper aiReviewMapper;
    private final SensitiveWordService sensitiveWordService;
    private final com.example.zhixueban.mapper.UserMapper userMapper;
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Value("${llm.base-url:}")
    private String llmBaseUrl;

    @Value("${llm.api-key:}")
    private String llmApiKey;

    @Value("${llm.model:deepseek-chat}")
    private String llmModel;

    public CheckinServiceImpl(CheckinMapper checkinMapper,
                              AiReviewMapper aiReviewMapper,
                              SensitiveWordService sensitiveWordService,
                              com.example.zhixueban.mapper.UserMapper userMapper) {
        this.checkinMapper = checkinMapper;
        this.aiReviewMapper = aiReviewMapper;
        this.sensitiveWordService = sensitiveWordService;
        this.userMapper = userMapper;
    }

    @Override
    public com.example.zhixueban.entity.dto.CheckinVO submit(Long userId, CheckinRequest request) {
        // 0. 敏感词过滤（SRS §6.2.2）：命中启用中的敏感词直接拒绝
        String hit = sensitiveWordService.matchSensitive(request.getContent());
        if (hit != null) {
            throw new BusinessException(ErrorCode.CONTENT_SENSITIVE);
        }

        // 1. 幂等校验：同一天只能打卡一次
        LocalDateTime dayStart = LocalDateTime.of(LocalDate.now(), LocalTime.MIN);
        LocalDateTime dayEnd = dayStart.plusDays(1);
        Long todayCount = checkinMapper.selectCount(
                new LambdaQueryWrapper<Checkin>()
                        .eq(Checkin::getUserId, userId)
                        .ge(Checkin::getCreatedAt, dayStart)
                        .lt(Checkin::getCreatedAt, dayEnd)
        );
        if (todayCount != null && todayCount > 0) {
            throw new BusinessException(ErrorCode.CHECKIN_ALREADY_DONE);
        }

        // 2. 落库（初始待审核，AI 复盘同步生成后置为通过）
        Checkin checkin = Checkin.builder()
                .userId(userId)
                .content(request.getContent().trim())
                .imageUrl(request.getImageUrl())
                .status(0)
                .createdAt(LocalDateTime.now())
                .build();
        checkinMapper.insert(checkin);

        // 3. 同步生成 AI 复盘建议 → 独立写入 ai_review 表（S1b 拆表，1:1）
        String aiReview = generateAiReview(checkin.getContent());
        AiReview review = AiReview.builder()
                .checkinId(checkin.getId())
                .userId(userId)
                .content(aiReview)
                .model(StringUtils.hasText(llmApiKey) ? llmModel : "local-template")
                .createdAt(LocalDateTime.now())
                .build();
        aiReviewMapper.insert(review);

        // 4. 置为已通过
        checkin.setStatus(1);
        checkinMapper.updateById(checkin);

        // 5. 奖励每日打卡自律积分（+10 币）
        com.example.zhixueban.entity.User user = userMapper.selectById(userId);
        if (user != null) {
            user.setCoins((user.getCoins() != null ? user.getCoins() : 0) + 10);
            userMapper.updateById(user);
        }

        log.info("打卡提交成功: id={}, userId={}, coinsAwarded=10, aiReview={}", checkin.getId(), userId,
                StringUtils.hasText(aiReview) ? "AI生成" : "模板生成");

        CheckinVO vo = CheckinVO.fromEntity(checkin);
        vo.setAiReview(aiReview);
        return vo;
    }

    @Override
    public List<CheckinVO> myHistory(Long userId) {
        List<Checkin> list = checkinMapper.selectList(
                new LambdaQueryWrapper<Checkin>()
                        .eq(Checkin::getUserId, userId)
                        .ne(Checkin::getStatus, 2) // 排除已删除
                        .orderByDesc(Checkin::getCreatedAt)
        );
        List<CheckinVO> vos = list.stream().map(CheckinVO::fromEntity).toList();
        fillAiReview(vos);
        return vos;
    }

    /**
     * 批量回填 AI 复盘建议（一次查询 ai_review 表，避免 N+1）
     */
    private void fillAiReview(List<CheckinVO> vos) {
        if (vos.isEmpty()) {
            return;
        }
        List<Long> checkinIds = vos.stream().map(CheckinVO::getId).toList();
        Map<Long, String> reviewMap = aiReviewMapper.selectList(
                        new LambdaQueryWrapper<AiReview>()
                                .in(AiReview::getCheckinId, checkinIds))
                .stream()
                .collect(Collectors.toMap(AiReview::getCheckinId, AiReview::getContent, (a, b) -> a));
        for (CheckinVO vo : vos) {
            vo.setAiReview(reviewMap.get(vo.getId()));
        }
    }

    /**
     * 生成 AI 复盘建议：优先调用 LLM，失败/未配置则模板降级
     */
    private String generateAiReview(String content) {
        if (StringUtils.hasText(llmApiKey) && StringUtils.hasText(llmBaseUrl)) {
            try {
                return callLlm(content);
            } catch (Exception e) {
                log.warn("调用 LLM 复盘失败，降级为模板点评: {}", e.getMessage());
            }
        }
        return templateReview(content);
    }

    /**
     * 调用 OpenAI 兼容 Chat Completions 接口
     */
    private String callLlm(String content) throws Exception {
        String payload = objectMapper.writeValueAsString(
                java.util.Map.of(
                        "model", llmModel,
                        "messages", List.of(
                                java.util.Map.of("role", "system", "content", SYSTEM_PROMPT),
                                java.util.Map.of("role", "user", "content", "今天我的学习心得：" + content)
                        ),
                        "max_tokens", 300,
                        "temperature", 0.7
                )
        );

        String url = llmBaseUrl.endsWith("/") ? llmBaseUrl + "chat/completions" : llmBaseUrl + "/chat/completions";
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .header("Content-Type", "application/json")
                .header("Authorization", "Bearer " + llmApiKey)
                .POST(HttpRequest.BodyPublishers.ofString(payload))
                .timeout(Duration.ofSeconds(15))
                .build();

        HttpResponse<String> response = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(5))
                .build()
                .send(request, HttpResponse.BodyHandlers.ofString());

        if (response.statusCode() == 200) {
            JsonNode node = objectMapper.readTree(response.body());
            String text = node.path("choices").path(0).path("message").path("content").asText("").trim();
            if (StringUtils.hasText(text)) {
                return text;
            }
        }
        log.warn("LLM 返回异常状态码: {}", response.statusCode());
        throw new IllegalStateException("LLM 调用未返回有效内容");
    }

    /**
     * 本地模板点评（无 LLM 额度时的兜底，保证演示可用）
     */
    private String templateReview(String content) {
        String head = content.length() >= 30
                ? "今天记录得很充实，看得出你在踏踏实实坚持。"
                : "能坚持打卡本身就是很棒的一步，为你点赞！";
        String tail = content.contains("英语") || content.contains("单词") || content.contains("四六级")
                ? "明天可以固定一个 25 分钟背单词时段，坚持一周后你会看到明显变化。"
                : content.contains("考研") || content.contains("数学")
                ? "建议明早先做一套限时练习，再针对错题整理笔记，效率会更高。"
                : "明天试着给学习任务定一个小目标，完成后奖励自己休息 10 分钟。";
        return head + tail;
    }
}
