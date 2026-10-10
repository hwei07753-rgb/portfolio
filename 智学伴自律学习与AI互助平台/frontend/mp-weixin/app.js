// app.js
const request = require('./utils/request');

App({
  globalData: {
    userInfo: null,
    token: null,
    isLoggedIn: false
  },

  onLaunch() {
    // 读取本地缓存的登录凭据与用户信息
    const token = wx.getStorageSync('token');
    const userInfo = wx.getStorageSync('userInfo');
    if (token && !token.startsWith('mock_')) {
      this.globalData.token = token;
      this.globalData.userInfo = userInfo || null;
      this.globalData.isLoggedIn = true;
    } else {
      // 若缓存为旧版离线 mock token 或未登录，清理并静默换取真实后端 JWT
      wx.removeStorageSync('token');
      wx.removeStorageSync('userInfo');
      this.autoLogin();
    }
  },

  autoLogin() {
    wx.login({
      success: (loginRes) => {
        if (loginRes.code) {
          request.post('/user/wx-login', { code: loginRes.code }, { loading: false, silentAuth: true, silentError: true })
            .then(res => {
              if (res && res.token) {
                wx.setStorageSync('token', res.token);
                wx.setStorageSync('userInfo', res.user);
                this.globalData.token = res.token;
                this.globalData.userInfo = res.user;
                this.globalData.isLoggedIn = true;
                // 若页面已挂载，通知各页刷新状态
                const pages = getCurrentPages();
                if (pages && pages.length > 0) {
                  pages.forEach(p => {
                    if (p && typeof p.fetchTodayStats === 'function') p.fetchTodayStats();
                    if (p && typeof p.refreshLoginState === 'function') p.refreshLoginState();
                    if (p && typeof p.fetchUserStats === 'function') p.fetchUserStats();
                  });
                }
              }
            })
            .catch(() => {});
        }
      }
    });
  },

  /**
   * 检查或提示登录
   */
  checkLogin(redirect = true) {
    if (this.globalData.isLoggedIn && this.globalData.token) {
      return true;
    }
    if (redirect) {
      wx.showModal({
        title: '提示',
        content: '该功能需要登录后使用，是否前往登录？',
        success: (res) => {
          if (res.confirm) {
            wx.switchTab({
              url: '/pages/mine/mine'
            });
          }
        }
      });
    }
    return false;
  }
});
