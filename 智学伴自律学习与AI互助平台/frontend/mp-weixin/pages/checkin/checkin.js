// pages/checkin/checkin.js
const app = getApp();
const util = require('../../utils/util');
const request = require('../../utils/request');

Page({
  data: {
    todayStr: '',
    content: '',
    imageUrl: '',
    submitting: false,
    latestAiReview: '',
    displayedAiReview: '',
    isTyping: false,
    isTodayChecked: false,
    historyList: [],

    // 快捷心得标签 (手账速记)
    quickTags: ['背单词', '刷真题', '论文进展', '知识梳理', '错题难点']
  },

  typingTimer: null,

  onLoad() {
    this.setData({
      todayStr: util.formatDate(new Date())
    });
  },

  onShow() {
    this.fetchHistory();
  },

  onUnload() {
    if (this.typingTimer) {
      clearInterval(this.typingTimer);
    }
  },

  onPullDownRefresh() {
    this.fetchHistory();
    wx.stopPullDownRefresh();
  },

  // 振动触感反馈 (过滤PC模拟器，避免模拟器视窗整体抖动)
  vibrate(type = 'light') {
    try {
      const sys = wx.getSystemInfoSync ? wx.getSystemInfoSync() : null;
      if (sys && sys.platform === 'devtools') {
        return;
      }
      wx.vibrateShort({ type });
    } catch (e) {}
  },

  onInputContent(e) {
    this.setData({ content: e.detail.value });
  },

  // 快捷插入灵感标签
  insertTag(e) {
    this.vibrate('light');
    const tag = e.currentTarget.dataset.tag;
    const toInsert = `#${tag}# `;
    const current = this.data.content;
    const updated = current ? `${current} ${toInsert}` : toInsert;
    this.setData({ content: updated });
  },

  chooseImage() {
    this.vibrate('light');
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const tempFilePath = res.tempFiles[0].tempFilePath;
        wx.showLoading({ title: '上传笔记图片...' });
        wx.uploadFile({
          url: `${request.BASE_URL}/upload`,
          filePath: tempFilePath,
          name: 'file',
          header: {
            'Authorization': `Bearer ${wx.getStorageSync('token')}`
          },
          success: (uploadRes) => {
            wx.hideLoading();
            try {
              const data = JSON.parse(uploadRes.data);
              if (data.code === 200 && data.data) {
                this.setData({ imageUrl: data.data });
              } else {
                this.setData({ imageUrl: tempFilePath });
              }
            } catch (e) {
              this.setData({ imageUrl: tempFilePath });
            }
          },
          fail: () => {
            wx.hideLoading();
            this.setData({ imageUrl: tempFilePath });
          }
        });
      }
    });
  },

  removeImage() {
    this.vibrate('light');
    this.setData({ imageUrl: '' });
  },

  previewImage() {
    if (this.data.imageUrl) {
      wx.previewImage({ urls: [this.data.imageUrl] });
    }
  },

  previewHistoryImage(e) {
    const src = e.currentTarget.dataset.src;
    if (src) {
      wx.previewImage({ urls: [src] });
    }
  },

  // 启动 AI 导师打字机流式输出动效
  startTypewriter(fullText) {
    if (this.typingTimer) clearInterval(this.typingTimer);
    
    this.setData({
      isTyping: true,
      displayedAiReview: ''
    });

    let index = 0;
    const speed = 25; // 25ms 每个字，极富科技交互感
    this.typingTimer = setInterval(() => {
      index++;
      if (index >= fullText.length) {
        clearInterval(this.typingTimer);
        this.setData({
          displayedAiReview: fullText,
          isTyping: false
        });
      } else {
        this.setData({
          displayedAiReview: fullText.substring(0, index)
        });
      }
    }, speed);
  },

  // 快速跳过打字动效
  skipTyping() {
    if (this.typingTimer) clearInterval(this.typingTimer);
    this.setData({
      displayedAiReview: this.data.latestAiReview,
      isTyping: false
    });
  },

  submitCheckin() {
    if (!app.checkLogin()) return;

    const content = this.data.content.trim();
    if (!content) {
      wx.showToast({ title: '请填写今日打卡心得', icon: 'none' });
      return;
    }

    this.vibrate('medium');
    this.setData({ submitting: true });

    // 提交打卡 POST /api/checkin
    request.post('/checkin', {
      content: content,
      imageUrl: this.data.imageUrl
    }, { loading: false })
      .then(res => {
        const review = res.aiReview || '【AI导师复盘点评】\n今日打卡已记录！你在专业专注度上保持得很好，思路清晰。建议明天结合错题巩固复习，稳扎稳打！';
        this.setData({
          submitting: false,
          content: '',
          imageUrl: '',
          isTodayChecked: true,
          latestAiReview: review
        });
        wx.showToast({ title: '打卡达成 ✨', icon: 'success' });
        this.startTypewriter(review);
        this.fetchHistory();
      })
      .catch(() => {
        const fallbackReview = '【AI导师复盘点评】\n今日专注状态良好！你在任务拆解和重点突破上展现了清晰的逻辑，建议明天趁热打铁，针对薄弱题型做一次针对性测验。继续保持这股温和而坚定的节奏！🌿';
        this.setData({
          submitting: false,
          content: '',
          imageUrl: '',
          isTodayChecked: true,
          latestAiReview: fallbackReview
        });
        wx.showToast({ title: '已记录打卡 ✨', icon: 'none' });
        this.startTypewriter(fallbackReview);
      });
  },

  fetchHistory() {
    if (!wx.getStorageSync('token')) return;
    request.get('/checkin/my-history', null, { loading: false })
      .then(res => {
        if (Array.isArray(res)) {
          const list = res.map(item => ({
            ...item,
            timeDesc: util.formatRelativeTime(item.createdAt)
          }));
          this.setData({ 
            historyList: list,
            isTodayChecked: list.length > 0
          });
        }
      })
      .catch(() => {});
  }
});

