import { createRouter, createMemoryHistory } from 'vue-router'

import PageHome from './PageHome.vue'

export default createRouter({
  //mode: process.env.NODE_ENV == "production" ? "hash" : "history",
  history: createMemoryHistory(),
  routes: [
    {
      path: '/',
      component: PageHome
    }
  ]
})
