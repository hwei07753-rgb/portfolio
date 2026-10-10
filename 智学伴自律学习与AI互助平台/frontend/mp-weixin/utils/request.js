/**
 * 网络请求封装
 * 适配后端 Spring Boot Result<T> 结构：{ code: 200, message: "...", data: ... }
 */
const BASE_URL = 'http://localhost:8080/api';

const request = (options = {}) => {
  return new Promise((resolve, reject) => {
    const token = wx.getStorageSync('token');
    const header = {
      'Content-Type': 'application/json',
      ...options.header
    };

    if (token) {
      header['Authorization'] = `Bearer ${token}`;
    }

    if (options.loading !== false) {
      wx.showLoading({
        title: options.loadingTitle || '加载中...',
        mask: true
      });
    }

    wx.request({
      url: options.url.startsWith('http') ? options.url : `${BASE_URL}${options.url}`,
      method: options.method || 'GET',
      data: options.data,
      header: header,
      timeout: options.timeout || 15000,
      success: (res) => {
        if (options.loading !== false) {
          wx.hideLoading();
        }

        // 处理 401 未授权（Token过期或无效）
        if (res.statusCode === 401 || (res.statusCode === 200 && res.data && res.data.code === 401)) {
          wx.removeStorageSync('token');
          wx.removeStorageSync('userInfo');
          try {
            const currentApp = getApp();
            if (currentApp && currentApp.globalData) {
              currentApp.globalData.token = null;
              currentApp.globalData.userInfo = null;
              currentApp.globalData.isLoggedIn = false;
            }
          } catch (e) {}

          if (!options.silentAuth) {
            wx.showToast({
              title: '登录已过期，请重新登录',
              icon: 'none'
            });
          }
          reject(new Error('未授权或登录已过期'));
          return;
        }

        if (res.statusCode === 200) {
          const body = res.data;
          // 后端 Result 规范：code == 200 为成功
          if (body.code === 200) {
            resolve(body.data);
          } else {
            if (!options.silentError) {
              wx.showToast({
                title: body.message || '操作失败',
                icon: 'none'
              });
            }
            reject(new Error(body.message || '业务异常'));
          }
        } else {
          if (!options.silentError) {
            wx.showToast({
              title: `网络状态异常 (${res.statusCode})`,
              icon: 'none'
            });
          }
          reject(new Error(`HTTP error ${res.statusCode}`));
        }
      },
      fail: (err) => {
        if (options.loading !== false) {
          wx.hideLoading();
        }
        if (!options.silentError) {
          wx.showToast({
            title: '网络连接失败，请检查后端服务',
            icon: 'none'
          });
        }
        reject(err);
      }
    });
  });
};

const get = (url, data, options = {}) => request({ url, data, method: 'GET', ...options });
const post = (url, data, options = {}) => request({ url, data, method: 'POST', ...options });
const put = (url, data, options = {}) => request({ url, data, method: 'PUT', ...options });
const del = (url, data, options = {}) => request({ url, data, method: 'DELETE', ...options });

module.exports = {
  BASE_URL,
  request,
  get,
  post,
  put,
  delete: del
};
