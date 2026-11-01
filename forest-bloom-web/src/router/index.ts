import { createRouter, createWebHashHistory } from 'vue-router'
import ToolFeaturePage from '../views/ToolFeaturePage.vue'

const router = createRouter({
  // GitHub Pages serves static files and does not rewrite deep URLs to index.html.
  // Hash history keeps nested tool routes refreshable without a 404 fallback page.
  history: createWebHashHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/diy/bead-pattern', name: 'bead-pattern', component: ToolFeaturePage },
  ],
})

export default router
