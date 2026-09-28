/** @type {import('tailwindcss').Config} */
// Apple HIG 风格设计令牌
// 页面底 #F5F5F7 / 卡片纯白 / 主文字 #1D1D1F / 强调蓝 #0071E3 / 分隔线 #D2D2D7
// token 名称保持不变（paper/ink/pine...），仅重映射取值，全站用法自动切换
export default {
  content: ['./index.html', './src/**/*.{vue,js}'],
  theme: {
    extend: {
      colors: {
        // 通过 CSS 变量取值（style.css :root / prefers-color-scheme: dark），
        // RGB 三元组 + <alpha-value> 保证 bg-ink/30 这类透明度修饰符可用
        paper: 'rgb(var(--c-paper) / <alpha-value>)',
        cream: 'rgb(var(--c-cream) / <alpha-value>)',
        sand: 'rgb(var(--c-sand) / <alpha-value>)',
        ink: {
          DEFAULT: 'rgb(var(--c-ink) / <alpha-value>)',
          mid: 'rgb(var(--c-ink-mid) / <alpha-value>)',
          dim: 'rgb(var(--c-ink-dim) / <alpha-value>)'
        },
        pine: {
          DEFAULT: 'rgb(var(--c-pine) / <alpha-value>)',
          deep: 'rgb(var(--c-pine-deep) / <alpha-value>)',
          soft: 'rgb(var(--c-pine-soft) / <alpha-value>)',
          tint: 'rgb(var(--c-pine-tint) / <alpha-value>)'
        },
        amber: {
          warm: 'rgb(var(--c-amber-warm) / <alpha-value>)',
          soft: 'rgb(var(--c-amber-soft) / <alpha-value>)'
        },
        clay: 'rgb(var(--c-clay) / <alpha-value>)',
        line: 'rgb(var(--c-line) / <alpha-value>)',
        'line-strong': 'rgb(var(--c-line-strong) / <alpha-value>)'
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
        // 提示卡：单层短距 + 一层长距柔化，模拟系统通知的悬浮感（不做硬投影）
        toast: '0 1px 2px rgba(0, 0, 0, 0.06), 0 12px 32px -6px rgba(0, 0, 0, 0.16)',
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
        shimmer: {
          '0%': { backgroundPosition: '-400px 0' },
          '100%': { backgroundPosition: '400px 0' }
        }
      },
      animation: {
        'fade-up': 'fade-up 0.55s cubic-bezier(0.22, 1, 0.36, 1) both',
        shimmer: 'shimmer 1.5s linear infinite'
      }
    }
  },
  plugins: []
}
