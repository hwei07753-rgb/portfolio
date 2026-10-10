package com.example.zhixueban.service;

/**
 * AI 智能服务接口（打卡复盘 + 社区学业助教答疑）
 */
public interface AiService {

    /**
     * 生成每日打卡 AI 复盘点评
     */
    String generateReview(String checkinContent);

    /**
     * 为社区帖子生成 AI 助教解答
     */
    String answerPost(String title, String content, String category);
}
