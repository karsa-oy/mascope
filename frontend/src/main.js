import Vue from "vue";
import store from "./store";
import { api, apiLog } from "$api";

// API

Vue.prototype.$api = api;
apiLog("registered API with Vue prototype");

// Buefy framework

import Buefy from "buefy"; // components
import "buefy/dist/buefy.css"; // styles
import "@mdi/font/css/materialdesignicons.min.css"; // material design icons
import "./assets/css/bulmaswatch/superhero.css"; // bulmaswatch superhero theme

Vue.use(Buefy);
Vue.config.productionTip = false;

// Routes

import VueRouter from "vue-router";

import ThePageHome from "./components/ThePageHome.vue";
import ThePageBatchOverview from "./components/ThePageBatchOverview.vue";
//import ThePageSampleSignal from "./components/ThePageSampleSignal.vue";
import ThePageMzCalibration from "./components/ThePageMzCalibration.vue";
import ThePageSampleManagement from "./components/ThePageSampleManagement.vue";
//import ThePageSettings from "./components/ThePageSettings.vue";
import ThePageScenthound from "./components/ThePageScenthound.vue";

Vue.use(VueRouter);

const router = new VueRouter({
  mode: process.env.NODE_ENV == "production" ? "hash" : "history",
  routes: [
    {
      path: "/",
      component: ThePageHome,
    },
    {
      path: "/batch-overview",
      component: ThePageBatchOverview,
      //  }, {
      //    path: '/sample-signal',
      //    component: ThePageSampleSignal
    },
    {
      path: "/mz-calibration",
      component: ThePageMzCalibration,
    },
    {
      path: "/sample-management",
      component: ThePageSampleManagement,
      //  }, {
      //    path: '/settings',
      //    component: ThePageSettings
    },
    {
      path: "/scenthound",
      component: ThePageScenthound,
      //  }, {
      //    path: "*",
      //    redirect: '/'
    },
  ],
});

// App

import App from "./App.vue";

new Vue({
  router,
  store,
  render: (h) => h(App),
}).$mount("#app");
