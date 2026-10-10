package com.example.zhixueban.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.example.zhixueban.common.Result;
import com.example.zhixueban.entity.dto.PostDetailVO;
import com.example.zhixueban.entity.dto.PostRequest;
import com.example.zhixueban.entity.dto.PostVO;
import com.example.zhixueban.entity.dto.ReplyRequest;
import com.example.zhixueban.entity.dto.ReplyVO;
import com.example.zhixueban.service.PostService;
import com.example.zhixueban.util.UserContext;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 社区互助模块（对齐 API_DESIGN.md S4 规划）
 */
@RestController
@RequestMapping("/api")
public class PostController {

    private final PostService postService;

    public PostController(PostService postService) {
        this.postService = postService;
    }

    /** 分页获取广场帖子列表（未登录可浏览） */
    @GetMapping("/post/page")
    public Result<Page<PostVO>> page(@RequestParam(defaultValue = "1") long page,
                                     @RequestParam(defaultValue = "10") long size,
                                     @RequestParam(required = false) String category) {
        if (size > 50) {
            size = 50;
        }
        return Result.success(postService.page(page, size, category));
    }

    /** 发布帖子（需登录，落库待审核） */
    @PostMapping("/post")
    public Result<PostVO> create(@Valid @RequestBody PostRequest request) {
        PostVO vo = postService.create(UserContext.getUserId(), request);
        return Result.success(vo, "发帖成功，等待审核");
    }

    /** 帖子详情 + 回复列表（未登录可浏览） */
    @GetMapping("/post/{id}")
    public Result<PostDetailVO> detail(@PathVariable Long id) {
        return Result.success(postService.detail(id));
    }

    /** 发表回复（需登录） */
    @PostMapping("/reply")
    public Result<ReplyVO> reply(@Valid @RequestBody ReplyRequest request) {
        ReplyVO vo = postService.reply(UserContext.getUserId(), request);
        return Result.success(vo, "回复成功");
    }

    /** 召唤 AI 助教为帖子生成答疑回复（需登录） */
    @PostMapping("/post/{id}/ai-reply")
    public Result<ReplyVO> aiReply(@PathVariable Long id) {
        ReplyVO vo = postService.aiReply(UserContext.getUserId(), id);
        return Result.success(vo, "AI 助教已解答");
    }

    /** 采纳最佳答案（仅楼主可操作，需登录） */
    @PostMapping("/post/{id}/adopt/{replyId}")
    public Result<PostDetailVO> adopt(@PathVariable Long id, @PathVariable Long replyId) {
        PostDetailVO vo = postService.adoptReply(UserContext.getUserId(), id, replyId);
        return Result.success(vo, "采纳成功，悬赏积分已转账给答疑学伴！");
    }
}
