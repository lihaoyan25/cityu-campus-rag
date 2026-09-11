import { createRouter, createWebHistory } from 'vue-router'
import { useAdminStore } from '../stores/admin'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: () => import('../views/HomeView.vue') },
    {
      path: '/admin',
      component: () => import('../views/admin/AdminLayout.vue'),
      redirect: '/admin/dashboard',
      children: [
        { path: 'dashboard', name: 'dashboard', component: () => import('../views/admin/Dashboard.vue') },
        { path: 'knowledge', name: 'knowledge', component: () => import('../views/admin/Knowledge.vue') },
        { path: 'prompts', name: 'prompts', component: () => import('../views/admin/Prompts.vue') },
        { path: 'model', name: 'model', component: () => import('../views/admin/ModelConfig.vue') },
      ],
    },
  ],
})

router.beforeEach((to) => {
  if (to.path.startsWith('/admin')) {
    const admin = useAdminStore()
    if (!admin.isLoggedIn) return { name: 'home' }
  }
})

export default router
