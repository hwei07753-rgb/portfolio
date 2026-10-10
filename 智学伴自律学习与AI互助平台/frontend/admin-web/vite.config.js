import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 智学伴后台管理页：Vite 构建配置
// 后端接口走 http://localhost:8080/api（CorsConfig 已允许全量跨域，无需代理）
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    open: false
  },
  build: {
    outDir: 'dist',
    chunkSizeWarningLimit: 1024
  }
})
