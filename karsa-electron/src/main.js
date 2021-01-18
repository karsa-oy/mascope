import Vue from 'vue'
import App from './App.vue'
import VueRouter from 'vue-router'; 
import MainUi from './components/MainUI.vue'; 
import SplashWindow from './components/SplashWindow'; 
import ServiceStatus from './components/ServiceStatus.vue'; 


  Vue.config.productionTip = false
  Vue.use(VueRouter); 

  const routes = [{
      path: '/',
      component: MainUi
    },
    {
      path: '/splash-window',
      component: SplashWindow
    },
    {
      path: '/service-status',
      component: ServiceStatus
    },
    {
      path: "*", 
      redirect: '/'
    } 
  ];

  const router = new VueRouter({
    mode: process.env.NODE_ENV=='production' ? 'hash' : 'history',
    routes
  }); 


  Vue.use(VueRouter);
  new Vue({
    router,
    render: h => h(App),
  }).$mount('#app');