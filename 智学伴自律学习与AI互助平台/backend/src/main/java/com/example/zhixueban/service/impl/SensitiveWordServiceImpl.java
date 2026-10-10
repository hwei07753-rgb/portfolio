package com.example.zhixueban.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.example.zhixueban.entity.SensitiveWord;
import com.example.zhixueban.mapper.SensitiveWordMapper;
import com.example.zhixueban.service.SensitiveWordService;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.util.List;

/**
 * 敏感词服务实现：发帖/打卡前校验内容（SRS §6.2.2）
 * 从简实现：每次校验实时查库（课设演示数据量小，无需缓存）
 */
@Service
public class SensitiveWordServiceImpl implements SensitiveWordService {

    private final SensitiveWordMapper sensitiveWordMapper;

    public SensitiveWordServiceImpl(SensitiveWordMapper sensitiveWordMapper) {
        this.sensitiveWordMapper = sensitiveWordMapper;
    }

    @Override
    public String matchSensitive(String content) {
        if (!StringUtils.hasText(content)) {
            return null;
        }
        List<String> words = listEnabledWords();
        for (String word : words) {
            if (content.contains(word)) {
                return word;
            }
        }
        return null;
    }

    @Override
    public List<String> listEnabledWords() {
        return sensitiveWordMapper.selectList(
                        new LambdaQueryWrapper<SensitiveWord>()
                                .eq(SensitiveWord::getStatus, 1)
                                .orderByDesc(SensitiveWord::getId))
                .stream()
                .map(SensitiveWord::getWord)
                .toList();
    }
}
