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
      }
    }
  }
})
