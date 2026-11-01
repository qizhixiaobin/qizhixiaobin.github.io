import { createRouter, createWebHistory } from 'vue-router'
import ToolFeaturePage from '../views/ToolFeaturePage.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/diy/bead-pattern', name: 'bead-pattern', component: ToolFeaturePage },
  ],
})

export default router
