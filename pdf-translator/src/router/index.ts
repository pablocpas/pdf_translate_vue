import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('../components/MainLayout.vue'),
    children: [
      {
        path: '',
        name: 'upload',
        component: () => import('../components/UploadPDF.vue')
      },
      {
        path: '/result',
        name: 'result',
        component: () => import('../components/ResultPDF.vue')
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
