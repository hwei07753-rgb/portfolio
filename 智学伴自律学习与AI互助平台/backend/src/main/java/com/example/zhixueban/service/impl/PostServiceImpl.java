package com.example.zhixueban.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.example.zhixueban.common.BusinessException;
import com.example.zhixueban.common.ErrorCode;
import com.example.zhixueban.entity.Post;
import com.example.zhixueban.entity.Reply;
import com.example.zhixueban.entity.User;
import com.example.zhixueban.entity.dto.PostDetailVO;
import com.example.zhixueban.entity.dto.PostRequest;
import com.example.zhixueban.entity.dto.PostVO;
import com.example.zhixueban.entity.dto.ReplyRequest;
import com.example.zhixueban.entity.dto.ReplyVO;
import com.example.zhixueban.mapper.PostMapper;
import com.example.zhixueban.mapper.ReplyMapper;
import com.example.zhixueban.mapper.UserMapper;
import com.example.zhixueban.service.PostService;
import com.example.zhixueban.service.SensitiveWordService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * 社区互助服务实现
 */
@Service
public class PostServiceImpl implements PostService {

    private static final Logger log = LoggerFactory.getLogger(PostServiceImpl.class);

    private final PostMapper postMapper;
    private final ReplyMapper replyMapper;
    private final UserMapper userMapper;
    private final SensitiveWordService sensitiveWordService;
    private final com.example.zhixueban.service.AiService aiService;

    public PostServiceImpl(PostMapper postMapper,
                           ReplyMapper replyMapper,
                           UserMapper userMapper,
                           SensitiveWordService sensitiveWordService,
                           com.example.zhixueban.service.AiService aiService) {
        this.postMapper = postMapper;
        this.replyMapper = replyMapper;
        this.userMapper = userMapper;
        this.sensitiveWordService = sensitiveWordService;
        this.aiService = aiService;
    }

    @Override
    public Page<PostVO> page(long page, long size, String category) {
        LambdaQueryWrapper<Post> wrapper = new LambdaQueryWrapper<Post>()
                .ne(Post::getStatus, 2) // 排除已删除
                .orderByDesc(Post::getCreatedAt);
        if (StringUtils.hasText(category)) {
            wrapper.eq(Post::getCategory, category.trim());
        }

        Page<Post> postPage = postMapper.selectPage(new Page<>(page, size), wrapper);
        Page<PostVO> voPage = new Page<>(postPage.getCurrent(), postPage.getSize(), postPage.getTotal());
        voPage.setRecords(buildPostVOs(postPage.getRecords()));
        return voPage;
    }

    @Override
    @org.springframework.transaction.annotation.Transactional(rollbackFor = Exception.class)
    public PostVO create(Long userId, PostRequest request) {
        // 敏感词过滤（SRS §6.2.2）：标题+内容任一命中即拒绝
        String hit = sensitiveWordService.matchSensitive(
                request.getTitle() + " " + request.getContent());
        if (hit != null) {
            throw new BusinessException(ErrorCode.CONTENT_SENSITIVE);
        }

        int bounty = request.getBountyCoins() != null ? Math.max(0, request.getBountyCoins()) : 0;
        if (bounty > 0) {
            User user = userMapper.selectById(userId);
            if (user == null || user.getCoins() == null || user.getCoins() < bounty) {
                throw new BusinessException(ErrorCode.INSUFFICIENT_COINS);
            }
            user.setCoins(user.getCoins() - bounty);
            userMapper.updateById(user);
        }

        Post post = Post.builder()
                .userId(userId)
                .category(request.getCategory().trim())
                .title(request.getTitle().trim())
                .content(request.getContent().trim())
                .bountyCoins(bounty)
                .isSolved(0)
                .status(0) // 待审核
                .createdAt(LocalDateTime.now())
                .build();
        postMapper.insert(post);
        log.info("发帖成功: id={}, userId={}, category={}, bounty={}", post.getId(), userId, post.getCategory(), bounty);
        return PostVO.fromEntity(post);
    }

