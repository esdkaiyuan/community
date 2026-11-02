/** @type {import('tailwindcss').Config} */
// 赛博简约手绘 × Apple HIG 设计系统
//
// 视觉语言：暖纸面 + 墨线手绘框 + 电光青强调 + 等宽终端小标签。
// 结构层遵守 HIG（字号阶、8pt 栅格、44pt 触控、焦点环、减弱动态）；
// 表层用手写体标题、不对称圆角、错位墨线阴影表达「手绘」。
//
// 两层令牌，职责分开：
//   1) 材质层（paper/ink/pine…）：直接取 CSS 变量，取值被 scripts/ 下的验证脚本钉死
//      （verify_dark_mode.py 逐值比对手写常量），**改名或改值会撞红大量断言**，
//      因此这一层只增不删；新页面与主站对齐时直接使用它。
//   2) 语义层（label/separator/system-blue…）：兼容早期 HIG 命名的别名，
//      指向同一批变量，已有代码继续可用，不强制迁移。
//
// 排版沿用文本样式表（34/28/22/20/17/16/15/13/12/11），避免散落硬编码；
// 首页与分区主标题另用 `clamp()` 做手绘大字号。
export default {
  content: ['./index.html', './src/**/*.{vue,js}'],
  theme: {
    extend: {
      colors: {
        // ---- 材质层（存量，勿动）----
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
        green: 'rgb(var(--c-green) / <alpha-value>)',
        line: 'rgb(var(--c-line) / <alpha-value>)',
        'line-strong': 'rgb(var(--c-line-strong) / <alpha-value>)',

        // ---- 语义层（早期 HIG 命名的兼容别名）----
        // 文本色：label > secondary > tertiary > quaternary
        label: 'rgb(var(--c-ink) / <alpha-value>)',
        'label-2': 'rgb(var(--c-ink-mid) / <alpha-value>)',
        'label-3': 'rgb(var(--c-ink-dim) / <alpha-value>)',
        separator: 'rgb(var(--c-line) / <alpha-value>)',
        'separator-opaque': 'rgb(var(--c-line-strong) / <alpha-value>)',
        // 背景：系统底 / 卡片面
        'sys-bg': 'rgb(var(--c-paper) / <alpha-value>)',
        'sys-surface': 'rgb(var(--c-cream) / <alpha-value>)',
        // 灰阶填充（芯片 / 按钮的灰底）
        'sys-fill': 'rgb(var(--c-sand) / <alpha-value>)',
        // 系统色：与 iOS 同名同值
        'system-blue': 'rgb(var(--c-pine) / <alpha-value>)',
        'system-blue-deep': 'rgb(var(--c-pine-deep) / <alpha-value>)',
        'system-red': 'rgb(var(--c-clay) / <alpha-value>)',
        'system-green': 'rgb(var(--c-green) / <alpha-value>)',
        'system-orange': 'rgb(var(--c-amber-warm) / <alpha-value>)',
        // 玻璃材质面层
        'glass-nav': 'var(--glass-nav)',
        'glass-card': 'var(--glass-card)',
        'glass-menu': 'var(--glass-menu)'
      },

      // ---- HIG 文本样式 ----
      // 只给 size + lineHeight + letterSpacing，字重留给 font-* 显式声明，
      // 避免「text-title1 自带 bold」与 font-medium 抢优先级。
      fontSize: {
        largetitle: ['2.125rem', { lineHeight: '2.5rem', letterSpacing: '-0.022em' }], // 34/40
        title1: ['1.75rem', { lineHeight: '2.125rem', letterSpacing: '-0.019em' }], // 28/34
        title2: ['1.375rem', { lineHeight: '1.75rem', letterSpacing: '-0.016em' }], // 22/28
        title3: ['1.25rem', { lineHeight: '1.5rem', letterSpacing: '-0.014em' }], // 20/24
        headline: ['1.0625rem', { lineHeight: '1.375rem', letterSpacing: '-0.012em' }], // 17/22
        body: ['1.0625rem', { lineHeight: '1.5rem', letterSpacing: '-0.012em' }], // 17/24
        callout: ['1rem', { lineHeight: '1.375rem', letterSpacing: '-0.01em' }], // 16/22
        subhead: ['0.9375rem', { lineHeight: '1.3125rem', letterSpacing: '-0.009em' }], // 15/21
        footnote: ['0.8125rem', { lineHeight: '1.125rem', letterSpacing: '-0.008em' }], // 13/18
        caption1: ['0.75rem', { lineHeight: '1rem', letterSpacing: '0' }], // 12/16
        caption2: ['0.6875rem', { lineHeight: '0.875rem', letterSpacing: '0.004em' }] // 11/14
      },

      // ---- 8pt 栅格补充档位 ----
      spacing: {
        13: '3.25rem', // 52
        18: '4.5rem', // 72
        22: '5.5rem', // 88
        30: '7.5rem' // 120
      },

      // ---- 圆角：卡片 20 / 小卡 16 / 大面板 28；手绘层再叠加不对称值 ----
      borderRadius: {
        xl2: '1.25rem',
        10: '0.625rem',
        14: '1rem',
        18: '1.25rem',
        22: '1.75rem'
      },

      maxWidth: {
        site: '1600px'
      },

      fontFamily: {
        sans: [
          '-apple-system',
          'BlinkMacSystemFont',
          '"SF Pro Text"',
          '"Helvetica Neue"',
          '"PingFang SC"',
          '"Hiragino Sans GB"',
          '"Noto Sans SC"',
          '"Microsoft YaHei"',
          'sans-serif'
        ],
        // 品牌 / 标题字：霞鹜文楷（手写楷体骨架），离线时退回系统楷体
        brand: [
          '"LXGW WenKai"',
          '"Kaiti SC"',
          '"STKaiti"',
          'KaiTi',
          '"Songti SC"',
          'serif'
        ],
        // 展示标题仍走系统无衬线，靠字重与紧字距撑住大字号
        display: [
          '"SF Pro Display"',
          '-apple-system',
          'BlinkMacSystemFont',
          '"PingFang SC"',
          '"Noto Sans SC"',
          '"Microsoft YaHei"',
          'sans-serif'
        ]
      },

      boxShadow: {
        // 手绘错位投影：硬边、微微偏右下，像纸稿叠了一层墨线
        card: '2px 3px 0 rgb(var(--c-ink) / 0.05)',
        'card-hover': '4px 6px 0 rgb(var(--c-ink) / 0.09)',
        toast: '0 1px 2px rgba(0, 0, 0, 0.06), 0 14px 38px -8px rgba(0, 0, 0, 0.18)',
        pop: '5px 7px 0 rgb(var(--c-ink) / 0.1)',
        // 悬浮层：菜单 / 分段控件的浅阴影，比 pop 更贴边更淡
        hig: '0 0 0 0.5px rgba(0, 0, 0, 0.04), 0 10px 30px -8px rgba(0, 0, 0, 0.14)'
      },

      // ---- 动效曲线（沿用原 HIG 命名，出场快起慢收）----
      transitionTimingFunction: {
        'hig-out': 'cubic-bezier(0.22, 1, 0.36, 1)', // 出场：快起慢收
        'hig-in-out': 'cubic-bezier(0.4, 0, 0.2, 1)', // 进出场：系统默认
        'hig-spring': 'cubic-bezier(0.34, 1.56, 0.64, 1)' // 回弹：点赞 / 收藏
      },
      transitionDuration: {
        150: '150ms',
        250: '250ms',
        350: '350ms',
        450: '450ms'
      },

      keyframes: {
        'fade-up': {
          from: { opacity: '0', transform: 'translateY(16px)' },
          to: { opacity: '1', transform: 'translateY(0)' }
        },
        shimmer: {
          '0%': { backgroundPosition: '-400px 0' },
          '100%': { backgroundPosition: '400px 0' }
        },
        // Sheet：从底部升起（iOS 模态表单）
        'sheet-up': {
          from: { transform: 'translateY(100%)' },
          to: { transform: 'translateY(0)' }
        }
      },
      animation: {
        'fade-up': 'fade-up 0.55s cubic-bezier(0.22, 1, 0.36, 1) both',
        shimmer: 'shimmer 1.5s linear infinite',
        'sheet-up': 'sheet-up 0.35s cubic-bezier(0.22, 1, 0.36, 1)'
      }
    }
  },
  plugins: []
}
