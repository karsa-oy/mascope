import { createRouter, createMemoryHistory } from 'vue-router'

import ThePageHome from './components/ThePageHome.vue'
import ThePageBatchOverview from './components/ThePageBatchOverview.vue'
import ThePageScenthound from './components/ThePageScenthound.vue'

export default createRouter({
  //mode: process.env.NODE_ENV == "production" ? "hash" : "history",
  history: createMemoryHistory(),
  routes: [
    {
      path: '/',
      component: ThePageHome,
    },
    {
      path: '/batch-overview',
      component: ThePageBatchOverview,
    },
    {
      path: '/scenthound',
      component: ThePageScenthound,
    },
  ],
})
