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
    currentDate: '',
    todaySummary: {}
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

    // 请求自律学霸榜概况展示 (GET /api/rank/leaderboard)
    request.get('/rank/leaderboard', { type: 'day' }, { loading: false, silentAuth: true, silentError: true })
      .then(res => {
        if (res) {
          let txt = '';
          if (res.topList && res.topList.length > 0) {
            const leader = res.topList[0];
            txt = `今日榜首: ${leader.nickname} (${leader.scoreFormatted})`;
            if (res.myRank && res.myRank.rank > 0) {
              txt += ` · 我的排位: 第${res.myRank.rank}名`;
            }
          } else {
            txt = '今日榜单虚位以待，快来开启专注抢占榜首！';
          }
          this.setData({ rankPreviewText: txt });
        }
      })
      .catch(() => {});

    // 请求学业计划与今日任务清单 (GET /api/plan/today-summary)
    request.get('/plan/today-summary', null, { loading: false, silentAuth: true, silentError: true })
      .then(res => {
        if (res) {
          this.setData({ todaySummary: res });
        }
      })
      .catch(() => {});
  },

  onToggleHomeTask(e) {
    if (!app.checkLogin()) return;
    const id = e.currentTarget.dataset.id;
    if (!id) return;
    if (wx.vibrateShort) wx.vibrateShort({ type: 'light' });
    request.post(`/plan/task/${id}/toggle`).then(res => {
      const isDone = res && res.isCompleted === 1;
      wx.showToast({ title: isDone ? '打勾完成 (+5 币 🪙)' : '已取消完成', icon: 'none' });
      this.fetchTodayStats();
    }).catch(err => {
      wx.showToast({ title: (err && err.message) || '操作失败', icon: 'none' });
    });
  },

  goToPomodoro() {
    wx.switchTab({ url: '/pages/pomodoro/pomodoro' });
  },

  goToCheckin() {
    wx.switchTab({ url: '/pages/checkin/checkin' });
  },

  goToCommunity() {
    wx.switchTab({ url: '/pages/community/community' });
  },

  goToRank() {
    wx.navigateTo({ url: '/pages/rank/rank' });
  },

  goToPlan() {
    wx.navigateTo({ url: '/pages/plan/plan' });
  }
});
