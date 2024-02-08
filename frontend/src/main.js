import Vue from "vue";
import store from "./store";
import { api, apiLog } from "$api";

// API

Vue.prototype.$api = api;
apiLog("registered API with Vue prototype");

// Buefy framework

import Buefy from "buefy"; // components
import "@mdi/font/css/materialdesignicons.min.css"; // material design icons

Vue.use(Buefy);
Vue.config.productionTip = false;

// Routes

import VueRouter from "vue-router";

import ThePageHome from "./components/ThePageHome.vue";
import ThePageBatchOverview from "./components/ThePageBatchOverview.vue";
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
    },
    {
      path: "/scenthound",
      component: ThePageScenthound,
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
