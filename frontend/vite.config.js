import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const dirname = path.dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(dirname, 'src')
    }
  },
  server: {
    // 统一用 3001（ skills 与 scripts/_verify_common.py 的 FRONT 都是这个值）：
    // 3000 容易被本机其它 Vite 项目抢走，一旦自动递增到别的端口，
    // 11 个验证脚本会全部连不上（-scripts 报 connection refused）
    port: 3001,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      // 用户上传的封面由后端静态直出：不代理的话请求会落到 Vite 自己身上，
      // 拿到 index.html 的 HTML 而不是图片（历史上封面的 404 就是这么来的）
      '/uploads': {
        target: 'http://localhost:5000',
        changeOrigin: true
      }
    }
  }
})
