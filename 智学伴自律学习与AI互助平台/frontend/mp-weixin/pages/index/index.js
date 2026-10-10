// pages/index/index.js
const app = getApp();
const util = require('../../utils/util');
const request = require('../../utils/request');

Page({
  data: {
    userInfo: {},
    greeting: '你好',
    todayMinutes: 0,
    focusCount: 0,
    checkinDays: 0,
    currentDate: ''
  },

  onLoad() {
    this.initGreeting();
    this.setData({
      currentDate: util.formatDate(new Date())
    });
  },

  onShow() {
    this.loadUserData();
    this.fetchTodayStats();
  },

  onPullDownRefresh() {
    this.fetchTodayStats();
    wx.stopPullDownRefresh();
  },

  initGreeting() {
    const hour = new Date().getHours();
    let greeting = '你好';
    if (hour < 6) greeting = '夜深了';
    else if (hour < 11) greeting = '早上好';
    else if (hour < 14) greeting = '中午好';
    else if (hour < 18) greeting = '下午好';
    else greeting = '晚上好';

    this.setData({ greeting });
  },

  loadUserData() {
    const userInfo = wx.getStorageSync('userInfo') || {};
    this.setData({ userInfo });
  },

  fetchTodayStats() {
    const token = wx.getStorageSync('token');
    if (!token || token.startsWith('mock_')) {
      return;
    }
    // 请求后端专注统计接口 (GET /api/focus/today-stats)
    request.get('/focus/today-stats', null, { loading: false, silentAuth: true, silentError: true })
      .then(res => {
        if (res) {
          this.setData({
            todayMinutes: res.todayMinutes || 0,
            focusCount: res.todayCount != null ? res.todayCount : (res.focusCount || 0)
          });
        }
      })
      .catch(() => {});

    // 请求用户个人累计数据以展示累计打卡天数 (GET /api/user/stats)
    request.get('/user/stats', null, { loading: false, silentAuth: true, silentError: true })
      .then(res => {
        if (res && res.totalCheckins != null) {
          this.setData({
            checkinDays: res.totalCheckins
          });
        }
      })
      .catch(() => {});
  },

  goToPomodoro() {
    wx.switchTab({ url: '/pages/pomodoro/pomodoro' });
  },

  goToCheckin() {
    wx.switchTab({ url: '/pages/checkin/checkin' });
  },

  goToCommunity() {
    wx.switchTab({ url: '/pages/community/community' });
  }
});
