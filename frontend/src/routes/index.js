import { createRouter, createWebHistory } from 'vue-router'

import MainRoute from './MainRoute.vue'
import TestRoute from './TestRoute.vue'

export default createRouter({
  //mode: process.env.NODE_ENV == "production" ? "hash" : "history",
  history: createWebHistory(),
  routes: [
    {
      path: '/test',
      component: TestRoute
    },
    {
      path: '/',
      component: MainRoute
    }
  ]
})
