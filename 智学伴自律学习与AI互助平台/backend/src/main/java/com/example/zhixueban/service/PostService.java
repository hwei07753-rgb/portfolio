package com.example.zhixueban.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.example.zhixueban.entity.dto.PostDetailVO;
import com.example.zhixueban.entity.dto.PostRequest;
import com.example.zhixueban.entity.dto.PostVO;
import com.example.zhixueban.entity.dto.ReplyRequest;
import com.example.zhixueban.entity.dto.ReplyVO;

/**
 * 社区互助服务（帖子 + 回复）
 */
public interface PostService {

    /** 分页获取广场帖子列表（未删除，支持分类过滤；未登录可浏览） */
    Page<PostVO> page(long page, long size, String category);

    /** 发布帖子（落库待审核状态） */
    PostVO create(Long userId, PostRequest request);

    /** 帖子详情 + 回复列表 */
    PostDetailVO detail(Long postId);

    /** 发表回复 */
    ReplyVO reply(Long userId, ReplyRequest request);

    /** 召唤 AI 助教为帖子生成答疑回复 */
    ReplyVO aiReply(Long userId, Long postId);
}
