// pages/pomodoro/pomodoro.js
const app = getApp();
const util = require('../../utils/util');
const request = require('../../utils/request');

Page({
  data: {
    status: 'IDLE', // IDLE, RUNNING, PAUSED
    currentTag: '背单词',
    presetTags: ['背单词', '刷题', '看网课', '论文写作', '复习备考'],
    selectedDuration: 25,
    presetDurations: [
      { label: '15分钟', minutes: 15 },
      { label: '25分钟', minutes: 25 },
      { label: '45分钟', minutes: 45 },
      { label: '60分钟', minutes: 60 }
    ],
    remainSeconds: 25 * 60,
    remainTimeString: '25:00',
    progressPercent: 0,
    progressAngle: 0,
    startTime: null,
    todayRecords: [],

    // 白噪音伴学模式（内置轻量无损治愈声学流）
    whiteNoiseList: [
      { id: 'none', name: '静音专注', icon: '🔇', src: '' },
      { id: 'rain', name: '淅沥细雨', icon: '🌧️', src: '/audio/rain.mp3' },
      { id: 'forest', name: '林间微风', icon: '🍃', src: '/audio/forest.mp3' },
      { id: 'cafe', name: '暖阳自习', icon: '☕', src: '/audio/cafe.mp3' }
    ],
    currentNoise: 'none',

    // 完成时的手账专属印章弹窗
    showStampModal: false,
    stampData: {
      minutes: 25,
      tag: '背单词',
      sealTitle: '静心笃行',
      quote: '每一次心无旁骛的沉浸，都在悄悄沉淀出更坚定的自己。'
    }
  },

  timer: null,
  audioCtx: null,

  initAudio() {
    if (!this.audioCtx) {
      this.audioCtx = wx.createInnerAudioContext();
      this.audioCtx.loop = true;
      this.audioCtx.obeyMuteSwitch = false;
      this.audioCtx.onError((err) => {
        console.warn('白噪音播放提示:', err);
      });
    }
  },

  playNoise() {
    if (this.data.currentNoise === 'none') {
      this.stopNoise();
      return;
    }
    const item = this.data.whiteNoiseList.find(n => n.id === this.data.currentNoise);
    if (!item || !item.src) {
      this.stopNoise();
      return;
    }
    this.initAudio();
    this.audioCtx.stop();
    this.audioCtx.src = item.src;
    this.audioCtx.play();
  },

  stopNoise() {
    if (this.audioCtx) {
      try {
        this.audioCtx.stop();
      } catch (e) {}
    }
  },

  pauseNoise() {
    if (this.audioCtx) {
      try {
        this.audioCtx.pause();
      } catch (e) {}
    }
  },

  resumeNoise() {
    if (this.data.status === 'RUNNING' && this.data.currentNoise !== 'none') {
      if (this.audioCtx) {
        this.audioCtx.play();
      } else {
        this.playNoise();
      }
    }
  },

  onShow() {
    this.fetchTodayRecords();
  },

  onHide() {
    this.pauseNoise();
  },

  onUnload() {
    if (this.timer) {
      clearInterval(this.timer);
    }
    this.stopNoise();
    if (this.audioCtx) {
      try {
        this.audioCtx.destroy();
      } catch (e) {}
      this.audioCtx = null;
    }
  },

  // 轻微触感振动辅助函数 (自动过滤PC开发者工具模拟器，避免模拟器窗口物理震颤抖屏；真机手机上才会产生清脆触感)
  vibrate(type = 'light') {
    try {
      const sys = wx.getSystemInfoSync ? wx.getSystemInfoSync() : null;
      if (sys && sys.platform === 'devtools') {
        return; // PC模拟器跳过，消除整个模块震动抖屏
      }
      wx.vibrateShort({ type });
    } catch (e) {}
  },

  onSelectTag(e) {
    if (this.data.status !== 'IDLE') return;
    this.vibrate('light');
    this.setData({ currentTag: e.currentTarget.dataset.tag });
  },

  onSelectDuration(e) {
    if (this.data.status !== 'IDLE') return;
    this.vibrate('light');
    const minutes = e.currentTarget.dataset.minutes;
    this.setData({
      selectedDuration: minutes,
      remainSeconds: minutes * 60,
      remainTimeString: util.formatDuration(minutes * 60),
      progressPercent: 0,
      progressAngle: 0
    });
  },

  onSelectNoise(e) {
    const noiseId = e.currentTarget.dataset.id;
    this.vibrate('medium');
    this.setData({ currentNoise: noiseId });
    const selected = this.data.whiteNoiseList.find(n => n.id === noiseId);
    if (noiseId !== 'none') {
      wx.showToast({
        title: `已开启 · ${selected ? selected.name : ''} 氛围`,
        icon: 'none'
      });
    }
    // 若当前正在专注倒计时中，实时切换/停止背景白噪音
    if (this.data.status === 'RUNNING') {
      this.playNoise();
    }
  },

  startTimer() {
    if (!app.checkLogin()) return;
    this.vibrate('medium');

    const startTime = util.formatTime(new Date());
    this.setData({
      status: 'RUNNING',
      startTime: startTime
    });

    this.playNoise();
    this.runCountdown();
  },

  runCountdown() {
    if (this.timer) clearInterval(this.timer);
    const totalSec = this.data.selectedDuration * 60;

    this.timer = setInterval(() => {
      let seconds = this.data.remainSeconds - 1;
      if (seconds <= 0) {
        clearInterval(this.timer);
        this.stopNoise();
        this.setData({
          remainSeconds: 0,
          remainTimeString: '00:00',
          progressPercent: 100,
          progressAngle: 360,
          status: 'IDLE'
        });
        this.finishFocus(0); // 0=正常完成
        this.triggerStampCelebration(this.data.selectedDuration, this.data.currentTag);
      } else {
        const percent = Math.min(100, Math.floor(((totalSec - seconds) / totalSec) * 100));
        const angle = Math.floor(((totalSec - seconds) / totalSec) * 360);
        this.setData({
          remainSeconds: seconds,
          remainTimeString: util.formatDuration(seconds),
          progressPercent: percent,
          progressAngle: angle
        });
      }
    }, 1000);
  },

  pauseTimer() {
    this.vibrate('light');
    if (this.timer) clearInterval(this.timer);
    this.setData({ status: 'PAUSED' });
    this.pauseNoise();
  },

  resumeTimer() {
    this.vibrate('light');
    this.setData({ status: 'RUNNING' });
    this.resumeNoise();
    this.runCountdown();
  },

  abandonTimer() {
    wx.showModal({
      title: '确认放弃',
      content: '确定要放弃本次专注吗？已专注时长将被记录为放弃状态。',
      confirmColor: '#E07A5F',
      success: (res) => {
        if (res.confirm) {
          this.vibrate('medium');
          if (this.timer) clearInterval(this.timer);
          this.stopNoise();
          this.finishFocus(1); // 1=放弃
          this.resetTimer();
        }
      }
    });
  },

  completeTimerEarly() {
    const elapsedMinutes = Math.max(1, Math.floor((this.data.selectedDuration * 60 - this.data.remainSeconds) / 60));
    wx.showModal({
      title: '提前完成',
      content: `已专注 ${elapsedMinutes} 分钟，是否确认提前结算并收下手账印章？`,
      confirmColor: '#81B29A',
      success: (res) => {
        if (res.confirm) {
          this.vibrate('heavy');
          if (this.timer) clearInterval(this.timer);
          this.stopNoise();
          this.finishFocus(0, elapsedMinutes);
          this.resetTimer();
          this.triggerStampCelebration(elapsedMinutes, this.data.currentTag);
        }
      }
    });
  },

  // 触发专属手账印章庆祝动画弹窗
  triggerStampCelebration(minutes, tag) {
    try {
      wx.vibrateLong && wx.vibrateLong();
    } catch (e) {}

    const seals = ['静心笃行', '温和坚定', '聚沙成塔', '学贵有恒', '专注生长'];
    const randomSeal = seals[Math.floor(Math.random() * seals.length)];

    this.setData({
      showStampModal: true,
      stampData: {
        minutes: minutes,
        tag: tag,
        sealTitle: randomSeal,
        quote: '每一次心无旁骛的沉浸，都是在悄悄成为更坚定的自己。'
      }
    });
  },

  closeStampModal() {
    this.vibrate('light');
    this.setData({ showStampModal: false });
  },

  resetTimer() {
    const defaultSec = this.data.selectedDuration * 60;
    this.setData({
      status: 'IDLE',
      remainSeconds: defaultSec,
      remainTimeString: util.formatDuration(defaultSec),
      progressPercent: 0,
      progressAngle: 0,
      startTime: null
    });
  },

  finishFocus(status, customMinutes = null) {
    const endTime = util.formatTime(new Date());
    const duration = customMinutes !== null ? customMinutes : this.data.selectedDuration;
    
    // 调用后端保存接口 POST /api/focus/record
    request.post('/focus/record', {
      durationMinutes: duration,
      tag: this.data.currentTag,
      status: status,
      startTime: this.data.startTime || endTime,
      endTime: endTime
    }).then(() => {
      this.fetchTodayRecords();
    }).catch(() => {
      // 容错展示本地记录
      const localItem = {
        id: Date.now(),
        tag: this.data.currentTag,
        durationMinutes: duration,
        status: status,
        timeDesc: '刚刚'
      };
      this.setData({
        todayRecords: [localItem, ...this.data.todayRecords]
      });
    });
  },

  fetchTodayRecords() {
    if (!wx.getStorageSync('token')) return;
    request.get('/focus/today-list', null, { loading: false })
      .then(res => {
        if (Array.isArray(res)) {
          const list = res.map(item => ({
            ...item,
            timeDesc: util.formatRelativeTime(item.startTime)
          }));
          this.setData({ todayRecords: list });
        }
      })
      .catch(() => {});
  }
});

