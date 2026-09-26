/** @type {import('tailwindcss').Config} */
// Apple HIG 风格设计令牌
// 页面底 #F5F5F7 / 卡片纯白 / 主文字 #1D1D1F / 强调蓝 #0071E3 / 分隔线 #D2D2D7
// token 名称保持不变（paper/ink/pine...），仅重映射取值，全站用法自动切换
export default {
  content: ['./index.html', './src/**/*.{vue,js}'],
  theme: {
    extend: {
      colors: {
        paper: '#F5F5F7',
        cream: '#FFFFFF',
        sand: '#E8E8ED',
        ink: {
          DEFAULT: '#1D1D1F',
          mid: '#6E6E73',
          dim: '#AEAEB2'
        },
        pine: {
          DEFAULT: '#0071E3',
          deep: '#0066CC',
          soft: '#E8F1FD',
          tint: '#F5F9FF'
        },
        amber: {
          warm: '#C93400',
          soft: '#FDF0E4'
        },
        clay: '#D70015',
        line: '#D2D2D7',
        'line-strong': '#A1A1A6'
      },
      fontFamily: {
        sans: [
          '-apple-system',
          'BlinkMacSystemFont',
          '"SF Pro Text"',
          '"Helvetica Neue"',
          '"PingFang SC"',
          '"Hiragino Sans GB"',
          '"Microsoft YaHei"',
          'sans-serif'
        ],
        // Apple 不使用衬线展示字体，display 统一走系统栈
        display: [
          '"SF Pro Display"',
          '-apple-system',
          'BlinkMacSystemFont',
          '"PingFang SC"',
          '"Microsoft YaHei"',
          'sans-serif'
        ]
      },
      boxShadow: {
        card: '0 2px 8px rgba(0, 0, 0, 0.04), 0 8px 24px rgba(0, 0, 0, 0.06)',
        'card-hover': '0 4px 12px rgba(0, 0, 0, 0.08), 0 16px 40px rgba(0, 0, 0, 0.12)',
        pop: '0 12px 40px rgba(0, 0, 0, 0.18)'
      },
      borderRadius: {
        xl2: '1.125rem'
      },
      keyframes: {
        'fade-up': {
          from: { opacity: '0', transform: 'translateY(16px)' },
          to: { opacity: '1', transform: 'translateY(0)' }
        },
        'toast-in': {
          from: { opacity: '0', transform: 'translateY(-10px) scale(0.98)' },
          to: { opacity: '1', transform: 'translateY(0) scale(1)' }
        },
        shimmer: {
          '0%': { backgroundPosition: '-400px 0' },
          '100%': { backgroundPosition: '400px 0' }
        }
      },
      animation: {
        'fade-up': 'fade-up 0.55s cubic-bezier(0.22, 1, 0.36, 1) both',
        'toast-in': 'toast-in 0.25s ease-out both',
        shimmer: 'shimmer 1.5s linear infinite'
      }
    }
  },
  plugins: []
}
