package com.example.zhixueban.service.impl;

import com.example.zhixueban.service.AiService;
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
import java.util.List;
import java.util.Map;

/**
 * AI 智能服务实现类：
 * 1. 当配置了 llm.api-key 时，调用 OpenAI 兼容 Chat Completions 接口（DeepSeek / 通义千问等）；
 * 2. 未配置或外部调用失败时，自动平滑降级为本地规则模板，确保高可用不报错。
 */
@Service
public class AiServiceImpl implements AiService {

    private static final Logger log = LoggerFactory.getLogger(AiServiceImpl.class);

    private static final String REVIEW_SYSTEM_PROMPT =
            "你是“智学伴”自律学习平台的 AI 学习教练。用户每天提交学习打卡心得，"
                    + "请用 2~3 句话给出温暖的肯定和 1 条可执行的学习建议。语气亲切、口语化，不要超过 120 字。";

    private static final String POST_ASSISTANT_SYSTEM_PROMPT =
            "你是“智学伴”自律学习平台的 AI 学业助教（专业热心的学长学姐）。"
                    + "针对同学在社区发布的求助或讨论，请给出专业、条理清晰且富有启发性的解答与学习指导。"
                    + "回答分 2~3 点陈述，重点明确，亲切诚恳，字数严格控制在 150~280 字之间。";

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Value("${llm.base-url:}")
    private String llmBaseUrl;

    @Value("${llm.api-key:}")
    private String llmApiKey;

    @Value("${llm.model:deepseek-chat}")
    private String llmModel;

    @Override
    public String generateReview(String checkinContent) {
        if (StringUtils.hasText(llmApiKey) && StringUtils.hasText(llmBaseUrl)) {
            try {
                return callLlm(REVIEW_SYSTEM_PROMPT, "今天我的学习心得：" + checkinContent, 300);
            } catch (Exception e) {
                log.warn("调用 LLM 复盘失败，降级为模板点评: {}", e.getMessage());
            }
        }
        return templateReview(checkinContent);
    }

    @Override
    public String answerPost(String title, String content, String category) {
        if (StringUtils.hasText(llmApiKey) && StringUtils.hasText(llmBaseUrl)) {
            try {
                String userPrompt = String.format("【分类】：%s\n【求助标题】：%s\n【详细说明】：%s\n请给出有针对性的解答与参考建议：",
                        category, title, content);
                return callLlm(POST_ASSISTANT_SYSTEM_PROMPT, userPrompt, 500);
            } catch (Exception e) {
                log.warn("调用 LLM 社区助教解答失败，降级为模板答疑: {}", e.getMessage());
            }
        }
        return templatePostAnswer(title, content, category);
    }

    private String callLlm(String systemPrompt, String userPrompt, int maxTokens) throws Exception {
        String payload = objectMapper.writeValueAsString(
                Map.of(
                        "model", llmModel,
                        "messages", List.of(
                                Map.of("role", "system", "content", systemPrompt),
                                Map.of("role", "user", "content", userPrompt)
                        ),
                        "max_tokens", maxTokens,
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

    private String templatePostAnswer(String title, String content, String category) {
        String query = (title + " " + content).toLowerCase();
        if ("求资料".equals(category) || query.contains("资料") || query.contains("真题") || query.contains("网盘") || query.contains("课件")) {
            return "【AI 助教指南】同学你好！对于该资料，建议优先检索学校数字图书馆资源（知网/超星/万方）。考研或期末真题建议重点吃透近 3 年核心大题，梳理高频考点。已为你置顶关注，也期待有网盘资料的同学跟帖共享！";
        } else if ("问问题".equals(category) || query.contains("错题") || query.contains("求助") || query.contains("怎么") || query.contains("难点")) {
            return "【AI 助教答疑思路】这是高频易错题！解题核心三步走：1. 回归课本基础定理，理清适用前提；2. 梳理题干已知约束，尝试画图或逆向代入验证；3. 将该题型归纳进错题本，举一反三。加油，持续思考必能突破！";
        } else {
            return "【AI 助教点赞与总结】非常赞同你的经验分享！自律学习最关键的是在实践中形成正向反馈闭环。建议结合番茄钟时间块与每日打卡复盘，把优秀的学习方法固化为肌肉记忆，期待在社区带领更多学友共同进步！";
        }
    }
}
