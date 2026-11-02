# 共创社区 - 响应式设计测试指南

> 2026-11-02 校准：当前前端已按「赛博简约手绘 × Apple HIG」重塑，不再有 `Sidebar` / `ProjectGrid`
> 独立组件；分类、搜索、排序都收在 `HomeView` 内，项目网格也直接写在页面里。

## 断点与布局

项目使用 Tailwind 默认断点（`sm` 640 / `lg` 1024 / `xl` 1280），首页项目网格为：

| 视口宽度 | 网格列数 | Tailwind 类 |
| --- | --- | --- |
| < 640px | 1 列 | `grid-cols-1` |
| 640 - 1023px | 2 列 | `sm:grid-cols-2` |
| 1024 - 1279px | 3 列 | `lg:grid-cols-3` |
| ≥ 1280px | 4 列 | `xl:grid-cols-4` |

页面容器统一使用 `max-w-7xl` + `px-4 sm:px-6`；首页 Hero 为 `max-w-4xl`。

## 组件与页面

| 组件 / 页面 | 响应式要点 |
| --- | --- |
| `AppHeader` | 移动端收敛搜索框与账号菜单；导航栏固定 44pt 高 |
| `HomeView` | 分类 / 标签 chip 可换行；排序使用 `AppSegmented` 分段控件 |
| `ProjectCard` | 卡片随网格拉伸，封面比例固定 |
| `ProjectDetailView` | 桌面双栏、窄屏单栏；评论与共创者列表纵向堆叠 |
| `CommentSection` | 评论树缩进在窄屏收敛，输入区贴底 |
| `ProjectForm` / `CoverCropper` | 表单单列；裁剪器在窄屏适配高度 |
| `AppSheet` | 窄屏底部升起，桌面居中卡片 |
| `NotificationsView` | 筛选 chip 换行；批量操作条贴底 |

## 触控与可访问性

- 交互控件最小热区 44×44px，通过伪元素扩展，不改变视觉尺寸
- 全局 `touch-action: manipulation` 防双击缩放
- 小屏输入框字号 16px，避免 iOS 聚焦自动放大
- 支持 `prefers-reduced-motion`，页面转场与浮现动画可关闭
- 深浅色跟随系统（`prefers-color-scheme`），令牌见 `style.css` / `tailwind.config.js`

## 如何测试

1. 启动前端：`cd frontend && npm run dev`，访问 `http://localhost:3001`
2. Chrome DevTools → 设备工具栏，依次检查：
   - iPhone SE 375×667
   - iPhone 14 Pro Max 430×932
   - iPad 768×1024
   - iPad Pro 1024×1366
   - Desktop 1440×900 / 1920×1080
3. 重点检查：无横向滚动条、卡片不重叠、文字不截断、触控目标可点、深色模式无写死颜色

## 自动化验证

```bash
python scripts/verify_mobile_touch.py   # 44px 热区真实命中探测
python scripts/verify_dark_mode.py      # 令牌逐值比对 + 逐页 console / 溢出
python scripts/verify_view_all.py       # 页面整体渲染与溢出巡检
python scripts/audit_frontend_ui.py     # 全站前端巡检
```

⚠️ 验证脚本默认连接 `http://localhost:3001`，请确认该端口上真的是 Vite；
被其它进程占用时用 `VERIFY_FRONT_BASE` 覆盖。