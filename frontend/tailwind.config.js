/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js}'],
  theme: {
    extend: {
      colors: {
        paper: '#F7F4EC',
        cream: '#FDFBF6',
        sand: '#EFEADF',
        ink: {
          DEFAULT: '#1F2A24',
          mid: '#5A665F',
          dim: '#98A29B'
        },
        pine: {
          DEFAULT: '#2E6B4F',
          deep: '#1F4D38',
          soft: '#E3EFE8',
          tint: '#F0F7F2'
        },
        amber: {
          warm: '#D9862A',
          soft: '#FBEEDD'
        },
        clay: '#C4553B',
        line: '#E4DFD2',
        'line-strong': '#D3CCBA'
      },
      fontFamily: {
        sans: ['"PingFang SC"', '"Microsoft YaHei"', '"Noto Sans SC"', '-apple-system', 'system-ui', 'sans-serif'],
        display: ['"Noto Serif SC"', '"Songti SC"', 'SimSun', 'serif']
      },
      boxShadow: {
        card: '0 1px 2px rgba(31, 42, 36, 0.04), 0 6px 20px rgba(31, 42, 36, 0.06)',
        'card-hover': '0 2px 4px rgba(31, 42, 36, 0.06), 0 14px 36px rgba(31, 42, 36, 0.12)',
        pop: '0 10px 40px rgba(31, 42, 36, 0.16)'
      },
      borderRadius: {
        xl2: '1.25rem'
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
