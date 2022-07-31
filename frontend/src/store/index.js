import Vue from 'vue'
import Vuex from 'vuex'
import pathify from 'vuex-pathify'

import logger from "./plugins/logger";
import api from "./plugins/api";

import app from './modules/app';
import workspace from './modules/workspace';
import batch from './modules/batch';
import key from './modules/key';
import modal from './modules/modal';

Vue.use(Vuex)

export default new Vuex.Store({
	modules: {
		app,
		workspace,
		batch,
		key,
		modal
	},
	plugins: [ // plugin order matters!
		logger, // logging first, so that next plugins log
		pathify.plugin, // pathify is a dependency of the api plugin
		api, // this last, so it has access to pathify
	]
});