    @Override
    @org.springframework.transaction.annotation.Transactional(rollbackFor = Exception.class)
    public PostDetailVO adoptReply(Long userId, Long postId, Long replyId) {
        Post post = postMapper.selectById(postId);
        if (post == null || post.getStatus() == 2) {
            throw new BusinessException(ErrorCode.POST_NOT_FOUND);
        }
        if (!post.getUserId().equals(userId)) {
            throw new BusinessException(ErrorCode.FORBIDDEN, "仅楼主本人有权采纳最佳答案");
        }
        if (post.getIsSolved() != null && post.getIsSolved() == 1) {
            throw new BusinessException(ErrorCode.POST_ALREADY_SOLVED);
        }

        Reply reply = replyMapper.selectById(replyId);
        if (reply == null || !reply.getPostId().equals(postId)) {
            throw new BusinessException(ErrorCode.REPLY_NOT_FOUND);
        }
        if (reply.getUserId().equals(userId)) {
            throw new BusinessException(ErrorCode.CANNOT_ADOPT_OWN_REPLY);
        }

        // 1. 标记帖子已解决，并绑定被采纳的回复
        post.setIsSolved(1);
        post.setAcceptedReplyId(replyId);
        postMapper.updateById(post);

        // 2. 标记回复被采纳
        reply.setIsAccepted(1);
        replyMapper.updateById(reply);

        // 3. 转账悬赏积分给回复者
        int bounty = post.getBountyCoins() != null ? post.getBountyCoins() : 0;
        if (bounty > 0) {
            User replier = userMapper.selectById(reply.getUserId());
            if (replier != null) {
                replier.setCoins((replier.getCoins() != null ? replier.getCoins() : 0) + bounty);
                userMapper.updateById(replier);
            }
        }
        log.info("采纳最佳答案成功: postId={}, replyId={}, replierId={}, bounty={}", postId, replyId, reply.getUserId(), bounty);

        return detail(postId);
    }

    @Override
    public PostDetailVO detail(Long postId) {
        Post post = postMapper.selectById(postId);
        if (post == null || post.getStatus() == 2) {
            throw new BusinessException(ErrorCode.POST_NOT_FOUND);
        }

        PostVO postVO = PostVO.fromEntity(post);
        fillAuthorAndReplyCount(List.of(postVO));

        List<Reply> replies = replyMapper.selectList(
                new LambdaQueryWrapper<Reply>()
                        .eq(Reply::getPostId, postId)
                        .orderByAsc(Reply::getCreatedAt)
        );
        List<ReplyVO> replyVOs = replies.stream().map(ReplyVO::fromEntity).toList();
        fillReplyAuthors(replyVOs);

        return PostDetailVO.builder().post(postVO).replies(replyVOs).build();
    }

    @Override
    public ReplyVO reply(Long userId, ReplyRequest request) {
        Post post = postMapper.selectById(request.getPostId());
        if (post == null || post.getStatus() == 2) {
            throw new BusinessException(ErrorCode.POST_NOT_FOUND);
        }

        Reply reply = Reply.builder()
                .postId(request.getPostId())
                .userId(userId)
                .content(request.getContent().trim())
                .createdAt(LocalDateTime.now())
                .build();
        replyMapper.insert(reply);
        log.info("回复成功: id={}, postId={}, userId={}", reply.getId(), post.getId(), userId);

        ReplyVO vo = ReplyVO.fromEntity(reply);
        User user = userMapper.selectById(userId);
        vo.setAuthorNickname(user != null && user.getNickname() != null ? user.getNickname() : "学伴");
        return vo;
    }

