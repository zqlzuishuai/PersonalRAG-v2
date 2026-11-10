import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '../views/LoginViews.vue'
import RegisterView from '../views/RegisterView.vue'
import LibraryView from '../views/LibraryView.vue'

import DocumentView from '../views/DocumentView.vue'
import TrashView from '../views/TrashView.vue'
import SearchView from '../views/SearchView.vue'

async function requireSession() {
  try {
    const response = await fetch('/api/auth/me')

    if (response.status === 200) return true
    if (response.status === 401) return { path: '/login' ,replace:true}
  } catch {

  }

  return { path: '/login', query: { reason: 'session-unavailable' }, replace: true }
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  scrollBehavior(to, from, savedPosition) {
    return savedPosition || (to.hash ? { el: to.hash } : { top: 0 })
  },
  routes: [
    {path:'/',redirect:'/login'},
    {path:'/login',component:LoginView},
    {path:'/register',component:RegisterView},
    { path: '/library', component: LibraryView, beforeEnter: requireSession },
    { path: '/search', component: SearchView, beforeEnter: requireSession },
    { path: '/trash', component: TrashView, beforeEnter: requireSession },
    { path: '/documents/:documentId', name: 'document', component: DocumentView, beforeEnter: requireSession },
  ],
})

export default router
