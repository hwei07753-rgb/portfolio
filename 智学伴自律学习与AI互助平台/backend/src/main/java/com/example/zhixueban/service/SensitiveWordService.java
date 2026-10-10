package com.example.zhixueban.service;

import com.example.zhixueban.entity.SensitiveWord;

import java.util.List;

/**
 * 敏感词服务（SRS §6.2.2 简单敏感词过滤）
 */
public interface SensitiveWordService {

    /**
     * 校验文本是否命中启用中的敏感词
     *
     * @param content 待校验文本
     * @return 命中的敏感词，未命中返回 null
     */
    String matchSensitive(String content);

    /**
     * 获取全部启用中的敏感词（后台管理/校验复用）
     */
    List<String> listEnabledWords();
}
