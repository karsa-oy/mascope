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

import ThePageLanding from "./components/ThePageLanding";
import ThePageBatchOverview from "./components/ThePageBatchOverview";
import ThePageDataManagement from "./components/ThePageDataManagement";
import ThePageSettings from "./components/ThePageSettings";

Vue.use(VueRouter);

const router = new VueRouter({
  mode: process.env.NODE_ENV == 'production' ? 'hash' : 'history',
  routes: [{
    path: '/',
    component: ThePageLanding
  }, {
    path: '/batch-overview',
    component: ThePageBatchOverview
  }, {
    path: '/data-management',
    component: ThePageDataManagement
  }, {
    path: '/settings',
    component: ThePageSettings
  }, {
    path: "*",
    redirect: '/'
  }]
});

// Directives 

import Cleave from "cleave.js";

Vue.directive('cleave', {
  bind(el, binding) {
    const input = el.querySelector("input");
    input._vCleave = new Cleave(input, binding.value);
  },
  unbind(el) {
    const input = el.querySelector("input");
    input._vCleave.destroy();
  },
});

// App

import App from './App'
import store from "./store"


new Vue({
  router,
  store,
  render: h => h(App),
}).$mount('#app');