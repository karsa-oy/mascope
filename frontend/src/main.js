import Vue from 'vue'

// Buefy framework

import Buefy from "buefy";  // components
import "buefy/dist/buefy.css"; // styles
import "@mdi/font/css/materialdesignicons.min.css"; // material design icons
import "./assets/css/bulmaswatch/superhero.css"; // bulmaswatch superhero theme

Vue.use(Buefy);
Vue.config.productionTip = false

// Routes

import VueRouter from 'vue-router';

import ThePageHome from "./components/ThePageHome.vue";
import ThePageBatchOverview from "./components/ThePageBatchOverview.vue";
import ThePageDataManagement from "./components/ThePageDataManagement.vue";
import ThePageSampleSignal from "./components/ThePageSampleSignal.vue";
import ThePageSampleManagement from "./components/ThePageSampleManagement.vue";
import ThePageMzCalibration from "./components/ThePageMzCalibration.vue";
import ThePageSettings from "./components/ThePageSettings.vue";

Vue.use(VueRouter);

const router = new VueRouter({
  mode: process.env.NODE_ENV == 'production' ? 'hash' : 'history',
  routes: [{
    path: '/',
    component: ThePageHome
  }, {
    path: '/batch-overview',
    component: ThePageBatchOverview
  }, {
    path: '/data-management',
    component: ThePageDataManagement
  }, {
    path: '/sample-signal',
    component: ThePageSampleSignal
  }, {
    path: '/sample-management',
    component: ThePageSampleManagement
  }, {
    path: '/mz-calibration',
    component: ThePageMzCalibration
  }, {
    path: '/settings',
    component: ThePageSettings
  }, {
    path: "*",
    redirect: '/'
  }]
});

// App

import App from './App.vue';
import store from './store';

new Vue({
  router,
  store,
  render: h => h(App),
}).$mount('#app');