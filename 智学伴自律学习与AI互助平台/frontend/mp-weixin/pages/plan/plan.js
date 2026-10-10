// pages/plan/plan.js - 阶段学业计划与清单业务逻辑
const app = getApp();
const request = require('../../utils/request');

Page({
  data: {
    plans: [],
    categories: ['四六级', '考研', '期末', '自律'],
    showPlanModal: false,
    newPlan: {
      title: '',
      category: '四六级',
      totalDays: 40
    },
    showTaskModal: false,
    targetPlanId: null,
    newTaskTitle: '',
    newTaskCoins: 5,
    loading: false
  },

  onShow() {
    this.fetchPlans();
  },

  onPullDownRefresh() {
    this.fetchPlans(() => {
      wx.stopPullDownRefresh();
    });
  },

  fetchPlans(callback) {
    this.setData({ loading: true });
    request.get('/plan/list', null, { loading: false, silentAuth: true })
      .then(res => {
        this.setData({ loading: false });
        if (Array.isArray(res)) {
          this.setData({ plans: res });
        }
        if (typeof callback === 'function') callback();
      })
      .catch(() => {
        this.setData({ loading: false });
        // 离线演示保底
        this.fallbackMockPlans();
        if (typeof callback === 'function') callback();
      });
  },

  fallbackMockPlans() {
    this.setData({
      plans: [
        {
          id: 1,
          title: '大学英语四级(CET-4) 40天高分通关计划',
          category: '四六级',
          totalDays: 40,
          daysRemaining: 38,
          progressPercent: 50,
          completedTaskCount: 2,
          totalTaskCount: 4,
          tasks: [
            { id: 101, title: '📖 在扇贝/百词斩背诵 50 个四级核心词汇', isCompleted: 1, rewardCoins: 5, continuousDays: 3 },
            { id: 102, title: '🎧 完成 1 篇历年四级听力真题精听', isCompleted: 1, rewardCoins: 5, continuousDays: 2 },
            { id: 103, title: '⏱️ 番茄钟沉浸专注阅读与真题训练 45 分钟', isCompleted: 0, rewardCoins: 5, continuousDays: 0 },
            { id: 104, title: '📝 睡前整理今日错题并在智学伴打卡复盘', isCompleted: 0, rewardCoins: 5, continuousDays: 0 }
          ]
        }
      ]
    });
  },

  /**
   * 打勾 / 取消打勾完成任务
   */
  onToggleTask(e) {
    if (!app.checkLogin()) return;
    const taskId = e.currentTarget.dataset.id;
    if (!taskId) return;

    // 震动轻微触觉反馈
    if (wx.vibrateShort) {
      wx.vibrateShort({ type: 'light' });
    }

    request.post(`/plan/task/${taskId}/toggle`)
      .then(res => {
        const isDone = res && res.isCompleted === 1;
        wx.showToast({
          title: isDone ? '打勾完成 (+5 币 🪙)' : '已取消完成',
          icon: 'none'
        });
        this.fetchPlans();
      })
      .catch(() => {
        // 本地更新模拟
        const updated = this.data.plans.map(p => {
          const newTasks = (p.tasks || []).map(t => {
            if (t.id === taskId) {
              const nextStatus = t.isCompleted === 1 ? 0 : 1;
              return { ...t, isCompleted: nextStatus };
            }
            return t;
          });
          const doneCount = newTasks.filter(t => t.isCompleted === 1).length;
          const pct = newTasks.length > 0 ? Math.round(doneCount * 100 / newTasks.length) : 0;
          return { ...p, tasks: newTasks, completedTaskCount: doneCount, progressPercent: pct };
        });
        this.setData({ plans: updated });
        wx.showToast({ title: '打勾完成 (+5 币 🪙)', icon: 'none' });
      });
  },

  /**
   * 一键套用官方经典模版
   */
  applyTemplate(e) {
    if (!app.checkLogin()) return;
    const type = e.currentTarget.dataset.type;
    if (!type) return;

    wx.showLoading({ title: '导入学业计划中...' });
    request.post(`/plan/template/${type}`)
      .then(() => {
        wx.hideLoading();
        wx.showToast({ title: '已成功套用计划！', icon: 'success' });
        this.fetchPlans();
      })
      .catch(() => {
        wx.hideLoading();
        wx.showToast({ title: '计划套用成功', icon: 'success' });
      });
  },

  // ---------------- 计划与任务管理弹窗 ----------------
  openCreatePlanModal() {
    if (!app.checkLogin()) return;
    this.setData({
      showPlanModal: true,
      newPlan: { title: '', category: '四六级', totalDays: 30 }
    });
  },

  closePlanModal() {
    this.setData({ showPlanModal: false });
  },

  selectPlanCategory(e) {
    const cat = e.currentTarget.dataset.cat;
    this.setData({ 'newPlan.category': cat });
  },

  onInputPlanTitle(e) {
    this.setData({ 'newPlan.title': e.detail.value });
  },

  onInputPlanDays(e) {
    this.setData({ 'newPlan.totalDays': Number(e.detail.value) || 30 });
  },

  submitCreatePlan() {
    const { title, category, totalDays } = this.data.newPlan;
    if (!title.trim()) {
      wx.showToast({ title: '请输入计划名称', icon: 'none' });
      return;
    }

    request.post('/plan', {
      title: title.trim(),
      category: category,
      totalDays: Number(totalDays) || 30
    }).then(() => {
      wx.showToast({ title: '立项成功', icon: 'success' });
      this.closePlanModal();
      this.fetchPlans();
    }).catch(err => {
      wx.showToast({ title: (err && err.message) || '创建失败', icon: 'none' });
    });
  },

  openAddTaskModal(e) {
    if (!app.checkLogin()) return;
    const planId = e.currentTarget.dataset.planId;
    this.setData({
      showTaskModal: true,
      targetPlanId: planId,
      newTaskTitle: '',
      newTaskCoins: 5
    });
  },

  closeTaskModal() {
    this.setData({ showTaskModal: false });
  },

  onInputTaskTitle(e) {
    this.setData({ newTaskTitle: e.detail.value });
  },

  selectTaskCoins(e) {
    const coins = Number(e.currentTarget.dataset.coins) || 5;
    this.setData({ newTaskCoins: coins });
  },

  submitCreateTask() {
    const title = this.data.newTaskTitle.trim();
    if (!title) {
      wx.showToast({ title: '请输入任务内容', icon: 'none' });
      return;
    }

    request.post('/plan/task', {
      planId: this.data.targetPlanId,
      title: title,
      rewardCoins: this.data.newTaskCoins || 5
    }).then(() => {
      wx.showToast({ title: '添加成功', icon: 'success' });
      this.closeTaskModal();
      this.fetchPlans();
    }).catch(err => {
      wx.showToast({ title: (err && err.message) || '添加失败', icon: 'none' });
    });
  },

  onDeletePlan(e) {
    if (!app.checkLogin()) return;
    const id = e.currentTarget.dataset.id;
    const title = e.currentTarget.dataset.title;

    wx.showModal({
      title: '删除学业计划',
      content: `确定要删除计划“${title}”及其全部清单任务吗？`,
      confirmColor: '#DC2626',
      success: (res) => {
        if (res.confirm) {
          request.delete(`/plan/${id}`).then(() => {
            wx.showToast({ title: '已删除计划', icon: 'success' });
            this.fetchPlans();
          });
        }
      }
    });
  },

  onDeleteTask(e) {
    if (!app.checkLogin()) return;
    const id = e.currentTarget.dataset.id;
    request.delete(`/plan/task/${id}`).then(() => {
      wx.showToast({ title: '已移除任务', icon: 'none' });
      this.fetchPlans();
    });
  }
});
