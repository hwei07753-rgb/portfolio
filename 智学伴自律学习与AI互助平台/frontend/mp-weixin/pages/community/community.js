// pages/community/community.js
const app = getApp();
const util = require('../../utils/util');
const request = require('../../utils/request');

Page({
  data: {
    categories: ['全部', '求资料', '问问题', '经验分享'],
    selectedCategory: '全部',
    postCategories: ['求资料', '问问题', '经验分享'],
    bountyOptions: [0, 10, 20, 50],
    userCoins: 0,
    currentUserId: null,
    posts: [],
    showCreateModal: false,
    newPost: {
      category: '求资料',
      title: '',
      content: '',
      bountyCoins: 0
    },
    replyingPostId: null,
    replyContent: ''
  },

  onShow() {
    this.initUserContext();
    this.fetchPosts();
  },

  initUserContext() {
    const userInfo = wx.getStorageSync('userInfo') || {};
    this.setData({ currentUserId: userInfo.id || null });
    // 获取用户最新积分余额
    request.get('/user/stats', null, { loading: false, silentAuth: true, silentError: true })
      .then(res => {
        if (res && res.coins != null) {
          this.setData({ userCoins: res.coins });
        }
      })
      .catch(() => {});
  },

  onPullDownRefresh() {
    this.initUserContext();
    this.fetchPosts();
    wx.stopPullDownRefresh();
  },

  onSelectCategory(e) {
    const cat = e.currentTarget.dataset.cat;
    this.setData({ selectedCategory: cat });
    this.fetchPosts();
  },

  fetchPosts() {
    const params = {};
    if (this.data.selectedCategory !== '全部') {
      params.category = this.data.selectedCategory;
    }

    request.get('/post/page', params, { loading: false })
      .then(res => {
        const records = (res && res.records) || (Array.isArray(res) ? res : []);
        const detailPromises = records.map(p => {
          const replies = (p.replies || []).map(r => ({
            ...r,
            userNickname: r.authorNickname || r.userNickname || '学友',
            isAi: r.isAi || ((r.authorNickname || r.userNickname || '').includes('AI'))
          }));
          const baseFormatted = {
            ...p,
            userNickname: p.authorNickname || p.userNickname || '热心学友',
            timeDesc: util.formatRelativeTime(p.createdAt),
            replies: replies
          };
          if (p.replyCount > 0 && (!p.replies || p.replies.length === 0)) {
            return request.get(`/post/${p.id}`, null, { loading: false, silentError: true })
              .then(detail => {
                if (detail && detail.replies) {
                  baseFormatted.replies = detail.replies.map(r => ({
                    ...r,
                    userNickname: r.authorNickname || '学友',
                    isAi: r.isAi || (r.authorNickname && r.authorNickname.includes('AI'))
                  }));
                }
                return baseFormatted;
              })
              .catch(() => baseFormatted);
          }
          return Promise.resolve(baseFormatted);
        });

        Promise.all(detailPromises).then(formatted => {
          this.setData({ posts: formatted });
        });
      })
      .catch(() => {
        // 后端离线时提供演示种子数据
        if (this.data.posts.length === 0) {
          this.setData({
            posts: [
              {
                id: 1,
                userNickname: '学霸小林',
                userAvatar: '/images/tabbar/mine.png',
                category: '经验分享',
                title: '大三备战四六级与考研数学时间管理心得',
                content: '坚持用番茄钟分段背单词，每天早起打卡复盘。推荐大家每完成一个阶段就让AI进行错因归类，效率提升很多！',
                timeDesc: '2小时前',
                replyCount: 1,
                replies: [
                  { id: 101, userNickname: '赵同舟', content: '很有帮助，今天也开始用番茄钟了！' }
                ]
              },
              {
                id: 2,
                userNickname: '代码小赵',
                userAvatar: '/images/tabbar/mine.png',
                category: '求资料',
                title: '求一份近几年的数据结构期末考试真题与解析',
                content: '二叉树和最短路径部分有点吃力，哪位大佬有整理好的思维导图或者真题借阅一下？必重谢！',
                timeDesc: '5小时前',
                replyCount: 0,
                replies: []
              }
            ]
          });
        }
      });
  },

  openCreateModal() {
    if (!app.checkLogin()) return;
    this.setData({
      showCreateModal: true,
      newPost: { category: '求资料', title: '', content: '', bountyCoins: 0 }
    });
  },

  closeCreateModal() {
    this.setData({ showCreateModal: false });
  },

  selectPostCategory(e) {
    const cat = e.currentTarget.dataset.cat;
    this.setData({ 'newPost.category': cat });
  },

  selectBountyCoins(e) {
    const coins = Number(e.currentTarget.dataset.coins) || 0;
    this.setData({ 'newPost.bountyCoins': coins });
  },

  onInputTitle(e) {
    this.setData({ 'newPost.title': e.detail.value });
  },

  onInputPostContent(e) {
    this.setData({ 'newPost.content': e.detail.value });
  },

  submitPost() {
    const { category, title, content, bountyCoins } = this.data.newPost;
    if (!title.trim()) {
      wx.showToast({ title: '请输入帖子标题', icon: 'none' });
      return;
    }
    if (!content.trim()) {
      wx.showToast({ title: '请输入帖子正文', icon: 'none' });
      return;
    }
    const bounty = Number(bountyCoins) || 0;
    if (bounty > 0 && bounty > (this.data.userCoins || 0)) {
      wx.showToast({ title: `自律积分不足(当前${this.data.userCoins || 0}币)，无法悬赏`, icon: 'none' });
      return;
    }

    request.post('/post', {
      category: category,
      title: title.trim(),
      content: content.trim(),
      bountyCoins: bounty
    }).then(() => {
      wx.showToast({ title: '发帖成功，待审核', icon: 'success' });
      this.closeCreateModal();
      this.initUserContext();
      this.fetchPosts();
    }).catch(err => {
      wx.showToast({ title: (err && err.message) || '发帖失败，请重试', icon: 'none' });
    });
  },

  /**
   * 楼主采纳最佳答案并转账悬赏金币
   */
  onAdoptReply(e) {
    if (!app.checkLogin()) return;
    const postId = e.currentTarget.dataset.postId;
    const replyId = e.currentTarget.dataset.replyId;
    if (!postId || !replyId) return;

    wx.showModal({
      title: '采纳最佳答案',
      content: '确认将该学友的回复采纳为最佳答案并分发悬赏金币吗？结案后不可更改。',
      confirmText: '确认采纳',
      confirmColor: '#276449',
      success: (res) => {
        if (res.confirm) {
          wx.showLoading({ title: '采纳结算中...' });
          request.post(`/post/${postId}/adopt/${replyId}`)
            .then(() => {
              wx.hideLoading();
              wx.showToast({ title: '已成功采纳最佳答案！', icon: 'success' });
              this.fetchPosts();
              this.initUserContext();
            })
            .catch(err => {
              wx.hideLoading();
              wx.showToast({ title: (err && err.message) || '采纳失败，请稍后重试', icon: 'none' });
            });
        }
      }
    });
  },

  openReplyInput(e) {
    if (!app.checkLogin()) return;
    const postId = e.currentTarget.dataset.postId;
    this.setData({
      replyingPostId: postId,
      replyContent: ''
    });
  },

  closeReplyInput() {
    this.setData({
      replyingPostId: null,
      replyContent: ''
    });
  },

  onInputReplyContent(e) {
    this.setData({ replyContent: e.detail.value });
  },

  submitReply() {
    const content = this.data.replyContent.trim();
    if (!content) {
      wx.showToast({ title: '请输入回复内容', icon: 'none' });
      return;
    }

    request.post('/reply', {
      postId: this.data.replyingPostId,
      content: content
    }).then(() => {
      wx.showToast({ title: '回复成功', icon: 'success' });
      this.closeReplyInput();
      this.fetchPosts();
    }).catch(() => {
      // 本地容错增加回复
      const postId = this.data.replyingPostId;
      const updated = this.data.posts.map(p => {
        if (p.id === postId) {
          const list = p.replies || [];
          return {
            ...p,
            replyCount: (p.replyCount || 0) + 1,
            replies: [...list, {
              id: Date.now(),
              userNickname: wx.getStorageSync('userInfo')?.nickname || '我',
              content: content
            }]
          };
        }
        return p;
      });
      this.setData({
        posts: updated,
        replyingPostId: null
      });
      wx.showToast({ title: '已回复 (离线预览)', icon: 'none' });
    });
  },

  /**
   * 一键召唤 AI 助教为当前求助/讨论生成专业答疑
   */
  onCallAiAssistant(e) {
    if (!app.checkLogin()) return;
    const postId = e.currentTarget.dataset.postId;
    if (!postId) return;

    // 检查是否已有 AI 助教解答，友好提示
    const targetPost = this.data.posts.find(p => p.id === postId);
    if (targetPost && targetPost.replies && targetPost.replies.some(r => r.isAi)) {
      wx.showToast({ title: 'AI 助教已在下方给出解答啦', icon: 'none' });
      return;
    }

    wx.showLoading({ title: 'AI 助教推导中...', mask: true });

    request.post(`/post/${postId}/ai-reply`, null, { loading: false })
      .then(res => {
        wx.hideLoading();
        wx.showToast({ title: 'AI 助教已解答', icon: 'success' });
        this.fetchPosts();
      })
      .catch(err => {
        wx.hideLoading();
        // 离线或服务异常容错
        const updated = this.data.posts.map(p => {
          if (p.id === postId) {
            const list = p.replies || [];
            return {
              ...p,
              replyCount: (p.replyCount || 0) + 1,
              replies: [...list, {
                id: Date.now(),
                userNickname: '智学伴 AI 助教',
                isAi: true,
                content: '【AI 助教答疑思路】建议从核心定理公式出发，梳理已知条件并尝试逆向推导，多做同类题型归纳巩固！'
              }]
            };
          }
          return p;
        });
        this.setData({ posts: updated });
        wx.showToast({ title: 'AI 助教已解答', icon: 'success' });
      });
  }
});
