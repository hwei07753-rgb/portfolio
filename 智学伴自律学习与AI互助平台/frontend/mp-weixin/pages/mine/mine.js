// pages/mine/mine.js
const app = getApp();
const request = require('../../utils/request');

Page({
  data: {
    isLoggedIn: false,
    userInfo: {},
    userStats: {
      totalMinutes: 0,
      totalCheckins: 0,
      totalPosts: 0
    },
    showGoalModal: false,
    newStudyGoal: '',

    // S5 管理员控制台数据
    showAdminModal: false,
    adminStats: {
      userCount: 0,
      postCount: 0,
      checkinCount: 0,
      focusTotalMinutes: 0
    },
    adminUsers: [],
    adminKeyword: '',
    loadingAdminUsers: false
  },

  onShow() {
    this.refreshLoginState();
    if (this.data.isLoggedIn) {
      this.fetchUserStats();
    }
  },

  refreshLoginState() {
    const token = wx.getStorageSync('token');
    const userInfo = wx.getStorageSync('userInfo');
    const logged = !!(token && userInfo);
    this.setData({
      isLoggedIn: logged,
      userInfo: userInfo || {}
    });
    app.globalData.isLoggedIn = logged;
    app.globalData.token = token;
    app.globalData.userInfo = userInfo;
  },

  handleWxLogin() {
    wx.login({
      success: (loginRes) => {
        if (loginRes.code) {
          // 调用后端微信登录换取 JWT: POST /api/user/wx-login { code }
          request.post('/user/wx-login', { code: loginRes.code }, { loadingTitle: '正在登录...' })
            .then(res => {
              wx.setStorageSync('token', res.token);
              wx.setStorageSync('userInfo', res.user);
              this.refreshLoginState();
              this.fetchUserStats();
              wx.showToast({ title: '登录成功', icon: 'success' });
            })
            .catch(() => {
              // 本地演示降级
              this.handleDemoLogin();
            });
        }
      }
    });
  },

  handleDemoLogin() {
    request.post('/user/wx-login', { code: 'demo_openid_0001' }, { loadingTitle: '学员模式加载中...', silentError: true })
      .then(res => {
        wx.setStorageSync('token', res.token);
        wx.setStorageSync('userInfo', res.user);
        this.refreshLoginState();
        this.fetchUserStats();
        wx.showToast({ title: '已登录学员账号', icon: 'success' });
      })
      .catch(() => {
        const mockUser = {
          id: 2,
          openid: 'demo_openid_0001',
          nickname: '张三 (自律学员)',
          avatarUrl: '/images/tabbar/mine.png',
          studyGoal: '2027计算机考研 408高分上岸',
          role: 0,
          status: 0
        };
        wx.setStorageSync('token', 'mock_jwt_token_student');
        wx.setStorageSync('userInfo', mockUser);
        this.refreshLoginState();
        this.setData({
          userStats: {
            totalMinutes: 50,
            totalCheckins: 2,
            totalPosts: 2
          }
        });
        wx.showToast({ title: '已进入学员演示模式', icon: 'none' });
      });
  },

  handleAdminLogin() {
    // S5 后端种子管理员 openid: admin_openid_0001
    request.post('/user/wx-login', { code: 'admin_openid_0001' }, { loadingTitle: '管理员模式加载中...', silentError: true })
      .then(res => {
        wx.setStorageSync('token', res.token);
        wx.setStorageSync('userInfo', res.user);
        this.refreshLoginState();
        this.fetchUserStats();
        wx.showToast({ title: '已登录管理员账号', icon: 'success' });
      })
      .catch(() => {
        const mockAdmin = {
          id: 1,
          openid: 'admin_openid_0001',
          nickname: '系统管理员',
          avatarUrl: '/images/tabbar/mine.png',
          studyGoal: '平台学术生态全景治理',
          role: 1,
          status: 0
        };
        wx.setStorageSync('token', 'mock_jwt_token_admin');
        wx.setStorageSync('userInfo', mockAdmin);
        this.refreshLoginState();
        this.setData({
          userStats: {
            totalMinutes: 1200,
            totalCheckins: 30,
            totalPosts: 12
          }
        });
        wx.showToast({ title: '已进入管理员演示模式', icon: 'none' });
      });
  },

  fetchUserStats() {
    request.get('/user/stats', null, { loading: false, silentAuth: true, silentError: true })
      .then(res => {
        if (res) {
          this.setData({ userStats: res });
        }
      })
      .catch(() => {});
  },

  openGoalModal() {
    this.setData({
      showGoalModal: true,
      newStudyGoal: this.data.userInfo.studyGoal || ''
    });
  },

  closeGoalModal() {
    this.setData({ showGoalModal: false });
  },

  onInputStudyGoal(e) {
    this.setData({ newStudyGoal: e.detail.value });
  },

  saveStudyGoal() {
    const goal = this.data.newStudyGoal.trim();
    if (!goal) {
      wx.showToast({ title: '请输入学习目标', icon: 'none' });
      return;
    }

    request.put('/user/profile', { studyGoal: goal })
      .then(() => {
        const userInfo = { ...this.data.userInfo, studyGoal: goal };
        wx.setStorageSync('userInfo', userInfo);
        this.setData({
          userInfo: userInfo,
          showGoalModal: false
        });
        wx.showToast({ title: '目标已更新', icon: 'success' });
      })
      .catch(() => {
        const userInfo = { ...this.data.userInfo, studyGoal: goal };
        wx.setStorageSync('userInfo', userInfo);
        this.setData({
          userInfo: userInfo,
          showGoalModal: false
        });
        wx.showToast({ title: '目标已更新(本地)', icon: 'none' });
      });
  },

  // ---------------- S5 管理员控制台逻辑 ----------------
  openAdminModal() {
    if (this.data.userInfo.role !== 1) {
      wx.showToast({ title: '无权访问管理员后台', icon: 'none' });
      return;
    }
    this.setData({ showAdminModal: true });
    this.fetchAdminStats();
    this.fetchAdminUsers();
  },

  closeAdminModal() {
    this.setData({ showAdminModal: false });
  },

  fetchAdminStats() {
    request.get('/admin/stats', null, { loading: false, silentError: true })
      .then(res => {
        if (res) {
          this.setData({ adminStats: res });
        }
      })
      .catch(() => {
        // 演示保底数据
        this.setData({
          adminStats: {
            userCount: 3,
            postCount: 3,
            checkinCount: 2,
            focusTotalMinutes: 50
          }
        });
      });
  },

  fetchAdminUsers() {
    this.setData({ loadingAdminUsers: true });
    const params = {
      page: 1,
      size: 20
    };
    if (this.data.adminKeyword.trim()) {
      params.keyword = this.data.adminKeyword.trim();
    }
    request.get('/admin/users', params, { loading: false, silentError: true })
      .then(res => {
        this.setData({
          loadingAdminUsers: false,
          adminUsers: (res && res.records) ? res.records : []
        });
      })
      .catch(() => {
        this.setData({
          loadingAdminUsers: false,
          adminUsers: [
            { id: 1, openid: 'admin_****0001', nickname: '系统管理员', role: 1, status: 0, createdAt: '2026-09-30 15:00:00' },
            { id: 2, openid: 'demo_o****0001', nickname: '张三 (自律学员)', role: 0, status: 0, createdAt: '2026-09-30 15:05:00' },
            { id: 3, openid: 'demo_o****0002', nickname: '李四', role: 0, status: 0, createdAt: '2026-09-30 15:10:00' }
          ]
        });
      });
  },

  onInputAdminKeyword(e) {
    this.setData({ adminKeyword: e.detail.value });
  },

  searchAdminUsers() {
    this.fetchAdminUsers();
  },

  toggleUserStatus(e) {
    const { id, status } = e.currentTarget.dataset;
    const targetStatus = parseInt(status, 10);
    const actionText = targetStatus === 1 ? '封禁' : '解封';

    wx.showModal({
      title: '状态变更确认',
      content: `确定要${actionText}该用户（ID: ${id}）吗？`,
      success: (mRes) => {
        if (mRes.confirm) {
          request.put(`/admin/user/${id}/status`, { status: targetStatus }, { loadingTitle: '正在提交...' })
            .then(() => {
              wx.showToast({ title: `已成功${actionText}用户`, icon: 'success' });
              this.fetchAdminUsers();
              this.fetchAdminStats();
            })
            .catch(err => {
              // 本地联调保底切换
              const updated = this.data.adminUsers.map(u => {
                if (u.id === id) {
                  return { ...u, status: targetStatus };
                }
                return u;
              });
              this.setData({ adminUsers: updated });
              wx.showToast({ title: `已${actionText}(演示)`, icon: 'none' });
            });
        }
      }
    });
  },

  handleLogout() {
    wx.showModal({
      title: '提示',
      content: '确定要退出当前账号吗？',
      success: (res) => {
        if (res.confirm) {
          wx.removeStorageSync('token');
          wx.removeStorageSync('userInfo');
          this.refreshLoginState();
          this.setData({
            userStats: { totalMinutes: 0, totalCheckins: 0, totalPosts: 0 }
          });
          wx.showToast({ title: '已退出登录', icon: 'none' });
        }
      }
    });
  },

  showAbout() {
    wx.showModal({
      title: '关于“智学伴”',
      content: '“智学伴”自律学习与AI互助平台（微信小程序客户端 v1.0.0）。旨在为高校学子提供番茄钟专注计时、每日学习打卡、大模型个性化复盘建议以及互助交流社区。',
      showCancel: false
    });
  },

  showTips() {
    wx.showModal({
      title: '答辩与课设设计说明',
      content: '系统采用前后端分离架构，核心后端基于 Spring Boot 3 + MyBatis-Plus + MySQL 8.0。AI复盘支持 DeepSeek / 通义千问大模型API调用。独创“自律学分-悬赏答疑闭环”与“全维度自律学霸排行榜”，支持榜首领跑与超越差距动态激励。',
      showCancel: false
    });
  },

  goToRank() {
    wx.navigateTo({
      url: '/pages/rank/rank'
    });
  },

  goToPlan() {
    wx.navigateTo({
      url: '/pages/plan/plan'
    });
  }
});
