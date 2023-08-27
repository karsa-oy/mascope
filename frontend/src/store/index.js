import Vue from "vue";
import Vuex from "vuex";
import pathify from "vuex-pathify";

import logger from "./plugins/logger";
import api from "./plugins/api";

import app from "./modules/app";
import batch from "./modules/batch";
import calibration from "./modules/calibration";
import instrument from "./modules/instrument";
import key from "./modules/key";
import modal from "./modules/modal";
import sample from "./modules/sample";
import targets from "./modules/targets";
import visualization from "./modules/visualization";
import workspace from "./modules/workspace";

Vue.use(Vuex);

export default new Vuex.Store({
  modules: {
    app,
    batch,
    calibration,
    instrument,
    key,
    modal,
    sample,
    targets,
    visualization,
    workspace,
  },
  plugins: [
    // plugin order matters!
    logger, // logging first, so that next plugins log
    pathify.plugin, // pathify is a dependency of the api plugin
    api, // this last, so it has access to pathify
  ],
});
