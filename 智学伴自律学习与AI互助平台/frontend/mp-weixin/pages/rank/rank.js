// pages/rank/rank.js - 学霸自律排行榜逻辑
const app = getApp();
const request = require('../../utils/request');

Page({
  data: {
    tabs: [
      { key: 'day', label: '今日专注', icon: '⏱️' },
      { key: 'week', label: '本周专注', icon: '📅' },
      { key: 'streak', label: '累计打卡', icon: '🔥' },
      { key: 'coins', label: '自律学分', icon: '🪙' }
    ],
    activeTab: 'day',
    topList: [],
    top3: [],
    remainingList: [],
    myRank: {},
    gapToAbove: 0,
    motivationText: '',
    loading: false
  },

  onLoad(options) {
    if (options && options.type) {
      this.setData({ activeTab: options.type });
    }
  },

  onShow() {
    this.fetchLeaderboard(this.data.activeTab);
  },

  onPullDownRefresh() {
    this.fetchLeaderboard(this.data.activeTab, () => {
      wx.stopPullDownRefresh();
    });
  },

  switchTab(e) {
    const key = e.currentTarget.dataset.key;
    if (key === this.data.activeTab) return;
    this.setData({ activeTab: key });
    this.fetchLeaderboard(key);
  },

  fetchLeaderboard(type, callback) {
    this.setData({ loading: true });
    request.get('/rank/leaderboard', { type: type }, { loading: false, silentAuth: true })
      .then(res => {
        this.setData({ loading: false });
        if (res) {
          const topList = res.topList || [];
          const top3 = topList.slice(0, 3);
          const remainingList = topList.slice(3);
          this.setData({
            topList: topList,
            top3: top3,
            remainingList: remainingList,
            myRank: res.myRank || {},
            gapToAbove: res.gapToAbove || 0,
            motivationText: res.motivationText || ''
          });
        }
        if (typeof callback === 'function') callback();
      })
      .catch(() => {
        this.setData({ loading: false });
        // 离线环境兜底模拟数据
        this.fallbackMockData(type);
        if (typeof callback === 'function') callback();
      });
  },

  fallbackMockData(type) {
    const unitMap = {
      day: ' 分钟',
      week: ' 分钟',
      streak: ' 天',
      coins: ' 币'
    };
    const unit = unitMap[type] || ' 分钟';
    const mockList = [
      { rank: 1, userId: 101, nickname: '晨曦求索者', avatarUrl: '/images/tabbar/mine.png', studyGoal: '清华计算机学硕', score: 180, scoreFormatted: '180' + unit, isSelf: false },
      { rank: 2, userId: 102, nickname: '笃行小林', avatarUrl: '/images/tabbar/mine.png', studyGoal: '雅思 7.5 分冲刺', score: 145, scoreFormatted: '145' + unit, isSelf: false },
      { rank: 3, userId: 103, nickname: '数学不挂科', avatarUrl: '/images/tabbar/mine.png', studyGoal: '考研数学二 130+', score: 120, scoreFormatted: '120' + unit, isSelf: false },
      { rank: 4, userId: 104, nickname: '图书馆常客', avatarUrl: '/images/tabbar/mine.png', studyGoal: '英语六级 550+', score: 95, scoreFormatted: '95' + unit, isSelf: false },
      { rank: 5, userId: 105, nickname: '自律学伴_2027', avatarUrl: '/images/tabbar/mine.png', studyGoal: '软考中级通关', score: 75, scoreFormatted: '75' + unit, isSelf: true }
    ];

    this.setData({
      topList: mockList,
      top3: mockList.slice(0, 3),
      remainingList: mockList.slice(3),
      myRank: mockList[4],
      gapToAbove: 20,
      motivationText: '距上一名仅差 20' + unit + '，一个番茄钟即可实现反超！'
    });
  },

  goToStudy() {
    wx.switchTab({
      url: '/pages/pomodoro/pomodoro'
    });
  }
});