    @Override
    @org.springframework.transaction.annotation.Transactional(rollbackFor = Exception.class)
    public ReplyVO aiReply(Long userId, Long postId) {
        Post post = postMapper.selectById(postId);
        if (post == null || post.getStatus() == 2) {
            throw new BusinessException(ErrorCode.POST_NOT_FOUND);
        }

        // 1. 获取或创建 AI 助教官方虚拟用户
        User aiBot = userMapper.selectOne(
                new LambdaQueryWrapper<User>().eq(User::getOpenid, "ai_assistant_bot")
        );
        Long aiUserId;
        if (aiBot != null) {
            aiUserId = aiBot.getId();
        } else {
            User newBot = User.builder()
                    .openid("ai_assistant_bot")
                    .nickname("智学伴 AI 助教")
                    .avatarUrl("/images/tabbar/ai-avatar.png")
                    .studyGoal("随时为同学们解答学业疑惑与考研难点")
                    .role(0)
                    .status(0)
                    .createdAt(LocalDateTime.now())
                    .build();
            userMapper.insert(newBot);
            aiUserId = newBot.getId();
        }

        // 2. 调用 AI 服务生成启发式解答
        String answer = aiService.answerPost(post.getTitle(), post.getContent(), post.getCategory());
        if (answer != null && answer.length() > 490) {
            answer = answer.substring(0, 487) + "...";
        }

        // 3. 落库 reply 表（受外键约束约束，aiUserId 必须存在于 user 表）
        Reply reply = Reply.builder()
                .postId(postId)
                .userId(aiUserId)
                .content(answer)
                .createdAt(LocalDateTime.now())
                .build();
        replyMapper.insert(reply);
        log.info("AI 助教为帖子生成回复成功: replyId={}, postId={}, userId={}", reply.getId(), postId, userId);

        ReplyVO vo = ReplyVO.fromEntity(reply);
        vo.setAuthorNickname("智学伴 AI 助教");
        vo.setIsAi(true);
        return vo;
    }

    /**
     * 帖子列表 → 批量填充作者昵称 + 回复数
     */
    private List<PostVO> buildPostVOs(List<Post> posts) {
        List<PostVO> vos = posts.stream().map(PostVO::fromEntity).toList();
        fillAuthorAndReplyCount(vos);
        return vos;
    }

    private void fillAuthorAndReplyCount(List<PostVO> vos) {
        if (vos.isEmpty()) {
            return;
        }
        // 1. 作者昵称（批量查询 user 表）
        List<Long> userIds = vos.stream().map(PostVO::getUserId).distinct().toList();
        Map<Long, String> nicknameMap = userMapper.selectBatchIds(userIds).stream()
                .collect(Collectors.toMap(User::getId,
                        u -> u.getNickname() != null ? u.getNickname() : "学伴"));

        // 2. 回复数（一次 group by 统计）
        List<Long> postIds = vos.stream().map(PostVO::getId).toList();
        Map<Long, Integer> replyCountMap = replyMapper.selectMaps(
                        new QueryWrapper<Reply>()
                                .select("post_id", "COUNT(*) AS cnt")
                                .in("post_id", postIds)
                                .groupBy("post_id"))
                .stream()
                .collect(Collectors.toMap(
                        row -> ((Number) row.get("post_id")).longValue(),
                        row -> ((Number) row.get("cnt")).intValue()));

        for (PostVO vo : vos) {
            vo.setAuthorNickname(nicknameMap.getOrDefault(vo.getUserId(), "学伴"));
            vo.setReplyCount(replyCountMap.getOrDefault(vo.getId(), 0));
        }
    }

    private void fillReplyAuthors(List<ReplyVO> replyVOs) {
        if (replyVOs.isEmpty()) {
            return;
        }
        List<Long> userIds = replyVOs.stream().map(ReplyVO::getUserId).distinct().toList();
        Map<Long, String> nicknameMap = userMapper.selectBatchIds(userIds).stream()
                .collect(Collectors.toMap(User::getId,
                        u -> u.getNickname() != null ? u.getNickname() : "学伴"));
        for (ReplyVO vo : replyVOs) {
            String nick = nicknameMap.getOrDefault(vo.getUserId(), "学伴");
            vo.setAuthorNickname(nick);
            vo.setIsAi("智学伴 AI 助教".equals(nick) || nick.contains("AI"));
        }
    }
}
