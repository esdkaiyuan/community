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
    meta: { title: '登录' }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/RegisterView.vue'),
    meta: { title: '注册' }
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
    // 账号安全：两个只读视图（安全提醒 / 我的操作）。
    // 数据全部来自 /logs/me 与 /logs/me/security，两条接口都只认「当前登录用户」，
    // 所以这一页天然不存在「越权看别人」的可能，requiresAuth 即可。
    path: '/security',
    name: 'Security',
    component: () => import('@/views/SecurityView.vue'),
    meta: { title: '账号安全', requiresAuth: true }
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
    return savedPosition || { top: 0 }
  }
})

router.beforeEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · 共创社区` : '共创社区'

  if (to.meta.requiresAuth && !localStorage.getItem('token')) {
    return { name: 'Login', query: { redirect: to.fullPath } }
  }
})

export default router
