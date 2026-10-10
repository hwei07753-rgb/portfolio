const parseSafeDate = (input) => {
  if (!input) return null;
  if (input instanceof Date) return input;
  if (typeof input === 'string') {
    // 兼容 iOS WebKit：将 "2026-10-08 16:01:47" 转为 "2026/10/08 16:01:47"
    const normalized = input.replace(/-/g, '/');
    const d = new Date(normalized);
    if (!isNaN(d.getTime())) return d;
  }
  return new Date(input);
};

/**
 * 格式化日期时间: YYYY-MM-DD HH:mm:ss
 */
const formatTime = (date) => {
  const d = parseSafeDate(date);
  if (!d || isNaN(d.getTime())) return '';
  const year = d.getFullYear();
  const month = d.getMonth() + 1;
  const day = d.getDate();
  const hour = d.getHours();
  const minute = d.getMinutes();
  const second = d.getSeconds();

  return `${[year, month, day].map(formatNumber).join('-')} ${[hour, minute, second].map(formatNumber).join(':')}`;
};

/**
 * 格式化年月日: YYYY-MM-DD
 */
const formatDate = (date) => {
  const d = parseSafeDate(date);
  if (!d || isNaN(d.getTime())) return '';
  const year = d.getFullYear();
  const month = d.getMonth() + 1;
  const day = d.getDate();
  return `${[year, month, day].map(formatNumber).join('-')}`;
};

/**
 * 格式化秒数为分秒: MM:SS
 */
const formatDuration = (totalSeconds) => {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${formatNumber(minutes)}:${formatNumber(seconds)}`;
};

/**
 * 友好时间展示: 刚刚、x分钟前、x小时前、日期
 */
const formatRelativeTime = (timeStr) => {
  if (!timeStr) return '';
  const d = parseSafeDate(timeStr);
  if (!d || isNaN(d.getTime())) return '';
  const timestamp = d.getTime();
  const now = Date.now();
  const diff = (now - timestamp) / 1000;

  if (diff < 60) return '刚刚';
  if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`;
  if (diff < 86400 * 3) return `${Math.floor(diff / 86400)}天前`;
  return formatDate(timeStr);
};

const formatNumber = (n) => {
  n = n.toString();
  return n[1] ? n : `0${n}`;
};

module.exports = {
  formatTime,
  formatDate,
  formatDuration,
  formatRelativeTime
};
