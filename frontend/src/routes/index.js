import { createRouter, createMemoryHistory } from 'vue-router'

import MainRoute from './MainRoute.vue'

export default createRouter({
  //mode: process.env.NODE_ENV == "production" ? "hash" : "history",
  history: createMemoryHistory(),
  routes: [
    {
      path: '/',
      component: MainRoute
    }
  ]
})
