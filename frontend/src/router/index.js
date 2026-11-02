import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/HomeView.vue'),
    meta: { title: '首页' }
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { title: '登录', authLayout: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/RegisterView.vue'),
    meta: { title: '注册', authLayout: true }
  },
  {
    path: '/forgot-password',
    name: 'ForgotPassword',
    component: () => import('@/views/ForgotPasswordView.vue'),
    meta: { title: '找回密码', authLayout: true }
  },
  {
    path: '/project/:id',
    name: 'ProjectDetail',
    component: () => import('@/views/ProjectDetailView.vue'),
    meta: { title: '项目详情' }
  },
  {
    path: '/publish',
    name: 'Publish',
    component: () => import('@/views/PublishView.vue'),
    meta: { title: '发布项目', requiresAuth: true }
  },
  {
    path: '/project/:id/edit',
    name: 'ProjectEdit',
    component: () => import('@/views/ProjectEditView.vue'),
    meta: { title: '编辑项目', requiresAuth: true }
  },
  {
    path: '/user/:id',
    name: 'UserProfile',
    component: () => import('@/views/UserProfileView.vue'),
    meta: { title: '共创者主页' }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('@/views/ProfileView.vue'),
    meta: { title: '个人中心', requiresAuth: true }
  },
  {
    path: '/notifications',
    name: 'Notifications',
    component: () => import('@/views/NotificationsView.vue'),
    meta: { title: '通知', requiresAuth: true }
  },
  {
    // 管理台：只要求登录，管理员身份由后端 /api/admin/* 的 requireAdmin 判定。
    // 不在路由层读 isAdmin，是因为本地缓存的角色可能已经过期（刚被撤权），
    // 由页面根据 403 展示「需要管理员权限」，比静默重定向回首页更说得清。
    path: '/admin',
    name: 'Admin',
    component: () => import('@/views/AdminView.vue'),
    meta: { title: '管理台', requiresAuth: true }
  },
  {
    // 账号安全：两个只读视图（安全提醒 / 我的操作）。
    // 数据全部来自 /logs/me 与 /logs/me/security，两条接口都只认「当前登录用户」，
    // 所以这一页天然不存在「越权看别人」的可能，requiresAuth 即可。
    path: '/security',
    name: 'Security',
    component: () => import('@/views/SecurityView.vue'),
    meta: { title: '账号安全', requiresAuth: true }
  },
  {
    // 外观：明暗模式 + 主题色。纯前端偏好，存在 localStorage，游客也能进（页脚有入口）。
    path: '/appearance',
    name: 'Appearance',
    component: () => import('@/views/AppearanceView.vue'),
    meta: { title: '外观设置' }
  },
  {
    // 协议、隐私、管理条例与帮助：静态内容页，游客与登录用户都可访问。
    path: '/terms',
    name: 'Terms',
    component: () => import('@/views/TermsView.vue'),
    meta: { title: '用户协议' }
  },
  {
    path: '/privacy',
    name: 'Privacy',
    component: () => import('@/views/PrivacyView.vue'),
    meta: { title: '隐私政策' }
  },
  {
    path: '/community-rules',
    name: 'CommunityRules',
    component: () => import('@/views/CommunityRulesView.vue'),
    meta: { title: '平台管理条例' }
  },
  {
    path: '/help',
    name: 'Help',
    component: () => import('@/views/HelpView.vue'),
    meta: { title: '帮助中心' }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFoundView.vue'),
    meta: { title: '页面不存在' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    // 文档页有 #report / #contact 锚点：让浏览器滚到锚点，并留出吸顶页头的高度。
    if (to.hash) return { el: to.hash, top: 88 }
    return { top: 0 }
  }
})

router.beforeEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · 共创社区` : '共创社区'

  if (to.meta.requiresAuth && !localStorage.getItem('token')) {
    return { name: 'Login', query: { redirect: to.fullPath } }
  }
})

export default router
