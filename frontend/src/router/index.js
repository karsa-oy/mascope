import { createRouter, createMemoryHistory } from 'vue-router'

import ThePageHomeView from '@/views/ThePageHomeView.vue'
import ThePageBatchOverviewView from '@/views/ThePageBatchOverviewView.vue'
import ThePageScenthoundView from '@/views/ThePageScenthoundView.vue'

export default createRouter({
  //mode: process.env.NODE_ENV == "production" ? "hash" : "history",
  history: createMemoryHistory(),
  routes: [
    {
      path: '/',
      component: ThePageHomeView
    },
    {
      path: '/batch-overview',
      component: ThePageBatchOverviewView
    },
    {
      path: '/scenthound',
      component: ThePageScenthoundView
    }
  ]
})
